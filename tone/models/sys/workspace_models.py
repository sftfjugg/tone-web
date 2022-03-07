from django.db import models
from django_extensions.db.fields import json

from tone.models.base.base_models import BaseModel


class Workspace(BaseModel):
    id = models.CharField(primary_key=True, max_length=8, help_text='WS唯一id')
    name = models.CharField(max_length=128, db_index=True, unique=True, help_text='名称')
    show_name = models.CharField(max_length=128, db_index=True, unique=True, help_text='显示名称')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    owner = models.IntegerField(help_text='Owner')
    is_public = models.BooleanField(help_text='是否公开')
    is_common = models.BooleanField(help_text='是否是通用的ws', default=False)
    is_approved = models.BooleanField(default=False, help_text='审核是否通过')
    logo = models.CharField(max_length=255, default='', help_text='logo图片')
    theme_color = models.CharField(max_length=64, default='')
    creator = models.IntegerField(help_text='创建者')
    is_show = models.BooleanField(default=False, help_text='是否显示')
    priority = models.IntegerField(default=10, help_text='优先级')

    class Meta:
        db_table = 'workspace'


class Project(BaseModel):
    name = models.CharField(max_length=128, db_index=True, help_text='名称')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')
    product_id = models.IntegerField(help_text='关联product', null=True)
    product_version = models.CharField(max_length=128, null=True, blank=True, db_index=True, help_text='产品版本')
    is_default = models.BooleanField(default=False, help_text='是否默认')
    priority = models.IntegerField(default=10, help_text="显示优先级")
    drag_modified = models.DateTimeField(auto_now_add=True, help_text='拖拽修改时间', null=True, blank=True)
    is_show = models.BooleanField(default=False, help_text='是否统计dashboard')

    class Meta:
        db_table = 'project'


class Product(BaseModel):
    name = models.CharField(max_length=128, db_index=True, help_text='名称')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    command = models.CharField(max_length=512, null=True, blank=True, help_text='获取版本的命令')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')
    is_default = models.BooleanField(default=False, help_text='是否默认')
    priority = models.IntegerField(default=10, help_text="显示优先级")
    drag_modified = models.DateTimeField(auto_now_add=True, help_text='拖拽修改时间', null=True, blank=True)

    class Meta:
        db_table = 'product'


class Repo(BaseModel):
    name = models.CharField(max_length=128, db_index=True, help_text='名称')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    git_url = models.CharField(max_length=512, null=True, blank=True, help_text='仓库路径')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')

    class Meta:
        db_table = 'repo'


class RepoBranch(BaseModel):
    name = models.CharField(max_length=128, db_index=True, help_text='名称')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    repo_id = models.IntegerField(help_text='关联repository')

    class Meta:
        db_table = 'repo_branch'


class ProjectBranchRelation(BaseModel):
    project_id = models.IntegerField(help_text='关联project')
    branch_id = models.IntegerField(help_text='branch')
    repo_id = models.IntegerField(help_text='关联project')
    is_master = models.BooleanField(default=False, help_text='是否为主仓库')

    class Meta:
        db_table = 'project_branch_relation'


class WorkspaceMember(BaseModel):
    user_id = models.IntegerField(db_index=True, help_text='关联用户')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')
    role_id = models.IntegerField(db_index=True, null=True, help_text='关联角色')

    class Meta:
        db_table = 'workspace_member'


class WorkspaceAccessHistory(BaseModel):
    user_id = models.IntegerField(db_index=True, help_text='关联用户')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')

    class Meta:
        db_table = 'workspace_access_history'


class AtomicConfig(BaseModel):
    CONFIG_TYPE_CHOICES = (
        ('aligroup', '集团内测试'),
        ('cloud', '云上测试')
    )
    name = models.CharField(max_length=64, help_text='配置项名称')
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='配置项描述')
    config_type = models.CharField(max_length=32, choices=CONFIG_TYPE_CHOICES, help_text='配置项类型')
    show_index = models.IntegerField(help_text='显示顺序')

    class Meta:
        db_table = 'atomic_config'


class AtomicMutexConfig(BaseModel):
    atomic_config_id = models.IntegerField(help_text='关联配置项')
    mutex_config_id = models.IntegerField(help_text='互斥配置项')

    class Meta:
        db_table = 'atomic_mutex_config'


class ProjectAtomicConfig(BaseModel):
    atomic_config_id = models.IntegerField(help_text='关联配置项')
    ws_id = models.CharField(max_length=8, help_text='关联Workspace')
    project_id = models.IntegerField(help_text='关联Project')

    class Meta:
        db_table = 'project_atomic_config'


class ApproveInfo(BaseModel):
    APPROVE_TYPE_CHOICES = (
        ('workspace', '工作组'),
        ('role', '角色'),
        ('permission', '权限'),
    )

    ACTION_CHOICES = (
        ('create', '创建'),
        ('delete', '注销'),
        ('join', '加入'),
    )
    STATUS_CHOICES = (
        ('waiting', '待审核'),
        ('passed', '已通过'),
        ('refused', '已拒绝'),
    )
    object_type = models.CharField(max_length=32, choices=APPROVE_TYPE_CHOICES, help_text='申请类型', db_index=True)
    object_id = models.CharField(max_length=8, help_text='申请对象ID', db_index=True)
    relation_data = json.JSONField(default={}, help_text='关联数据')
    reason = models.CharField(max_length=1024, help_text='申请理由', null=True, blank=True, db_index=True)
    action = models.CharField(max_length=32, choices=ACTION_CHOICES, help_text='操作类型')
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='waiting', help_text='审批状态', db_index=True)
    proposer = models.IntegerField(help_text='申请人', db_index=True)
    approver = models.IntegerField(help_text='审批人', null=True, blank=True, db_index=True)
    refuse_reason = models.CharField(max_length=512, null=True, blank=True)

    class Meta:
        db_table = 'approve_info'
