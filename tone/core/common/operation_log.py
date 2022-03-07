# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import uuid
from django.conf import settings
from tone.models.sys.log_model import OperationLogs
from django.db import transaction


class LogRecordOperation(object):

    def __init__(self, creator, operation_type, operation_object, table=None):
        self.creator = creator
        self.table = table
        self.operation_type = self.check_operation_type(operation_type)
        self.operation_object = self.check_operation_object(operation_object)

    @staticmethod
    def check_operation_type(operation_type):
        if operation_type not in settings.OPERATION_TYPE_LIST:
            raise ValueError('操作类型不符合')
        else:
            return operation_type

    @staticmethod
    def check_operation_object(operation_object):
        if operation_object not in settings.OPERATION_OBJECT_LIST:
            raise ValueError('操作模块不符合')
        else:
            return operation_object

    def update(self, pid, operation_sn, values_li):
        old_values = dict()
        new_values = dict()
        for value in values_li:
            if value[1] != value[2]:
                old_values[value[0]] = value[1]
                new_values[value[0]] = value[2]
        # 数据发生修改时保存日志记录
        if old_values != new_values:
            OperationLogs.objects.create(
                operation_type=self.operation_type,
                operation_object=self.operation_object,
                creator=self.creator,
                db_table=self.table,
                db_pid=pid,
                operation_sn=operation_sn,
                old_values=old_values,
                new_values=new_values,
            )

    def create_delete(self, pid, operation_sn):
        OperationLogs.objects.create(
            operation_type=self.operation_type,
            operation_object=self.operation_object,
            creator=self.creator,
            db_table=self.table,
            db_pid=pid,
            operation_sn=operation_sn,
        )


def operation(operation_li):
    if not isinstance(operation_li, list):
        raise ValueError('操作对象必须是列表')
    operation_sn = str(uuid.uuid4())
    with transaction.atomic():
        for op in operation_li:
            if not isinstance(op, dict):
                raise ValueError('操作对象中元素必须是字典')
            creator = op.get('creator')
            table = op.get('table')
            operation_type = op.get('operation_type')
            operation_object = op.get('operation_object')
            pid = op.get('pid')
            assert pid, ValueError('pid is needed')
            assert operation_type, ValueError('operation_type is needed')
            assert operation_object, ValueError('operation_object is needed')
            obj = LogRecordOperation(creator=creator, table=table, operation_type=operation_type,
                                     operation_object=operation_object)
            if operation_type == 'update':
                values_li = op.get('values_li')
                if not isinstance(values_li, list):
                    raise ValueError('values_li must be list')
                obj.update(pid, operation_sn, values_li)
            else:
                obj.create_delete(pid, operation_sn)
