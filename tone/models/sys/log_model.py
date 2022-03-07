# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from django.db import models
from tone.models import BaseModel
from django_extensions.db.fields.json import JSONField


class OperationLogs(BaseModel):
    OPERATION_TYPE_CHOICES = (
        ('update', '更新'),
        ('create', '新增'),
        ('delete', '删除'),
    )

    operation_type = models.CharField(max_length=64, choices=OPERATION_TYPE_CHOICES, default='', help_text='操作类型')
    operation_object = models.CharField(max_length=128, default='', help_text='操作模块')
    db_table = models.CharField(max_length=64, default='', null=True, help_text='操作的数据表')
    db_pid = models.CharField(max_length=64, default='', help_text='操作的数据行主键id')
    old_values = JSONField(default='', help_text='变更前字段map', null=True, blank=True)
    new_values = JSONField(default='', help_text='变更后字段map', null=True, blank=True)
    operation_sn = models.CharField(max_length=64, default='', help_text='操作号uuid')
    creator = models.CharField(max_length=64, null=True, help_text='操作人')

    class Meta:
        db_table = 'operation_logs'
