# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from importlib import import_module


def load_operations_module(operation_module):
    operation_object_list = list()
    operation_type_list = list()
    for module in operation_module:
        obj = import_module(module)
        operation_object_list.extend(getattr(obj, 'OPERATION_OBJECT_LIST'))
        operation_type_list.extend(getattr(obj, 'OPERATION_TYPE_LIST'))
    return operation_object_list, operation_type_list
