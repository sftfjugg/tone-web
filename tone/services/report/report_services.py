# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author:
"""
import json

from django.db.models import Q
from django.db import transaction

from tone.core.utils.permission_manage import check_operator_permission
from tone.models import Report, ReportItem, ReportItemConf, ReportItemMetric, ReportItemSubCase, ReportObjectRelation, \
    ReportItemSuite, TestJobCase, TestServerSnapshot, CloudServerSnapshot, PlanInstance, PlanInstanceTestRelation, \
    PerfResult, FuncResult, TestMetric, ReportDetail, FuncBaselineDetail, PerfBaselineDetail
from tone.core.common.job_result_helper import get_compare_result, get_func_compare_data
from tone.core.handle.report_handle import save_report_detail, get_old_report, get_group_server_info
from tone.core.common.services import CommonService
from tone.models.report.test_report import ReportTemplate, ReportTmplItem, ReportTmplItemSuite
from tone.services.plan.plan_services import random_choice_str
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import ReportException
from tone.core.utils.date_util import DateUtil
from tone.core.common.constant import FUNC_CASE_RESULT_TYPE_MAP


class ReportTemplateService(CommonService):
    @staticmethod
    def filter(queryset, data):
        """过滤报告模板"""
        q = Q()
        q &= Q(id=data.get('id')) if data.get('id') else q
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        q &= Q(name__icontains=data.get('name')) if data.get('name') else q
        q &= Q(creator__in=data.get('creator').split(',')) if data.get('creator') else q
        q &= Q(update_user__in=data.get('update_user').split(',')) if data.get('update_user') else q
        ordering = 'FIELD(`name`, "默认模板")'
        education_last = queryset.filter(q).extra(select={'ordering': ordering}, order_by=('-ordering', '-id'))
        return education_last

    def create_report_template(self, data, operator):
        create_data = dict()
        name = data.get('name', '')
        ws_id = data.get('ws_id')
        if ReportTemplate.objects.filter(name=name, ws_id=ws_id).exists():
            return False, '报告模板名称已存在'

        update_fields = ['ws_id', 'name', 'description', 'need_test_background', 'need_test_method',
                         'need_test_summary', 'need_test_conclusion', 'need_test_env', 'need_func_data',
                         'need_env_description', 'need_perf_data', 'background_desc', 'test_method_desc',
                         'test_summary_desc', 'test_conclusion_desc', 'test_env_desc', 'env_description_desc']

        for write_field in update_fields:
            create_data[write_field] = data.get(write_field)

        create_data.update({'creator': operator})
        report_template_obj = ReportTemplate.objects.create(**create_data)
        self.create_report_tmpl_item(data, report_template_obj.id)

        return True, report_template_obj

    def create_report_tmpl_item(self, data, report_tmpl_id):
        self.create_template_item(data, report_tmpl_id, 'functional')
        self.create_template_item(data, report_tmpl_id, 'performance')

    def get_group_item_name(self, group_data, item_name=''):
        if group_data.get('group_name'):
            item_name = '{}:{}'.format(item_name, group_data.get('group_name'))
            return self.get_group_item_name(group_data.get('group_data'), item_name)
        else:
            item_name = '{}:{}'.format(item_name, group_data.get('item_name'))
            return item_name, group_data.get('item_suite_list')

    @staticmethod
    def create_default_template(ws_id):
        ReportTemplate.objects.create(name='默认模板',
                                      is_default=True,
                                      ws_id=ws_id,
                                      need_test_background=True,
                                      need_test_method=True,
                                      need_test_summary=True,
                                      need_test_conclusion=True,
                                      need_test_env=True,
                                      need_env_description=True,
                                      need_func_data=True,
                                      need_perf_data=True,
                                      description='系统默认报告模板',
                                      creator=0
                                      )

    @staticmethod
    def adapt_font_data(origin_item_list):
        def pack_item_name(item_list, item_name=''):
            for init_item in item_list:
                new_name = init_item.get('name') if not item_name else '{}:{}'.format(item_name, init_item.get('name'))
                if not init_item.get('is_group'):
                    result[new_name] = init_item.get('list')
                    continue
                pack_item_name(init_item.get('list'), new_name)

        result = dict()
        pack_item_name(origin_item_list)
        return [{'name': item_name, 'suite_list': suite_list} for item_name, suite_list in result.items()]

    def create_template_item(self, data, report_tmpl_id, test_type):
        param_map = {
            'functional': ('func_item', 'func_conf'),
            'performance': ('perf_item', 'perf_conf'),
        }
        template_item = data.get(param_map.get(test_type)[0], list())
        config_data = data.get(param_map.get(test_type)[1], {})
        need_test_suite_description = config_data.get('need_test_suite_description', False)
        need_test_env = config_data.get('need_test_env', False)
        need_test_description = config_data.get('need_test_description', False)
        need_test_conclusion = config_data.get('need_test_conclusion', False)
        show_type = config_data.get('show_type', 'list')
        test_env_desc = config_data.get('test_env_desc', '')
        test_description_desc = config_data.get('test_description_desc', '')
        test_conclusion_desc = config_data.get('test_conclusion_desc', '')
        template_item = self.adapt_font_data(template_item)
        for tmp_item in template_item:
            tmpl_item_obj = ReportTmplItem.objects.create(name=tmp_item.get('name'),
                                                          tmpl_id=report_tmpl_id,
                                                          test_type=test_type)
            item_suite_list = tmp_item.get('suite_list')
            for item_suite_data in item_suite_list:
                conf_id_list = [suite_data.get('test_conf_id') for suite_data in item_suite_data.get('case_source')]
                ReportTmplItemSuite.objects.create(report_tmpl_item_id=tmpl_item_obj.id,
                                                   test_suite_id=item_suite_data.get('test_suite_id'),
                                                   test_suite_show_name=item_suite_data.get('suite_show_name'),
                                                   test_conf_list=conf_id_list,
                                                   show_type=show_type,
                                                   need_test_suite_description=need_test_suite_description,
                                                   need_test_env=need_test_env,
                                                   need_test_description=need_test_description,
                                                   need_test_conclusion=need_test_conclusion,
                                                   test_env_desc=test_env_desc,
                                                   test_description_desc=test_description_desc,
                                                   test_conclusion_desc=test_conclusion_desc
                                                   )

    @staticmethod
    def check_report_template(report_template_id):
        report_template_queryset = ReportTemplate.objects.filter(id=report_template_id)
        if report_template_queryset.first() is None:
            return False, None
        else:
            return True, report_template_queryset

    def update_report_template(self, data, operator):
        report_template_id = data.get('id')
        ws_id = data.get('ws_id')
        success, report_template_queryset = self.check_report_template(report_template_id)
        if not success:
            return False, '报告模板id不存在'
        report_template = report_template_queryset.first()
        if report_template.is_default:
            return False, '默认模板不允许修改'
        if not check_operator_permission(operator, report_template):
            return False, ''
        if report_template.name != data.get('name') and ReportTemplate.objects.filter(name=data.get('name'),
                                                                                      ws_id=ws_id).exists():
            return False, '报告模板名称不能重复'
        update_data = dict()
        allow_update_fields = ['name', 'description', 'need_test_background', 'need_test_method',
                               'need_test_summary', 'need_test_conclusion', 'need_test_env', 'need_env_description',
                               'need_func_data', 'need_perf_data', 'background_desc', 'test_method_desc',
                               'test_summary_desc', 'test_conclusion_desc', 'test_env_desc', 'env_description_desc']
        for update_field in allow_update_fields:
            update_data[update_field] = data.get(update_field)

        update_data.update({'update_user': operator})
        with transaction.atomic():
            report_template_queryset.update(**update_data)

            item_queryset = ReportTmplItem.objects.filter(tmpl_id=report_template_id)
            item_id_list = item_queryset.values_list('id')
            item_queryset.delete()
            ReportTmplItemSuite.objects.filter(report_tmpl_item_id__in=item_id_list).delete()
            self.create_report_tmpl_item(data, report_template_id)
        return True, report_template

    def delete_report_template(self, data, operator):
        report_template_id = data.get('id')
        success, report_template_queryset = self.check_report_template(report_template_id)
        if not success:
            return False, '报告模板id不存在'
        report_template = report_template_queryset.first()
        if report_template.is_default:
            return False, '默认模板不允许删除'
        if not check_operator_permission(operator, report_template):
            return False, ''
        with transaction.atomic():
            report_template_queryset.delete()
            item_queryset = ReportTmplItem.objects.filter(tmpl_id=report_template_id)
            item_id_list = item_queryset.values_list('id')
            item_queryset.delete()
            ReportTmplItemSuite.objects.filter(report_tmpl_item_id__in=item_id_list).delete()
        return True, ''

    def copy_report_template(self, data, operator):
        report_template_id = data.get('id')
        success, report_template_queryset = self.check_report_template(report_template_id)
        if not success:
            return False, '报告模板id不存在'
        report_template = report_template_queryset.first()
        if ReportTemplate.objects.filter(name=data.get('name', ''), ws_id=data.get('ws_id')).exists():
            return False, '报告模板名称不能重复'
        report_template.id = None
        if data.get('name'):
            report_template.name = data.get('name')
        else:
            if '-copy-' in report_template.name:
                report_template.name = '{}-copy-{}'.format(report_template.name.split('-copy-')[0], random_choice_str())
            else:
                report_template.name = '{}-copy-{}'.format(report_template.name, random_choice_str())
        if data.get('description'):
            report_template.description = data.get('description')
        report_template.creator = operator
        report_template.update_user = None
        if report_template.is_default:
            report_template.is_default = False
        report_template.save()
        new_report_template_id = report_template.id
        self.copy_template_relation(report_template_id, new_report_template_id)

        return True, report_template

    @staticmethod
    def copy_template_relation(report_template_id, new_report_template_id):
        for tmp_item in ReportTmplItem.objects.filter(tmpl_id=report_template_id):
            origin_item_id = tmp_item.id
            tmp_item.id = None
            tmp_item.tmpl_id = new_report_template_id
            tmp_item.save()
            new_item_id = tmp_item.id
            for tmp_item_suite in ReportTmplItemSuite.objects.filter(report_tmpl_item_id=origin_item_id):
                tmp_item_suite.id = None
                tmp_item_suite.report_tmpl_item_id = new_item_id
                tmp_item_suite.save()


class ReportService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(id=data.get('report_id')) if data.get('report_id') else q
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        q &= Q(name__icontains=data.get('name')) if data.get('name') else q
        q &= Q(product_version=data.get('product_version')) if data.get('product_version') else q
        q &= Q(tmpl_id=data.get('tmpl_id')) if data.get('tmpl_id') else q
        q &= Q(creator__in=[int(i) for i in data.getlist('creator')]) if data.getlist('creator') else q
        q &= Q(project_id__in=[int(i) for i in data.getlist('project_id')]) if data.getlist('project_id') else q
        if data.get('gmt_modified'):
            time_data = json.loads(data.get('gmt_modified'))
            start_time = DateUtil.str_to_datetime(time_data.get('start_time'))
            end_time = DateUtil.str_to_datetime(time_data.get('end_time'))
            q &= Q(gmt_created__range=(start_time, end_time))
        return queryset.filter(q)

    def create(self, data, operator):
        if not operator:
            raise ReportException(ErrorCode.LOGIN_ERROR)
        name = data.get('name')
        product_version = data.get('product_version', '')
        project_id = data.get('project_id')
        test_background = data.get('test_background')
        test_method = data.get('test_method')
        test_conclusion = data.get('test_conclusion', dict())
        report_source = data.get('report_source')
        test_env = data.get('test_env', dict())
        env_description = data.get('env_description', '')
        description = data.get('description')
        tmpl_id = data.get('tmpl_id')
        test_item = data.get('test_item')
        creator = operator
        ws_id = data.get('ws_id')
        job_li = data.get('job_li', list())
        plan_li = data.get('plan_li', list())
        assert name, ReportException(ErrorCode.NAME_NEED)
        assert ws_id, ReportException(ErrorCode.WS_NEED)
        # assert product_version, ReportException(ErrorCode.PRODUCT_VERSION_DUPLICATION)
        # assert project_id, ReportException(ErrorCode.PROJECT_ID_NEED)
        assert report_source, ReportException(ErrorCode.REPORT_SOURCE_NEED)
        assert test_env, ReportException(ErrorCode.TEST_ENV_NEED)
        assert tmpl_id, ReportException(ErrorCode.TEMPLATE_NEED)
        assert test_item, ReportException(ErrorCode.TEST_ITEM_NEED)
        base_index = test_env.get('base_index', 0)
        server_info = get_group_server_info(test_env['base_group'], test_env['compare_groups'])
        test_env['base_group'] = server_info['base_group']
        test_env['compare_groups'] = server_info['compare_groups']
        test_env['count'] = len(test_env['base_group']['base_objs'])
        with transaction.atomic():
            report = Report.objects.create(name=name, product_version=product_version, project_id=project_id,
                                           ws_id=ws_id, test_method=test_method, test_conclusion=test_conclusion,
                                           report_source=report_source, test_env=test_env, description=description,
                                           tmpl_id=tmpl_id, creator=creator, test_background=test_background,
                                           env_description=env_description)
            [ReportObjectRelation.objects.create(object_type='job', object_id=job_id, report_id=report.id) for job_id in
             job_li]
            [ReportObjectRelation.objects.create(object_type='plan', object_id=plan_id, report_id=report.id) for plan_id
             in plan_li]
            report_id = report.id
            perf_data = test_item.get('perf_data', list())
            func_data = test_item.get('func_data', list())
            self.save_test_item_v1(perf_data, report_id, 'performance', base_index)
            self.save_test_item_v1(func_data, report_id, 'functional', base_index)
        save_report_detail(report_id, base_index, get_old_report(report), report.is_automatic)
        return report

    def save_test_item_v1(self, data, report_id, test_type, base_index):
        for item in data:
            name = item.get('name')
            suite_list = item.get('suite_list', list())
            assert name, ReportException(ErrorCode.ITEM_NAME_NEED)
            report_item = ReportItem.objects.filter(report_id=report_id, test_type=test_type).first()
            if not report_item:
                report_item = ReportItem.objects.create(name=name, report_id=report_id, test_type=test_type)
            report_item_id = report_item.id
            for suite in suite_list:
                self.save_item_suite_v1(suite, report_item_id, test_type, base_index)

    def save_item_suite_v1(self, suite, report_item_id, test_type, base_index):
        test_suite_id = suite.get('suite_id')
        test_suite_name = suite.get('suite_name')
        show_type = suite.get('show_type', 0)
        conf_list = suite.get('conf_list', list())
        assert test_suite_id, ReportException(ErrorCode.TEST_SUITE_NEED)
        assert test_suite_name, ReportException(ErrorCode.TEST_SUITE_NAME_NEED)
        item_suite = ReportItemSuite.objects.filter(report_item_id=report_item_id, test_suite_id=test_suite_id).first()
        if not item_suite:
            item_suite = ReportItemSuite.objects.create(report_item_id=report_item_id, test_suite_id=test_suite_id,
                                                        test_suite_name=test_suite_name, show_type=show_type)
        item_suite_id = item_suite.id
        for conf in conf_list:
            self.save_item_conf_v1(conf, item_suite_id, test_suite_id, test_type, base_index)

    def save_item_conf_v1(self, conf, item_suite_id, test_suite_id, test_type, base_index):
        test_conf_id = conf.get('conf_id')
        test_conf_name = conf.get('conf_name')
        compare_conf_list = list()
        conf_source = dict()
        job_index = 0
        for compare_job in conf.get('job_list'):
            if test_type == 'functional':
                if compare_job.get('is_baseline', 0):
                    func_results = FuncBaselineDetail.objects. \
                        filter(baseline_id=compare_job.get('job_id'), test_suite_id=test_suite_id,
                               test_case_id=test_conf_id)
                    compare_count = dict({
                        'is_job': 0,
                        'all_case': func_results.count(),
                        'obj_id': compare_job.get('job_id'),
                        'success_case': 0,
                        'fail_case': func_results.count(),
                    })
                else:
                    func_results = FuncResult.objects. \
                        filter(test_job_id=compare_job.get('job_id'), test_suite_id=test_suite_id,
                               test_case_id=test_conf_id)
                    compare_count = dict({
                        'is_job': 1,
                        'all_case': func_results.count(),
                        'obj_id': compare_job.get('job_id'),
                        'success_case': func_results.filter(sub_case_result=1).count(),
                        'fail_case': func_results.filter(sub_case_result=2).count(),
                    })
            else:
                compare_count = dict({
                    'is_job': 0 if compare_job.get('is_baseline', 0) else 1,
                    'obj_id': compare_job.get('job_id'),
                })
            if job_index == base_index:
                conf_source = compare_count
            else:
                compare_conf_list.append(compare_count)
            job_index += 1
        compare_conf_list.insert(base_index, conf_source)
        item_conf = ReportItemConf.objects.filter(report_item_suite_id=item_suite_id, test_conf_id=test_conf_id).first()
        if not item_conf:
            item_conf = ReportItemConf.objects.create(report_item_suite_id=item_suite_id, test_conf_id=test_conf_id,
                                                      test_conf_name=test_conf_name, conf_source=conf_source,
                                                      compare_conf_list=compare_conf_list)
        item_conf_id = item_conf.id
        if test_type == 'functional':
            self.save_item_sub_case_v1(test_suite_id, test_conf_id, item_conf_id, conf.get('job_list'), base_index)
        else:
            self.save_item_metric_v1(test_suite_id, test_conf_id, item_conf_id, conf.get('job_list'), base_index)

    @staticmethod
    def save_item_sub_case_v1(test_suite_id, test_conf_id, item_conf_id, job_list, base_index):
        base_job_id = job_list.pop(base_index)
        base_is_baseline = base_job_id.get('is_baseline', 0)
        if base_is_baseline:
            func_results = FuncBaselineDetail.objects. \
                filter(baseline_id=base_job_id.get('job_id'), test_suite_id=test_suite_id, test_case_id=test_conf_id). \
                values_list('sub_case_name', flat=True)
        else:
            func_results = FuncResult.objects. \
                filter(test_job_id=base_job_id.get('job_id'), test_suite_id=test_suite_id, test_case_id=test_conf_id). \
                values_list('sub_case_name', 'sub_case_result')
        item_sub_case_list = list()
        for func_result in func_results:
            compare_data = get_func_compare_data(test_suite_id, test_conf_id, func_result[0], job_list)
            if base_is_baseline:
                func_case_result = FUNC_CASE_RESULT_TYPE_MAP.get(2)
                func_case_name = func_result
            else:
                func_case_name = func_result[0]
                func_case_result = FUNC_CASE_RESULT_TYPE_MAP.get(func_result[1])
            compare_data.insert(base_index, func_case_result)
            report_sub_case = ReportItemSubCase(
                report_item_conf_id=item_conf_id,
                sub_case_name=func_case_name,
                result=func_case_result,
                compare_data=compare_data)
            item_sub_case_list.append(report_sub_case)
        ReportItemSubCase.objects.filter(report_item_conf_id=item_conf_id).delete()
        ReportItemSubCase.objects.bulk_create(item_sub_case_list)

    @staticmethod
    def save_item_metric_v1(test_suite_id, test_conf_id, item_conf_id, job_list, base_index):
        base_job_id = job_list.pop(base_index)
        base_is_baseline = base_job_id.get('is_baseline', 0)
        job_id = base_job_id.get('job_id')
        if base_is_baseline:
            perf_results = PerfBaselineDetail.objects.filter(baseline_id=job_id, test_suite_id=test_suite_id,
                                                             test_case_id=test_conf_id)
        else:
            perf_results = PerfResult.objects.filter(test_job_id=job_id, test_suite_id=test_suite_id,
                                                     test_case_id=test_conf_id)
        item_metric_list = list()
        job_id_list = [job.get('job_id') for job in job_list if job.get('is_baseline', 0) == 0]
        base_id_list = [job.get('job_id') for job in job_list if job.get('is_baseline', 0) == 1]
        for perf_result in perf_results:
            compare_data_list = list()
            if TestMetric.objects.filter(name=perf_result.metric, object_type='case', object_id=test_conf_id).exists():
                test_metric = TestMetric.objects.get(name=perf_result.metric, object_type='case',
                                                     object_id=test_conf_id)
            elif TestMetric.objects.filter(name=perf_result.metric, object_type='suite',
                                           object_id=test_suite_id).exists():
                test_metric = TestMetric.objects.get(name=perf_result.metric, object_type='suite',
                                                     object_id=test_suite_id)
            else:
                continue
            test_value = round(float(perf_result.test_value), 2)
            if len(job_id_list) > 0:
                compare_data = PerfResult.objects. \
                    filter(test_job_id__in=job_id_list, metric=perf_result.metric, test_suite_id=test_suite_id,
                           test_case_id=test_conf_id).distinct()
                for job_id in job_id_list:
                    compare_metric = compare_data.filter(test_job_id=job_id).first()
                    if compare_metric:
                        value = round(float(compare_metric.test_value), 2)
                        cv_value = compare_metric.cv_value.split('±')[-1]
                        compare_value, compare_result = get_compare_result(test_value, value, test_metric.direction,
                                                                           test_metric.cmp_threshold, cv_value,
                                                                           test_metric.cv_threshold)
                        compare = dict({
                            'test_value': round(float(compare_metric.test_value), 2),
                            'cv_value': compare_metric.cv_value.split('±')[-1],
                            'max_value': compare_metric.max_value,
                            'min_value': compare_metric.min_value,
                            'compare_value': compare_value,
                            'compare_result': compare_result,
                            'value_list': compare_metric.value_list
                        })
                        compare_data_list.append(compare)
                    else:
                        compare_data_list.append(dict())
            if len(base_id_list) > 0:
                compare_data = PerfBaselineDetail.objects. \
                    filter(baseline_id__in=base_id_list, metric=perf_result.metric, test_suite_id=test_suite_id,
                           test_case_id=test_conf_id).distinct()
                for job_id in base_id_list:
                    compare_metric = compare_data.filter(baseline_id=job_id).first()
                    if compare_metric:
                        value = round(float(compare_metric.test_value), 2)
                        cv_value = compare_metric.cv_value.split('±')[-1]
                        compare_value, compare_result = get_compare_result(test_value, value, test_metric.direction,
                                                                           test_metric.cmp_threshold, cv_value,
                                                                           test_metric.cv_threshold)
                        compare = dict({
                            'test_value': round(float(compare_metric.test_value), 2),
                            'cv_value': compare_metric.cv_value.split('±')[-1],
                            'max_value': compare_metric.max_value,
                            'min_value': compare_metric.min_value,
                            'compare_value': compare_value,
                            'compare_result': compare_result,
                            'value_list': compare_metric.value_list
                        })
                        compare_data_list.append(compare)
                    else:
                        compare_data_list.append(dict())
            report_metric = ReportItemMetric(
                report_item_conf_id=item_conf_id,
                test_metric=perf_result.metric,
                test_value=perf_result.test_value,
                cv_value=perf_result.cv_value,
                unit=perf_result.unit,
                max_value=perf_result.max_value,
                min_value=perf_result.min_value,
                value_list=perf_result.value_list,
                direction=test_metric.direction,
                compare_data=compare_data_list)
            item_metric_list.append(report_metric)
        ReportItemMetric.objects.filter(report_item_conf_id=item_conf_id).delete()
        ReportItemMetric.objects.bulk_create(item_metric_list)

    def update(self, data):
        report_id = data.get('report_id')
        report = Report.objects.get(id=report_id)
        base_index = report.test_env.get('base_index', 0)
        if data.get('test_env') and data.get('test_env').get('text'):
            report.test_env['text'] = data.get('test_env').get('text')
        assert report_id, ReportException(ErrorCode.REPORT_ID_NEED)
        for key, value in data.items():
            if key == 'test_env':
                continue
            if hasattr(report, key):
                setattr(report, key, value)
        test_item = data.get('test_item', None)
        with transaction.atomic():
            if test_item:
                perf_data = test_item.get('perf_data', list())
                func_data = test_item.get('func_data', list())
                self.save_test_item_v1(perf_data, report_id, 'performance', base_index)
                self.save_test_item_v1(func_data, report_id, 'functional', base_index)
            report.save()
        save_report_detail(report_id, base_index, get_old_report(report), report.is_automatic)

    @staticmethod
    def delete(data, operator):
        report_id = data.get('report_id')
        assert report_id, ReportException(ErrorCode.REPORT_ID_NEED)
        Report.objects.filter(id=report_id).delete()
        ReportDetail.objects.filter(report_id=report_id).delete()

    @staticmethod
    def update_item(test_item, test_type, report_id):
        if test_item:
            delete_item = test_item.get('delete_item', list())
            update_item = test_item.get('update_item', dict())
            ReportItem.objects.filter(name__in=delete_item, report_id=report_id, test_type=test_type).delete()
            for key, value in update_item.items():
                item = ReportItem.objects.filter(report_id=report_id, name=key, test_type=test_type).first()
                for item_key, item_value in value.items():
                    if hasattr(item, item_key):
                        setattr(item, item_key, item_value)
                update_suite = value.get('update_suite', dict())
                delete_suite = value.get('delete_suite', list())
                ReportItemSuite.objects.filter(id__in=delete_suite).delete()
                for suite_id, update_value in update_suite.items():
                    item_suite = ReportItemSuite.objects.get(id=int(suite_id))
                    for suite_key, suite_value in update_value.items():
                        if hasattr(item_suite, suite_key):
                            setattr(item_suite, suite_key, suite_value)
                        if suite_key == 'delete_conf':
                            ReportItemConf.objects.filter(id__in=suite_value).delete()
                    item_suite.save()

    @staticmethod
    def update_item_suite_desc(data):
        test_suite_description = data.get('test_suite_description')
        test_env = data.get('test_env')
        test_description = data.get('test_description')
        test_conclusion = data.get('test_conclusion')
        item_suite_id = data.get('item_suite_id')
        report_item_suite = ReportItemSuite.objects.filter(id=item_suite_id).first()
        if report_item_suite:
            if test_suite_description:
                report_item_suite.test_suite_description = test_suite_description
            if test_env:
                report_item_suite.test_env = test_env
            if test_description:
                report_item_suite.test_description = test_description
            if test_conclusion:
                report_item_suite.test_conclusion = test_conclusion
            report_item_suite.save()
            report_item = ReportItem.objects.filter(id=report_item_suite.report_item_id).first()
            if report_item:
                report = Report.objects.filter(id=report_item.report_id).first()
                if report:
                    base_index = 0
                    if report.test_env:
                        base_index = report.test_env.get('base_index', 0)
                    save_report_detail(report.id, base_index, get_old_report(report), report.is_automatic)

    @staticmethod
    def update_report_desc(data):
        description = data.get('description')
        test_background = data.get('test_background')
        test_method = data.get('test_method')
        report_id = data.get('report_id')
        report = Report.objects.filter(id=report_id).first()
        if report:
            if 'description' in data:
                report.description = description
            if 'test_background' in data:
                report.test_background = test_background
            if 'test_method' in data:
                report.test_method = test_method
            if 'test_conclusion' in data and 'custom' in data.get('test_conclusion'):
                report.test_conclusion['custom'] = data.get('test_conclusion').get('custom')
            if 'test_env' in data and 'text' in data.get('test_env'):
                report.test_env['text'] = data.get('test_env').get('text')
            report.save()


class ReportDetailService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        report_id = data.get('report_id')
        assert report_id, ReportException(ErrorCode.REPORT_ID_NEED)
        q &= Q(id=report_id)
        return queryset.filter(q)
