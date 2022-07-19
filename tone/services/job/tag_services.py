# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from django.db.models import Q
from django.db import transaction

from tone.models import JobTag, JobTagRelation, WorkspaceMember, Role, TestJob, RoleMember, TemplateTagRelation
from tone.core.common.services import CommonService
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import JobTagException


class JobTagService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(id=data.get('tag_id')) if data.get('tag_id') else q
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        q &= Q(name__icontains=data.get('name')) if data.get('name') else q
        q &= Q(creator=data.get('creator')) if data.get('creator') else q
        q &= Q(update_user=data.get('update_user')) if data.get('update_user') else q
        q &= Q(tag_color=data.get('tag_color')) if data.get('tag_color') else q
        q &= Q(description__icontains=data.get('description')) if data.get('description') else q
        return sorted(queryset.filter(q), key=lambda x: (0 if not x.creator else 1, -x.id))

    def update(self, data, operator):
        tag_id = data.get('tag_id')
        assert tag_id, JobTagException(ErrorCode.TAG_ID_NEED)
        if not operator:
            raise JobTagException(ErrorCode.LOGIN_ERROR)
        self.check_id(tag_id)
        # 不能修改系统标签
        obj = JobTag.objects.get(id=tag_id)
        if obj.name in {'analytics', 'nightly'}:
            return False
        # 非系统管理员super_admin, sys_admin ws_member 只能修改自己
        sys_role_id = RoleMember.objects.get(user_id=operator.id).role_id
        sys_role = Role.objects.get(id=sys_role_id).title
        if sys_role not in ['super_admin', 'sys_admin']:
            operator_role_id = WorkspaceMember.objects.get(ws_id=obj.ws_id, user_id=operator.id).role_id
            operator_role = Role.objects.get(id=operator_role_id).title
            allow_list = ['ws_owner', 'ws_admin', 'ws_test_admin']
            if operator_role not in allow_list and operator.id != obj.creator:
                return False
        for key, value in data.items():
            if key == 'name':
                if value != obj.name:
                    self.check_name(value, obj.ws_id)
            if hasattr(obj, key):
                setattr(obj, key, value)
            else:
                pass
        obj.update_user = operator.id
        obj.save()
        return True

    def create(self, data, operator):
        name = data.get('name')
        creator = operator.id
        description = data.get('description')
        tag_color = data.get('tag_color')
        ws_id = data.get('ws_id')
        assert name, JobTagException(ErrorCode.NAME_NEED)
        assert ws_id, JobTagException(ErrorCode.WS_NEED)
        if not operator:
            raise JobTagException(ErrorCode.LOGIN_ERROR)
        self.check_name(name, ws_id)
        JobTag.objects.create(name=name, description=description, creator=creator, tag_color=tag_color,
                              ws_id=ws_id)

    def delete(self, data, operator):
        tag_id = data.get('tag_id')
        if not operator:
            raise JobTagException(ErrorCode.LOGIN_ERROR)
        assert tag_id, JobTagException(ErrorCode.TAG_ID_NEED)
        self.check_id(tag_id)
        # 不能删除系统标签
        obj = JobTag.objects.get(id=tag_id)
        if obj.name in {'analytics', 'nightly'}:
            return False
        # 非系统管理员super_admin, sys_admin ws_member 只能修改自己
        sys_role_id = RoleMember.objects.get(user_id=operator.id).role_id
        sys_role = Role.objects.get(id=sys_role_id).title
        if sys_role not in ['super_admin', 'sys_admin']:
            operator_role_id = WorkspaceMember.objects.get(ws_id=obj.ws_id, user_id=operator.id).role_id
            operator_role = Role.objects.get(id=operator_role_id).title
            allow_list = ['ws_owner', 'ws_admin', 'ws_test_admin']
            if operator_role not in allow_list and operator.id != obj.creator:
                return False
        JobTag.objects.filter(id=tag_id).delete()
        TemplateTagRelation.objects.filter(tag_id=tag_id).delete()
        JobTagRelation.objects.filter(tag_id=tag_id).delete()
        return True

    @staticmethod
    def check_name(name, ws_id):
        obj = JobTag.objects.filter(name=name, ws_id=ws_id)
        if obj.exists():
            raise JobTagException(ErrorCode.TAG_DUPLICATION)

    @staticmethod
    def check_id(tag_id):
        obj = JobTag.objects.filter(id=tag_id)
        if not obj.exists():
            raise JobTagException(ErrorCode.TAG_NONEXISTENT)


class JobTagRelationService(CommonService):

    @staticmethod
    def create(data, operator):
        tag_ids = data.get('tag_id')
        job_id = data.get('job_id')
        assert job_id, JobTagException(ErrorCode.JOB_NEED)
        if not isinstance(tag_ids, list):
            raise JobTagException(ErrorCode.TAG_ID_NEED)
        # 非系统管理员super_admin, sys_admin ws_member 只能修改自己
        sys_role_id = RoleMember.objects.get(user_id=operator.id).role_id
        sys_role = Role.objects.get(id=sys_role_id).title
        if sys_role not in ['super_admin', 'sys_admin']:
            obj = TestJob.objects.get(id=job_id)
            operator_role_id = WorkspaceMember.objects.get(ws_id=obj.ws_id, user_id=operator.id).role_id
            operator_role = Role.objects.get(id=operator_role_id).title
            allow_list = ['ws_owner', 'ws_admin', 'ws_test_admin']
            if operator_role not in allow_list and operator.id != obj.creator:
                return False
        with transaction.atomic():
            JobTagRelation.objects.filter(job_id=job_id).delete()
            [JobTagRelation.objects.create(job_id=job_id, tag_id=tag_id) for tag_id in tag_ids]
        return True
