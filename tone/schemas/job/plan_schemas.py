# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author:
"""
from tone.core.common.schemas import BaseSchema


class PlanListSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': '通过ws id过滤'},
            'name': {'type': str, 'required': False, 'example': '计划名称', 'desc': '通过计划名称过滤'},
            'enable': {'type': bool, 'required': False, 'example': 'True', 'desc': '通过是否启用过滤'},
            'creator': {'type': int, 'required': False, 'example': 2, 'desc': '通过创建人过滤'},
            'id': {'type': int, 'required': False, 'example': 2, 'desc': '通过plan id过滤'},
        }

    def get_body_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': '所属ws id'},
            'name': {'type': str, 'required': True, 'example': '计划名称', 'desc': '计划名称'},
            'description': {'type': str, 'required': False, 'example': '计划描述', 'desc': '计划描述'},
            'project_id': {'type': int, 'required': False, 'example': 184, 'desc': '项目的id'},
            'func_baseline': {'type': int, 'required': False, 'example': 329, 'desc': '功能基线的id'},
            'perf_baseline': {'type': int, 'required': False, 'example': '', 'desc': '性能基线的id'},
            'test_obj': {'type': str, 'required': False, 'example': 'kernel', 'desc': '测试类型(kernel / rpm)'},
            'kernel_version': {'type': str, 'required': False, 'example': 'x86_64',
                               'desc': '内核版本, 用来区分 已发布/未发布'},
            'env_info': {'type': str, 'required': False, 'example': 'a=1,b=2,c=3', 'desc': '全局变量'},
            'subject': {'type': str, 'required': False, 'example': '[Tone]您的测试已完成', 'desc': '通知主题'},
            'ding_talk_info': {'type': str, 'required': False, 'example': '123', 'desc': '钉钉通知'},
            'email_info': {'type': str, 'required': False, 'example': 'wxx@123.com', 'desc': '邮件通知'},
            'enable': {'type': bool, 'required': False, 'example': True, 'desc': '是否启用'},
            'env_prep': {'type': dict, 'required': False, 'example': {
                'name': '环境准备',
                'machine_info': [{'machine': '1.2.3.4', 'script': 'ls'}]}, 'desc': '环境准备配置'},
            'test_config': {'type': list, 'required': False, 'example': [
                {'name': '运行阶段1', 'template': [86, 87], 'impact_next': True},
                {'name': '运行阶段2', 'template': [88], 'impact_next': False}], 'desc': '测试阶段配置'},
            'cron_schedule': {'type': bool, 'required': False, 'example': True, 'desc': '是否周期触发'},
            'cron_info': {'type': str, 'required': False, 'example': '0 21 * * 1-6', 'desc': 'crontab定时信息'},
            'blocking_strategy': {'type': int, 'required': False, 'example': 1,
                                  'desc': '阻塞策略(1: 忽略前序计划，直接同时执行 2: 中止前序运行中计划,再执行 '
                                          '3: 有前序运行中的计划，忽略本次执行'}
        }


class PlanDetailSchema(BaseSchema):
    def get_param_data(self):
        return {
            'id': {'type': int, 'required': True, 'example': 2, 'desc': '计划 id'},
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': 'ws id用来校验ws下权限'},
        }

    def get_update_data(self):
        return {
            'plan_id': {'type': int, 'required': True, 'example': 2, 'desc': '计划 id'},
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': '所属ws id'},
            'name': {'type': str, 'required': True, 'example': '计划名称', 'desc': '计划名称'},
            'description': {'type': str, 'required': False, 'example': '计划描述', 'desc': '计划描述'},
            'project_id': {'type': int, 'required': False, 'example': 184, 'desc': '项目的id'},
            'func_baseline': {'type': int, 'required': False, 'example': 329, 'desc': '功能基线的id'},
            'perf_baseline': {'type': int, 'required': False, 'example': '', 'desc': '性能基线的id'},
            'test_obj': {'type': str, 'required': False, 'example': 'kernel', 'desc': '测试类型(kernel / rpm)'},
            'kernel_version': {'type': str, 'required': False, 'example': 'x86_64',
                               'desc': '内核版本, 用来区分 已发布/未发布'}, 'desc': '内核信息（已发布、未发布）',
            'env_info': {'type': str, 'required': False, 'example': 'a=1,b=2,c=3', 'desc': '全局变量'},
            'subject': {'type': str, 'required': False, 'example': '[Tone]您的测试已完成', 'desc': '通知主题'},
            'ding_talk_info': {'type': str, 'required': False, 'example': 'xxx', 'desc': '钉钉通知'},
            'email_info': {'type': str, 'required': False, 'example': 'xx@163.com', 'desc': '邮件通知'},
            'enable': {'type': bool, 'required': False, 'example': True, 'desc': '是否启用'},
            'env_prep': {'type': dict, 'required': False, 'example': {
                'name': '环境准备',
                'machine_info': [{'machine': '1.2.3.4', 'script': 'ls'}]}, 'desc': '环境准备配置'},
            'test_config': {'type': list, 'required': False, 'example': [
                {'name': '运行阶段1', 'template': [86, 87], 'impact_next': True},
                {'name': '运行阶段2', 'template': [88], 'impact_next': False}], 'desc': '测试阶段配置'},
            'cron_schedule': {'type': bool, 'required': False, 'example': True, 'desc': '是否周期触发'},
            'cron_info': {'type': str, 'required': False, 'example': '0 21 * * 1-6', 'desc': 'crontab定时信息'},
            'blocking_strategy': {'type': int, 'required': False, 'example': 1,
                                  'desc': '阻塞策略(1: 忽略前序计划，直接同时执行 2: 中止前序运行中计划,再执行 '
                                          '3: 有前序运行中的计划，忽略本次执行'}
        }

    def get_delete_data(self):
        return {
            'plan_id': {'type': int, 'required': True, 'example': 2, 'desc': '计划 id'},
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': 'ws id用来校验ws下权限'},
        }


class PlanCopySchema(BaseSchema):
    def get_body_data(self):
        return {
            'plan_id': {'type': int, 'required': True, 'example': 2, 'desc': '拷贝的计划 id'},
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': 'ws id用来校验ws下权限'},
        }


class PlanRunSchema(BaseSchema):
    def get_body_data(self):
        return {
            'is_save': {'type': bool, 'required': True, 'example': True, 'desc': '运行时是否保存计划配置'},
            'plan_id': {'type': int, 'required': True, 'example': 2, 'desc': '计划 id'},
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': '所属ws id'},
            'name': {'type': str, 'required': True, 'example': '计划名称', 'desc': '计划名称'},
            'description': {'type': str, 'required': False, 'example': '计划描述', 'desc': '计划描述'},
            'project_id': {'type': int, 'required': False, 'example': 184, 'desc': '项目的id'},
            'func_baseline': {'type': int, 'required': False, 'example': 329, 'desc': '功能基线的id'},
            'perf_baseline': {'type': int, 'required': False, 'example': '', 'desc': '性能基线的id'},
            'test_obj': {'type': str, 'required': False, 'example': 'kernel', 'desc': '测试类型(kernel / rpm)'},
            'kernel_version': {'type': str, 'required': False, 'example': 'x86_64',
                               'desc': '内核版本, 用来区分 已发布/未发布'},
            'env_info': {'type': str, 'required': False, 'example': 'a=1,b=2,c=3', 'desc': '全局变量'},
            'subject': {'type': str, 'required': False, 'example': '[Tone]您的测试已完成', 'desc': '通知主题'},
            'ding_talk_info': {'type': str, 'required': False, 'example': 'xxx', 'desc': '钉钉通知'},
            'email_info': {'type': str, 'required': False, 'example': 'xx@163.com', 'desc': '邮件通知'},
            'enable': {'type': bool, 'required': False, 'example': True, 'desc': '是否启用'},
            'env_prep': {'type': dict, 'required': False, 'example': {
                'name': '环境准备',
                'machine_info': [{'machine': '1.2.3.4', 'script': 'ls'}]}, 'desc': '环境准备配置'},
            'test_config': {'type': list, 'required': False, 'example': [
                {'name': '运行阶段1', 'template': [86, 87], 'impact_next': True},
                {'name': '运行阶段2', 'template': [88], 'impact_next': False}], 'desc': '测试阶段配置'},
            'cron_schedule': {'type': bool, 'required': False, 'example': True, 'desc': '是否周期触发'},
            'cron_info': {'type': str, 'required': False, 'example': '0 21 * * 1-6', 'desc': 'crontab定时信息'},
            'blocking_strategy': {'type': int, 'required': False, 'example': 1,
                                  'desc': '阻塞策略(1: 忽略前序计划，直接同时执行 2: 中止前序运行中计划,再执行 '
                                          '3: 有前序运行中的计划，忽略本次执行'}
        }


class PlanViewSchema(BaseSchema):
    def get_param_data(self):
        return {
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': '通过ws id过滤计划视图'},
        }


class PlanResultSchema(BaseSchema):
    def get_param_data(self):
        return {
            'plan_id': {'type': int, 'required': True, 'example': 2, 'desc': '通过计划 id过滤计划实例'},
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': 'ws id用来校验ws下权限'},
        }

    def get_delete_data(self):
        return {
            'plan_instance_id': {'type': int, 'required': True, 'example': 2, 'desc': '计划运行实例的id'},
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': 'ws id用来校验ws下权限'},
        }


class PlanResultDetailSchema(BaseSchema):
    def get_param_data(self):
        return {
            'plan_instance_id': {'type': int, 'required': True, 'example': 2, 'desc': '计划运行实例的id'},
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': 'ws id用来校验ws下权限'},
        }

    def get_body_data(self):
        return {
            'plan_instance_id': {'type': int, 'required': True, 'example': 2, 'desc': '计划运行实例的id'},
            'note': {'type': int, 'required': True, 'example': '备注信息', 'desc': '修改的备注信息'},
            'ws_id': {'type': str, 'required': True, 'example': 'ah9m9or5', 'desc': 'ws id用来校验ws下权限'},
        }
