# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author:
"""
import logging
import re
import random

import croniter
from apscheduler.triggers.cron import CronTrigger
from django.db.models import Q
from django.db import transaction

from tone.core.common.job_result_helper import get_server_ip_sn
from tone.core.handle.report_handle import ReportHandle
from tone.core.schedule.schedule_handle import ScheduleHandle
from tone.core.schedule.schedule_job import TestPlanScheduleJob
from tone.core.schedule.single_scheduler import scheduler
from tone.core.utils.common_utils import pack_env_infos
from tone.core.utils.permission_manage import check_operator_permission
from tone.models import TestPlan, PlanStageRelation, PlanStagePrepareRelation, PlanStageTestRelation, datetime, \
    PlanInstance, PlanInstanceStageRelation, PlanInstancePrepareRelation, PlanInstanceTestRelation, ScheduleMap, \
    Project, TestTemplate, JobType
from tone.core.common.services import CommonService
from tone.services.plan.complete_plan_report import plan_create_report

logger = logging.getLogger('test_plan')


def random_choice_str(num=4):
    choice_str = 'abcdefghijklmnopqrstuvwxyz'
    return ''.join([random.choice(choice_str) for _ in range(num)])


def template_get_test_type(template_id):
    template_obj = TestTemplate.objects.filter(id=template_id, query_scope='all').first()
    return JobType.objects.filter(id=template_obj.job_type_id, query_scope='all').first().test_type


class PlanService(CommonService):
    @staticmethod
    def filter(queryset, data):
        """过滤计划"""
        q = Q()
        q &= Q(id=data.get('id')) if data.get('id') else q
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        q &= Q(name__icontains=data.get('name')) if data.get('name') else q
        q &= Q(enable=data.get('enable')) if data.get('enable') else q
        q &= Q(creator=data.get('creator')) if data.get('creator') else q
        return queryset.filter(q)

    @staticmethod
    def filter_plan_view(queryset, data):
        ws_id = data.get('ws_id')
        plan_id = data.get('plan_id')
        product_version = data.get('product_version')
        if plan_id:
            return False, queryset.filter(ws_id=ws_id, id=plan_id).first()
        elif product_version:
            project_id_list = Project.objects.filter(product_version=product_version).values_list('id', flat=True)
            return True, queryset.filter(ws_id=ws_id, project_id__in=project_id_list)
        else:
            plan_instance_list = PlanInstance.objects.filter(ws_id=ws_id).values_list('plan_id', flat=True)
            return True, queryset.filter(ws_id=ws_id, id__in=set(plan_instance_list))

    @staticmethod
    def get_env_info(origin_env_info):
        """获取全局变量"""
        return pack_env_infos(origin_env_info)

    def create_plan(self, data, operator):
        """
        创建测试计划
        一、基础配置信息：
        1.计划名称  唯一，64
        2.计划描述  非必填，200
        3.project   必填， 项目下拉列表
        4.测试基线（功能）
        5.测试基线（性能）基线二选一
        6.被测对象  默认：内核包
        7.内核： 安装已发布、安装未发布、Build内核
                内核版本、kernel包、devel包、headers包、hotfix
        8.全局变量   非必填
        9.通知主题
        10.邮件主题
        11.钉钉通知
        12.启用  默认True
        二、测试配置信息：
        开始   必须有一个阶段，最多五个阶段，一个最多10个模板
        环境准备，
            添加机器 输入ip/sn
            自定义脚本
        第一阶段  添加阶段
        阶段序号
        阶段名称
        是否影响后续步骤，默认：False
        添加模板 ，返回模板列表
        三、触发配置
        1.定时触发  默认False
        2.触发规则        推算下次触发时间
        3.阻塞处理策略
            忽略前序计划，直接同时执行（默认选中）
            中止前序运行中计划，再执行
            有前序运行中计划，忽略本次执行

        {
            'name': '计划名称',
            'description': '计划描述',
            'project_id': 1,    #  '项目的id'
            'baseline_info': {'functional': 2, 'performance': 3},    #  '测量基线信息'
            'test_obj': 'kernel'    # 被测对象   kernel / rpm
            'kernel_info': {}       # 内核信息
            'rpm_info': {}          # rpm包信息
            'env_info': {}   # 全局变量
            'notice_info':  {'subject': '',     # 通知主题
                             'ding_talk_info': '',   # 钉钉通知
                             'email_info': ''        # 邮件通知
                            }   # 通知设置
            'enable': True,     # 是否启用
            'test_config':                    # 测试配置
            'cron_schedule':
            'cron_info':                   #
            'blocking_strategy':           # 阻塞策略
        }
        """
        create_data = dict()
        success, msg = self.check_plan_name(data)
        if not success:
            return False, msg

        update_fields = ['ws_id', 'name', 'description', 'project_id', 'test_obj', 'enable', 'cron_schedule',
                         'cron_info', 'blocking_strategy', 'auto_report', 'report_name', 'report_description',
                         'group_method', 'base_group', 'stage_id']
        if not data.get('cron_schedule'):
            data['cron_schedule'] = False
            create_data['blocking_strategy'] = 0
        for write_field in update_fields:
            write_data = data.get(write_field)
            if write_data:
                create_data[write_field] = write_data.strip() if isinstance(write_data, str) else write_data
        baseline_info = self.pack_baseline_info(data)

        rpm_info = list()
        if data.get('rpm_info', ''):
            rpm_info = data.get('rpm_info').replace('\n', ',').split(',')

        create_data.update({
            'baseline_info': baseline_info,
            'kernel_info': data.get('kernel_info', dict()),
            'kernel_version': data.get('kernel_version'),
            'build_pkg_info': data.get('build_pkg_info', dict()),
            'rpm_info': rpm_info,
            'script_info': data.get('scripts', list()),
            'env_info': self.get_env_info(data.get('env_info', '')),
            'notice_info': self.pack_notice_info(data.get('email_info', None),
                                                 data.get('ding_talk_info', None),
                                                 data.get('notice_name', None)),
            'creator': operator,
            'report_tmpl_id': data.get('report_template_id'),
        })
        # 创建计划
        success, msg = self.check_stage_relation(data)
        if not success:
            return False, msg
        plan_obj = TestPlan.objects.create(**create_data)
        self.create_plan_relation(data, plan_obj.id)
        # 当计划开启时，添加触发任务
        if plan_obj.enable and plan_obj.cron_schedule:
            PlanScheduleService().add_plan_to_schedule(plan_obj.id)
        return True, plan_obj

    @staticmethod
    def pack_notice_info(email=None, ding=None, subject=None):
        """
        组装notice_info信息
        """
        notice_info = list()
        if email:
            email_data = {'type': 'email', "to": email}
            if subject:
                email_data['subject'] = subject
            notice_info.append(email_data)
        if ding:
            ding_data = {'type': 'ding', "to": ding}
            if subject:
                ding_data['subject'] = subject
            notice_info.append(ding_data)
        return notice_info

    @staticmethod
    def check_plan_name(data):
        name = data.get('name', '')
        if not name.strip():
            return False, '计划名称不能为空'
        # 计划名称不能重复
        if TestPlan.objects.filter(name=name).exists():
            return False, '计划名称已存在'
        return True, ''

    @staticmethod
    def check_stage_relation(data):
        msg = ''
        if data.get('test_config'):
            test_stage_info = data.get('test_config', list())
            if not test_stage_info:
                return False, '测试准备阶段不能为空'
            for tmp_stage_info in test_stage_info:
                if not tmp_stage_info.get('template'):
                    return False, '阶段：{}, 测试配置模板不能为空'.format(tmp_stage_info.get('name'))
        return True, msg

    @staticmethod
    def create_plan_relation(data, plan_id):
        """创建计划准备/测试 阶段关系"""
        # 环境准备
        if data.get('env_prep'):
            env_prep_info = data.get('env_prep')
            prepare_env_stage = PlanStageRelation.objects.create(plan_id=plan_id,
                                                                 stage_name=env_prep_info.get('name'),
                                                                 stage_index=1,
                                                                 stage_type='prepare_env',
                                                                 impact_next=False)
            if env_prep_info.get('machine_info'):
                for run_index, tmp_machine_info in enumerate(env_prep_info.get('machine_info', dict()), start=1):
                    machine_ip_sn = tmp_machine_info.get('machine')
                    channel_type = tmp_machine_info.get('channel_type', 'staragent')
                    try:
                        tmp_ip, tmp_sn = get_server_ip_sn(machine_ip_sn, channel_type)
                    except (TypeError, Exception):
                        tmp_ip = tmp_sn = None
                    if re.match(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', machine_ip_sn) is None:
                        tmp_machine_info.update({'ip': tmp_ip, 'sn': machine_ip_sn, 'channel_type': channel_type})
                    else:
                        tmp_machine_info.update({'ip': machine_ip_sn, 'sn': tmp_sn, 'channel_type': channel_type})
                    PlanStagePrepareRelation.objects.create(plan_id=plan_id, run_index=run_index,
                                                            stage_id=prepare_env_stage.id,
                                                            prepare_info=tmp_machine_info)
        # 测试配置
        if data.get('test_config'):
            test_stage_info = data.get('test_config', list())
            for stage_index, tmp_stage_info in enumerate(test_stage_info, start=1):
                tmp_test_stage = PlanStageRelation.objects.create(plan_id=plan_id,
                                                                  stage_name=tmp_stage_info.get('name'),
                                                                  stage_index=stage_index,
                                                                  stage_type='test_stage',
                                                                  impact_next=tmp_stage_info.get('impact_next'))
                # 创建模板顺序
                for run_index, tmpl_id in enumerate(tmp_stage_info.get('template', list()), start=1):
                    PlanStageTestRelation.objects.create(plan_id=plan_id, run_index=run_index,
                                                         stage_id=tmp_test_stage.id,
                                                         tmpl_id=tmpl_id)

    @staticmethod
    def create_plan_instance_relation(data, plan_instance_id):
        """创建计划准备/测试 阶段关系"""
        # 环境准备
        if data.get('env_prep'):
            env_prep_info = data.get('env_prep')
            prepare_env_stage = PlanInstanceStageRelation.objects.create(plan_instance_id=plan_instance_id,
                                                                         stage_name=env_prep_info.get('name'),
                                                                         stage_index=1,
                                                                         stage_type='prepare_env',
                                                                         impact_next=False)

            for run_index, tmp_machine_info in enumerate(env_prep_info.get('machine_info', dict()), start=1):
                machine_ip_sn = tmp_machine_info.get('machine', '').strip()
                try:
                    tmp_ip, tmp_sn = get_server_ip_sn(machine_ip_sn, tmp_machine_info.get('channel_type', 'staragent'))
                except (TypeError, Exception):
                    tmp_ip = tmp_sn = None
                if re.match(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', machine_ip_sn) is None:
                    tmp_machine_info.update({'ip': tmp_ip, 'sn': machine_ip_sn})
                else:
                    tmp_machine_info.update({'ip': machine_ip_sn, 'sn': tmp_sn})
                PlanInstancePrepareRelation.objects.create(plan_instance_id=plan_instance_id,
                                                           run_index=run_index,
                                                           instance_stage_id=prepare_env_stage.id,
                                                           extend_info=tmp_machine_info,
                                                           channel_type=data.get('channel_type', 'staragent'),
                                                           ip=tmp_ip if tmp_ip is not None else machine_ip_sn,
                                                           sn=tmp_sn if tmp_sn is not None else machine_ip_sn,
                                                           script_info=tmp_machine_info.get('script'),
                                                           )
        # 测试配置
        if data.get('test_config'):
            test_stage_info = data.get('test_config', list())
            for stage_index, tmp_stage_info in enumerate(test_stage_info, start=1):
                tmp_test_stage = PlanInstanceStageRelation.objects.create(plan_instance_id=plan_instance_id,
                                                                          stage_name=tmp_stage_info.get('name'),
                                                                          stage_index=stage_index,
                                                                          stage_type='test_stage',
                                                                          impact_next=tmp_stage_info.get('impact_next'))
                # 创建模板顺序
                for run_index, tmpl_id in enumerate(tmp_stage_info.get('template', list()), start=1):
                    PlanInstanceTestRelation.objects.create(plan_instance_id=plan_instance_id,
                                                            run_index=run_index,
                                                            instance_stage_id=tmp_test_stage.id,
                                                            tmpl_id=tmpl_id,
                                                            test_type=template_get_test_type(tmpl_id))

    @staticmethod
    def check_test_plan(plan_id):
        """校验plan id 是否存在"""
        test_plan_queryset = TestPlan.objects.filter(id=plan_id)
        if test_plan_queryset.first() is None:
            return False, None
        else:
            return True, test_plan_queryset

    def update_plan(self, data, operator):
        plan_id = data.get('plan_id')
        success, test_plan_queryset = self.check_test_plan(plan_id)
        if not success:
            return False, 'plan 不存在'
        test_plan = test_plan_queryset.first()
        if not check_operator_permission(operator, test_plan):
            return False, ''
        if test_plan.name != data.get('name') and TestPlan.objects.filter(name=data.get('name')).exists():
            return False, '计划名称不能重复'
        update_data = dict()
        origin_cron_info = test_plan.cron_info
        allow_update_fields = ['name', 'description', 'project_id', 'test_obj', 'enable', 'cron_schedule',
                               'cron_info', 'blocking_strategy', 'auto_report', 'report_name', 'report_description',
                               'group_method', 'base_group', 'stage_id']
        for update_field in allow_update_fields:
            if data.get(update_field) is not None or update_field in {'enable', 'cron_schedule', 'auto_report',
                                                                      'report_name', 'report_description'}:
                update_value = data.get(update_field)
                update_data[update_field] = update_value.strip() if isinstance(update_value, str) else update_value

        baseline_info = self.pack_baseline_info(data)

        rpm_info = list()
        if data.get('rpm_info', ''):
            rpm_info = data.get('rpm_info').replace('\n', ',').split(',')

        update_data.update({
            'baseline_info': baseline_info,
            'kernel_info': data.get('kernel_info', dict()),
            'kernel_version': data.get('kernel_version'),
            'build_pkg_info': data.get('build_pkg_info', dict()),
            'rpm_info': rpm_info,
            'script_info': data.get('scripts', list()),
            'env_info': self.get_env_info(data.get('env_info', '')),
            'notice_info': self.pack_notice_info(data.get('email_info', None),
                                                 data.get('ding_talk_info', None),
                                                 data.get('notice_name', None)),
            'update_user': operator,
            'report_tmpl_id': data.get('report_template_id'),
        })
        success, msg = self.check_stage_relation(data)
        if not success:
            return False, msg
        test_plan_queryset.update(**update_data)
        # 修改测试准备 / 测试配置 , 删除原配置信息, 生成新的配置
        PlanStageRelation.objects.filter(plan_id=test_plan.id).delete()
        PlanStageTestRelation.objects.filter(plan_id=test_plan.id).delete()
        PlanStagePrepareRelation.objects.filter(plan_id=test_plan.id).delete()
        self.create_plan_relation(data, test_plan.id)
        self.modify_plan_schedule(plan_id, origin_cron_info)
        return True, None

    @staticmethod
    def modify_plan_schedule(plan_id, origin_cron_info):
        """删除原触发任务, 创建新触发任务"""
        test_plan = TestPlan.objects.filter(id=plan_id).first()
        new_cron_info = test_plan.cron_info
        cron_info_changed = True if origin_cron_info != new_cron_info else False

        if cron_info_changed:
            # 开启
            if test_plan.enable and test_plan.cron_schedule:
                if ScheduleMap.objects.filter(object_type='plan', object_id=plan_id).exists():
                    PlanScheduleService().remove_schedule(plan_id)
                PlanScheduleService().add_plan_to_schedule(plan_id)

            # 关闭
            else:
                if ScheduleMap.objects.filter(object_type='plan', object_id=plan_id).exists():
                    PlanScheduleService().remove_schedule(plan_id)
                PlanScheduleService().add_plan_to_schedule(plan_id)
                PlanScheduleService().stop_schedule(plan_id)

        else:
            # 任务无修改
            if not all([test_plan.enable, test_plan.cron_schedule]) and \
                    ScheduleMap.objects.filter(object_type='plan', object_id=plan_id).exists():
                PlanScheduleService().stop_schedule(plan_id)

            # 启动定时任务
            if test_plan.enable and test_plan.cron_schedule:
                PlanScheduleService().resume_schedule(plan_id)

    def delete_plan(self, data, operator):
        plan_id = data.get('plan_id')
        success, test_plan_queryset = self.check_test_plan(plan_id)
        if not success:
            return False
        if not check_operator_permission(operator, test_plan_queryset.first()):
            return False
        # 删除计划本身和关联的阶段信息
        with transaction.atomic():
            test_plan_queryset.delete()
            PlanStageRelation.objects.filter(plan_id=plan_id).delete()
            PlanStageTestRelation.objects.filter(plan_id=plan_id).delete()
            PlanStagePrepareRelation.objects.filter(plan_id=plan_id).delete()
            # 删除计划实例信息
            plan_instance_queryset = PlanInstance.objects.filter(plan_id=plan_id)
            if plan_instance_queryset.first() is not None:
                plan_instance_id = plan_instance_queryset.first().id
                plan_instance_queryset.delete()
                PlanInstanceTestRelation.objects.filter(plan_instance_id=plan_instance_id).delete()
                PlanInstanceStageRelation.objects.filter(plan_instance_id=plan_instance_id).delete()
                PlanInstancePrepareRelation.objects.filter(plan_instance_id=plan_instance_id).delete()
            # 删除触发任务
            if ScheduleMap.objects.filter(object_type='plan', object_id=plan_id).exists():
                PlanScheduleService().remove_schedule(plan_id)
        return True

    @staticmethod
    def copy_plan_relation(origin_plan_id, new_plan_id):
        """拷贝关系"""
        for tmp_stage in PlanStageRelation.objects.filter(plan_id=origin_plan_id):
            origin_stage_id = tmp_stage.id
            tmp_stage.id = None
            tmp_stage.plan_id = new_plan_id
            tmp_stage.save()
            new_stage_id = tmp_stage.id
            if tmp_stage.stage_type == 'prepare_env':
                relation_list = PlanStagePrepareRelation.objects.filter(plan_id=origin_plan_id,
                                                                        stage_id=origin_stage_id)
            else:
                relation_list = PlanStageTestRelation.objects.filter(plan_id=origin_plan_id, stage_id=origin_stage_id)
            for tmp_relation in relation_list:
                tmp_relation.id = None
                tmp_relation.plan_id = new_plan_id
                tmp_relation.stage_id = new_stage_id
                tmp_relation.save()

    def copy_plan(self, data, operator):
        plan_id = data.get('plan_id')
        success, test_plan_queryset = self.check_test_plan(plan_id)
        if not success:
            return False, '计划id不存在'
        test_plan = test_plan_queryset.first()
        test_plan.id = None
        if '-copy-' in test_plan.name:
            test_plan.name = '{}-copy-{}'.format(test_plan.name.split('-copy-')[0], random_choice_str())
        else:
            test_plan.name = '{}-copy-{}'.format(test_plan.name, random_choice_str())
        test_plan.creator = operator
        test_plan.save()
        new_plan_id = test_plan.id
        self.copy_plan_relation(plan_id, new_plan_id)
        # 拷贝计划启用并定时触发，创建触发任务
        if test_plan.cron_schedule:
            if test_plan.enable:
                PlanScheduleService().add_plan_to_schedule(new_plan_id)
            else:
                PlanScheduleService().add_plan_to_schedule(new_plan_id)
                PlanScheduleService().stop_schedule(new_plan_id)
        return True, test_plan

    @staticmethod
    def pack_baseline_info(data):
        # 获取基线信息
        baseline_info = dict()
        if data.get('func_baseline'):
            baseline_info['func_baseline'] = data.get('func_baseline')
        if data.get('func_baseline_aliyun'):
            baseline_info['func_baseline_aliyun'] = data.get('func_baseline_aliyun')
        if data.get('perf_baseline'):
            baseline_info['perf_baseline'] = data.get('perf_baseline')
        if data.get('perf_baseline_aliyun'):
            baseline_info['perf_baseline_aliyun'] = data.get('perf_baseline_aliyun')
        return baseline_info

    def run_plan(self, data, operator):
        """手动创建待运行计划实例"""
        create_data = dict()
        plan_id = data.get('plan_id')
        check_flag, test_plan_queryset = self.check_test_plan(plan_id)
        if not check_flag:
            return False, 'plan id 不存在'
        name = data.get('name', '手动运行计划')
        test_obj = data.get('test_obj', 'kernel')
        ws_id = data.get('ws_id')
        test_plan_obj = test_plan_queryset.first()
        if not ws_id:
            ws_id = test_plan_obj.ws_id
        project_id = data.get('project_id')
        baseline_info = self.pack_baseline_info(data)

        rpm_info = list()
        if data.get('rpm_info', ''):
            rpm_info = data.get('rpm_info').replace('\n', ',').split(',')
        if not data.get('enable'):
            return False, '计划未启用, 不可运行'
        # 仅运行
        auto_count = PlanInstance.objects.filter(plan_id=plan_id, query_scope='all').count() + 1
        create_data.update({
            'plan_id': plan_id,
            'run_mode': 'manual',
            'name': '{}-{}'.format(name, auto_count),
            'test_obj': test_obj,
            'ws_id': ws_id,
            'project_id': project_id,
            'creator': operator,
            'baseline_info': baseline_info,
            'kernel_info': data.get('kernel_info', dict()),
            'kernel_version': data.get('kernel_version'),
            'build_pkg_info': data.get('build_pkg_info', dict()),
            'rpm_info': rpm_info,
            'script_info': data.get('scripts', list()),
            'env_info': self.get_env_info(data.get('env_info', '')),
            'notice_info': self.pack_notice_info(data.get('email_info', None),
                                                 data.get('ding_talk_info', None),
                                                 data.get('notice_name', None)),
            'start_time': datetime.now(),
            'auto_report': data.get('auto_report', False),
            'report_name': data.get('report_name', ''),
            'report_tmpl_id': data.get('report_template_id', None),
            'report_description': data.get('report_description', ''),
            'group_method': data.get('group_method', test_plan_obj.group_method),
            'base_group': data.get('base_group', test_plan_obj.base_group),
            'stage_id': data.get('stage_id', test_plan_obj.stage_id),
        })
        plan_instance = PlanInstance.objects.create(**create_data)
        self.create_plan_instance_relation(data, plan_instance.id)
        # 运行并保存/保存并运行
        if data.get('is_save'):
            TestPlan.objects.filter(id=plan_id)
            self.update_plan(data, operator)

        return True, plan_instance

    @staticmethod
    def get_constraint_job(queryset, data):
        plan_instance_list = data.get('plan_instance_list', '').split(',')
        job_id_list = PlanInstanceTestRelation.objects.filter(plan_instance_id__in=plan_instance_list
                                                              ).values_list('job_id', flat=True)
        job_id_list = [job_id for job_id in set(job_id_list) if job_id]
        return queryset.filter(id__in=job_id_list)

    @staticmethod
    def check_cron_express(data, query_times=3, time_fmt='%Y-%m-%d %H:%M:%S'):
        cron_express = data.get('cron_express')
        if not cron_express:
            return False, 'Crontab表达式不能为空'
        try:
            CronTrigger.from_crontab(cron_express)
        except ValueError:
            return False, 'Crontab 表达式格式错误'
        cron = croniter.croniter(cron_express, datetime.now())
        return True, [cron.get_next(datetime).strftime(time_fmt) for _ in range(query_times)]

    @staticmethod
    def get_schedule_job_id(plan_id):
        schedule_job_id = None
        schedule_obj = ScheduleMap.objects.filter(object_type='plan', object_id=plan_id).first()
        if schedule_obj is not None:
            schedule_job_id = schedule_obj.schedule_job_id
        return schedule_job_id

    def get_plan_next_time(self, plan_id):
        next_time = None
        schedule_job_id = self.get_schedule_job_id(plan_id)
        if schedule_job_id is not None:
            schedule_job = scheduler.get_job(job_id=schedule_job_id)
            if schedule_job:
                next_time = schedule_job.next_run_time
        return next_time

    @staticmethod
    def manual_create_report(data):
        test_job_id = data.get('job_id')
        if test_job_id:
            ReportHandle(test_job_id).save_report()
        else:
            plan_instance_id = data.get('plan_instance_id')
            plan_create_report(plan_instance_id)
        return True, None


class PlanResultService(CommonService):
    @staticmethod
    def get_plan_result(queryset, data):
        """查询计划结果视图"""
        q = Q()
        q &= Q(plan_id=data.get('plan_id')) if data.get('plan_id') else q
        q &= Q(run_mode=data.get('run_mode')) if data.get('run_mode') else q
        q &= Q(name__icontains=data.get('name')) if data.get('name') else q
        q &= Q(state__in=data.getlist('state')) if data.get('state') else q
        q &= Q(creator=data.get('creator')) if data.get('creator') else q
        return queryset.filter(q)

    @staticmethod
    def delete_plan_instance(data, operator):
        plan_instance_id = data.get('plan_instance_id')
        plan_instance_queryset = PlanInstance.objects.filter(id=plan_instance_id)
        if not check_operator_permission(operator, plan_instance_queryset.first()):
            return False

        with transaction.atomic():
            plan_instance_queryset.delete()
        return True

    @staticmethod
    def get_plan_detail_result(queryset, data):
        return queryset.filter(id=data.get('plan_instance_id')).first()

    @staticmethod
    def modify_note(data, operator):
        plan_instance = PlanInstance.objects.filter(id=data.get('plan_instance_id')).first()
        if plan_instance is not None and data.get('note'):
            if not check_operator_permission(operator, plan_instance):
                return False
            plan_instance.note = data.get('note')
            plan_instance.save()
        return True


class PlanScheduleService(object):

    @staticmethod
    def add_plan_to_schedule(plan_id):
        plan = TestPlan.objects.filter(id=plan_id, cron_schedule=True)
        if not plan.exists():
            logger.info('no plan, so can not add to schedule. plan_id:{}'.format(plan_id))
            return
        ScheduleHandle.add_crontab_job(TestPlanScheduleJob.run, plan.first().cron_info, args=[plan_id])

    @staticmethod
    def stop_schedule(plan_id):
        ScheduleHandle.pause_job(obj_id=str(plan_id))

    @staticmethod
    def resume_schedule(plan_id):
        ScheduleHandle.resume_job(obj_id=str(plan_id))

    @staticmethod
    def remove_schedule(plan_id):
        ScheduleHandle.remove_job(obj_id=str(plan_id))
