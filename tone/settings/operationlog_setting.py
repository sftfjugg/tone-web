# _*_ coding:utf-8 _*_
"""
Module Description: 日志记录操作模块注册工厂
Date:
Author: Yfh
"""
from tone.core.common.load_files import load_operations_module
OPERATION_CLS = [
    'tone.core.common.operation_module.machine_management',
]

OPERATION_OBJECT_LIST, OPERATION_TYPE_LIST = load_operations_module(OPERATION_CLS)
