from django.db import transaction

from initial.base_config.initialize import BaseConfigDataInitialize
from initial.job_type.initialize import JobTypeDataInitialize
from initial.role_type.initialize import RoleTypeDataInitialize
from initial.workspace.initialize import WorkspaceDataInitialize
from tone.models import RoleMember, User, Role


def initialize_all():
    # 基础配置
    with transaction.atomic():
        BaseConfigDataInitialize().initialize_base_config()
        # Job类型配置项
        JobTypeDataInitialize().initialize_job_type_item()
        # 角色配置项
        RoleTypeDataInitialize().initialize_role_type_item()
        # 公共ws
        WorkspaceDataInitialize().initialize_common_ws()
    return 'success!'


def set_admin(username):
    if not User.objects.filter(username=username).exists():
        return f'The user {username} does not exist; Please register first!'
    RoleMember.objects.filter(
        user_id=User.objects.get(username=username).id
    ).update(
        role_id=Role.objects.get(title='sys_admin').id
    )
    return 'success!'
