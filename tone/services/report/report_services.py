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
    ReportItemSuite, TestJobCase, TestServerSnapshot, CloudServerSnapshot, PlanInstance, PlanInstanceTestRelation
from tone.core.common.services import CommonService
from tone.models.report.test_report import ReportTemplate, ReportTmplItem, ReportTmplItemSuite
from tone.services.plan.plan_services import random_choice_str
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import ReportException
from tone.core.utils.date_util import DateUtil


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
        assert report_source, ReportException(ErrorCode.REPORT_SOURCE_NEED)
        assert test_env, ReportException(ErrorCode.TEST_ENV_NEED)
        assert tmpl_id, ReportException(ErrorCode.TEMPLATE_NEED)
        assert test_item, ReportException(ErrorCode.TEST_ITEM_NEED)
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
            self.save_test_item(perf_data, report_id, 'performance', job_li, plan_li)
            self.save_test_item(func_data, report_id, 'functional', job_li, plan_li)
        return report

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

    def update(self, data, operator):
        report_id = data.get('report_id')
        report = Report.objects.get(id=report_id)
        assert report_id, ReportException(ErrorCode.REPORT_ID_NEED)
        for key, value in data.items():
            if hasattr(report, key):
                setattr(report, key, value)
        test_item = data.get('test_item', None)
        with transaction.atomic():
            if test_item:
                ReportItem.objects.filter(report_id=report_id).delete()
                perf_data = test_item.get('perf_data', list())
                func_data = test_item.get('func_data', list())
                self.save_test_item(perf_data, report_id, 'performance')
                self.save_test_item(func_data, report_id, 'functional')
            report.save()

    @staticmethod
    def delete(data, operator):
        report_id = data.get('report_id')
        assert report_id, ReportException(ErrorCode.REPORT_ID_NEED)
        Report.objects.filter(id=report_id).delete()

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


class ReportDetailService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        report_id = data.get('report_id')
        assert report_id, ReportException(ErrorCode.REPORT_ID_NEED)
        q &= Q(id=report_id)
        return queryset.filter(q)
