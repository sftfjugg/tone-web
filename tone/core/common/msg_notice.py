"""站内消息通知"""
import json
from collections import OrderedDict
import logging
from datetime import timedelta
from django.db import transaction
from django.template.loader import render_to_string

from tone import settings
from tone.core.common.callback import JobCallBack, CallBackType
from tone.models import RoleMember, WorkspaceMember, Role, ApproveInfo, InSiteWorkProcessMsg, \
    InSiteWorkProcessUserMsg, User, Workspace, InSiteSimpleMsg, TestJob, TestServerSnapshot, CloudServerSnapshot, \
    TestSuite, OutSiteMsg, Baseline, JobTag, JobTagRelation, PerfResult, TestCase, TestPlan, CloudServer, TestServer, \
    datetime, PlanInstance

from tone.serializers.job.test_serializers import JobTestResultSerializer, JobTestSummarySerializer
from tone.services.portal.sync_portal_task_servers import save_report


logger = logging.getLogger('message')
callback_logger = logging.getLogger('callback')
EMAIL_CC = ''


class SendByChoices:
    DING_TALK = 'ding_talk'
    EMAIL = 'email'


def get_skip_url():
    """获取平台url"""
    return settings.APP_DOMAIN


def get_admin_user(ws_id='', test_admin=False):
    """查询系统级/Workspace级 管理员用户id列表"""
    # 系统级：super_admin + sys_admin , WS级： ws_owner + ws_admin + ws_test_admin
    role_map = {
        'sys_admin': ['super_admin', 'sys_admin'],
        'ws_admin': ['ws_owner', 'ws_admin'],
        'ws_test_admin': ['ws_owner', 'ws_admin', 'ws_test_admin']
    }
    if not ws_id:
        sys_role = Role.objects.filter(title__in=role_map.get('sys_admin')).values_list('id', flat=True)
        admin_id_list = RoleMember.objects.filter(role_id__in=sys_role).values_list('user_id', flat=True)
    else:
        admin_choice = 'ws_test_admin' if test_admin else 'ws_admin'
        ws_role = Role.objects.filter(title__in=role_map.get(admin_choice)).values_list('id', flat=True)
        admin_id_list = WorkspaceMember.objects.filter(
            ws_id=ws_id, role_id__in=ws_role).values_list('user_id', flat=True)
    return admin_id_list


def get_user_info(user_id):
    """查询用户信息"""
    from tone.serializers.auth.auth_serializers import get_user_avatar
    user_obj = User.objects.get(id=user_id)
    return {
        'user_id': user_obj.id,
        'avatar': get_user_avatar(user_id),
        'user_name': '{}({})'.format(user_obj.last_name, user_obj.first_name
                                     ) if user_obj.first_name else user_obj.last_name,
    }


def get_ws_info(ws_id):
    """查询workspace信息"""
    ws_obj = Workspace.objects.get(id=ws_id, query_scope='all')
    return {
        'ws_id': ws_obj.id,
        'ws_show_name': ws_obj.show_name,
    }


def get_user_name(user_id):
    """查询用户名"""
    user_obj = User.objects.filter(id=user_id).first()
    if not user_obj:
        return
    return '{}({})'.format(user_obj.last_name, user_obj.first_name) if user_obj.first_name else user_obj.last_name


def get_baseline_name(baseline_id):
    """查询基线名称"""
    baseline = None
    if baseline_id and Baseline.objects.filter(id=baseline_id).exists():
        baseline = Baseline.objects.get(id=baseline_id).name
    return baseline


def get_job_state(state, job_obj):
    """查询job运行状态"""
    if state == 'success':
        if job_obj.test_result:
            try:
                result_data = json.loads(job_obj.test_result)
            except Exception:
                result_data = {}
            if result_data.get('fail', 0) > 0 or result_data.get('total', 0) == 0 or result_data.get('pass', 0) == 0:
                return '未通过'
            else:
                return '已通过'
        else:
            return '未通过'
    state_map = {'pending': '队列中',
                 'running': '运行中',
                 'success': '已完成',
                 'fail': '已失败',
                 'stop': '已终止',
                 'skip': '已跳过'}
    return state_map.get(state)


class InSiteMsgHandle(object):
    """站内消息"""

    @staticmethod
    def get_status(status):
        if status == 'passed':
            status = '通过'
        elif status == 'refused':
            status = '拒绝'
        return status if status else ''

    @staticmethod
    def get_action(action):
        if action == 'create':
            action = '创建'
        elif action == 'delete':
            action = '注销'
        elif action == 'join':
            action = '加入'
        else:
            action = ''
        return action

    @staticmethod
    def get_send_msg(approve_obj, is_create=False):
        return {
            'approve_id': approve_obj.id,
            'action': approve_obj.action,
            'status': approve_obj.status,
            'operator_info': get_user_info(approve_obj.approver if is_create else approve_obj.proposer),
            'ws_info': get_ws_info(approve_obj.object_id),
        }

    def create_apply(self, approve_info_id):
        """创建/注销 ws申请，系统管理员接收消息"""
        #     王芳 申请创建Workspace 袋鼠
        #     王芳 申请注销Workspace 袋鼠
        approve_obj = ApproveInfo.objects.get(id=approve_info_id)
        send_msg = self.get_send_msg(approve_obj)
        # 创建ws、注销ws
        action = self.get_action(approve_obj.action)
        subject = '申请{}Workspace'.format(action)
        process_msg_obj = InSiteWorkProcessMsg.objects.create(subject=subject, content=send_msg,
                                                              process_id=approve_info_id)
        # 关联所有系统级管理员
        admin_id_list = get_admin_user()
        user_msg_list = [InSiteWorkProcessUserMsg(user_id=user_id, msg_id=process_msg_obj.id)
                         for user_id in admin_id_list]
        InSiteWorkProcessUserMsg.objects.bulk_create(user_msg_list)

    def handle_apply(self, approve_info_id):
        """
        WS创建/注销 处理审批完成后，申请人接收消息
        """
        # 通过 / 拒绝
        approve_obj = ApproveInfo.objects.get(id=approve_info_id)
        # 审批后, 修改消息操作状态
        process_msg_queryset = InSiteWorkProcessMsg.objects.filter(process_id=approve_info_id)
        process_msg_queryset.update(is_handle=True)
        if process_msg_queryset.first():
            InSiteWorkProcessUserMsg.objects.filter(msg_id=process_msg_queryset.first().id).update(i_am_handle=True)
        # 审批状态
        status = self.get_status(approve_obj.status)
        # 申请人
        proposer = approve_obj.proposer
        # 操作类型
        action = self.get_action(approve_obj.action)
        subject = '{}{}申请'.format(status, action)
        send_msg = self.get_send_msg(approve_obj, is_create=True)
        if status == '通过' and action == '注销':
            process_id_list = ApproveInfo.objects.filter(object_type='workspace', object_id=approve_obj.object_id,
                                                         query_scope='all').values_list('id', flat=True)
            process_msg_queryset = InSiteWorkProcessMsg.objects.filter(process_id__in=process_id_list)
            process_msg_queryset.delete()
            process_msg_id_list = process_msg_queryset.values_list('id', flat=True)
            InSiteWorkProcessUserMsg.objects.filter(msg_id__in=process_msg_id_list).delete()
        # 创建审批结果消息
        process_msg_obj = InSiteWorkProcessMsg.objects.create(subject=subject, content=send_msg,
                                                              process_id=approve_info_id)
        # 关联申请创建人
        InSiteWorkProcessUserMsg.objects.create(user_id=proposer, msg_id=process_msg_obj.id)

    def apply_join(self, approve_info_id):
        """
        申请加入ws， ws管理员接收消息
        王芳 申请加入Workspace 袋鼠
        """
        approve_obj = ApproveInfo.objects.get(id=approve_info_id)
        ws_id = approve_obj.object_id
        action = self.get_action(approve_obj.action)
        subject = '申请{}Workspace'.format(action)
        send_msg = self.get_send_msg(approve_obj)
        # 创建审批结果消息
        process_msg_obj = InSiteWorkProcessMsg.objects.create(subject=subject, content=send_msg,
                                                              process_id=approve_info_id)
        ws_admin_id_list = get_admin_user(ws_id=ws_id)
        user_msg_list = [InSiteWorkProcessUserMsg(user_id=user_id, msg_id=process_msg_obj.id)
                         for user_id in ws_admin_id_list]
        InSiteWorkProcessUserMsg.objects.bulk_create(user_msg_list)

    def handle_join(self, approve_info_id):
        """
        加入审批后，发送申请人消息
        """
        approve_obj = ApproveInfo.objects.get(id=approve_info_id)
        # 审批后, 修改消息操作状态
        process_msg_queryset = InSiteWorkProcessMsg.objects.filter(process_id=approve_info_id)
        process_msg_queryset.update(is_handle=True)
        InSiteWorkProcessUserMsg.objects.filter(msg_id=process_msg_queryset.first().id).update(i_am_handle=True)
        # 审批状态
        status = self.get_status(approve_obj.status)
        # 申请人
        proposer = approve_obj.proposer
        # 操作类型
        action = self.get_action(approve_obj.action)
        subject = '{}你{}申请'.format(status, action)
        send_msg = self.get_send_msg(approve_obj, is_create=True)
        # 创建审批结果消息
        process_msg_obj = InSiteWorkProcessMsg.objects.create(subject=subject, content=send_msg,
                                                              process_id=approve_info_id)
        # 关联申请创建人
        InSiteWorkProcessUserMsg.objects.create(user_id=proposer, msg_id=process_msg_obj.id)

    @staticmethod
    def by_update_ws_role(operator, by_operator, ws_id, role_id, action='add'):
        """被修改角色， 被操作人接收消息"""
        subject = '设置WS角色'
        role_title = Role.objects.get(id=role_id).title
        operator_info = get_user_info(operator)
        operator_info['action'] = action
        send_msg = {
            'action': 'set_ws_role',
            'operator_info': operator_info,
            'ws_info': get_ws_info(ws_id),
            'role_title': role_title
        }
        # 创建审批结果消息
        process_msg_obj = InSiteWorkProcessMsg.objects.create(subject=subject, content=send_msg)
        # 关联申请创建人
        InSiteWorkProcessUserMsg.objects.create(user_id=by_operator, msg_id=process_msg_obj.id)

    @staticmethod
    def by_update_sys_role(operator, by_operator, role_title):
        """被设置系统角色"""
        subject = '设置SYS角色'
        send_msg = {
            'action': 'set_sys_role',
            'operator_info': get_user_info(operator),
            'role_title': role_title
        }
        # 创建审批结果消息
        process_msg_obj = InSiteWorkProcessMsg.objects.create(subject=subject, content=send_msg)
        # 关联申请创建人
        InSiteWorkProcessUserMsg.objects.create(user_id=by_operator, msg_id=process_msg_obj.id)

    @staticmethod
    def by_remove(operator, by_operator, ws_id):
        """移除WS"""
        subject = '移除WS'
        send_msg = {
            'action': 'remove',
            'operator_info': get_user_info(operator),
            'ws_info': get_ws_info(ws_id)
        }
        # 创建审批结果消息
        process_msg_obj = InSiteWorkProcessMsg.objects.create(subject=subject, content=send_msg)
        # 关联申请创建人
        InSiteWorkProcessUserMsg.objects.create(user_id=by_operator, msg_id=process_msg_obj.id)

    @staticmethod
    def by_transfer_owner(operator, by_operator, ws_id):
        """转交owner"""
        subject = 'owner转让'
        send_msg = {
            'action': 'transfer',
            'operator_info': get_user_info(operator),
            'ws_info': get_ws_info(ws_id)
        }
        # 创建审批结果消息
        process_msg_obj = InSiteWorkProcessMsg.objects.create(subject=subject, content=send_msg)
        # 关联申请创建人
        InSiteWorkProcessUserMsg.objects.create(user_id=by_operator, msg_id=process_msg_obj.id)


class SimpleMsgHandle(object):
    """普通消息处理"""

    @staticmethod
    def job_handle(message_obj, message_key):
        """
        Job任务结果消息处理
        [Job] 测试完成 rund-runtime-sanity-check-asi-reqId-4364026
        {
            'job_id': 123,
            'state': 'success'
        }
        """
        job_id = message_obj.job_id
        job_obj = TestJob.objects.filter(id=job_id).first()
        if job_obj is None:
            return False
        # sync_job_data.delay(job_id, check_master=True)
        # job_state_change
        if message_key == 'job_start_running':
            if job_obj.callback_api:
                JobCallBack(job_id=job_id, callback_type=CallBackType.JOB_RUNNING).callback()
                return True
        if message_obj.job_state == 'running':
            return False
        ws_id = job_obj.ws_id
        admin_id_list = get_admin_user(ws_id=ws_id, test_admin=True)
        simple_msg_list = list()
        subject = '[Job]测试{}'.format(get_job_state(message_obj.job_state, job_obj))
        # subject = '[Job]测试完成'
        content = {
            'job_id': job_id,
            'job_name': job_obj.name,
            'ws_id': ws_id,
            'job_state': message_obj.job_state,
        }
        receiver_list = set(admin_id_list) | {job_obj.creator}
        logger.info(f'job completed notice receiver:{receiver_list}')
        for user_id in receiver_list:
            simple_msg_obj = InSiteSimpleMsg(subject=subject, content=content, msg_type='job_complete',
                                             msg_object_id=job_id, receiver=user_id)
            simple_msg_list.append(simple_msg_obj)
        InSiteSimpleMsg.objects.bulk_create(simple_msg_list)
        # 创建站外消息
        OutSiteMsgHandle().job_handle(job_obj, receiver_list, message_obj.job_state)
        if job_obj.callback_api:
            JobCallBack(job_id=job_id, callback_type=CallBackType.JOB_COMPLETED).callback()
        return True

    @staticmethod
    def plan_handle(message_obj, message_key):
        """
        计划结果消息处理
        [计划] 测试完成 rund-runtime-sanity-check-asi-reqId-4364026
        {
            'plan_id': 123,
            'state': 'success'
        }
        """
        plan_id = message_obj.plan_id
        plan_inst_id = message_obj.plan_inst_id
        # 计划完成生成报告
        from tone.services.plan.complete_plan_report import plan_create_report
        plan_create_report.delay(plan_inst_id)
        if message_key == 'plan_state_change':
            pass
        plan_obj = TestPlan.objects.filter(id=plan_id).first()
        if plan_obj is None:
            return False
        plan_inst_obj = PlanInstance.objects.filter(id=plan_inst_id).first()
        if plan_inst_obj is None:
            return False
        ws_id = plan_obj.ws_id
        admin_id_list = get_admin_user(ws_id=ws_id, test_admin=True)
        simple_msg_list = list()
        subject = '[计划]测试完成'
        content = {
            'plan_id': plan_id,
            'plan_instance_id': plan_inst_id,
            'plan_name': plan_obj.name,
            'plan_instance_name': plan_inst_obj.name,
            'ws_id': ws_id,
            'plan_state': message_obj.plan_state,
        }
        for user_id in admin_id_list:
            simple_msg_obj = InSiteSimpleMsg(subject=subject, content=content, msg_type='plan_complete',
                                             msg_object_id=plan_id, receiver=user_id)
            simple_msg_list.append(simple_msg_obj)
        with transaction.atomic():
            InSiteSimpleMsg.objects.bulk_create(simple_msg_list)
        # 创建站外消息
        OutSiteMsgHandle().plan_handle(plan_obj, plan_inst_obj, admin_id_list, message_obj.plan_state)
        return True

    @staticmethod
    def announcement_handle(message_value):
        """
        系统公告处理
        [公告]：post_msg
        {
            'post_msg': '通告',
        }
        """

    @staticmethod
    def get_server_model(server_provider, in_pool):
        if in_pool:
            server_model = TestServer if server_provider == 'aligroup' else CloudServer
        else:
            server_model = TestServerSnapshot if server_provider == 'aligroup' else CloudServerSnapshot
        return server_model

    def machine_handle(self, message_obj, message_key):
        """
        机器故障消息处理
        [故障]测试机器故障 VM20201228-0/11.164.65.13 上的任务在测试准备阶段失败, 机器可能已经故障，请及时处理 ！
        影响的Job:   64026 影响的Suite有: sp_hadoop
        {
            'machine_id': ,
            'machine_type': 'aliyun',  # 'aligroup' / 'aliyun'
            'impact_job': '123,        # 影响job
            'impact_suite': [1,2,3],        # 影响的suite id 列表
            'state': 'Broken',
            'in_pool': 1
        }
        """
        if message_key == 'machine_broken':
            pass
        machine_type = message_obj.machine_type
        server_model = self.get_server_model(machine_type, message_obj.in_pool)
        machine_id = message_obj.machine_id
        impact_suite = message_obj.impact_suite
        machine_obj = server_model.objects.filter(id=machine_id).first()
        if machine_obj is None:
            return False
        job_obj = TestJob.objects.filter(id=message_obj.impact_job).first()
        if job_obj is None:
            return False
        ws_id = job_obj.ws_id
        admin_id_list = get_admin_user(ws_id=ws_id, test_admin=True)
        simple_msg_list = list()
        subject = '[故障]测试机器故障'
        # impact_suite_list = [suite_id.strip() for suite_id in impact_suite.split(',')]
        suite_name_list = TestSuite.objects.filter(id__in=impact_suite).values_list('name', flat=True)
        machine_ip = machine_obj.ip if machine_type == 'aligroup' else machine_obj.private_ip
        content = {
            'machine_id': machine_id,
            'machine_type': machine_type,
            'ip': machine_ip,
            'sn': machine_obj.sn,
            'machine_name': machine_obj.name if machine_type == 'aligroup' else machine_obj.instance_name,
            'impact_job': message_obj.impact_job,
            'ws_id': ws_id,
            'impact_suite': ','.join(suite_name_list),
            'state': message_obj.state
        }
        for user_id in admin_id_list:
            simple_msg_obj = InSiteSimpleMsg(subject=subject, content=content, msg_type='machine_broken',
                                             msg_object_id=machine_id, receiver=user_id)
            simple_msg_list.append(simple_msg_obj)
        with transaction.atomic():
            InSiteSimpleMsg.objects.bulk_create(simple_msg_list)
            # 创建站外消息
            OutSiteMsgHandle().machine_handle(message_obj, machine_obj, admin_id_list, machine_type)
            if job_obj.callback_api:
                message_obj.machine_ip = machine_ip
                message_obj.machine_sn = machine_obj.sn
                JobCallBack(
                    job_id=job_obj.id, server_id=machine_id,
                    callback_type=CallBackType.SERVER_BROKEN,
                    message_obj=message_obj
                ).callback()
        return True

    @staticmethod
    def report_handle(message_obj, message_key):
        job_id = message_obj.job_id
        job_obj = TestJob.objects.filter(id=job_id).first()
        if not job_obj or not job_obj.report_template_id or job_obj.state != 'success' or job_obj.report_is_saved:
            return False
        logger.info(f'start saving report job_id: {job_id}')
        save_report.delay(job_id)
        return True


class OutSiteMsgHandle(object):
    """站外消息"""

    @staticmethod
    def server_broken_in_prepare(sn, ip, msg_link, job_id, suite=None):
        content = """
        <p>
        <h3>
            测试机器&nbsp;
            <span style="color:#E53333;">{sn}/{ip}</span>
            &nbsp;上的任务在测试准备阶段失败, 机器可能已经<span style="color:#E53333;">故障</span>，请及时处理 ！
        </h3>
        <h3>
            <span>影响的Task:&nbsp;</span>
            <a href="{msg_link}" target="_blank">
            <span style="color:#E53333;">{task_id}</span></a>
        </h3>
        %s
        <br />
        <p>
            处理建议： 确保可以登陆机器 {sn}/{ip} 并检查 staragent 
            (命令：&nbsp;/home/staragent/bin/staragentctl status) 及uptime是否正常 .
        </p>
        </p>
                """ % (
            '' if not suite else '<h3><span>影响的Suite有: <span style="color:#E53333;">{suite_name}</span></span></h3>')
        context = {'sn': sn,
                   'ip': ip,
                   'msg_link': msg_link,
                   'task_id': job_id,
                   'suite_name': suite}
        return content.format(**context)

    @staticmethod
    def get_send_config(job_id, obj_type='job'):
        """TestJob中获取消息发送配置"""
        # job自定义配置   notice_info
        config_dic = dict()
        obj_model = TestJob if obj_type == 'job' else PlanInstance
        test_obj = obj_model.objects.filter(id=job_id).first()
        if test_obj is None:
            return config_dic
        for config in test_obj.notice_info:
            if config['type'] == 'email':
                config_dic['email'] = config
            else:
                config_dic['ding'] = config
        return config_dic

    @staticmethod
    def get_job_content(job_obj):
        """获取job信息"""
        content = '''Tone平台\nID: {task_id}\nTask: {task}\nAuthor: {author}\nDuration: {duration} (hour)'''
        content = content.format(task_id=job_obj.id, task=job_obj.name, author=get_user_name(job_obj.creator),
                                 duration=round(
                                     (job_obj.gmt_modified - job_obj.gmt_created).total_seconds() / 60 / 60, 2))
        return content

    @staticmethod
    def get_plan_content(plan_inst_obj):
        """获取计划信息"""
        content = '''Tone平台\nID: {task_id}\nPlan: {task}\nAuthor: {author}\nDuration: {duration} (hour)'''
        content = content.format(task_id=plan_inst_obj.id, task=plan_inst_obj.name,
                                 author=get_user_name(plan_inst_obj.creator),
                                 duration=round(
                                     (plan_inst_obj.gmt_modified -
                                      plan_inst_obj.gmt_created).total_seconds() / 60 / 60, 2))
        return content

    @staticmethod
    def _extract_perf_result(case_result):
        result = dict()
        result['indicator'] = case_result.metric
        test_value = "%.2f" % (float(case_result.test_value)) if case_result.test_value else case_result.test_value
        result['test_value'] = '{}{}'.format(test_value, case_result.cv_value)
        result['cmp_note'] = case_result.track_result
        result['change_rate'] = ''
        result['changeRate'] = 0
        if case_result.compare_baseline:
            baseline_value = "%.2f" % (float(case_result.baseline_value)) if case_result.baseline_value \
                else case_result.baseline_value
            result['baseline_value'] = '{}{}'.format(baseline_value, case_result.baseline_cv_value)
            if case_result.compare_result:
                result['change_rate'] = "%.2f%%" % (float(case_result.compare_result) * 100)
                result['changeRate'] = float(case_result.compare_result)
        return result

    @staticmethod
    def get_plan_email_content(plan_inst_obj):
        content = """
        <p>
        <h3>
            测试计划&nbsp;
            <span style="color:#E53333;">{task}</span>
            &nbsp;已完成
        </h3>
        <h3>
            <span>Plan Instance ID: {task_id}</span>
            <br>
            <span>Creator: {author}</span>
            <br>
            <span>Plan: <a href="{msg_link}" target="_blank">{task}</a></span>
            <br>Start：{start_time}
            <br>End：{end_time}
            <br>
            <span style="color:#E53333;">Duration: {duration}H</span>
        </h3>
        <br />
        </p>
                """
        msg_link = '{}/ws/{}/test_plan/view/detail/{}'.format(get_skip_url(), plan_inst_obj.ws_id, plan_inst_obj.id)
        context = {'task_id': plan_inst_obj.id,
                   'task': plan_inst_obj.name,
                   'author': get_user_name(plan_inst_obj.creator),
                   'msg_link': msg_link,
                   'start_time': plan_inst_obj.gmt_created,
                   'end_time': plan_inst_obj.gmt_modified,
                   'duration': round((plan_inst_obj.gmt_modified -
                                      plan_inst_obj.gmt_created).total_seconds() / 60 / 60, 2)}
        return content.format(**context)

    def get_job_email_content(self, job_obj):  # noqa: C901
        """获取job email信息"""
        func_result = list()
        perf_result = list()
        # 功能测试
        if job_obj.test_type == 'functional':
            func_result = JobTestResultSerializer().get_test_suite(job_obj)
            func_result = sorted(func_result, key=lambda x: x.get('result'), reverse=True)
        else:
            perf_result = JobTestSummarySerializer().get_case_result(job_obj)
        job_result = json.loads('{}' if job_obj.test_result is None else job_obj.test_result)
        tag_id_list = JobTagRelation.objects.filter(job_id=job_obj.id).values_list('tag_id', flat=True)
        tags = JobTag.objects.filter(id__in=tag_id_list).values_list('name')
        nightly_tag = None
        if tags:
            can_link = False
            for tag in tags:
                if tag[0] == 'analytics':
                    can_link = True
                if 'nightly-' in tag[0] or tag[0].endswith('-nig') or tag[0].endswith('-ni'):
                    nightly_tag = tag[0]
            if not can_link:
                nightly_tag = None

        last_perf_result = None
        nightly_flag = 2
        if nightly_tag:
            analytics_tag = JobTag.objects.filter(name='analytics', ws_id=job_obj.ws_id).values_list('id')
            tag_id_list = JobTag.objects.filter(name=nightly_tag).values_list('id')
            analytics_task = JobTagRelation.objects.filter(tag_id__in=analytics_tag).values_list('job_id')
            nightly_task_list = JobTagRelation.objects.filter(tag_id__in=tag_id_list, job_id__in=analytics_task
                                                              ).exclude(job_id=job_obj.id).values_list('job_id')
            last_task_id = PerfResult.objects.values('test_job_id').filter(test_job_id__in=nightly_task_list
                                                                           ).order_by('-gmt_created').first()
            last_perf_result = PerfResult.objects.filter(test_job_id=last_task_id['test_job_id']).order_by('-cv_value')
        else:
            nightly_flag = 1
        case_results_decline = []
        case_results_increase = []
        case_results_other = []
        suite_id_list = PerfResult.objects.filter(test_job_id=job_obj.id).values_list('test_suite_id', flat=True)
        _perf_result = {}
        for tmp_suite_id in set(suite_id_list):
            cases_queryset = PerfResult.objects.filter(test_job_id=job_obj.id, test_suite_id=tmp_suite_id)
            tmp_suite = TestSuite.objects.filter(id=tmp_suite_id, query_scope='all').first()
            _perf_result[tmp_suite.name] = cases_queryset

        for suite_name, case_results in _perf_result.items():
            perf_result[suite_name] = []
            _case_results = OrderedDict()
            for case_result in case_results:
                case_id = case_result.test_case_id
                conf_name = TestCase.objects.get(id=case_id).name
                presult_e = self._extract_perf_result(case_result)
                case_name = suite_name + ': ' + conf_name
                presult_e['case_name'] = case_name
                presult_e['suite_name'] = suite_name
                if nightly_tag:
                    job_tag = JobTag.objects.filter(name=nightly_tag).first()
                    tag_id = job_tag.id if job_tag else ''
                    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                    end_date = datetime.now().strftime('%Y-%m-%d')
                    presult_e['link'] = '{}/ws/{}/test_analysis/time?' \
                                        'test_type={}&show_type=0&provider_env={}&start_time={}&end_time={}&' \
                                        'tag={}&project_id={}&test_suite_id={}&test_case_id={}&' \
                                        'metric={}&title={}%2F{}'.\
                        format(get_skip_url(), job_obj.ws_id, job_obj.test_type, job_obj.server_provider, start_date,
                               end_date, tag_id, job_obj.project_id, case_result.test_suite_id, case_id,
                               case_result.metric, suite_name, conf_name)
                else:
                    presult_e['link'] = ''
                last_presult_e = None
                if last_perf_result:
                    last_case = last_perf_result.filter(test_suite_id=case_result.test_suite_id,
                                                        test_case_id=case_result.test_case_id,
                                                        metric=case_result.metric).first()
                    if last_case:
                        last_presult_e = self._extract_perf_result(last_case)
                if last_presult_e:
                    presult_e['last_test_value'] = last_presult_e['test_value']
                    presult_e['last_change_rate'] = last_presult_e['change_rate']
                    presult_e['last_cmp_note'] = last_presult_e['cmp_note']
                    nightly_flag = 0
                else:
                    presult_e['last_test_value'] = ''
                    presult_e['last_change_rate'] = ''
                    presult_e['last_cmp_note'] = ''

                if case_name not in _case_results:
                    _case_results[case_name] = [presult_e]
                else:
                    _case_results[case_name].append(presult_e)
                if case_result.track_result == 'decline':
                    case_results_decline.append(presult_e)
                elif case_result.track_result == 'increase':
                    case_results_increase.append(presult_e)
                else:
                    case_results_other.append(presult_e)
        suite_order = list()
        for case_res in sorted(case_results_decline, key=lambda x: x['changeRate'], reverse=True):
            suite_name = case_res['suite_name']
            if suite_name not in suite_order:
                suite_order.append(suite_name)
        for case_res in sorted(case_results_increase, key=lambda x: x['changeRate'], reverse=True):
            suite_name = case_res['suite_name']
            if suite_name not in suite_order:
                suite_order.append(suite_name)
        for case_res in sorted(case_results_other, key=lambda x: x['changeRate'], reverse=True):
            suite_name = case_res['suite_name']
            if suite_name not in suite_order:
                suite_order.append(suite_name)
        perf_result_decline = OrderedDict()
        perf_result_increase = OrderedDict()
        perf_result_other = OrderedDict()
        for suite_name in suite_order:
            suite_case_decline = [case_result for case_result in case_results_decline
                                  if case_result['suite_name'] == suite_name]
            for case_res in sorted(suite_case_decline, key=lambda x: x['changeRate'], reverse=True):
                case_name = case_res['case_name']
                if case_name in perf_result_decline:
                    perf_result_decline[case_name].append(case_res)
                else:
                    perf_result_decline[case_name] = [case_res]
            suite_case_increase = [case_result for case_result in case_results_increase
                                   if case_result['suite_name'] == suite_name]
            for case_res in sorted(suite_case_increase, key=lambda x: x['changeRate'], reverse=True):
                case_name = case_res['case_name']
                if case_name in perf_result_increase:
                    perf_result_increase[case_name].append(case_res)
                else:
                    perf_result_increase[case_name] = [case_res]
            suite_case_other = [case_result for case_result in case_results_other
                                if case_result['suite_name'] == suite_name]
            for case_res in sorted(suite_case_other, key=lambda x: x['changeRate'], reverse=True):
                case_name = case_res['case_name']
                if case_name in perf_result_other:
                    perf_result_other[case_name].append(case_res)
                else:
                    perf_result_other[case_name] = [case_res]

        if len(perf_result_decline) == 0 and len(perf_result_increase) == 0:
            nightly_flag = 2
        context = {
            'job_skp_link': '{}/ws/{}/test_result/{}'.format(get_skip_url(), job_obj.ws_id, job_obj.id),
            'job_name': job_obj.name,
            'creator': get_user_name(job_obj.creator),
            'kernel_version': job_obj.kernel_version,
            'baseline': get_baseline_name(job_obj.baseline_id),
            'start_time': str(job_obj.start_time),
            'end_time': str(job_obj.end_time),
            'func_result': func_result,
            'perf_result': perf_result,
            'perf_chart_link': '{}/ws/{}/test_analysis/compare'.format(get_skip_url(), job_obj.ws_id),
            'total_tests': job_result.get('total', '0'),
            'pass_count': job_result.get('pass', '0'),
            'fail_count': job_result.get('fail', '0'),
            'perf_result_decline': perf_result_decline,
            'perf_result_increase': perf_result_increase,
            'perf_result_other': perf_result_other,
            'nightly_flag': nightly_flag
        }
        return render_to_string('email/task_notice.html', context)

    @staticmethod
    def get_machine_content(msg_obj):
        """获取机器信息"""

    def get_msg_content(self, msg_obj, msg_type):
        """获取消息内容"""
        content = ''
        # job
        if msg_type == 'job_complete':
            content = self.get_job_content(msg_obj)
        # plan
        elif msg_type == 'plan_complete':
            content = self.get_plan_content(msg_obj)
        # machine
        elif msg_type == 'machine_broken':
            content = self.get_machine_content(msg_obj)
        return content

    @staticmethod
    def get_email_list(id_list):
        return [User.objects.get(id=user_id).email.strip() for user_id in id_list]

    @staticmethod
    def check_ding_token(ding_to):
        check_ding = list()
        if ding_to:
            for tmp_token in ding_to.replace('\n', ',').split(','):
                tmp_token = tmp_token.strip()
                if len(tmp_token) == 64:
                    check_ding.append(tmp_token)
        return ','.join(check_ding)

    def plan_handle(self, plan_obj, plan_inst_obj, admin_id_list, plan_state):
        """Plan站外消息处理"""
        creator_email = ','.join(self.get_email_list([plan_obj.creator]))
        # email_list = ','.join(self.get_email_list(admin_id_list))
        subject = '[Tone]测试计划{}已完成'.format(plan_inst_obj.name)
        content = self.get_msg_content(plan_inst_obj, 'plan_complete')
        bcc_to = ''
        ding_subject = ''
        email_subject = ''
        ding_to = ''
        email_to = ''
        config_dic = self.get_send_config(plan_inst_obj.id, obj_type='plan')
        if config_dic.get('ding'):
            ding_info = config_dic.get('ding')
            ding_subject = ding_info.get('subject')
            ding_to = self.check_ding_token(ding_info.get('to').strip().replace(' ', ','))
        if config_dic.get('email'):
            email_info = config_dic.get('email')
            email_subject = email_info.get('subject')
            email_to = email_info.get('to').strip().replace('.net', '-inc.com').replace(' ', ',')
        if settings.MSG_SWITCH_ON:
            OutSiteMsg.objects.create(
                subject=subject if not email_subject else email_subject,
                content=self.get_plan_email_content(plan_inst_obj),
                send_to='{},{}'.format(creator_email, email_to),
                cc_to=EMAIL_CC,  # 配置中获取抄送
                bcc_to=bcc_to,  # 配置中获取邮件组
                send_by=SendByChoices.EMAIL,
                send_type='html'
            )
        send_type = 'link'  # 'markdown'
        msg_link = '{}/ws/{}/test_plan/view/detail/{}'.format(get_skip_url(), plan_inst_obj.ws_id, plan_inst_obj.id)
        if plan_state == 'fail':
            msg_pic = 'https://www.iconsdb.com/icons/preview/soylent-red/x-mark-3-xxl.png'
        else:
            msg_pic = 'https://icons.iconarchive.com/icons/paomedia/small-n-flat/1024/sign-check-icon.png'
        if ding_to and settings.MSG_SWITCH_ON:
            OutSiteMsg.objects.create(
                subject=subject if not ding_subject else ding_subject,
                content=content,
                send_to=ding_to,
                send_by=SendByChoices.DING_TALK,
                send_type=send_type,
                msg_link=msg_link,
                msg_pic=msg_pic,
            )

    def job_handle(self, job_obj, receiver_list, job_state):
        """Job站外消息处理"""
        creator_email = ','.join(self.get_email_list([job_obj.creator]))
        job_state = get_job_state(job_state, job_obj)
        subject = '[Tone]{}测试{}'.format(job_obj.name, job_state)
        content = self.get_msg_content(job_obj, 'job_complete')
        bcc_to = ''
        ding_subject = ''
        email_subject = ''
        ding_to = ''
        email_to = ''
        config_dic = self.get_send_config(job_obj.id)
        if config_dic.get('ding'):
            ding_info = config_dic.get('ding')
            ding_subject = ding_info.get('subject', '').replace('{date}', datetime.now().strftime("%Y.%m.%d"))
            ding_to = self.check_ding_token(ding_info.get('to').strip().replace(' ', ','))
        if config_dic.get('email'):
            email_info = config_dic.get('email')
            email_subject = email_info.get('subject', '').replace('{date}', datetime.now().strftime("%Y.%m.%d"))
            email_to = email_info.get('to').strip().replace('.net', '-inc.com').replace(' ', ',')
        try:
            email_content = self.get_job_email_content(job_obj)
        except Exception as error:
            email_content = ''
            logger.error(f'get job email content fail:{error}')
        if settings.MSG_SWITCH_ON:
            OutSiteMsg.objects.create(
                subject=subject if not email_subject else email_subject,
                content=email_content,
                send_to='{},{}'.format(creator_email, email_to),
                cc_to=EMAIL_CC,  # 配置中获取抄送
                bcc_to=bcc_to,  # 配置中获取邮件组
                send_by=SendByChoices.EMAIL,
                send_type='html'
            )
        send_type = 'link'  # 'markdown'
        msg_link = '{}/ws/{}/test_result/{}'.format(get_skip_url(), job_obj.ws_id, job_obj.id)
        if job_state == '已通过':
            msg_pic = 'https://icons.iconarchive.com/icons/paomedia/small-n-flat/1024/sign-check-icon.png'
        else:
            msg_pic = 'https://www.iconsdb.com/icons/preview/soylent-red/x-mark-3-xxl.png'
        if ding_to and settings.MSG_SWITCH_ON:
            OutSiteMsg.objects.create(
                subject=subject if not ding_subject else ding_subject,
                content=content,
                send_to=ding_to,
                send_by=SendByChoices.DING_TALK,
                send_type=send_type,
                msg_link=msg_link,
                msg_pic=msg_pic,
            )

    def machine_handle(self, message_obj, machine_obj, admin_id_list, machine_type='aligroup'):
        """[故障]测试机器故障 VM20201228-0/11.164.65.13 上的任务在测试准备阶段失败, 机器可能已经故障，请及时处理 ！
        影响的Job:   64026 影响的Suite有: sp_hadoop"""
        job_obj = TestJob.objects.get(id=message_obj.impact_job)
        creator_email = ','.join(self.get_email_list([job_obj.creator]))
        subject = '[Tone]{}机器已故障'.format(machine_obj.sn)
        suite_name_list = TestSuite.objects.filter(id__in=message_obj.impact_suite).values_list('name', flat=True)
        ip = machine_obj.ip if machine_type == 'aligroup' else machine_obj.private_ip
        content = '''Tone平台[故障]测试机器故障 {}/{} 上的任务在测试准备阶段失败, 机器可能已经故障，请及时处理 ！
        影响的Job:   {} 影响的Suite有: {}'''.format(machine_obj.sn, ip, message_obj.impact_job,
                                             ''.join(suite_name_list))
        bcc_to = ''
        ding_to = ''
        email_to = ''
        msg_link = '{}/ws/{}/test_result/{}'.format(get_skip_url(), job_obj.ws_id, message_obj.impact_job)
        email_content = self.server_broken_in_prepare(
            machine_obj.sn, ip, msg_link, message_obj.impact_job, ''.join(suite_name_list))
        config_dic = self.get_send_config(message_obj.impact_job)
        if config_dic.get('ding'):
            ding_info = config_dic.get('ding')
            ding_to = self.check_ding_token(ding_info.get('to').strip().replace(' ', ','))
        if config_dic.get('email'):
            email_info = config_dic.get('email')
            email_to = email_info.get('to').strip().replace('.net', '-inc.com').replace(' ', ',')
        if settings.MSG_SWITCH_ON:
            OutSiteMsg.objects.create(
                subject=subject,
                content=email_content,
                send_to='{},{}'.format(creator_email, email_to),
                cc_to=EMAIL_CC,  # 配置中获取抄送
                bcc_to=bcc_to,  # 配置中获取邮件组
                send_by=SendByChoices.EMAIL,
                send_type='html'
            )
        send_type = 'link'  # 'markdown'
        msg_pic = 'https://imgb14.photophoto.cn/20200817/shiliangweixiubiaozhi-38516026_3.jpg'
        if ding_to and settings.MSG_SWITCH_ON:
            OutSiteMsg.objects.create(
                subject=subject,
                content=content,
                send_to=ding_to,
                send_by=SendByChoices.DING_TALK,
                send_type=send_type,
                msg_link=msg_link,
                msg_pic=msg_pic,
            )

    def create_out_site_msg(self, message_obj, admin_id_list, msg_type):
        """创建站外消息记录"""
        job_id = message_obj.job_id  # impact_job  plan_id
        config_dic = self.get_send_config(job_id)
        if not config_dic:
            return False
        content = self.get_msg_content(message_obj, msg_type)
        # 钉钉
        if config_dic.get('ding') and settings.MSG_SWITCH_ON:
            send_type = 'link'  # 'markdown'
            msg_link = ''
            msg_pic = ''
            ding_info = config_dic.get('ding')
            OutSiteMsg.objects.create(
                subject=ding_info.get('subject'),
                content=content,
                send_to=ding_info.get('to'),
                send_by=SendByChoices.DING_TALK,
                send_type=send_type,
                msg_link=msg_link,
                msg_pic=msg_pic,
            )
        # 邮件
        if config_dic.get('email') and settings.MSG_SWITCH_ON:
            email_info = config_dic.get('email')
            send_type = 'html'
            cc = ''
            bcc = ''
            OutSiteMsg.objects.create(
                subject=email_info.get('subject'),
                content=content,
                send_to=email_info.get('to'),
                cc_to=cc,  # 配置中获取抄送
                bcc_to=bcc,  # 配置中获取邮件组
                send_by=SendByChoices.EMAIL,
                send_type=send_type
            )
        return True
