import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timedelta

from PIL import Image
from django.conf import settings
from django.db import transaction

from django.db.models import Q, When, Case

from initial.job_type.initialize import JobTypeDataInitialize
from tone.core.common.constant import RANDOM_THEME_COLOR_LIST, WS_LOGO_DIR, DOC_IMG_DIR
from tone.core.common.exceptions.exception_class import DataExistsException
from tone.core.common.msg_notice import InSiteMsgHandle
from tone.core.common.permission_config_info import WS_ROLE_MAP, WS_SHOW_MEMBER_CONFIG
from tone.core.common.services import CommonService
from tone.core.utils.sftp_client import sftp_client
from tone.core.utils.short_uuid import short_uuid
from tone.core.utils.tone_thread import ToneThread
from tone.models import WorkspaceMember, Workspace, ApproveInfo, WorkspaceAccessHistory, User, TestCase, \
    WorkspaceCaseRelation, TestSuite, Product, Project, TestJob, Role, RoleMember, JobTag, TestServer, CloudServer, \
    InSiteWorkProcessMsg, InSiteWorkProcessUserMsg, InSiteSimpleMsg, BaseConfig, FuncResult, TestJobCase
from tone.services.report.report_services import ReportTemplateService
from tone.settings import MEDIA_ROOT

logger = logging.getLogger(__name__)


class WorkspaceService(CommonService):

    @classmethod
    def get_ws_logo(cls, original_logo):
        if not original_logo:
            return ''
        file_path_name = WS_LOGO_DIR + '/' + original_logo
        ws_logo_link = 'http://{}:{}{}'.format(
            settings.TONE_STORAGE_HOST,
            settings.TONE_STORAGE_PROXY_PORT,
            file_path_name
        )
        return ws_logo_link

    @staticmethod
    def filter(queryset, data, operator):
        scope = data.get('scope')
        q = Q()
        if scope:
            operator = data.get('operator', operator)
            if scope == 'owner':
                q &= Q(owner=operator)
            elif scope == 'creator':
                q &= Q(creator=operator)
            elif scope == 'join':
                ws_id_list = WorkspaceMember.objects.filter(user_id=operator).values_list('ws_id', flat=True)
                q &= Q(id__in=ws_id_list)
        return queryset.filter(q)

    def create(self, data, operator):
        form_fields = ['name', 'show_name', 'description', 'is_public', 'logo', 'theme_color']
        create_data = dict(id=short_uuid(), creator=operator, owner=operator)
        for field in form_fields:
            create_data.update({field: data.get(field)})
        if not create_data.get('theme_color'):
            create_data['theme_color'] = random.choice(RANDOM_THEME_COLOR_LIST)
        # 超级管理员和系统管理员，创建ws不需要审批
        if Role.objects.get(id=RoleMember.objects.get(user_id=operator).role_id).title in ['super_admin', 'sys_admin']:
            create_data['is_approved'] = True
            workspace = Workspace.objects.create(**create_data)
            self.add_workspace_relation_data(workspace.id, operator)
        else:
            workspace = Workspace.objects.create(**create_data)
            self.apply_for(workspace.id, 'create', data.get('reason'), operator)
        return True, workspace

    def update(self, data, operator):
        update_data = dict()
        ws_id = data.get('id')
        workspace = Workspace.objects.filter(id=ws_id)
        allow_modify_fields = ['show_name', 'description', 'owner', 'is_public', 'logo', 'is_show']
        if workspace.first() is None:
            return False, 'Workspace 不存在'

        if 'is_show' in data:
            self.update_ws_is_show(data)
            return True, workspace.first()

        if data.get('show_name'):
            compare_workspace = Workspace.objects.filter(show_name=data.get('show_name')).first()
            if compare_workspace is not None and compare_workspace.id != ws_id:
                return False, '显示名称已存在'

        if data.get('owner'):
            # 所有权转交：替换 ws_owner为 ws_admin
            ws_owner = Role.objects.filter(title='ws_owner').first()
            ws_admin = Role.objects.filter(title='ws_admin').first()
            origin_owner = WorkspaceMember.objects.filter(ws_id=ws_id, role_id=ws_owner.id).first()
            WorkspaceMember.objects.filter(ws_id=ws_id, user_id=origin_owner.user_id).update(role_id=ws_admin.id)
            WorkspaceMember.objects.filter(ws_id=ws_id, user_id=data.get('owner')).update(role_id=ws_owner.id)
            # 所有权转交, 发送消息到被操作人
            InSiteMsgHandle().by_transfer_owner(operator, data.get('owner'), ws_id)

        for field in allow_modify_fields:
            if data.get(field) is not None:
                update_data.update({field: data.get(field)})
        Workspace.objects.filter(id=ws_id).update(**update_data)
        return True, workspace.first()

    @staticmethod
    def update_ws_is_show(data):
        ws_id = data.get('id')
        workspace = Workspace.objects.filter(id=ws_id)

        config = BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST').values_list('config_value', flat=True) if \
            BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST') else None
        if not config:
            config_list = []
        else:
            config_list = json.loads(list(config)[0])

        if data.get('is_show'):
            config_list.append(data.get('id'))
            workspace.update(is_show=True)
        else:
            config_list.remove(data.get('id'))
            workspace.update(is_show=False)
        if BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST'):
            BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST').update(config_value=json.dumps(config_list))
        else:
            BaseConfig.objects.create(config_key='SHOW_WS_ID_LIST', config_value=json.dumps(config_list))

    def delete(self, data, operator):
        workspace = Workspace.objects.filter(id=data.get('id')).first()
        # 超级管理员和系统管理员可以直接注销 ws
        if Role.objects.get(id=RoleMember.objects.get(user_id=operator).role_id).title in ['super_admin', 'sys_admin']:
            with transaction.atomic():
                Workspace.objects.filter(id=data.get('id')).delete()
                self.delete_workspace_relation_data(data.get('id'))
            # return True, 'cancellation of success'
        else:
            # ws_owner 需要申请注销
            if ApproveInfo.objects.filter(
                    object_type='workspace',
                    object_id=workspace.id,
                    action='delete',
                    status__in=['passed', 'waiting']).exists():
                raise DataExistsException
                # return False, 'The application record already exists'
            else:
                self.apply_for(workspace.id, 'delete', data.get('reason'), operator)
        # return True, 'The application is successful, waiting for approval'

    @staticmethod
    def apply_for(object_id, action, reason, operator):
        approve_obj = ApproveInfo.objects.create(
            object_type='workspace',
            object_id=object_id,
            action=action,
            reason=reason,
            proposer=operator
        )
        # 创建  / 注销ws, 申请发送消息
        InSiteMsgHandle().create_apply(approve_obj.id)

    @staticmethod
    def add_default_case_to_ws(ws_id):
        cases = TestCase.objects.filter(is_default=True)
        case_relations_obj_list = []
        for case in cases:
            test_suite = TestSuite.objects.filter(id=case.test_suite_id)
            if not test_suite:
                continue
            case_relations_obj_list.append(
                WorkspaceCaseRelation(
                    test_case_id=case.id,
                    test_suite_id=case.test_suite_id,
                    test_type=test_suite.first().test_type,
                    ws_id=ws_id
                )
            )
        WorkspaceCaseRelation.objects.bulk_create(case_relations_obj_list)

    def add_workspace_relation_data(self, ws_id, operator):
        with transaction.atomic():
            # 1.add member
            WorkspaceMember.objects.get_or_create(
                user_id=operator,
                ws_id=ws_id,
                role_id=Role.objects.filter(title='ws_owner').first().id
            )
            # 2.add history
            # WorkspaceHistoryService().add_entry_history(data={'ws_id': ws_id}, operator=operator)
            # 3.add job type
            ToneThread(JobTypeDataInitialize().initialize_ws_job_type, (ws_id,)).start()
            # 4.add default case
            ToneThread(self.add_default_case_to_ws, (ws_id,)).start()
            # 5.add default product/project
            ToneThread(self.add_default_product_and_project, (ws_id,)).start()
            # 6.add default sys_tag
            ToneThread(self.add_default_job_sys_tag, (ws_id,)).start()
            # 7. add default report template
            ToneThread(self.add_default_report_tmpl_ws, (ws_id,)).start()

    @staticmethod
    def add_default_report_tmpl_ws(ws_id):
        ReportTemplateService().create_default_template(ws_id)

    def delete_workspace_relation_data(self, ws_id):
        # delete history
        WorkspaceAccessHistory.objects.filter(ws_id=ws_id).delete()
        # delete member
        WorkspaceMember.objects.filter(ws_id=ws_id).delete()
        # delete jobs
        TestJob.objects.filter(ws_id=ws_id).delete()
        # delete job type
        JobTypeDataInitialize().clear_ws_job_type_data(ws_id)
        # delete case
        WorkspaceCaseRelation.objects.filter(ws_id=ws_id).delete()
        # delete product/project
        Product.objects.filter(ws_id=ws_id).delete()
        Project.objects.filter(ws_id=ws_id).delete()
        # delete job tag
        JobTag.objects.filter(ws_id=ws_id).delete()
        # delete machine
        TestServer.objects.filter(ws_id=ws_id).delete()
        CloudServer.objects.filter(ws_id=ws_id).delete()
        # delete approve
        ApproveInfo.objects.filter(object_type='workspace', object_id=ws_id).delete()
        # delete process msg
        # self.delete_in_site_msg(ws_id)
        # delete simple msg
        self.delete_simple_msg(ws_id)

    @staticmethod
    def delete_simple_msg(ws_id):
        job_id_list = TestJob.objects.filter(ws_id=ws_id).values_list('id', flat=True)
        InSiteSimpleMsg.objects.filter(msg_type='job_complete', msg_object_id__in=job_id_list).delete()

    @staticmethod
    def delete_in_site_msg(ws_id):
        process_id_list = ApproveInfo.objects.filter(object_type='workspace', object_id=ws_id, query_scope='all'
                                                     ).values_list('id', flat=True)
        process_msg_queryset = InSiteWorkProcessMsg.objects.filter(process_id__in=process_id_list)
        process_msg_queryset.delete()
        process_msg_id_list = process_msg_queryset.values_list('id', flat=True)
        InSiteWorkProcessUserMsg.objects.filter(msg_id__in=process_msg_id_list).delete()

    @staticmethod
    def add_default_product_and_project(ws_id):
        workspace = Workspace.objects.get(id=ws_id)
        product = Product.objects.create(
            name='default_{}'.format(workspace.name),
            description='default product',
            command='uname -r',
            ws_id=ws_id,
            is_default=True
        )
        Project.objects.create(
            name='default_{}'.format(workspace.name),
            description='default project',
            ws_id=ws_id,
            is_default=True,
            product_id=product.id,
            product_version='default'
        )

    @staticmethod
    def add_default_job_sys_tag(ws_id):
        JobTag.objects.create(
            name='nightly',
            source_tag='system_tag',
            ws_id=ws_id,
            description='Nightly测试专用标签'
        )
        JobTag.objects.create(
            name='analytics',
            source_tag='system_tag',
            ws_id=ws_id,
            description='Analytics性能分析专用标签'
        )

    @staticmethod
    def check_ws(data):
        name = data.get('name')
        if name and Workspace.objects.filter(name=name).exists():
            return 201, '名称已存在'
        show_name = data.get('show_name')
        if show_name and Workspace.objects.filter(show_name=show_name).exists():
            return 201, '显示名已存在'
        return 200, 'success'


class WorkspaceHistoryService(CommonService):
    @staticmethod
    def get_distinct_queryset(queryset, operator, data):
        call_page = data.get('call_page', 'index')
        ws_id = data.get('ws_id')
        history_ws_id_list = list(queryset.filter(user_id=operator).
                                  values_list('ws_id', flat=True))
        if call_page == 'menu':
            public_ws_id_list = list(Workspace.objects.filter(is_approved=True, is_public=True).
                                     values_list('id', flat=True))
            history_ws_id_list.extend(public_ws_id_list)
        history_ws_id_distinct = list(set(history_ws_id_list))
        history_ws_id_distinct.sort(key=history_ws_id_list.index)
        # if call_page == 'index' and len(history_ws_id_list) > 6:
        #     history_ws_id_distinct = history_ws_id_distinct[:6]
        common_ws = Workspace.objects.filter(is_common=True).first()
        if common_ws and common_ws.id not in history_ws_id_distinct:
            history_ws_id_distinct.append(common_ws.id)
        if ws_id and ws_id not in history_ws_id_distinct:
            history_ws_id_distinct.insert(0, ws_id)
        # 按照访问顺序倒叙排列
        _order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(history_ws_id_distinct)])
        return Workspace.objects.filter(id__in=history_ws_id_distinct).order_by(_order)

    @staticmethod
    def add_entry_history(data, operator):
        if not operator:
            operator = data.get('user_id')
        if not operator:
            return
        if not WorkspaceMember.objects.filter(ws_id=data.get('ws_id'), user_id=operator).exists():
            role_title = Role.objects.get(id=RoleMember.objects.get(user_id=operator).role_id).title
            # 超级管理员和系统管理员直接加入ws,并设置角色为 ws_member,拥有ws下所有配置权限
            if role_title in {'super_admin', 'sys_admin'}:
                WorkspaceMember.objects.get_or_create(
                    user_id=operator,
                    ws_id=data.get('ws_id'),
                    role_id=Role.objects.get(title='ws_member').id
                )
                # 公共的WS创建 ws_member记录
            elif Workspace.objects.get(id=data.get('ws_id')).is_common:
                WorkspaceMember.objects.get_or_create(
                    ws_id=data.get('ws_id'),
                    user_id=operator,
                    role_id=Role.objects.get(title='ws_member').id
                )
        if WorkspaceAccessHistory.objects.filter(
                ws_id=data.get('ws_id'),
                user_id=operator
        ).exists():
            first_entry = False
        else:
            first_entry = True
        WorkspaceAccessHistory.objects.create(
            ws_id=data.get('ws_id'),
            user_id=operator,
        )
        return first_entry


class WorkspaceMemberService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        keyword = data.get('keyword')
        if keyword:
            user_q = Q(first_name__contains=keyword) | Q(last_name__contains=keyword)
            user_id_list = User.objects.filter(user_q).exclude(username='system', is_superuser=True)\
                .values_list('id', flat=True)
        else:
            user_id_list = User.objects.exclude(username='system').values_list('id', flat=True)
        q &= Q(user_id__in=user_id_list)
        # 根据角色名称过滤ws成员信息
        role = data.get('role', '')
        ws_id = data.get('ws_id', '')
        if ws_id:
            q &= Q(ws_id=ws_id)
        if role:
            # 通过角色名称找到角色id
            role_id = Role.objects.get(title=role).id
            q &= Q(role_id=role_id)
        return queryset.filter(q)

    @staticmethod
    def apply_for_join(data, operator):
        ws_id = data.get('ws_id')
        reason = data.get('reason')
        if WorkspaceMember.objects.filter(user_id=operator.id, ws_id=ws_id).exists():
            return False, '你已经是Workspace成员!'
        if ApproveInfo.objects.filter(
                object_type='workspace',
                object_id=ws_id,
                action='join',
                status='waiting',
                proposer=operator.id,
                relation_data=dict(user_id=operator.id, role_id=Role.objects.get(title='ws_member').id)
        ).exists():
            msg = '审批已经存在，请等待审批结果'
        else:
            approve_obj = ApproveInfo.objects.create(
                object_type='workspace',
                object_id=ws_id,
                action='join',
                reason=reason,
                proposer=operator.id,
                relation_data=dict(user_id=operator.id, role_id=Role.objects.get(title='ws_member').id)
            )
            msg = '申请成功，请等待审批结果'
            # 申请加入ws, 发送消息到管理员
            InSiteMsgHandle().apply_join(approve_obj.id)
        return True, msg

    @staticmethod
    def add_member(data, operator):
        emp_id_list = data.get('emp_id_list') or [data.get('emp_id')]
        user_list = []
        role_id = data.get('role_id', '')
        for emp_id in emp_id_list:
            if User.objects.filter(emp_id=emp_id).exists():
                user = User.objects.filter(emp_id=emp_id).first()
                user_list.append(user.id)
        ws_id = data.get('ws_id')
        user_object_list = []
        for user_id in user_list:
            if WorkspaceMember.objects.filter(ws_id=ws_id, user_id=user_id).exists():
                continue
            else:
                user_object_list.append(
                    WorkspaceMember(
                        user_id=user_id,
                        ws_id=ws_id,
                        role_id=role_id if role_id else Role.objects.get(title='ws_member').id
                    )
                )
            # 添加用户并设置ws角色，发送消息到被操作人
            InSiteMsgHandle().by_update_ws_role(operator, user_id, ws_id, role_id)
        if not user_object_list:
            return False, '用户已添加'
        else:
            return True, WorkspaceMember.objects.bulk_create(user_object_list)

    @staticmethod
    def modify_member_role(data, operator):
        """修改ws 下用户角色"""
        ws_id = data.get('ws_id')
        user_id = data.get('user_id')
        role_id = data.get('role_id')
        if user_id == operator:
            return False, '不能修改自己'
        member_obj = WorkspaceMember.objects.filter(ws_id=ws_id, user_id=user_id)
        # 不能修改owner
        member_role_title = Role.objects.get(id=member_obj.first().role_id).title
        if member_role_title == 'ws_owner':
            return False, '不能修改 WS owner'
        # 系统级管理员可以直接修改
        sys_role_id = RoleMember.objects.get(user_id=operator).role_id
        sys_role_title = Role.objects.get(id=sys_role_id).title
        if sys_role_title in {'super_admin', 'sys_admin'}:
            member_obj.update(role_id=role_id)
        else:
            # 当前角色可以设置的角色
            user_member_obj = WorkspaceMember.objects.filter(ws_id=ws_id, user_id=operator).first()
            role = Role.objects.filter(id=user_member_obj.role_id).first()
            if role.id >= member_obj.first().role_id:
                return False, '当前权限不足'
            if Role.objects.filter(title__in=WS_ROLE_MAP.get(role.title), id=role_id).exists():
                member_obj.update(role_id=role_id)
        # 设置ws角色，发送消息到被操作人
        InSiteMsgHandle().by_update_ws_role(operator, user_id, ws_id, role_id, action='update')
        return True, member_obj.first()

    @staticmethod
    def remove_member(data, operator):
        member_list = data.get('user_id_list') or [data.get('user_id')]
        ws_id = data.get('ws_id')
        # 自己不能删除自己
        if operator in member_list:
            return False, '自己不能移除自己'
        # 不能移除owner
        member_obj = WorkspaceMember.objects.filter(ws_id=ws_id, user_id=data.get('user_id'))
        member_role_title = Role.objects.get(id=member_obj.first().role_id).title
        if member_role_title == 'ws_owner':
            return False, '不能移除 WS owner'
        # 系统级管理员可以直接删除除owner外成员
        sys_role_id = RoleMember.objects.get(user_id=operator).role_id
        sys_role_title = Role.objects.get(id=sys_role_id).title
        if sys_role_title not in {'super_admin', 'sys_admin'}:
            # 不能移除角色等级比自己高的
            user_member_obj = WorkspaceMember.objects.filter(ws_id=ws_id, user_id=operator).first()
            role = Role.objects.filter(id=user_member_obj.role_id).first()
            if role.id >= member_obj.first().role_id:
                return False, '当前权限不足'
        with transaction.atomic():
            WorkspaceMember.objects.filter(ws_id=ws_id, user_id__in=member_list).delete()
            WorkspaceAccessHistory.objects.filter(ws_id=ws_id, user_id__in=member_list).delete()
            # 移除ws成员, 发送消息到被操作人
            [InSiteMsgHandle().by_remove(operator, user_id, ws_id) for user_id in member_list]
        return True, '移除成功'


class ApproveService(CommonService):
    @staticmethod
    def filter(queryset, data):
        param_data = dict(
            object_type=data.get('object_type', 'workspace'),
            object_id=data.get('object_id'),
            proposer=data.get('proposer'),
            approver=data.get('approver')
        )
        q = Q()
        status = data.get('status')
        action = data.get('action')
        if param_data['object_type'] == 'workspace':
            if action == 'join':
                q &= Q(action='join')
            else:
                q &= ~Q(action='join')
        if status:
            if status == '0' or status == 0:
                q &= Q(status='waiting')
            else:
                q &= ~Q(status='waiting')
        for field, value in param_data.items():
            if not value:
                continue
            q &= Q(**{field: value})
        return queryset.filter(q)

    def approve(self, data, operator):
        instance_id = data.get('id')
        instance_id_list = data.get('id_list')
        if not instance_id_list:
            instance_id_list = [instance_id]
        action = data.get('action')
        reason = data.get('reason')
        with transaction.atomic():
            for instance_id in instance_id_list:
                instance = ApproveInfo.objects.filter(id=instance_id).first()
                if instance.object_type == 'workspace':
                    self._ws_approve(instance, action, reason, operator)

    def _ws_approve(self, instance, action, reason, operator):  # noqa: C901
        if instance.action == 'create':
            if action == 'pass' and instance.status != 'passed':
                Workspace.objects.filter(id=instance.object_id).update(is_approved=True)
                instance.status = 'passed'
                instance.save()
                workspace = Workspace.objects.filter(id=instance.object_id).first()
                WorkspaceService().add_workspace_relation_data(workspace.id, instance.proposer)
            elif action == 'refuse' and instance.status != 'refused':
                instance.status = 'refused'
                instance.save()
                instance.refuse_reason = reason
                ws = Workspace.objects.filter(id=instance.object_id).first()
                suffix = '[refused at {}]'.format(int(time.time()))
                ws.name = '{}{}'.format(ws.name, suffix)
                ws.show_name = '{}{}'.format(ws.show_name, suffix)
                ws.save()
            instance.approver = operator
            instance.save()
            # 创建审批处理后，发送消息到申请人
            InSiteMsgHandle().handle_apply(instance.id)
        elif instance.action == 'delete':
            if action == 'pass' and instance.status != 'passed':
                with transaction.atomic():
                    Workspace.objects.filter(id=instance.object_id).delete()
                    WorkspaceService().delete_workspace_relation_data(instance.object_id)
                instance.status = 'passed'
            elif action == 'refuse' and instance.status != 'refused':
                instance.status = 'refused'
                instance.refuse_reason = reason
            instance.approver = operator
            instance.save()
            # 注销审批处理后，发送消息到申请人
            InSiteMsgHandle().handle_apply(instance.id)
        elif instance.action == 'join':
            self.apply_join(action, instance, reason, operator)

    @staticmethod
    def apply_join(action, instance, reason, operator):
        if action == 'pass' and instance.status != 'passed':
            with transaction.atomic():
                if not WorkspaceMember.objects.filter(
                        ws_id=instance.object_id,
                        user_id=instance.relation_data.get('user_id'),
                ).exists():
                    WorkspaceMember.objects.create(
                        ws_id=instance.object_id,
                        user_id=instance.relation_data.get('user_id'),
                        role_id=instance.relation_data.get('role_id', Role.objects.get(title='ws_member').id)
                    )
                WorkspaceAccessHistory.objects.create(
                    ws_id=instance.object_id,
                    user_id=instance.relation_data.get('user_id')
                )
            instance.status = 'passed'
        elif action == 'refuse' and instance.status != 'refused':
            instance.status = 'refused'
            instance.refuse_reason = reason
        instance.approver = operator
        instance.save()
        # 加入审批处理后，发送消息到申请人
        InSiteMsgHandle().handle_join(instance.id)


class ApproveQuantityService(object):
    def get_quantity(self, data):
        if data.get('action') == 'join':
            if not data.get('ws_id'):
                return
            apporver_queryset = ApproveInfo.objects.filter(object_type='workspace',
                                                           object_id=data.get('ws_id'), action='join',
                                                           query_scope='all')
        else:
            apporver_queryset = ApproveInfo.objects.all(query_scope='all').exclude(
                object_type='workspace', action='join')
        backlog_count = apporver_queryset.filter(status='waiting').count()
        finished_count = apporver_queryset.filter(~Q(status='waiting')).count()
        return {
            'backlog_count': backlog_count,
            'finished_count': finished_count
        }


class MemberQuantityService(CommonService):
    @staticmethod
    def get_quantity_result(data):
        scope = data.get('scope', 'ws')
        ws_id = data.get('ws_id')
        # 当ws下成员无，角色信息时，默认设置为成员
        WorkspaceMember.objects.filter(ws_id=ws_id, role_id=None).update(role_id=Role.objects.get(title='ws_member').id)
        if scope == 'ws':
            result = {
                'all_count': WorkspaceMember.objects.filter(ws_id=ws_id).count()}
            for user_title in WS_SHOW_MEMBER_CONFIG:
                result.setdefault(user_title, WorkspaceMember.objects.filter(
                    ws_id = ws_id,
                    role_id=Role.objects.get(title=user_title).id
                ).count())
            return result


class UploadService(object):
    def upload(self, data, file):
        file_type = data.get('file_type', 'ws_logo')
        try:
            file_name = str(uuid.uuid4()) + '.' + 'png'
            local_dir = MEDIA_ROOT + file_name
            if not os.path.exists(MEDIA_ROOT):
                os.makedirs(MEDIA_ROOT)
            image = Image.open(file)
            image.save(local_dir)
            if file_type == 'ws_logo':
                server_dir = f'{WS_LOGO_DIR}/{file_name}'
            elif file_type == 'doc_img':
                server_dir = f'{DOC_IMG_DIR}/{file_name}'
            else:
                server_dir = f'/{file_name}'
            ret = sftp_client.upload_file(local_dir, server_dir)
            os.remove(local_dir)
            if ret:
                return file_name, WorkspaceService().get_ws_logo(file_name)
            else:
                logger.error(f'upload ws logo[{file_name}] failed!')
                return '', ''
        except Exception as e:
            logger.error(f'upload ws logo error!{e}')
            return '', ''


class WorkspaceListService(CommonService):

    def filter(self, queryset, request):
        user_id = request.user.id
        scope = request.GET.get('scope', 'all')
        if scope == 'public':
            return self.get_public_ws(queryset)
        elif scope == 'created':
            return self.get_created_by_me_ws(queryset, user_id)
        elif scope == 'joined':
            return self.get_joined_by_me_ws(queryset, user_id)
        elif scope == 'history':
            return self.get_history_ws(user_id)
        return queryset.order_by('-gmt_created')

    def filter_select(self, queryset, request):
        user_id = request.user.id
        scope = request.GET.get('scope', 'all')
        if scope == 'public':
            return self.get_public_ws(queryset)
        elif scope == 'created':
            return self.get_created_by_me_ws(queryset, user_id)
        elif scope == 'joined':
            return self.get_joined_by_me_ws(queryset, user_id)
        elif scope == 'history':
            return self.get_history_ws(user_id)
        return queryset

    @staticmethod
    def get_public_ws(queryset):
        ws_list = list(queryset.filter(is_public=True, is_common=False).order_by('gmt_created'))
        if ws_list:
            ws_list.insert(0, queryset.filter(is_common=True).first())
        else:
            ws_list = [queryset.filter(is_common=True).first()]
        return ws_list

    @staticmethod
    def get_created_by_me_ws(queryset, user_id):
        return queryset.filter(creator=user_id).order_by('gmt_created')

    @staticmethod
    def get_joined_by_me_ws(queryset, user_id):
        return queryset.filter(
            id__in=WorkspaceMember.objects.filter(user_id=user_id).values_list('ws_id', flat=True)
        ).exclude(creator=user_id).order_by('gmt_created')

    @staticmethod
    def get_history_ws(user_id):
        history_ws_id_list = list(WorkspaceAccessHistory.objects.filter(user_id=user_id).
                                  order_by('-id').values_list('ws_id', flat=True))
        history_ws_id_distinct = list(set(history_ws_id_list))
        history_ws_id_distinct.sort(key=history_ws_id_list.index)
        _order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(history_ws_id_distinct)])
        return Workspace.objects.filter(id__in=history_ws_id_distinct, is_approved=True).order_by(_order)


class WorkspaceSelectService(CommonService):

    def filter(self):
        config_list_ws_id = json.loads(
            BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST').values()[0]['config_value']) if \
            BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST') else None
        # 按照config_list_ws_id里面的顺序排列
        if config_list_ws_id:
            preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(config_list_ws_id)])
            queryset = Workspace.objects.filter(Q(Q(id__in=config_list_ws_id) | Q(is_common=True)) &
                                                Q(is_approved=True)).order_by(preserved)
            return queryset
        else:
            queryset = Workspace.objects.filter(is_common=True)
            return queryset

    def update_ws(self):
        config_list_ws_id = json.loads(
            BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST').values()[0][
                'config_value']) if BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST') else None
        # 按照config_list_ws_id里面的顺序排列
        if config_list_ws_id:
            preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(config_list_ws_id)])
            queryset = Workspace.objects.filter(Q(id__in=config_list_ws_id) & Q(is_common=False)).order_by(preserved)
            return queryset
        else:
            queryset = Workspace.objects.filter(Q(id=None) & Q(is_approved=True))
            return queryset

    @staticmethod
    def get_distincts_queryset(queryset, data):
        ws_queryset_list = list(queryset.values())
        ws_start_priority = data.get('from')
        ws_end_priority = data.get('to')
        if ws_start_priority < ws_end_priority:
            ws_queryset_list.insert(ws_end_priority, ws_queryset_list[ws_start_priority - 1])
            del ws_queryset_list[ws_start_priority - 1]
        else:
            ws_queryset_list.insert(ws_end_priority - 1, ws_queryset_list[ws_start_priority - 1])
            del ws_queryset_list[ws_start_priority]
        config_list = []
        for ws_queryset in ws_queryset_list:
            for key, value in ws_queryset.items():
                if key == 'id':
                    config_list.append(ws_queryset['id'])
        if BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST').values():
            BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST').update(config_value=json.dumps(config_list))
        else:
            BaseConfig.objects.create(config_key='SHOW_WS_ID_LIST', config_value=json.dumps(config_list))
        config_list_ws_id = json.loads(
            BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST').values()[0]['config_value'])
        preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(config_list_ws_id)])
        ws_queryset = Workspace.objects.filter(Q(id__in=config_list_ws_id) & Q(is_common=False)).order_by(preserved)
        return True, ws_queryset


class AllWorkspaceService(CommonService):

    def filter(self, request):
        config_list_ws_id = json.loads(
            BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST').values()[0][
                'config_value']) if BaseConfig.objects.filter(config_key='SHOW_WS_ID_LIST') else None
        # 按照config_list_ws_id里面的顺序排列
        if config_list_ws_id:
            preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(config_list_ws_id)])
            # 查找出id在config_list_ws_id或通用的ws，并且审核通过的ws,根据preserved排序,定义为queryset_need_update
            queryset_need_update = Workspace.objects.filter(Q(Q(id__in=config_list_ws_id) | Q(is_common=True)) &
                                                            Q(is_approved=True)).order_by(preserved)
            # 查找出不属于queryset_update并且非通用的ws，定义为queryset_no_need_update
            queryset_dont_need_update = Workspace.objects.filter(is_approved=True,
                                                                 is_common=False).exclude(id__in=queryset_need_update)
            # 定义一个空的列表，按照queryset_update，queryset_update_not的顺序增加到列表中
            queryset = []
            queryset.extend(queryset_need_update)
            queryset.extend(queryset_dont_need_update)
            queryset_id_list = []
            for q in queryset:
                queryset_id_list.append(q.id)
            preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(queryset_id_list)])
            if request.GET.get('keyword'):
                keyword = request.GET.get('keyword')
                queryset = Workspace.objects.filter(Q(name__contains=keyword) | Q(show_name__contains=keyword)) \
                    .order_by(preserved)
            return queryset
        else:
            queryset = Workspace.objects.filter(is_approved=True).order_by('-is_common')
            return queryset


class DashboardListService(CommonService):
    @staticmethod
    def get_ws_data_list(data):
        ws_id = data.get('ws_id')
        ws_data = dict()
        product_queryset = Product.objects.filter(ws_id=ws_id).order_by('drag_modified')
        total_product = product_queryset.count()
        total_project = Project.objects.filter(ws_id=ws_id).count()
        total_job = TestJob.objects.filter(ws_id=ws_id).count()
        total_conf = WorkspaceCaseRelation.objects.filter(ws_id=ws_id).count()
        group_server = TestServer.objects.filter(ws_id=ws_id)
        group_use_num = group_server.filter(state='Occupied').count()
        cloud_server = CloudServer.objects.filter(ws_id=ws_id)
        cloud_use_num = cloud_server.filter(state='Occupied').count()
        server_use_num = group_use_num + cloud_use_num
        server_total_num = group_server.count() + cloud_server.count()
        ws_data.update({
            'total_product': total_product,
            'total_project': total_project,
            'total_job': total_job,
            'total_conf': total_conf,
            'server_use_num': server_use_num,
            'server_total_num': server_total_num,
        })
        product_list = list()
        for tmp_product in product_queryset:
            tmp_product_data = dict()
            product_id = tmp_product.id
            product_name = tmp_product.name
            product_description = tmp_product.description
            product_is_default = tmp_product.is_default
            project_list = list()
            tmp_product_data = product_project(product_id, data, product_name, product_description, product_is_default,
                                               tmp_product, tmp_product_data, project_list)
            product_list.append(tmp_product_data)
        ws_data.update({'product_list': product_list})
        return ws_data


def product_project(product_id, data, product_name, product_description, product_is_default, tmp_product,
                    tmp_product_data, project_list):
    if Project.objects.filter(product_id=product_id):
        func_view_config = BaseConfig.objects.filter(config_type='ws', ws_id=data.get('ws_id'),
                                                     config_key='FUNC_RESULT_VIEW_TYPE').first()
        for tmp_project in Project.objects.filter(product_id=product_id).order_by('drag_modified'):
            if tmp_project.is_show:
                project_id = tmp_project.id
                project_name = tmp_project.name
                project_description = tmp_project.description
                product_version = tmp_project.product_version
                project_is_default = tmp_project.is_default
                job_all = TestJob.objects.filter(product_id=product_id, project_id=project_id).count()
                job_queryset = TestJob.objects.filter(product_id=product_id, project_id=project_id)
                complete_num = job_queryset.filter(state='success').count()
                fail_num = job_queryset.filter(state='fail').count()
                now = datetime.now()
                hours_24_ago = (now - timedelta(days=1))
                day_querys = get_day_querys(data, now, product_id, project_id, hours_24_ago)
                day_query_fail = day_querys.filter(state='fail')
                day_query_pending = day_querys.filter(state__in=['running', 'pending_q'])
                if day_query_fail:
                    state = "fail"
                elif day_query_pending:
                    state = "pending"
                else:
                    state = "success"
                today_query_list = []
                if day_querys:
                    for day_query in day_querys:
                        if day_query.test_result:
                            today_query_list.append({
                                'today_job_id': day_query.id,
                                'today_query_name': day_query.name,
                                'today_query_state':
                                    get_job_state(day_query.id, day_query.test_type, day_query.state, func_view_config),
                                'today_query_pass': json.loads(day_query.test_result)['pass'],
                                'today_query_fail': json.loads(day_query.test_result)['fail'],
                            })
                        elif day_query.state in ['pending_q', 'pending']:
                            today_query_list.append({
                                'today_job_id': day_query.id,
                                'today_query_name': day_query.name,
                                'today_query_job_start_time': datetime.strftime(day_query.start_time,
                                                                                '%Y-%m-%d %H:%M:%S'),
                                'today_query_state': 'pending',
                                'today_query_pass': 0,
                                'today_query_fail': 0,
                            })
                        else:
                            today_query_list.append({
                                'today_job_id': day_query.id,
                                'today_query_name': day_query.name,
                                'today_query_state': day_query.state,
                                'today_query_job_start_time': datetime.strftime(day_query.start_time,
                                                                                '%Y-%m-%d %H:%M:%S'),
                                'today_query_pass': 0,
                                'today_query_fail': 0,
                            })
                else:
                    state = None
                today_job_all = day_querys.count()
                today_job_fail = len(list(filter(lambda x: x.get('today_query_state') in ['fail'], today_query_list)))
                today_job_success = len(list(
                    filter(lambda x: x.get('today_query_state') in ['success', 'pass'], today_query_list)))
                project_list.append({
                    'project_id': project_id,
                    'project_name': project_name,
                    'product_version': product_version,
                    'project_description': project_description,
                    'project_is_default': project_is_default,
                    'project_total_job': job_all,
                    'project_state': state,
                    'complete_num': complete_num,
                    'fail_num': fail_num,
                    'today_job_all': today_job_all,
                    'today_job_fail': today_job_fail,
                    'today_job_success': today_job_success,
                    'today_query': today_query_list,
                })
        tmp_product_data.update({
            'product_id': product_id,
            'product_name': product_name,
            'product_description': product_description,
            'product_create': str(tmp_product.gmt_created).split('.')[0],
            'product_is_default': product_is_default,
            'project_list': project_list,
        })
    else:
        tmp_product_data.update({
            'product_id': product_id,
            'product_name': product_name,
            'product_description': product_description,
            'product_create': str(tmp_product.gmt_created).split('.')[0],
            'product_is_default': product_is_default,
            'project_list': [],
        })
    return tmp_product_data


def get_job_state(test_job_id, test_type, state, func_view_config):
    if state == 'pending_q':
        state = 'pending'
    if test_type == 'functional' and (state == 'fail' or state == 'success'):
        if func_view_config and func_view_config.config_value == '2':
            if not FuncResult.objects.filter(test_job_id=test_job_id).exists():
                state = 'fail'
                return state
            if TestJobCase.objects.filter(job_id=test_job_id, state='fail').exists():
                state = 'fail'
            else:
                if not FuncResult.objects.filter(test_job_id=test_job_id, sub_case_result=2).exists():
                    state = 'pass'
                else:
                    if FuncResult.objects.filter(test_job_id=test_job_id, sub_case_result=2, match_baseline=0).exists():
                        state = 'fail'
                    else:
                        state = 'pass'
    return state


def get_day_querys(data, now, product_id, project_id, hours_24_ago):
    day_querys = TestJob.objects.filter(product_id=product_id, project_id=project_id,
                                        start_time__gte=hours_24_ago,
                                        start_time__lte=now).order_by('-start_time')
    if data.get('hours_24_ago'):
        hours_24_ago = (now - timedelta(days=1))
        day_querys = TestJob.objects.filter(product_id=product_id, project_id=project_id,
                                            start_time__gte=hours_24_ago,
                                            start_time__lte=now).order_by('-start_time')
    elif data.get('hours_48_ago'):
        hours_48_ago = (now - timedelta(days=2))
        day_querys = TestJob.objects.filter(product_id=product_id, project_id=project_id,
                                            start_time__gte=hours_48_ago,
                                            start_time__lte=now).order_by('-start_time')
    elif data.get('seven_day_ago'):
        seven_day_ago = (now - timedelta(days=7))
        day_querys = TestJob.objects.filter(product_id=product_id, project_id=project_id,
                                            start_time__gte=seven_day_ago,
                                            start_time__lte=now).order_by('-start_time')
    elif data.get('date'):
        start_time = data.get('date') + " 00:00:00"
        end_time = data.get('date') + " 23:59:59"
        day_querys = TestJob.objects.filter(product_id=product_id, project_id=project_id,
                                            start_time__gte=start_time, start_time__lte=end_time,
                                            ws_id=data.get('ws_id')).order_by('-start_time')
    return day_querys

