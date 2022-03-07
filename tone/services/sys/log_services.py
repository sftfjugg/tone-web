# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from tone.core.common.services import CommonService


class OperationLogsService(CommonService):

    @staticmethod
    def filter(queryset, data):
        operation_object = data.get('operation_object')
        pid = data.get('pid')
        if operation_object and pid:
            return queryset.filter(db_pid=pid, operation_object=operation_object)
        elif operation_object:
            return queryset.filter(operation_object=operation_object)
        else:
            return queryset
