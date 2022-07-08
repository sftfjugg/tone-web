# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from django.db.models import Q
from django.db import transaction

from tone.core.common.services import CommonService
from tone.models import TestTemplate, TestTmplCase, TestTmplSuite, WorkspaceMember, Role, RoleMember, \
    PlanStageTestRelation, TestPlan
from tone.models.sys.config_models import TemplateTagRelation
from tone.core.handle.template_handle import TestTemplateHandle
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import JobTestException
from tone.serializers.job.plan_serializers import TestPlanSerializer


class TestTemplateService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        q &= Q(enable=data.get('enable')) if data.get('enable') else q
        q &= Q(id=data.get('template_id')) if data.get('template_id') else q
        q &= Q(name__icontains=data.get('name')) if data.get('name') else q
        q &= Q(creator=data.get('creator')) if data.get('creator') else q
        q &= Q(update_user=data.get('update_user')) if data.get('update_user') else q
        q &= Q(job_type_id__in=data.getlist('job_type_id')) if data.get('job_type_id') else q
        return queryset.filter(q)

    def update(self, data, operator):  # noqa: C901
        template_id = data.get('template_id')
        update_item = data.get('update_item', 'detail')
        assert template_id, JobTestException(ErrorCode.TEMPLATE_NEED)
        self.check_id(template_id)
        obj = TestTemplate.objects.get(id=template_id)
        # 非系统管理员super_admin, sys_admin ws_member 只能修改自己
        sys_role_id = RoleMember.objects.get(user_id=operator.id).role_id
        sys_role = Role.objects.get(id=sys_role_id).title
        if sys_role not in ['super_admin', 'sys_admin']:
            operator_role_id = WorkspaceMember.objects.get(ws_id=obj.ws_id, user_id=operator.id).role_id
            operator_role = Role.objects.get(id=operator_role_id).title
            allow_list = ['ws_owner', 'ws_admin', 'ws_test_admin']
            if operator_role not in allow_list and operator.id != obj.creator:
                return False
        if update_item == 'template':
            for key, value in data.items():
                if key == 'template_name':
                    if value != obj.name:
                        self.check_name(value, obj.ws_id)
                if hasattr(obj, key):
                    setattr(obj, key, value)
                else:
                    pass
            obj.update_user = operator.id
            obj.save()
        else:
            with transaction.atomic():
                handler = TestTemplateHandle(data, operator, obj)
                data_dic, case_list, suite_list, tag_list = handler.return_result()
                data_dic['update_user'] = operator.id
                for key, value in data_dic.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                    else:
                        pass
                if data.get('test_config'):
                    TestTmplSuite.objects.filter(tmpl_id=template_id).delete()
                    TestTmplCase.objects.filter(tmpl_id=template_id).delete()
                    for suite in suite_list:
                        suite['tmpl_id'] = template_id
                        TestTmplSuite.objects.create(**suite)
                    for case in case_list:
                        case['tmpl_id'] = template_id
                        TestTmplCase.objects.create(**case)
                if data.get('tags'):
                    TemplateTagRelation.objects.filter(template_id=template_id).delete()
                    for tag in tag_list:
                        TemplateTagRelation.objects.create(tag_id=tag, template_id=template_id)
                obj.save()
        return True

    def delete(self, data, operator):
        template_id = data.get('template_id')
        assert template_id, JobTestException(ErrorCode.TEMPLATE_NEED)
        self.check_id(template_id)
        obj = TestTemplate.objects.get(id=template_id)
        # 非系统管理员super_admin, sys_admin ws_member 只能删除自己
        sys_role_id = RoleMember.objects.get(user_id=operator.id).role_id
        sys_role = Role.objects.get(id=sys_role_id).title
        if sys_role not in ['super_admin', 'sys_admin']:
            operator_role_id = WorkspaceMember.objects.get(ws_id=obj.ws_id, user_id=operator.id).role_id
            operator_role = Role.objects.get(id=operator_role_id).title
            allow_list = ['ws_owner', 'ws_admin', 'ws_test_admin']
            if operator_role not in allow_list and operator.id != obj.creator:
                return False
        TestTemplate.objects.filter(id=template_id).delete()
        TestTmplSuite.objects.filter(tmpl_id=template_id).delete()
        TestTmplCase.objects.filter(tmpl_id=template_id).delete()
        TemplateTagRelation.objects.filter(template_id=template_id).delete()
        PlanStageTestRelation.objects.filter(tmpl_id=template_id).delete()
        return True

    def del_confirm(self, data):
        template_id = data.get('template_id')
        assert template_id, JobTestException(ErrorCode.TEMPLATE_NEED)
        self.check_id(template_id)
        plan_list = PlanStageTestRelation.objects.filter(tmpl_id=template_id).values_list('plan_id', flat=True)
        return TestPlan.objects.filter(id__in=plan_list)

    @staticmethod
    def pack_notice_info(email=None, ding=None, subject=None):
        notice_info = list()
        if email:
            email_data = {'type': 'email', "to": email}
            if subject:
                email_data['subject'] = subject
            notice_info.append(email_data)
        if ding:
            ding_data = {'type': 'ding', "to": ding}
            if subject:
                ding_data['subject'] = subject
            notice_info.append(ding_data)
        return notice_info

    @staticmethod
    def create(data, operator):
        handler = TestTemplateHandle(data, operator)
        with transaction.atomic():
            data_dic, case_list, suite_list, tag_list = handler.return_result()
            test_template = TestTemplate.objects.create(**data_dic)
            for suite in suite_list:
                suite['tmpl_id'] = test_template.id
                TestTmplSuite.objects.create(**suite)
            for case in case_list:
                case['tmpl_id'] = test_template.id
                TestTmplCase.objects.create(**case)
            for tag in tag_list:
                TemplateTagRelation.objects.create(tag_id=tag, template_id=test_template.id)

    @staticmethod
    def check_id(template_id):
        obj = TestTemplate.objects.filter(id=template_id)
        if not obj.exists():
            raise JobTestException(ErrorCode.TEST_TEMPLATE_NONEXISTENT)

    @staticmethod
    def check_name(name, ws_id):
        obj = TestTemplate.objects.filter(name=name, ws_id=ws_id)
        if obj.exists():
            raise JobTestException(ErrorCode.TEMPLATE_NAME_EXIST)


class TestTemplateDetailService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(id=data.get('template_id')) if data.get('template_id') else q
        queryset.filter(q)
        return queryset.filter(q)


class TestTemplateCopyService(CommonService):
    @staticmethod
    def create(data, operator):
        template_id = data.get('template_id')
        assert template_id, JobTestException(ErrorCode.TEMPLATE_NEED)
        old_template = TestTemplate.objects.get(id=template_id)
        with transaction.atomic():
            if data.get('name'):
                name_obj = TestTemplate.objects.filter(name=data.get('name'), ws_id=old_template.ws_id)
                if name_obj.exists():
                    raise JobTestException(ErrorCode.TEMPLATE_NAME_EXIST)
                name = data.get('name')
            else:
                name = ''
            test_template = TestTemplate.objects.create(
                name=name,
                job_name=old_template.job_name,
                schedule_info=old_template.schedule_info,
                description=data.get('description', ''),
                job_type_id=old_template.job_type_id,
                project_id=old_template.project_id,
                product_id=old_template.product_id,
                baseline_id=old_template.baseline_id,
                iclone_info=old_template.iclone_info,
                kernel_info=old_template.kernel_info,
                need_reboot=old_template.need_reboot,
                rpm_info=old_template.rpm_info,
                script_info=old_template.script_info,
                monitor_info=old_template.monitor_info,
                cleanup_info=old_template.cleanup_info,
                notice_info=old_template.notice_info,
                console=old_template.console,
                kernel_version=old_template.kernel_version,
                report_name=old_template.report_name,
                report_template_id=old_template.report_template_id,
                env_info=old_template.env_info,
                callback_api=old_template.callback_api,
                enable=data.get('enable', True),
                creator=operator.id,
                ws_id=old_template.ws_id,
            )
            suites = TestTmplSuite.objects.filter(tmpl_id=old_template.id)
            cases = TestTmplCase.objects.filter(tmpl_id=old_template.id)
            tags = TemplateTagRelation.objects.filter(template_id=old_template.id)
            for suite in suites:
                TestTmplSuite.objects.create(
                    tmpl_id=test_template.id,
                    test_suite_id=suite.test_suite_id,
                    need_reboot=suite.need_reboot,
                    setup_info=suite.setup_info,
                    cleanup_info=suite.cleanup_info,
                    console=suite.console,
                    monitor_info=suite.monitor_info,
                    priority=suite.priority,
                )
            for case in cases:
                TestTmplCase.objects.create(
                    tmpl_id=test_template.id,
                    test_case_id=case.test_case_id,
                    test_suite_id=case.test_suite_id,
                    run_mode=case.run_mode,
                    server_provider=case.server_provider,
                    repeat=case.repeat,
                    custom_ip=case.custom_ip,
                    custom_sn=case.custom_sn,
                    custom_channel=case.custom_channel,
                    server_object_id=case.server_object_id,
                    server_tag_id=case.server_tag_id,
                    env_info=case.env_info,
                    need_reboot=case.need_reboot,
                    setup_info=case.setup_info,
                    cleanup_info=case.cleanup_info,
                    console=case.console,
                    monitor_info=case.monitor_info,
                    priority=case.priority,
                )
            for tag in tags:
                TemplateTagRelation.objects.create(
                    template_id=test_template.id,
                    tag_id=tag.tag_id,
                )


class TestTemplateItemsService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(id=data.get('template_id')) if data.get('template_id') else q
        queryset.filter(q)
        return queryset.filter(q)
