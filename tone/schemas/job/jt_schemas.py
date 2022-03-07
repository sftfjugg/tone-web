# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from tone.core.common.schemas import BaseSchema


class JobTypeSchema(BaseSchema):

    def get_param_data(self):
        return {
            'operation_object': {'type': str, 'required': False, 'example': 'machine_test_server', 'desc': '操作对象'},
        }

    def get_body_data(self):
        return {
            'name': {'type': str, 'required': True, 'example': 'test_example', 'desc': 'JobType名称'},
            'is_default': {'type': bool, 'required': False, 'example': False, 'desc': '是否系统默认'},
            'test_type': {'type': str, 'required': True, 'example': 'function', 'desc': '测试类型'},
            'server_type': {'type': str, 'required': True, 'example': 'aligroup', 'desc': '机器类型'},
            'ws_id': {'type': str, 'required': True, 'example': '2vjy2z7g', 'desc': 'workspace id'},
            'item_dict': {'type': dict, 'required': True, 'example': {"49": None, "50": "test_alias"},
                          'desc': '关联item的id和别名，没有别名就为None'},
        }


class JobItemSchema(BaseSchema):

    def get_param_data(self):
        return {}
