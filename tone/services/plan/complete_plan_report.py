import itertools
import logging
from tone.celery import app
from tone.models import PlanInstance, PlanInstanceTestRelation, TestJob, ReportTemplate, Project, \
    ReportObjectRelation, datetime, ReportTmplItem, ReportTmplItemSuite, PlanInstanceStageRelation

from tone.services.job.result_compare_services import CompareListService, CompareEnvInfoService
from tone.views.api.get_domain_group import get_domain_group

logger = logging.getLogger('plan_create_report')


@app.task
def plan_create_report(plan_inst_id):  # noqa: C901
    plan_instance = PlanInstance.objects.filter(id=plan_inst_id).first()
    if plan_instance is not None and plan_instance.auto_report:
        # 获取报告分组方式 和 基准组
        if plan_instance.group_method == 'job':
            handle_job_group(plan_instance, plan_inst_id)
        else:
            # 按阶段对job进行分组, 几个阶段对应几个对比组
            handler_stage_group(plan_instance, plan_inst_id)


def handler_stage_group(plan_instance, plan_inst_id):  # noqa: C901
    from tone.services.job.result_compare_services import CompareSuiteInfoService
    from tone.services.report.report_services import ReportService
    base_stage_id = plan_instance.base_group

    stage_job_map = {}
    stage_index_map = {tmp_relation.id: tmp_relation.stage_index for tmp_relation in
                       PlanInstanceStageRelation.objects.filter(plan_instance_id=plan_inst_id,
                                                                stage_type='test_stage')}
    func_base_li = []
    perf_base_li = []
    func_compare_job_li = []
    perf_compare_job_li = []
    for test_relation in PlanInstanceTestRelation.objects.filter(plan_instance_id=plan_inst_id):
        stage_id = stage_index_map.get(test_relation.instance_stage_id)
        if not stage_id:
            continue
        tmp_job_obj = TestJob.objects.filter(id=test_relation.job_id).first()
        if not tmp_job_obj:
            continue
        if stage_id not in stage_job_map:
            if test_relation.job_id:
                stage_job_map[stage_id] = {'func': [], 'perf': []}
                if tmp_job_obj.test_type == 'functional':
                    stage_job_map[stage_id]['func'] = [test_relation.job_id]
                    if stage_id == base_stage_id:
                        func_base_li.append(test_relation.job_id)
                    else:
                        func_compare_job_li.append(test_relation.job_id)
                elif tmp_job_obj.test_type == 'performance':
                    stage_job_map[stage_id]['perf'] = [test_relation.job_id]
                    if stage_id == base_stage_id:
                        perf_base_li.append(test_relation.job_id)
                    else:
                        perf_compare_job_li.append(test_relation.job_id)
        else:
            if test_relation.job_id:
                if tmp_job_obj.test_type == 'functional':
                    stage_job_map[stage_id]['func'].append(test_relation.job_id)
                    if stage_id == base_stage_id:
                        func_base_li.append(test_relation.job_id)
                    else:
                        func_compare_job_li.append(test_relation.job_id)
                elif tmp_job_obj.test_type == 'performance':
                    stage_job_map[stage_id]['perf'].append(test_relation.job_id)
                    if stage_id == base_stage_id:
                        perf_base_li.append(test_relation.job_id)
                    else:
                        perf_compare_job_li.append(test_relation.job_id)

    func_base_obj_li = [{'is_job': 1, 'obj_id': tmp_job}
                        for tmp_job in stage_job_map.get(base_stage_id, {}).get('func', [])]
    perf_base_obj_li = [{'is_job': 1, 'obj_id': tmp_job}
                        for tmp_job in stage_job_map.get(base_stage_id, {}).get('perf', [])]
    group_num = len(stage_job_map)
    func_compare_groups = [[{'is_job': 1, 'obj_id': tmp_job} for tmp_job in stage_job_map.get(
        tmp_stage, {}).get('func', [])] for tmp_stage in stage_job_map if tmp_stage != base_stage_id]
    perf_compare_groups = [[{'is_job': 1, 'obj_id': tmp_job} for tmp_job in stage_job_map.get(
        tmp_stage, {}).get('perf', [])] for tmp_stage in stage_job_map if tmp_stage != base_stage_id]
    func_comp_num = len(func_compare_groups)
    perf_comp_num = len(perf_compare_groups)
    comp_num = group_num - 1
    [func_compare_groups.append([]) for _ in range(comp_num - func_comp_num)]
    [perf_compare_groups.append([]) for _ in range(comp_num - perf_comp_num)]
    data = {
        'func_data': {'base_obj_li': func_base_obj_li,
                      'compare_groups': func_compare_groups
                      },
        'group_num': group_num,
        'perf_data': {'base_obj_li': perf_base_obj_li,
                      'compare_groups': perf_compare_groups}
    }

    compare_suite_data = CompareSuiteInfoService().filter(data)
    func_suite_data = {suite_id: list(suite_data.get('conf_dic', {}).keys())
                       for suite_id, suite_data in compare_suite_data.get('func_suite_dic', {}).items()}
    perf_suite_data = {suite_id: list(suite_data.get('conf_dic', {}).keys())
                       for suite_id, suite_data in compare_suite_data.get('perf_suite_dic', {}).items()}
    conf_set = set()
    for case_list in func_suite_data.values():
        conf_set.update(set(case_list))
    for case_list in perf_suite_data.values():
        conf_set.update(set(case_list))
    conf_list = list(conf_set)
    origin_func_suite = compare_suite_data.get('func_suite_dic')
    origin_perf_suite = compare_suite_data.get('perf_suite_dic')

    get_compare_date(origin_func_suite)
    get_compare_date(origin_perf_suite)
    compare_list_data = CompareListService().filter(compare_suite_data)
    func_data_result = compare_list_data.get('func_data_result')
    func_data_result = {} if not func_data_result else func_data_result
    perf_data_result = compare_list_data.get('perf_data_result')
    perf_data_result = {} if not perf_data_result else perf_data_result

    # compare info
    base_objs = []
    for tmp_job in stage_job_map.get(base_stage_id, {}).get('func', []):
        base_objs.append({
            'is_job': 1,
            'obj_id': tmp_job,
            'suite_data': func_suite_data
        })
    for tmp_job in stage_job_map.get(base_stage_id, {}).get('perf', []):
        base_objs.append({
            'is_job': 1,
            'obj_id': tmp_job,
            'suite_data': perf_suite_data
        })
    project_id = plan_instance.project_id
    product_version = None
    if project_id:
        product_version = Project.objects.filter(id=project_id, query_scope='all').first().product_version
    product_version = product_version if product_version else 'default_version'
    tag_name = product_version if product_version else '对比标识'
    base_group = {
        'base_objs': base_objs,
        'tag': f'{tag_name}(1)'
    }
    compare_groups = []
    start_idx = 2
    for tmp_stage in stage_job_map:
        if tmp_stage == base_stage_id:
            continue
        func_compare_job = stage_job_map.get(tmp_stage, {}).get('func', [])
        perf_compare_job = stage_job_map.get(tmp_stage, {}).get('perf', [])
        tmp_base_objs = []
        for func_job, perf_job in itertools.zip_longest(func_compare_job, perf_compare_job):
            if func_job:
                tmp_base_objs.append({
                    'is_job': 1,
                    'obj_id': func_job,
                    'suite_data': func_suite_data
                })
            if perf_job:
                tmp_base_objs.append({
                    'is_job': 1,
                    'obj_id': perf_job,
                    'suite_data': perf_suite_data
                })
        compare_groups.append(
            {
                'base_objs': tmp_base_objs,
                'tag': f'{tag_name}({start_idx})'
            }
        )
        start_idx += 1

    test_env = CompareEnvInfoService().get_env_info(base_group, compare_groups)

    # 模板名称
    ws_id = plan_instance.ws_id
    job_li = test_env.get('job_li')

    report_source = 'plan'
    default_tmpl_id = ReportTemplate.objects.filter(ws_id=ws_id, name='默认模板', query_scope='all').first().id
    name = plan_instance.report_name
    before_name = name if name else '{plan_name}_report-{report_seq_id}'
    tmpl_id = plan_instance.report_tmpl_id if plan_instance.report_tmpl_id else default_tmpl_id
    description = plan_instance.report_description
    # # 将conf 根据 domain_group 分组
    domain_group = get_domain_group(conf_list)

    func_group = domain_group.get('functional')
    perf_group = domain_group.get('performance')
    job_data = {}
    if tmpl_id == default_tmpl_id:
        func_data = get_func_item(func_group, func_data_result, job_data)
        perf_data = get_perf_item(perf_group, perf_data_result, job_data)
    else:
        # report_template_obj = ReportTemplate.objects.filter(id=tmpl_id, query_scope='all').first()
        # 模板关联的测试项以及suite
        item_suite_map = {}
        [item_suite_map.update({report_template_item.name: list(
            ReportTmplItemSuite.objects.filter(
                report_tmpl_item_id=report_template_item.id).values_list('test_suite_id', flat=True))})
            for report_template_item in ReportTmplItem.objects.filter(tmpl_id=tmpl_id, test_type='functional')]
        func_data = get_func_item(item_suite_map, func_data_result, job_data, custom=True)
        [item_suite_map.update({report_template_item.name: list(
            ReportTmplItemSuite.objects.filter(
                report_tmpl_item_id=report_template_item.id).values_list('test_suite_id', flat=True))})
            for report_template_item in ReportTmplItem.objects.filter(tmpl_id=tmpl_id, test_type='performance')]
        perf_data = get_perf_item(item_suite_map, perf_data_result, job_data, custom=True)

    custom = '-'
    test_background = '-'
    test_method = '-'
    # 测试结论
    func_base_all = 0
    func_base_fail = 0
    func_base_success = 0

    for func_base_job in func_base_li:
        func_base_all += job_data.get(func_base_job, {}).get('all', 0)
        func_base_fail += job_data.get(func_base_job, {}).get('fail', 0)
        func_base_success += job_data.get(func_base_job, {}).get('success', 0)
    compare_groups = []
    idx = 2
    for stage_id in stage_job_map:
        if stage_id == base_stage_id:
            continue
        tmp_func_all = 0
        tmp_func_fail = 0
        tmp_func_success = 0
        tmp_perf_all = 0
        tmp_perf_decline = 0
        tmp_perf_increase = 0
        for tmp_job in stage_job_map.get(stage_id, {}).get('func', []):
            tmp_func_all += job_data.get(tmp_job, {}).get('all', 0)
            tmp_func_fail += job_data.get(tmp_job, {}).get('fail', 0)
            tmp_func_success += job_data.get(tmp_job, {}).get('success', 0)
        for tmp_job in stage_job_map.get(stage_id, {}).get('perf', []):
            tmp_perf_all += job_data.get(tmp_job, {}).get('all', 0)
            tmp_perf_decline += job_data.get(tmp_job, {}).get('decline', 0)
            tmp_perf_increase += job_data.get(tmp_job, {}).get('increase', 0)

        compare_groups.append({
            'tag': f'{tag_name}({idx})',
            'is_job': 1,
            'func_data': {
                'all': tmp_func_all,
                'fail': tmp_func_fail,
                'success': tmp_func_success,
            },
            'perf_data': {
                'all': tmp_perf_all,
                'decline': tmp_perf_decline,
                'increase': tmp_perf_increase
            }
        })
        idx += 1

    test_conclusion = {
        'custom': custom,
        'summary': {
            'base_group': {
                'all': func_base_all,
                'all_case': 0,
                'fail': func_base_fail,
                'fail_case': 0,
                'is_job': 1,
                'success': func_base_success,
                'success_case': 0,
                'tag': f'{tag_name}(1)',
            },
            'compare_groups': compare_groups
        }
    }
    test_item = {
        'func_data': func_data,
        'perf_data': perf_data
    }
    data = {
        'job_li': job_li,
        'name': before_name,
        'product_version': product_version,
        'project_id': project_id,
        'report_source': report_source,
        'test_conclusion': test_conclusion,
        'test_env': test_env,
        'test_item': test_item,
        'tmpl_id': tmpl_id,
        'ws_id': ws_id,
        'test_background': test_background,
        'test_method': test_method,
        'description': description,
    }
    operator = plan_instance.creator
    report = ReportService().create(data, operator)
    report_id = report.id
    report.name = before_name.format(date=datetime.strftime(report.gmt_created, "%Y-%m-%d %H:%M:%S"),
                                     plan_name=plan_instance.name, plan_id=str(plan_instance.plan_id),
                                     report_id=report_id, product_version=product_version,
                                     report_seq_id=report_id + 1)
    report.save()
    plan_id = plan_instance.plan_id
    ReportObjectRelation.objects.create(object_type='plan_instance', object_id=plan_inst_id, report_id=report_id)
    ReportObjectRelation.objects.create(object_type='plan_', object_id=plan_id, report_id=report_id)


def handle_job_group(plan_instance, plan_inst_id):  # noqa: C901
    from tone.services.job.result_compare_services import CompareSuiteInfoService
    from tone.services.report.report_services import ReportService
    base_tmpl_id = plan_instance.base_group
    stage_id = plan_instance.stage_id
    stage_instance = PlanInstanceStageRelation.objects.filter(plan_instance_id=plan_inst_id, stage_type='test_stage',
                                                              stage_index=stage_id).first()
    if not stage_instance:
        return
    plan_instance_test = PlanInstanceTestRelation.objects.filter(
        plan_instance_id=plan_inst_id, tmpl_id=base_tmpl_id, instance_stage_id=stage_instance.id).first()
    if not plan_instance_test:
        return
    base_job_id = plan_instance_test.job_id
    base_job_obj = TestJob.objects.filter(id=base_job_id).first()
    if not base_job_obj:
        return
    job_list = PlanInstanceTestRelation.objects.filter(
        plan_instance_id=plan_inst_id).values_list('job_id', flat=True)
    job_list = list(job_list)
    job_list.sort()
    func_job_list = [job for job in job_list if TestJob.objects.filter(id=job, test_type='functional')]
    perf_job_list = [job for job in job_list if TestJob.objects.filter(id=job, test_type='performance')]
    # 按job个数进行分组对比
    group_num = max(len(func_job_list), len(perf_job_list))
    func_base_job = None if not func_job_list else func_job_list[0]
    perf_base_job = None if not perf_job_list else perf_job_list[0]
    func_compare_job = func_job_list[1:]
    perf_compare_job = perf_job_list[1:]
    if base_job_obj is not None:
        test_type = base_job_obj.test_type
        if test_type == 'functional' and base_job_id in func_job_list:
            func_base_job = base_job_id
            func_compare_job = [job_id for job_id in func_job_list if job_id != base_job_id]
        else:
            perf_base_job = base_job_id
            perf_compare_job = [job_id for job_id in perf_job_list if job_id != base_job_id]
    func_base_obj_li = [] if not func_job_list else [{'is_job': 1, 'obj_id': func_base_job}]
    perf_base_obj_li = [] if not perf_job_list else [{'is_job': 1, 'obj_id': perf_base_job}]
    # 对比suite
    func_compare_groups = [[{'is_job': 1, 'obj_id': job_id}] for job_id in func_compare_job]
    perf_compare_groups = [[{'is_job': 1, 'obj_id': job_id}] for job_id in perf_compare_job]
    func_comp_num = len(func_compare_groups)
    perf_comp_num = len(perf_compare_groups)
    comp_num = group_num - 1
    [func_compare_groups.append([]) for _ in range(comp_num - func_comp_num)]
    [perf_compare_groups.append([]) for _ in range(comp_num - perf_comp_num)]
    data = {
        'func_data': {'base_obj_li': func_base_obj_li,
                      'compare_groups': func_compare_groups
                      },
        'group_num': group_num,
        'perf_data': {'base_obj_li': perf_base_obj_li,
                      'compare_groups': perf_compare_groups}
    }

    compare_suite_data = CompareSuiteInfoService().filter(data)

    func_suite_data = {suite_id: list(suite_data.get('conf_dic', {}).keys())
                       for suite_id, suite_data in compare_suite_data.get('func_suite_dic', {}).items()}
    perf_suite_data = {suite_id: list(suite_data.get('conf_dic', {}).keys())
                       for suite_id, suite_data in compare_suite_data.get('perf_suite_dic', {}).items()}

    conf_set = set()
    for case_list in func_suite_data.values():
        conf_set.update(set(case_list))
    for case_list in perf_suite_data.values():
        conf_set.update(set(case_list))
    conf_list = list(conf_set)
    origin_func_suite = compare_suite_data.get('func_suite_dic')
    origin_perf_suite = compare_suite_data.get('perf_suite_dic')
    get_compare_date(origin_func_suite)
    get_compare_date(origin_perf_suite)
    compare_list_data = CompareListService().filter(compare_suite_data)
    func_data_result = compare_list_data.get('func_data_result')
    func_data_result = {} if not func_data_result else func_data_result
    perf_data_result = compare_list_data.get('perf_data_result')
    perf_data_result = {} if not perf_data_result else perf_data_result

    # compare info
    base_objs = []
    if func_job_list:
        base_objs.append({
            'is_job': 1,
            'obj_id': func_base_job,
            'suite_data': func_suite_data
        })
    if perf_job_list:
        base_objs.append({
            'is_job': 1,
            'obj_id': perf_base_job,
            'suite_data': perf_suite_data
        })
    project_id = plan_instance.project_id
    product_version = None
    if project_id:
        product_version = Project.objects.filter(id=project_id, query_scope='all').first().product_version
    product_version = product_version if product_version else 'default_version'
    tag_name = product_version if product_version else '对比标识'
    base_group = {
        'base_objs': base_objs,
        'tag': f'{tag_name}(1)'
    }
    compare_groups = []
    start_idx = 2
    for func_job, perf_job in itertools.zip_longest(func_compare_job, perf_compare_job):
        tmp_base_objs = []
        if func_job:
            tmp_base_objs.append({
                'is_job': 1,
                'obj_id': func_job,
                'suite_data': func_suite_data
            })
        if perf_job:
            tmp_base_objs.append({
                'is_job': 1,
                'obj_id': perf_job,
                'suite_data': perf_suite_data
            })
        compare_groups.append(
            {
                'base_objs': tmp_base_objs,
                'tag': f'{tag_name}({start_idx})'
            }
        )
        start_idx += 1
    test_env = CompareEnvInfoService().get_env_info(base_group, compare_groups)
    # 模板名称
    ws_id = plan_instance.ws_id
    job_li = func_job_list
    report_source = 'plan'
    default_tmpl_id = ReportTemplate.objects.filter(ws_id=ws_id, name='默认模板', query_scope='all').first().id
    name = plan_instance.report_name
    before_name = name if name else '{plan_name}_report-{report_seq_id}'
    tmpl_id = plan_instance.report_tmpl_id if plan_instance.report_tmpl_id else default_tmpl_id
    description = plan_instance.report_description
    # 将conf 根据 domain_group 分组
    domain_group = get_domain_group(conf_list)
    func_group = domain_group.get('functional')
    perf_group = domain_group.get('performance')
    job_data = {}
    if tmpl_id == default_tmpl_id:
        func_data = get_func_item(func_group, func_data_result, job_data)
        perf_data = get_perf_item(perf_group, perf_data_result, job_data)
    else:
        # report_template_obj = ReportTemplate.objects.filter(id=tmpl_id, query_scope='all').first()
        # 模板关联的测试项以及suite
        item_suite_map = {}
        [item_suite_map.update({report_template_item.name: list(
            ReportTmplItemSuite.objects.filter(
                report_tmpl_item_id=report_template_item.id).values_list('test_suite_id', flat=True))})
            for report_template_item in ReportTmplItem.objects.filter(tmpl_id=tmpl_id, test_type='functional')]
        func_data = get_func_item(item_suite_map, func_data_result, job_data, custom=True)
        [item_suite_map.update({report_template_item.name: list(
            ReportTmplItemSuite.objects.filter(
                report_tmpl_item_id=report_template_item.id).values_list('test_suite_id', flat=True))})
            for report_template_item in ReportTmplItem.objects.filter(tmpl_id=tmpl_id, test_type='performance')]
        perf_data = get_perf_item(item_suite_map, perf_data_result, job_data, custom=True)

    custom = '-'
    test_background = '-'
    test_method = '-'
    # 测试结论
    test_conclusion = {
        'custom': custom,
        'summary': {
            'base_group': {
                'all': 0 if not func_job_list else job_data[func_base_job].get('all', 0),
                'all_case': 0,
                'fail': 0 if not func_job_list else job_data[func_base_job].get('fail', 0),
                'fail_case': 0,
                'is_job': 1,
                'success': 0 if not func_job_list else job_data[func_base_job].get('success', 0),
                'success_case': 0,
                'tag': f'{tag_name}(1)',
            },
            'compare_groups': [
                {
                    'tag': f'{tag_name}({idx})',
                    'is_job': 1,
                    'func_data': {
                        'all': job_data.get(job_ids[0], {}).get('all', 0),
                        'fail': job_data.get(job_ids[0], {}).get('fail', 0),
                        'success': job_data.get(job_ids[0], {}).get('success', 0),
                    },
                    'perf_data': {
                        'all': job_data.get(job_ids[1], {}).get('all', 0),
                        'decline': job_data.get(job_ids[1], {}).get('decline', 0),
                        'increase': job_data.get(job_ids[1], {}).get('increase', 0),
                    },
                } for idx, job_ids in enumerate(
                    itertools.zip_longest(func_compare_job, perf_compare_job, fillvalue=0), start=2)
            ],
        }
    }
    test_item = {
        'func_data': func_data,
        'perf_data': perf_data
    }
    data = {
        'job_li': job_li,
        'name': before_name,
        'product_version': product_version,
        'project_id': project_id,
        'report_source': report_source,
        'test_conclusion': test_conclusion,
        'test_env': test_env,
        'test_item': test_item,
        'tmpl_id': tmpl_id,
        'ws_id': ws_id,
        'test_background': test_background,
        'test_method': test_method,
        'description': description,
    }
    operator = plan_instance.creator
    report = ReportService().create(data, operator)
    report_id = report.id
    report.name = before_name.format(date=datetime.strftime(report.gmt_created, "%Y-%m-%d %H:%M:%S"),
                                     plan_name=plan_instance.name, plan_id=str(plan_instance.plan_id),
                                     report_id=report_id, product_version=product_version,
                                     report_seq_id=report_id + 1)
    report.save()
    plan_id = plan_instance.plan_id
    ReportObjectRelation.objects.create(object_type='plan_instance', object_id=plan_inst_id, report_id=report_id)
    ReportObjectRelation.objects.create(object_type='plan_', object_id=plan_id, report_id=report_id)


def get_compare_date(origin_func_suite):
    for origin_suite in origin_func_suite:
        origin_suite_data = origin_func_suite[origin_suite]
        origin_conf_dic = origin_suite_data.get('conf_dic', {})
        for origin_conf in origin_conf_dic:
            origin_conf_data = origin_conf_dic.get(origin_conf)
            base_obj = origin_conf_data.get('base_obj_li', [])[0]
            compare_objs = []
            for compare_group in origin_conf_data.get('compare_groups', []):
                if not compare_group:
                    compare_objs.append({})
                    continue
                compare_objs.append({
                    'is_job': 1,
                    'obj_id': compare_group[0].get('obj_id')
                })

            origin_suite_data['conf_dic'][origin_conf] = {
                'compare_objs': compare_objs,
                'conf_name': origin_conf_data.get('conf_name'),
                'is_job': 1,
                'obj_id': base_obj.get('obj_id'),
            }


def get_perf_item(perf_group, perf_data_result, job_data, custom=False):
    perf_data = []
    for tmp_group, group_info in perf_group.items():
        tmp_suite_list = []
        tmp_suite_id_list = group_info if custom else list(group_info.keys())
        for tmp_suite_info in perf_data_result:
            suite_id = tmp_suite_info.get('suite_id')
            if suite_id in tmp_suite_id_list:
                suite_name = tmp_suite_info.get('suite_name')
                conf_list = tmp_suite_info.get('conf_list')
                compare_count = tmp_suite_info.get('compare_count')
                tmp_conf_list = []
                for tmp_conf_info in conf_list:
                    conf_id = tmp_conf_info.get('conf_id')
                    conf_name = tmp_conf_info.get('conf_name')
                    conf_source = {
                        'obj_id': tmp_conf_info.get('obj_id'),
                        'is_job': 1,
                    }
                    if not job_data.get(tmp_conf_info.get('obj_id')):
                        job_data[tmp_conf_info.get('obj_id')] = {
                            'increase': 0,
                            'decline': 0,
                            'all': 0,
                        }
                    compare_conf_list = tmp_conf_info.get('conf_compare_data')
                    comp_jobs = [compare_data.get('obj_id') for compare_data in compare_conf_list]
                    metric_list = tmp_conf_info.get('metric_list')
                    for tmp_job, tmp_count_data in zip(comp_jobs, compare_count):
                        if not job_data.get(tmp_job):
                            job_data[tmp_job] = {
                                'increase': 0,
                                'decline': 0,
                                'all': 0,
                            }
                        job_data[tmp_job]['increase'] += tmp_count_data.get('increase', 0)
                        job_data[tmp_job]['decline'] += tmp_count_data.get('decline', 0)
                        job_data[tmp_job]['all'] += tmp_count_data.get('all', 0)

                    tmp_conf_list.append({
                        'conf_id': conf_id,
                        'conf_name': conf_name,
                        'conf_source': conf_source,
                        'compare_conf_list': compare_conf_list,
                        'metric_list': metric_list,
                    })
                tmp_suite_list.append({
                    'suite_id': suite_id,
                    'suite_name': suite_name,
                    'show_type': 0,
                    'test_conclusion': '-',
                    'test_description': '-',
                    'test_env': '-',
                    'test_suite_description': '-',
                    'conf_list': tmp_conf_list
                })
        perf_data.append({
            'name': tmp_group,
            'suite_list': tmp_suite_list
        })
    return perf_data


def get_func_item(func_group, func_data_result, job_data, custom=False):
    func_data = []
    for tmp_group, group_info in func_group.items():
        tmp_suite_list = []
        tmp_suite_id_list = group_info if custom else list(group_info.keys())
        for tmp_suite_info in func_data_result:
            suite_id = tmp_suite_info.get('suite_id')
            if suite_id in tmp_suite_id_list:
                suite_name = tmp_suite_info.get('suite_name')
                conf_list = tmp_suite_info.get('conf_list')
                tmp_conf_list = []
                for tmp_conf_info in conf_list:
                    conf_id = tmp_conf_info.get('conf_id')
                    conf_name = tmp_conf_info.get('conf_name')
                    conf_source = {
                        'all_case': tmp_conf_info.get('all_case', 0),
                        'fail_case': tmp_conf_info.get('fail_case', 0),
                        'warn_case': tmp_conf_info.get('warn_case', 0),
                        'obj_id': tmp_conf_info.get('obj_id'),
                        'success_case': tmp_conf_info.get('success_case', 0),
                        'is_job': 1,
                    }
                    if job_data.get(tmp_conf_info.get('obj_id')):
                        job_data[tmp_conf_info.get('obj_id')]['success'] += \
                            int(tmp_conf_info.get('success_case', 0))
                        job_data[tmp_conf_info.get('obj_id')]['fail'] += \
                            int(tmp_conf_info.get('fail_case', 0))
                        job_data[tmp_conf_info.get('obj_id')]['warn'] += \
                            int(tmp_conf_info.get('warn_case', 0))
                        job_data[tmp_conf_info.get('obj_id')]['all'] += \
                            int(tmp_conf_info.get('all_case', 0))
                    else:
                        job_data[tmp_conf_info.get('obj_id')] = {
                            'success': int(tmp_conf_info.get('success_case', 0)),
                            'fail': int(tmp_conf_info.get('fail_case', 0)),
                            'warn': int(tmp_conf_info.get('warn_case', 0)),
                            'all': int(tmp_conf_info.get('all_case', 0)),
                        }
                    compare_conf_list = tmp_conf_info.get('conf_compare_data')
                    for compare_conf_data in compare_conf_list:
                        if job_data.get(compare_conf_data.get('obj_id')):
                            job_data[compare_conf_data.get('obj_id')]['success'] += \
                                int(compare_conf_data.get('success_case', 0))
                            job_data[compare_conf_data.get('obj_id')]['fail'] += \
                                int(compare_conf_data.get('fail_case', 0))
                            job_data[compare_conf_data.get('obj_id')]['warn'] += \
                                int(compare_conf_data.get('warn_case', 0))
                            job_data[compare_conf_data.get('obj_id')]['all'] += \
                                int(compare_conf_data.get('all_case', 0))
                        else:
                            job_data[compare_conf_data.get('obj_id')] = {
                                'success': int(compare_conf_data.get('success_case', 0)),
                                'fail': int(compare_conf_data.get('fail_case', 0)),
                                'warn': int(compare_conf_data.get('warn_case', 0)),
                                'all': int(compare_conf_data.get('all_case', 0)),
                            }
                    sub_case_list = tmp_conf_info.get('sub_case_list')
                    tmp_conf_list.append({
                        'conf_id': conf_id,
                        'conf_name': conf_name,
                        'conf_source': conf_source,
                        'compare_conf_list': compare_conf_list,
                        'sub_case_list': sub_case_list,
                    })
                tmp_suite_list.append({
                    'suite_id': suite_id,
                    'suite_name': suite_name,
                    'conf_list': tmp_conf_list
                })
        func_data.append({
            'name': tmp_group,
            'suite_list': tmp_suite_list
        })
    return func_data
