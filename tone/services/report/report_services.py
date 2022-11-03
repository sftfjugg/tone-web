# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author:
"""
import json

from django.db.models import Q
from django.db import transaction
from datetime import datetime
from django.db import connection

from tone.core.utils.permission_manage import check_operator_permission
from tone.models import Report, ReportItem, ReportItemConf, ReportItemMetric, ReportItemSubCase, ReportObjectRelation, \
    ReportItemSuite, TestJobCase, TestServerSnapshot, CloudServerSnapshot, PlanInstance, PlanInstanceTestRelation, \
    PerfResult, FuncResult, TestMetric, TestJob, ReportDetail, TestSuite
from tone.core.common.job_result_helper import get_compare_result, get_func_compare_data
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
        product_version = data.get('product_version')
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
        assert product_version, ReportException(ErrorCode.PRODUCT_VERSION_DUPLICATION)
        # assert project_id, ReportException(ErrorCode.PROJECT_ID_NEED)
        assert report_source, ReportException(ErrorCode.REPORT_SOURCE_NEED)
        assert test_env, ReportException(ErrorCode.TEST_ENV_NEED)
        assert tmpl_id, ReportException(ErrorCode.TEMPLATE_NEED)
        assert test_item, ReportException(ErrorCode.TEST_ITEM_NEED)
        with transaction.atomic():
            base_index = test_env.get('base_index', 0)
            test_env['base_group']['is_job'] = 1
            if not test_env['base_group'].get('server_info'):
                test_env['base_group']['server_info'] = list()
            base_job_list = list()
            server_provider = None
            for base_obj in test_env['base_group']['base_objs']:
                base_job_list.append(base_obj.get('obj_id'))
                if not server_provider:
                    test_job = TestJob.objects.filter(id=base_obj.get('obj_id')).first()
                    if test_job:
                        server_provider = test_job.server_provider
            test_env['base_group']['server_info'] = self.package_server_li(base_job_list, server_provider)
            count = len(test_env['base_group']['base_objs'])
            for group in test_env['compare_groups']:
                compare_job_list = list()
                group['is_job'] = 1
                if not group.get('server_info'):
                    group['server_info'] = list()
                for base_obj in group['base_objs']:
                    if len(group['base_objs']) > count:
                        count = len(group['base_objs'])
                    compare_job_list.append(base_obj.get('obj_id'))
                    compare_job = TestJob.objects.filter(id=base_obj.get('obj_id')).first()
                    if compare_job:
                        server_provider = compare_job.server_provider
                group['server_info'] = self.package_server_li(compare_job_list, server_provider)
            test_env['count'] = count
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
        self.save_report_detail(report_id, base_index, get_old_report(report), report.is_automatic)
        return report

    def save_report_detail(self, report_id, base_index, is_old_report, is_automatic):
        detail_perf_data = get_perf_data(report_id, base_index, is_old_report, is_automatic)
        detail_func_data = get_func_data(report_id, base_index, is_old_report, is_automatic)
        report_detail = ReportDetail.objects.filter(report_id=report_id).first()
        if report_detail:
            report_detail.func_data = detail_func_data
            report_detail.perf_data = detail_perf_data
            report_detail.save()
        else:
            ReportDetail.objects.create(report_id=report_id, perf_data=detail_perf_data, func_data=detail_func_data)

    def package_server_li(self, job_list, server_provider):
        server_li = list()
        ip_list = list()
        snap_shot_objs = TestServerSnapshot.objects.filter(job_id__in=job_list, distro__isnull=False).distinct() \
            if server_provider == 'aligroup' else CloudServerSnapshot.objects. \
            filter(job_id__in=job_list, distro__isnull=False).distinct()
        for snap_shot_obj in snap_shot_objs:
            ip = snap_shot_obj.ip if server_provider == 'aligroup' else snap_shot_obj.pub_ip
            if ip in ip_list:
                continue
            ip_list.append(ip)
            if not (snap_shot_obj.distro or snap_shot_obj.rpm_list or snap_shot_obj.gcc):
                continue
            server = ({
                'ip/sn': ip,
                'distro': snap_shot_obj.sm_name if server_provider == 'aligroup' else
                snap_shot_obj.instance_type,
                'os': snap_shot_obj.distro,
                'rpm': snap_shot_obj.rpm_list.split('\n') if snap_shot_obj.rpm_list else list(),
                'kernel': snap_shot_obj.kernel_version,
                'gcc': snap_shot_obj.gcc,
                'glibc': snap_shot_obj.glibc,
                'memory_info': snap_shot_obj.memory_info,
                'disk': snap_shot_obj.disk,
                'cpu_info': snap_shot_obj.cpu_info,
                'ether': snap_shot_obj.ether,
            })
            server_li.append(server)
        return server_li

    def save_test_item_v1(self, data, report_id, test_type, base_index):
        for item in data:
            name = item.get('name')
            suite_list = item.get('suite_list', list())
            assert name, ReportException(ErrorCode.ITEM_NAME_NEED)
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
        if test_type == 'functional':
            item_suite = ReportItemSuite.objects.create(report_item_id=report_item_id, test_suite_id=test_suite_id,
                                                        test_suite_name=test_suite_name, show_type=show_type)
        else:
            test_suite_description = suite.get('test_suite_description')
            test_env = suite.get('test_env')
            test_description = suite.get('test_description')
            test_conclusion = suite.get('test_conclusion')
            item_suite = ReportItemSuite.objects.create(report_item_id=report_item_id, test_suite_id=test_suite_id,
                                                        test_suite_name=test_suite_name, show_type=show_type,
                                                        test_suite_description=test_suite_description,
                                                        test_env=test_env, test_description=test_description,
                                                        test_conclusion=test_conclusion)
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
                func_results = FuncResult.objects. \
                    filter(test_job_id=compare_job, test_suite_id=test_suite_id, test_case_id=test_conf_id)
                compare_count = dict({
                    'is_job': 1,
                    'all_case': func_results.count(),
                    'obj_id': compare_job,
                    'success_case': func_results.filter(sub_case_result=1).count(),
                    'fail_case': func_results.filter(sub_case_result=2).count(),
                })
            else:
                compare_count = dict({
                    'is_job': 1,
                    'obj_id': compare_job,
                })
            if job_index == base_index:
                conf_source = compare_count
            else:
                compare_conf_list.append(compare_count)
            job_index += 1
        compare_conf_list.insert(base_index, conf_source)
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
        func_results = FuncResult.objects. \
            filter(test_job_id=base_job_id, test_suite_id=test_suite_id, test_case_id=test_conf_id). \
            values_list('sub_case_name', 'sub_case_result')
        item_sub_case_list = list()
        for func_result in func_results:
            compare_data = get_func_compare_data(test_suite_id, test_conf_id, func_result[0], job_list)
            compare_data.insert(base_index, FUNC_CASE_RESULT_TYPE_MAP.get(func_result[1]))
            report_sub_case = ReportItemSubCase(
                report_item_conf_id=item_conf_id,
                sub_case_name=func_result[0],
                result=FUNC_CASE_RESULT_TYPE_MAP.get(func_result[1]),
                compare_data=compare_data)
            item_sub_case_list.append(report_sub_case)
        ReportItemSubCase.objects.bulk_create(item_sub_case_list)

    @staticmethod
    def save_item_metric_v1(test_suite_id, test_conf_id, item_conf_id, job_list, base_index):
        base_job_id = job_list.pop(base_index)
        perf_results = PerfResult.objects. \
            filter(test_job_id=base_job_id, test_suite_id=test_suite_id, test_case_id=test_conf_id)
        item_metric_list = list()
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
            compare_data = PerfResult.objects. \
                filter(test_job_id__in=job_list, metric=perf_result.metric, test_suite_id=test_suite_id,
                       test_case_id=test_conf_id).distinct()
            test_value = round(float(perf_result.test_value), 2)
            for job_id in job_list:
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
        ReportItemMetric.objects.bulk_create(item_metric_list)

    def save_test_item(self, data, report_id, test_type, job_li, plan_li):
        for item in data:
            name = item.get('name')
            suite_list = item.get('suite_list', list())
            assert name, ReportException(ErrorCode.ITEM_NAME_NEED)
            report_item = ReportItem.objects.create(name=name, report_id=report_id, test_type=test_type)
            report_item_id = report_item.id
            for suite in suite_list:
                self.save_item_suite(suite, report_item_id, test_type, job_li, plan_li)

    def save_item_suite(self, suite, report_item_id, test_type, job_li, plan_li):
        test_suite_id = suite.get('suite_id')
        test_suite_name = suite.get('suite_name')
        show_type = suite.get('show_type', 0)
        conf_list = suite.get('conf_list', list())
        assert test_suite_id, ReportException(ErrorCode.TEST_SUITE_NEED)
        assert test_suite_name, ReportException(ErrorCode.TEST_SUITE_NAME_NEED)
        if test_type == 'functional':
            item_suite = ReportItemSuite.objects.create(report_item_id=report_item_id, test_suite_id=test_suite_id,
                                                        test_suite_name=test_suite_name, show_type=show_type)
        else:
            test_suite_description = suite.get('test_suite_description')
            test_env = self.get_suite_env(test_suite_id, job_li, plan_li)
            test_description = suite.get('test_description')
            test_conclusion = suite.get('test_conclusion')
            item_suite = ReportItemSuite.objects.create(report_item_id=report_item_id, test_suite_id=test_suite_id,
                                                        test_suite_name=test_suite_name, show_type=show_type,
                                                        test_suite_description=test_suite_description,
                                                        test_env=test_env, test_description=test_description,
                                                        test_conclusion=test_conclusion)
        item_suite_id = item_suite.id
        for conf in conf_list:
            self.save_item_conf(conf, item_suite_id, test_type)

    def get_suite_env(self, test_suite_id, job_li, plan_li):
        test_env = list()
        if plan_li:
            plan_id_list = PlanInstance.objects.filter(plan_id__in=plan_li).values_list('id', flat=True)
            if plan_id_list:
                job_li = PlanInstanceTestRelation.objects.filter(plan_instance_id__in=plan_id_list). \
                    values_list('job_id', flat=True)
        for job_id in job_li:
            ip = ''
            test_job_case = TestJobCase.objects.filter(job_id=job_id, test_suite_id=test_suite_id).first()
            if test_job_case:
                snapshot = TestServerSnapshot.objects.filter(id=test_job_case.server_object_id).first()
                if snapshot:
                    ip = snapshot.ip
                else:
                    snapshot = CloudServerSnapshot.objects.filter(id=test_job_case.server_object_id).first()
                    if snapshot:
                        ip = snapshot.pub_ip
            test_env.append(ip)
        return test_env

    def save_item_conf(self, conf, item_suite_id, test_type):
        test_conf_id = conf.get('conf_id')
        test_conf_name = conf.get('conf_name')
        conf_source = conf.get('conf_source', dict())
        compare_conf_list = conf.get('compare_conf_list', list())
        item_conf = ReportItemConf.objects.create(report_item_suite_id=item_suite_id, test_conf_id=test_conf_id,
                                                  test_conf_name=test_conf_name, conf_source=conf_source,
                                                  compare_conf_list=compare_conf_list)
        item_conf_id = item_conf.id
        if test_type == 'functional':
            sub_case_list = conf.get('sub_case_list', list())
            for sub_case in sub_case_list:
                self.save_item_sub_case(sub_case, item_conf_id)
        else:
            metric_list = conf.get('metric_list', list())
            for metric in metric_list:
                self.save_item_metric(metric, item_conf_id)

    @staticmethod
    def save_item_sub_case(sub_case, item_conf_id):
        sub_case_name = sub_case.get('sub_case_name')
        result = sub_case.get('result')
        compare_data = sub_case.get('compare_data', list())
        ReportItemSubCase.objects.create(report_item_conf_id=item_conf_id, sub_case_name=sub_case_name, result=result,
                                         compare_data=compare_data)

    @staticmethod
    def save_item_metric(metric, item_conf_id):
        test_metric = metric.get('metric')
        test_value = metric.get('test_value')
        cv_value = metric.get('cv_value')
        max_value = metric.get('max_value')
        min_value = metric.get('min_value')
        value_list = metric.get('value_list', list())
        unit = metric.get('unit')
        direction = metric.get('direction')
        compare_data = metric.get('compare_data', list())
        ReportItemMetric.objects.create(report_item_conf_id=item_conf_id, test_metric=test_metric,
                                        test_value=test_value, cv_value=cv_value, unit=unit, max_value=max_value,
                                        min_value=min_value, value_list=value_list, direction=direction,
                                        compare_data=compare_data)

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
                ReportItem.objects.filter(report_id=report_id).delete()
                perf_data = test_item.get('perf_data', list())
                func_data = test_item.get('func_data', list())
                self.save_test_item_v1(perf_data, report_id, 'performance', base_index)
                self.save_test_item_v1(func_data, report_id, 'functional', base_index)
            report.save()
            self.save_report_detail(report_id, base_index, get_old_report(report), report.is_automatic)

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


def get_perf_data(report_id, base_index, is_old_report, is_automatic):
    item_map = dict()
    item_objs = ReportItem.objects.filter(report_id=report_id, test_type='performance')
    for item in item_objs:
        name = item.name
        for item in item_objs:
            name = item.name
            name_li = name.split(':')
            if is_old_report:
                package_name(0, item_map, name_li, item.id, 'performance', base_index)
            else:
                package_name_v1(0, item_map, name_li, item.id, 'performance', base_index, is_automatic)
    return item_map


def get_func_data(report_id, base_index, is_old_report, is_automatic):
    item_map = dict()
    item_objs = ReportItem.objects.filter(report_id=report_id, test_type='functional')
    for item in item_objs:
        name = item.name
        name_li = name.split(':')
        if is_old_report:
            package_name(0, item_map, name_li, item.id, 'functional', base_index)
        else:
            package_name_v1(0, item_map, name_li, item.id, 'functional', base_index, is_automatic)
    return item_map


def get_old_report(report):
    return 1 if report.gmt_created < datetime.strptime('2022-09-13', '%Y-%m-%d') else 0


def package_name(index, _data, name_li, report_item_id, test_type, base_index):
    if index == len(name_li) - 1:
        _data[name_li[index]] = get_func_suite_list(
            report_item_id, base_index) if test_type == 'functional' else get_perf_suite_list(report_item_id)
    else:
        if name_li[index] in _data:
            package_name(index + 1, _data[name_li[index]], name_li, report_item_id, test_type, base_index)
        else:
            _data[name_li[index]] = dict()
            package_name(index + 1, _data[name_li[index]], name_li, report_item_id, test_type, base_index)


def get_func_suite_list(report_item_id, base_index):
    suite_list = list()
    test_suite_objs = ReportItemSuite.objects.filter(report_item_id=report_item_id)
    for test_suite_obj in test_suite_objs:
        suite_data = dict()
        suite_data['item_suite_id'] = test_suite_obj.id
        suite_data['suite_id'] = test_suite_obj.test_suite_id
        suite_data['suite_name'] = test_suite_obj.test_suite_name
        conf_list = list()
        test_conf_objs = ReportItemConf.objects.filter(report_item_suite_id=test_suite_obj.id)
        for test_conf_obj in test_conf_objs:
            conf_data = dict()
            conf_data['item_conf_id'] = test_conf_obj.id
            conf_data['conf_id'] = test_conf_obj.test_conf_id
            conf_data['conf_name'] = test_conf_obj.test_conf_name
            conf_data['conf_source'] = test_conf_obj.conf_source
            conf_data['compare_conf_list'] = test_conf_obj.compare_conf_list
            sub_case_list = list()
            sub_case_objs = ReportItemSubCase.objects.filter(report_item_conf_id=test_conf_obj.id)
            for sub_case_obj in sub_case_objs:
                sub_case_data = dict()
                sub_case_data['sub_case_name'] = sub_case_obj.sub_case_name
                sub_case_data['result'] = sub_case_obj.result
                sub_case_data['compare_data'] = sub_case_obj.compare_data
                sub_case_list.append(sub_case_data)
            conf_data['sub_case_list'] = sub_case_list
            conf_list.append(conf_data)
        suite_data['conf_list'] = conf_list
        suite_list.append(suite_data)
    return suite_list


def package_name_v1(index, _data, name_li, report_item_id, test_type, base_index, is_automatic):
    if index == len(name_li) - 1:
        _data[name_li[index]] = get_func_suite_list_v1(
            report_item_id) if test_type == 'functional' else \
            get_perf_suite_list_v1(report_item_id, base_index, is_automatic)
    else:
        if name_li[index] in _data:
            package_name_v1(index + 1, _data[name_li[index]], name_li, report_item_id, test_type, base_index,
                            is_automatic)
        else:
            _data[name_li[index]] = dict()
            package_name_v1(index + 1, _data[name_li[index]], name_li, report_item_id, test_type, base_index,
                            is_automatic)


def get_func_suite_list_v1(report_item_id):
    suite_list = list()
    raw_sql = 'SELECT a.id AS item_suite_id, a.test_suite_id AS suite_id, a.test_suite_name AS suite_name, ' \
              'b.id AS item_conf_id, b.test_conf_id AS conf_id,b.test_conf_name AS conf_name, b.conf_source,' \
              'b.compare_conf_list, c.sub_case_name, c.compare_data,c.result FROM report_item_suite a ' \
              'LEFT JOIN report_item_conf b ON b.report_item_suite_id=a.id ' \
              'LEFT JOIN report_item_sub_case c ON c.report_item_conf_id=b.id ' \
              'WHERE a.report_item_id=%s AND a.is_deleted=0 AND b.is_deleted=0 AND c.is_deleted=0'
    test_suite_objs = query_all_dict(raw_sql, [report_item_id])
    for test_suite_obj in test_suite_objs:
        exist_suite = [suite for suite in suite_list if suite['item_suite_id'] == test_suite_obj['item_suite_id']]
        if len(exist_suite) > 0:
            suite_data = exist_suite[0]
            if 'conf_list' in suite_data:
                conf_list = suite_data['conf_list']
            else:
                conf_list = list()
        else:
            suite_data = dict()
            suite_data['item_suite_id'] = test_suite_obj['item_suite_id']
            suite_data['suite_id'] = test_suite_obj['suite_id']
            suite_data['suite_name'] = test_suite_obj['suite_name']
            conf_list = list()
            suite_list.append(suite_data)
        exist_conf = [conf for conf in conf_list if conf['conf_id'] == test_suite_obj['conf_id']]
        if len(exist_conf) > 0:
            conf_data = exist_conf[0]
            if 'sub_case_list' in conf_data:
                sub_case_list = conf_data['sub_case_list']
            else:
                sub_case_list = list()
        else:
            compare_conf_list = json.loads(test_suite_obj['compare_conf_list'])
            conf_data = dict()
            conf_data['conf_id'] = test_suite_obj['conf_id']
            conf_data['conf_name'] = test_suite_obj['conf_name']
            conf_data['compare_conf_list'] = compare_conf_list
            sub_case_list = list()
            conf_list.append(conf_data)
        compare_data = list()
        if test_suite_obj['compare_data']:
            compare_data = json.loads(test_suite_obj['compare_data'])
        sub_case_data = dict()
        sub_case_data['sub_case_name'] = test_suite_obj['sub_case_name']
        sub_case_data['compare_data'] = compare_data
        sub_case_list.append(sub_case_data)
        conf_data['sub_case_list'] = sub_case_list
        suite_data['conf_list'] = conf_list
    return suite_list


def _get_compare_data(metric_obj):
    compare_data = list()
    for item in metric_obj:
        if item:
            metric_cmp = dict()
            metric_cmp['test_value'] = item.get('test_value')
            metric_cmp['cv_value'] = item.get('cv_value')
            metric_cmp['compare_result'] = item.get('compare_result')
            metric_cmp['compare_value'] = item.get('compare_value')
            metric_cmp['compare_value'] = item['compare_value'].strip('-') if item.get('compare_value') else ''
            compare_data.append(metric_cmp)
        else:
            compare_data.append(dict())
    return compare_data


def get_perf_suite_list(report_item_id):
    suite_list = list()
    test_suite_objs = ReportItemSuite.objects.filter(report_item_id=report_item_id)
    for test_suite_obj in test_suite_objs:
        suite_data = dict()
        suite_data['item_suite_id'] = test_suite_obj.id
        suite_data['suite_name'] = test_suite_obj.test_suite_name
        suite_data['suite_id'] = test_suite_obj.test_suite_id
        suite_data['show_type'] = test_suite_obj.show_type
        suite_data['test_suite_description'] = TestSuite.objects.filter(name=test_suite_obj.test_suite_name).first().doc
        suite_data['test_env'] = test_suite_obj.test_env
        suite_data['test_description'] = test_suite_obj.test_description
        suite_data['test_conclusion'] = test_suite_obj.test_conclusion
        conf_list = list()
        test_conf_objs = ReportItemConf.objects.filter(report_item_suite_id=test_suite_obj.id)
        for test_conf_obj in test_conf_objs:
            conf_data = dict()
            conf_data['item_conf_id'] = test_conf_obj.id
            conf_data['conf_id'] = test_conf_obj.test_conf_id
            conf_data['conf_name'] = test_conf_obj.test_conf_name
            conf_data['conf_source'] = test_conf_obj.conf_source
            conf_data['compare_conf_list'] = test_conf_obj.compare_conf_list
            metric_list = list()
            metric_objs = ReportItemMetric.objects.filter(report_item_conf_id=test_conf_obj.id)
            for metric_obj in metric_objs:
                test_metric = TestMetric.objects.filter(name=metric_obj.test_metric, object_type='case').first()
                compare_data = _get_compare_data(metric_obj.compare_data)
                metric_data = dict()
                metric_data['metric'] = metric_obj.test_metric
                metric_data['test_value'] = format(float(metric_obj.test_value), '.2f')
                metric_data['cv_value'] = metric_obj.cv_value
                metric_data['unit'] = metric_obj.unit
                metric_data['max_value'] = metric_obj.max_value
                metric_data['min_value'] = metric_obj.min_value
                metric_data['value_list'] = metric_obj.value_list
                metric_data['direction'] = metric_obj.direction
                metric_data['cv_threshold'] = test_metric.cv_threshold if test_metric else None
                metric_data['cmp_threshold'] = test_metric.cmp_threshold if test_metric else None
                metric_data['compare_data'] = compare_data
                metric_list.append(metric_data)
            conf_data['metric_list'] = metric_list
            conf_list.append(conf_data)
        suite_data['conf_list'] = conf_list
        suite_list.append(suite_data)
    return suite_list


def get_perf_suite_list_v1(report_item_id, base_index, is_automatic):
    suite_list = list()
    case_metric_sql = 'SELECT c.test_metric' \
                      ' FROM report_item_suite a ' \
                      'LEFT JOIN report_item_conf b ON b.report_item_suite_id=a.id ' \
                      'LEFT JOIN report_item_metric c ON c.report_item_conf_id=b.id ' \
                      'LEFT JOIN test_suite d ON a.test_suite_name=d.name ' \
                      'LEFT JOIN test_track_metric e ON c.test_metric=e.name AND e.object_id=b.test_conf_id ' \
                      'WHERE e.object_type="case" AND a.report_item_id=%s AND a.is_deleted=0 AND b.is_deleted=0 ' \
                      'AND c.is_deleted=0 AND d.is_deleted=0 AND e.is_deleted=0'
    raw_sql = 'SELECT a.id AS item_suite_id, a.test_suite_id AS suite_id, a.test_suite_name AS suite_name,' \
              'a.show_type, a.test_env, a.test_description, a.test_conclusion, ' \
              'b.id AS item_conf_id, b.test_conf_id AS conf_id,b.test_conf_name AS conf_name, b.conf_source,' \
              'b.compare_conf_list, c.test_metric,c.test_value,c.cv_value,d.doc AS test_suite_description,' \
              'c.compare_data,e.cv_threshold,e.cmp_threshold,e.unit,e.direction' \
              ' FROM report_item_suite a ' \
              'LEFT JOIN report_item_conf b ON b.report_item_suite_id=a.id ' \
              'LEFT JOIN report_item_metric c ON c.report_item_conf_id=b.id ' \
              'LEFT JOIN test_suite d ON a.test_suite_name=d.name ' \
              'LEFT JOIN test_track_metric e ON c.test_metric=e.name AND e.object_id=b.test_conf_id ' \
              'WHERE e.object_type="case" AND a.report_item_id=%s AND a.is_deleted=0 AND b.is_deleted=0 ' \
              'AND c.is_deleted=0 AND d.is_deleted=0 AND e.is_deleted=0'
    raw_sql += " union "
    raw_sql += 'SELECT a.id AS item_suite_id, a.test_suite_id AS suite_id, a.test_suite_name AS suite_name,' \
               'a.show_type, a.test_env, a.test_description, a.test_conclusion, ' \
               'b.id AS item_conf_id, b.test_conf_id AS conf_id,b.test_conf_name AS conf_name, b.conf_source,' \
               'b.compare_conf_list, c.test_metric,c.test_value,c.cv_value,d.doc AS test_suite_description,' \
               'c.compare_data,e.cv_threshold,e.cmp_threshold,e.unit,e.direction' \
               ' FROM report_item_suite a ' \
               'LEFT JOIN report_item_conf b ON b.report_item_suite_id=a.id ' \
               'LEFT JOIN report_item_metric c ON c.report_item_conf_id=b.id ' \
               'LEFT JOIN test_suite d ON a.test_suite_name=d.name ' \
               'LEFT JOIN test_track_metric e ON c.test_metric=e.name AND e.object_id=a.test_suite_id ' \
               'WHERE e.object_type="suite" AND a.report_item_id=%s AND a.is_deleted=0 AND b.is_deleted=0 ' \
               'AND c.is_deleted=0 AND d.is_deleted=0 AND e.is_deleted=0 AND c.test_metric not in (' + \
               case_metric_sql + ')'
    test_suite_objs = query_all_dict(raw_sql, [report_item_id, report_item_id, report_item_id])
    for test_suite_obj in test_suite_objs:
        exist_suite = [suite for suite in suite_list if suite['item_suite_id'] == test_suite_obj['item_suite_id']]
        if len(exist_suite) > 0:
            suite_data = exist_suite[0]
            if 'conf_list' in suite_data:
                conf_list = suite_data['conf_list']
            else:
                conf_list = list()
        else:
            suite_data = dict()
            suite_data['item_suite_id'] = test_suite_obj['item_suite_id']
            suite_data['suite_name'] = test_suite_obj['suite_name']
            suite_data['suite_id'] = test_suite_obj['suite_id']
            suite_data['show_type'] = test_suite_obj['show_type']
            suite_data['test_suite_description'] = test_suite_obj['test_suite_description']
            suite_data['test_env'] = test_suite_obj['test_env']
            suite_data['test_description'] = test_suite_obj['test_description']
            suite_data['test_conclusion'] = test_suite_obj['test_conclusion']
            conf_list = list()
            suite_list.append(suite_data)
        exist_conf = [conf for conf in conf_list if conf['conf_id'] == test_suite_obj['conf_id']]
        if len(exist_conf) > 0:
            conf_data = exist_conf[0]
            if 'metric_list' in conf_data:
                metric_list = conf_data['metric_list']
            else:
                metric_list = list()
        else:
            compare_conf_list = json.loads(test_suite_obj['compare_conf_list'])
            conf_data = dict()
            conf_data['conf_id'] = test_suite_obj['conf_id']
            conf_data['conf_name'] = test_suite_obj['conf_name']
            conf_data['compare_conf_list'] = compare_conf_list
            metric_list = list()
            conf_list.append(conf_data)
        compare_data = list()
        suite_compare_data = json.loads(test_suite_obj['compare_data'])
        if suite_compare_data:
            compare_data = _get_compare_data(suite_compare_data)
        metric_base_data = dict()
        metric_base_data['test_value'] = format(float(test_suite_obj['test_value']), '.2f')
        metric_base_data['cv_value'] = test_suite_obj['cv_value'].split('±')[-1] if test_suite_obj[
            'cv_value'] else None,
        if is_automatic:
            compare_data.append(metric_base_data)
        else:
            compare_data.insert(base_index, metric_base_data)
        metric_data = dict()
        metric_data['metric'] = test_suite_obj['test_metric']
        metric_data['cv_threshold'] = test_suite_obj['cv_threshold']
        metric_data['cmp_threshold'] = test_suite_obj['cmp_threshold']
        metric_data['unit'] = test_suite_obj['unit']
        metric_data['direction'] = test_suite_obj['direction']
        metric_data['compare_data'] = compare_data
        metric_list.append(metric_data)
        conf_data['metric_list'] = metric_list
        suite_data['conf_list'] = conf_list
    return suite_list


def query_all_dict(sql, params=None):
    '''
    查询所有结果返回字典类型数据
    :param sql:
    :param params:
    :return:
    '''
    with connection.cursor() as cursor:
        if params:
            cursor.execute(sql, params=params)
        else:
            cursor.execute(sql)
        col_names = [desc[0] for desc in cursor.description]
        row = cursor.fetchall()
        rowList = []
        for list in row:
            tMap = dict(zip(col_names, list))
            rowList.append(tMap)
        return rowList


class ReportDetailService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        report_id = data.get('report_id')
        assert report_id, ReportException(ErrorCode.REPORT_ID_NEED)
        q &= Q(id=report_id)
        return queryset.filter(q)
