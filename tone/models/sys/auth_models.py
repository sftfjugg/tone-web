from django.contrib.auth.models import AbstractUser
from django.db import models

from tone.models.base.base_models import BaseModel


class User(AbstractUser):
    emp_id = models.CharField(max_length=64, null=True)
    job_desc = models.CharField(max_length=128)
    dep_desc = models.CharField(max_length=255)
    token = models.CharField(max_length=500, null=True, help_text='随机token')

    class Meta:
        db_table = 'user'


class Role(BaseModel):
    ROLE_TYPE_CHOICES = (
        ('system', '系统角色'),
        ('workspace', '工作台角色')
    )
    title = models.CharField(max_length=50, db_index=True, help_text='角色名')
    description = models.CharField(max_length=200, null=True, blank=True, help_text='描述')
    role_type = models.CharField(max_length=64, choices=ROLE_TYPE_CHOICES, null=True, help_text='关联角色类型')

    class Meta:
        db_table = 'role'


class RoleMember(BaseModel):
    user_id = models.IntegerField(db_index=True, help_text='关联User')
    role_id = models.IntegerField(db_index=True, help_text='关联角色')

    class Meta:
        db_table = 'role_member'


class Permission(BaseModel):
    title = models.CharField(max_length=50, db_index=True, help_text='权限名')
    description = models.CharField(max_length=200, null=True, blank=True, help_text='描述')

    class Meta:
        db_table = 'permission'


class PermissionRelation(BaseModel):
    OBJECTION_TYPE_CHOICES = (
        ('role', '角色'),
        ('user', '用户'),
    )
    object_type = models.CharField(max_length=64, choices=OBJECTION_TYPE_CHOICES, help_text='关联对象类型')
    object_id = models.IntegerField(db_index=True, help_text='关联对象ID')
    permission_id = models.IntegerField(db_index=True, help_text='关联权限')

    class Meta:
        db_table = 'permission_relation'
