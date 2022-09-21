# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import urllib.parse as urlparse
from datetime import datetime

from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from tone import settings
from tone.core.common.constant import CASE_STEP_STAGE_MAP, PREPARE_STEP_STAGE_MAP, \
    FUNC_CASE_RESULT_TYPE_MAP, PERF_CASE_RESULT_TYPE_MAP, SUITE_STEP_PREPARE_MAP
from tone.core.common.enums.job_enums import JobState
from tone.core.common.info_map import get_result_map
from tone.core.common.job_result_helper import calc_job_suite, calc_job_case, calc_job, get_job_case_server, \
    get_job_case_run_server
from tone.core.common.serializers import CommonSerializer
from tone.core.utils.tone_thread import ToneThread
from tone.models import TestJob, JobType, Project, Product, TestJobCase, TestJobSuite, TestCase, TestSuite, \
    JobTagRelation, JobTag, TestStep, FuncResult, PerfResult, ResultFile, User, TestMetric, FuncBaselineDetail, \
    TestServerSnapshot, CloudServerSnapshot, PlanInstanceTestRelation, PlanInstance, ReportObjectRelation, Report, \
    BusinessSuiteRelation, TestBusiness, WorkspaceCaseRelation, JobMonitorItem, MonitorInfo, BaseConfig, \
    TestClusterSnapshot, TestCluster, CloudServer
from tone.models.sys.baseline_models import Baseline, PerfBaselineDetail


class JobTestSerializer(CommonSerializer):
    test_type = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()

    class Meta:
        model = TestJob
        fields = ['id', 'name', 'creator_name', 'ws_id', 'gmt_created', 'end_time', 'state', 'test_type', 'project_id',
                  'project_name', 'collection', 'test_result', 'state_desc', 'start_time', 'product_version', 'creator',
                  'server', 'report_li', 'product_id', 'product_name', 'report_name', 'report_template_id',
                  'callback_api', 'created_from']

    @staticmethod
    def get_start_time(obj):
        return get_time(obj.start_time)

    @staticmethod
    def get_end_time(obj):
        return get_time(obj.end_time)

    @staticmethod
    def get_state(obj):
        state = obj.state
        if obj.state == 'pending_q':
            state = 'pending'
        if obj.test_type == 'functional' and (obj.state == 'fail' or obj.state == 'success'):
            func_view_config = BaseConfig.objects.filter(config_type='ws', ws_id=obj.ws_id,
                                                         config_key='FUNC_RESULT_VIEW_TYPE').first()
            if func_view_config and func_view_config.config_value == '2':
                func_result = FuncResult.objects.filter(test_job_id=obj.id)
                if func_result.count() == 0:
                    state = 'fail'
                    return state
                func_result_list = FuncResult.objects.filter(test_job_id=obj.id, sub_case_result=2)
                if func_result_list.count() == 0:
                    state = 'pass'
                else:
                    if func_result_list.filter(match_baseline=0).count() > 0:
                        state = 'fail'
                    else:
                        state = 'pass'
        return state

    @staticmethod
    def get_test_type(obj):
        test_type_map = {
            'functional': '功能测试',
            'performance': '性能测试',
            'business': '业务测试',
            'stability': '稳定性测试'
        }
        return test_type_map.get(obj.test_type)


class JobTestConfigSerializer(CommonSerializer):
    product_name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    test_config = serializers.SerializerMethodField()
    iclone_info = serializers.JSONField()
    env_info = serializers.JSONField()
    script_info = serializers.JSONField()
    kernel_info = serializers.JSONField()
    build_pkg_info = serializers.JSONField()
    notice_info = serializers.JSONField()
    monitor_info = serializers.JSONField()
    rpm_info = serializers.JSONField()
    tags = serializers.SerializerMethodField()
    project_id = serializers.SerializerMethodField()

    class Meta:
        model = TestJob
        fields = ['product_name', 'project_name', 'iclone_info', 'env_info', 'rpm_info', 'script_info', 'monitor_info',
                  'cleanup_info', 'notice_info', 'test_config', 'need_reboot', 'kernel_info', 'build_pkg_info',
                  'kernel_version', 'tags', 'report_name', 'report_template_id', 'callback_api', 'project_id']

    @staticmethod
    def get_tags(obj):
        tag_config = [tag.tag_id for tag in JobTagRelation.objects.filter(job_id=obj.id)]
        tag_config = [tag for tag in tag_config if JobTag.objects.filter(id=tag).exists()]
        return tag_config

    @staticmethod
    def get_product_name(obj):
        product_name = Product.objects.filter(id=obj.product_id).first().name if Product.objects.filter(
            id=obj.product_id).first() else ''
        return product_name

    @staticmethod
    def get_project_name(obj):
        project_name = Project.objects.filter(id=obj.project_id).first().name if Project.objects.filter(
            id=obj.project_id).first() else ''
        return project_name

    @staticmethod
    def get_project_id(obj):
        project_id = Project.objects.filter(id=obj.project_id).first().id if Project.objects.filter(
            id=obj.project_id).exists() else ''
        return project_id

    @staticmethod
    def get_test_config(obj):
        test_config = list()
        job_suites = TestJobSuite.objects.filter(job_id=obj.id)
        job_cases = TestJobCase.objects.filter(job_id=obj.id)
        for job_suite in job_suites:
            obj_dict = {
                'test_suite_id': job_suite.test_suite_id,
                'test_suite_name': TestSuite.objects.get_value(
                    id=job_suite.test_suite_id) and TestSuite.objects.get_value(id=job_suite.test_suite_id).name,
                'need_reboot': job_suite.need_reboot,
                'setup_info': job_suite.setup_info,
                'cleanup_info': job_suite.cleanup_info,
                'monitor_info': job_suite.monitor_info,
                'priority': job_suite.priority,
                'run_mode': TestSuite.objects.get_value(id=job_suite.test_suite_id) and TestSuite.objects.get_value(
                    id=job_suite.test_suite_id).run_mode,
            }
            if WorkspaceCaseRelation.objects.filter(test_type='business',
                                                    test_suite_id=job_suite.test_suite_id,
                                                    query_scope='all').exists():
                business_relation = BusinessSuiteRelation.objects.filter(test_suite_id=obj.id,
                                                                         query_scope='all').first()
                if business_relation:
                    test_business = TestBusiness.objects.filter(id=business_relation.business_id,
                                                                query_scope='all').first()
                    if test_business:
                        obj_dict.update({'business_name': test_business.name})
            cases = list()
            for case in job_cases.filter(test_suite_id=job_suite.test_suite_id):
                ip = get_job_case_server(case.id, is_config=True)[0]
                is_instance = get_job_case_server(case.id, is_config=True)[1]
                cases.append({
                    'test_case_id': case.test_case_id,
                    'test_case_name': TestCase.objects.get_value(id=case.test_case_id) and TestCase.objects.get_value(
                        id=case.test_case_id).name,
                    'setup_info': case.setup_info,
                    'cleanup_info': case.cleanup_info,
                    'server_ip': ip,
                    'is_instance': is_instance,
                    'need_reboot': case.need_reboot,
                    'console': case.console,
                    'monitor_info': case.monitor_info,
                    'priority': case.priority,
                    'env_info': case.env_info,
                    'repeat': case.repeat,
                    'run_mode': case.run_mode,
                })
            obj_dict['cases'] = cases
            test_config.append(obj_dict)
        return test_config


class JobTestSummarySerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    test_type = serializers.SerializerMethodField()
    baseline_name = serializers.SerializerMethodField()
    provider_name = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    job_type = serializers.SerializerMethodField()
    case_result = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    plan_instance_id = serializers.SerializerMethodField()
    plan_instance_name = serializers.SerializerMethodField()
    report_li = serializers.SerializerMethodField()
    business_type = serializers.SerializerMethodField()
    pending_state_desc = serializers.SerializerMethodField()

    class Meta:
        model = TestJob
        fields = ['id', 'name', 'creator_name', 'gmt_created', 'end_time', 'state', 'test_type', 'baseline_name',
                  'provider_name', 'tags', 'project_name', 'product_version', 'job_type', 'case_result', 'note',
                  'creator', 'job_type_id', 'start_time', 'plan_instance_id', 'plan_instance_name', 'report_li',
                  'created_from', 'business_type', 'pending_state_desc', 'baseline_job_id']

    @staticmethod
    def get_business_type(obj):
        if obj.test_type == 'business':
            if obj.job_type_id and JobType.objects.filter(id=obj.job_type_id).exists():
                return JobType.objects.get(id=obj.job_type_id).business_type
        return None

    def get_report_li(self, obj):
        report_li = []
        report_id_list = ReportObjectRelation.objects.filter(object_type='job',
                                                             object_id=obj.id).values_list('report_id')
        if report_id_list:
            report_queryset = Report.objects.filter(id__in=report_id_list)
            report_li = [{
                'id': report.id,
                'name': report.name,
                'creator': report.creator,
                'creator_name': self.get_creator_name(report),
                'gmt_created': datetime.strftime(report.gmt_created, "%Y-%m-%d %H:%M:%S"),
            } for report in report_queryset]
        return report_li

    @staticmethod
    def get_plan_instance_id(obj):
        plan_instance_relation = PlanInstanceTestRelation.objects.filter(job_id=obj.id).first()
        if plan_instance_relation is not None:
            plan_instance = PlanInstance.objects.filter(id=plan_instance_relation.plan_instance_id).first()
            if plan_instance is not None:
                return plan_instance.id

    @staticmethod
    def get_plan_instance_name(obj):
        plan_instance_relation = PlanInstanceTestRelation.objects.filter(job_id=obj.id).first()
        if plan_instance_relation is not None:
            plan_instance = PlanInstance.objects.filter(id=plan_instance_relation.plan_instance_id).first()
            if plan_instance is not None:
                return plan_instance.name

    @staticmethod
    def get_start_time(obj):
        return get_time(obj.start_time)

    @staticmethod
    def get_end_time(obj):
        return get_time(obj.end_time)

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_state(obj):
        state = obj.state
        if obj.state == 'pending_q':
            state = 'pending'
        if obj.test_type == 'functional' and (obj.state == 'fail' or obj.state == 'success'):
            func_view_config = BaseConfig.objects.filter(config_type='ws', ws_id=obj.ws_id,
                                                         config_key='FUNC_RESULT_VIEW_TYPE').first()
            if func_view_config and func_view_config.config_value == '2':
                func_result = FuncResult.objects.filter(test_job_id=obj.id)
                if func_result.count() == 0:
                    state = 'fail'
                    return state
                func_result_list = FuncResult.objects.filter(test_job_id=obj.id, sub_case_result=2)
                if func_result_list.count() == 0:
                    state = 'pass'
                else:
                    if func_result_list.filter(match_baseline=0).count() > 0:
                        state = 'fail'
                    else:
                        state = 'pass'
        return state

    @staticmethod
    def get_test_type(obj):
        business_type = ''
        if obj.test_type == 'business':
            if obj.job_type_id and JobType.objects.filter(id=obj.job_type_id).exists():
                business_type = {
                    'functional': '功能',
                    'performance': '性能',
                    'business': '接入',
                }.get(JobType.objects.get(id=obj.job_type_id).business_type, '')

        test_type_map = {
            'functional': '功能测试',
            'performance': '性能测试',
            'business': '业务{}测试'.format(business_type),
            'stability': '稳定性测试'
        }
        return test_type_map.get(obj.test_type)

    @staticmethod
    def get_baseline_name(obj):
        baseline = None
        if obj.baseline_id and Baseline.objects.filter(id=obj.baseline_id).exists():
            baseline = Baseline.objects.get(id=obj.baseline_id).name
        return baseline

    def get_pending_state_desc(self, obj):
        state = self.get_state(obj)
        if state == 'pending':
            pending_state_desc = obj.state_desc
            return pending_state_desc

    @staticmethod
    def get_job_type(obj):
        if obj.job_type_id and JobType.objects.filter(id=obj.job_type_id).exists():
            return JobType.objects.get(id=obj.job_type_id).name
        return None

    @staticmethod
    def get_project_name(obj):
        project_name = None
        if obj.project_id and Project.objects.filter(id=obj.project_id).exists():
            project_name = Project.objects.get(id=obj.project_id).name
        return project_name

    @staticmethod
    def get_provider_name(obj):
        return obj.server_provider

    @staticmethod
    def get_tags(obj):
        tag_list = list()
        tags = [tag.tag_id for tag in JobTagRelation.objects.filter(job_id=obj.id)]
        for tag in tags:
            if JobTag.objects.filter(id=tag).exists():
                tag_list.append({'id': JobTag.objects.get(id=tag).id, 'name': JobTag.objects.get(id=tag).name,
                                 'color': JobTag.objects.get(id=tag).tag_color})
        return tag_list

    @staticmethod
    def get_case_result(obj):
        return calc_job(obj.id)


class JobTestProcessSuiteSerializer(CommonSerializer):
    test_suite_name = serializers.SerializerMethodField()
    step = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()

    class Meta:
        model = TestJobSuite
        fields = ['id', 'test_suite_id', 'test_suite_name', 'state', 'need_reboot', 'setup_info', 'cleanup_info',
                  'console', 'monitor_info', 'note', 'step', 'start_time', 'end_time', 'creator', 'business_name']

    @staticmethod
    def get_business_name(obj):
        business_relation = BusinessSuiteRelation.objects.filter(test_suite_id=obj.test_suite_id,
                                                                 query_scope='all').first()
        if business_relation:
            test_business = TestBusiness.objects.filter(id=business_relation.business_id, query_scope='all').first()
            if test_business:
                return test_business.name

    @staticmethod
    def get_creator(obj):
        job_obj = TestJob.objects.filter(id=obj.job_id).first()
        if job_obj is not None:
            return job_obj.creator

    @staticmethod
    def get_start_time(obj):
        return get_time(obj.start_time)

    @staticmethod
    def get_end_time(obj):
        return get_time(obj.end_time)

    @staticmethod
    def get_step(obj):
        step_li = list()
        steps = TestStep.objects.filter(job_suite_id=obj.id)
        for step in steps:
            if step.stage in SUITE_STEP_PREPARE_MAP.keys():
                step_li.append({
                    'stage': SUITE_STEP_PREPARE_MAP.get(step.stage),
                    'state': step.state,
                    'result': step.result,
                    'tid': step.tid,
                    'gmt_created': datetime.strftime(step.gmt_created, "%Y-%m-%d %H:%M:%S"),
                    'gmt_modified': datetime.strftime(step.gmt_modified,
                                                      "%Y-%m-%d %H:%M:%S") if step.state != 'running' else None
                })
        return step_li

    @staticmethod
    def get_test_suite_name(obj):
        return TestSuite.objects.get_value(id=obj.test_suite_id) and TestSuite.objects.get_value(
            id=obj.test_suite_id).name


class JobTestProcessCaseSerializer(CommonSerializer):
    test_case_name = serializers.SerializerMethodField()
    tid = serializers.SerializerMethodField()
    result = serializers.SerializerMethodField()
    step = serializers.SerializerMethodField()
    server = serializers.SerializerMethodField()
    server_id = serializers.SerializerMethodField()
    log_file = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()

    class Meta:
        model = TestJobCase
        fields = ['id', 'state', 'test_case_name', 'need_reboot', 'setup_info', 'cleanup_info', 'start_time',
                  'console', 'monitor_info', 'note', 'end_time', 'tid', 'result', 'step', 'server',
                  'log_file', 'server_id']

    @staticmethod
    def get_start_time(obj):
        return get_time(obj.start_time)

    @staticmethod
    def get_end_time(obj):
        return get_time(obj.end_time)

    @staticmethod
    def get_test_case_name(obj):
        return TestCase.objects.get_value(id=obj.test_case_id) and TestCase.objects.get_value(id=obj.test_case_id).name

    @staticmethod
    def get_server(obj):
        step = TestStep.objects.filter(job_case_id=obj.id).first() if TestStep.objects.filter(
            job_case_id=obj.id).exists() else None
        if not step or not step.server:
            return None
        if step.server.isdigit():
            server = get_check_server_ip(step.server, obj.server_provider, )
        else:
            server = step.server
        return server

    @staticmethod
    def get_server_id(obj):
        step = TestStep.objects.filter(job_case_id=obj.id).first() \
            if TestStep.objects.filter(job_case_id=obj.id).exists() else None
        if not step or not step.server:
            return None
        return step.server

    @staticmethod
    def get_tid(obj):
        if TestStep.objects.filter(job_case_id=obj.id, stage='run_case').exists():
            return TestStep.objects.get(job_case_id=obj.id, stage='run_case').tid
        else:
            return None

    @staticmethod
    def get_log_file(obj):
        test_step = TestStep.objects.filter(job_case_id=obj.id, stage='run_case')
        if test_step.exists():
            path = urlparse.urlparse(test_step.first().log_file).path
            return f"http://{settings.TONE_STORAGE_DOMAIN}:{settings.TONE_STORAGE_PROXY_PORT}{path}"

    @staticmethod
    def get_result(obj):
        result = ""
        if TestStep.objects.filter(job_case_id=obj.id, stage='run_case', state__in=['success', 'fail']).exists():
            result = TestStep.objects.filter(job_case_id=obj.id, stage='run_case').last().result
        else:
            if obj.state == 'fail' and not obj.start_time:
                result = 'machine prepare failed'
            elif obj.state == 'stop' or obj.state == 'skip':
                result = TestJobCase.objects.get(job_id=obj.job_id, test_case_id=obj.test_case_id,
                                                 test_suite_id=obj.test_suite_id).note
            elif obj.state == 'pending':
                result = "Waiting to run"
            elif obj.state == 'running':
                result = "Running"
        if result:
            return get_result_map("output_result", result)

    @staticmethod
    def get_step(obj):
        step = list()
        test_steps = TestStep.objects.filter(job_case_id=obj.id)
        for test_step in test_steps:
            if test_step.stage in CASE_STEP_STAGE_MAP.keys():
                step.append({
                    'state': test_step.state,
                    'stage': test_step.stage,
                    'result': test_step.result,
                    'tid': test_step.tid,
                    'gmt_created': datetime.strftime(test_step.gmt_created, "%Y-%m-%d %H:%M:%S"),
                    'gmt_modified': datetime.strftime(test_step.gmt_created, "%Y-%m-%d %H:%M:%S"),
                })
        return step


class JobTestPrepareSerializer(CommonSerializer):
    test_prepare = serializers.SerializerMethodField()

    class Meta:
        model = TestJob
        fields = ['test_prepare']

    @staticmethod
    def get_test_prepare(obj):
        server_step = {'standalone': dict(), 'cluster': dict()}
        data_list = []
        steps = TestStep.objects.filter(job_id=obj.id, stage__in=PREPARE_STEP_STAGE_MAP.keys())
        provider = obj.server_provider
        for step in steps:
            if step.cluster_id:
                insert_cluster(server_step, provider, step, data_list)
            else:
                insert_standalone(step, server_step, provider)
        return server_step


class JobTestResultSerializer(CommonSerializer):
    test_suite = serializers.SerializerMethodField()

    class Meta:
        model = TestJob
        fields = ['test_suite', 'creator']

    def get_test_suite(self, obj):
        suite_list = list()
        suites = TestJobSuite.objects.filter(job_id=obj.id, state__in=['success', 'fail', 'skip', 'stop', 'running'])
        test_type = get_test_type(obj)
        test_type_map = {
            'functional': '功能测试',
            'performance': '性能测试',
            'business': '业务测试',
            'stability': '稳定性测试'
        }
        thread_tasks = []
        for suite in suites:
            thread_tasks.append(
                ToneThread(self._get_test_suite_result, (suite, obj, test_type, test_type_map))
            )
            thread_tasks[-1].start()
        for thread_task in thread_tasks:
            thread_task.join()
            suite_item_data = thread_task.get_result()
            suite_list.append(suite_item_data)
        return suite_list

    @staticmethod
    def _get_test_suite_result(suite, test_job, test_type, test_type_map):
        test_suite = TestSuite.objects.get(id=suite.test_suite_id)
        business_name = None
        if suite.state != 'running':
            if test_job.test_type == 'business':
                tmp_test_suite = TestSuite.objects.filter(id=suite.test_suite_id, query_scope='all').first()
                test_type = test_type_map.get(tmp_test_suite.test_type)
                business = BusinessSuiteRelation.objects.filter(test_suite_id=suite.test_suite_id,
                                                                query_scope='all').first()
                business_name = TestBusiness.objects.filter(id=business.business_id, query_scope='all').first().name
            suite_data = {
                'job_suite_id': suite.id,
                'suite_id': suite.test_suite_id,
                'suite_name': test_suite.name,
                'test_type': test_type,
                'note': suite.note,
                'start_time': datetime.strftime(suite.start_time,
                                                "%Y-%m-%d %H:%M:%S") if suite.start_time else None,
                'end_time': datetime.strftime(suite.end_time, "%Y-%m-%d %H:%M:%S") if suite.end_time else None,
                'creator': test_job.creator,
                'business_name': business_name,
            }
            if test_type == '性能测试':
                per_result = PerfResult.objects.filter(test_job_id=test_job.id, test_suite_id=suite.test_suite_id)
                baseline_id = test_job.baseline_id
                baseline = None
                if per_result.exists() and per_result.first().compare_baseline:
                    baseline_id = per_result.first().compare_baseline
                if Baseline.objects.filter(id=baseline_id).exists():
                    baseline = Baseline.objects.get(id=baseline_id).name
                suite_data['baseline'] = baseline
                _, count_data = calc_job_suite(suite.id, test_job.ws_id, test_job.test_type)
            elif test_type == '业务测试':
                result, count_data = calc_job_suite(suite.id, test_job.ws_id, test_job.test_type)
                suite_data['result'] = result
            else:
                result, count_data = calc_job_suite(suite.id, test_job.ws_id, test_job.test_type)
                suite_data['result'] = result
            suite_data = {**suite_data, **count_data}
            suite_data['baseline_job_id'] = test_job.baseline_job_id
            return suite_data
        else:
            # 当有任意case结束时返回running的suite
            check_cases = TestJobCase.objects.filter(job_id=test_job.id, test_suite_id=suite.test_suite_id,
                                                     state__in=['success', 'fail', 'skip', 'stop']).count()
            if check_cases > 0:
                suite_data = {
                    'job_suite_id': suite.id,
                    'suite_id': suite.test_suite_id,
                    'suite_name': test_suite.name,
                    'test_type': test_type,
                    'note': suite.note,
                    'start_time': datetime.strftime(suite.start_time,
                                                    "%Y-%m-%d %H:%M:%S") if suite.start_time else None,
                    'end_time': datetime.strftime(suite.end_time, "%Y-%m-%d %H:%M:%S") if suite.end_time else None,
                    'creator': test_job.creator,
                    'business_name': business_name
                }
                if test_type == '性能测试':
                    count_data = {
                        'count': '-',
                        'increase': '-',
                        'decline': '-',
                        'normal': '-',
                        'invalid': '-',
                        'na': '-'
                    }
                else:
                    count_data = {
                        'conf_count': '-',
                        'conf_success': '-',
                        'conf_fail': '-',
                        'conf_warn': '-',
                        'conf_skip': '-',
                        'result': 'running'
                    }
                suite_data = {**suite_data, **count_data}
                suite_data['baseline_job_id'] = test_job.baseline_job_id
                return suite_data


class JobTestConfResultSerializer(CommonSerializer):
    conf_name = serializers.SerializerMethodField()
    server_ip = serializers.SerializerMethodField()
    server_id = serializers.SerializerMethodField()
    result_data = serializers.SerializerMethodField()
    baseline = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    baseline_job_id = serializers.SerializerMethodField()

    class Meta:
        model = TestJobCase
        fields = ['id', 'conf_name', 'test_case_id', 'server_ip', 'result_data', 'start_time', 'end_time', 'note',
                  'baseline', 'baseline_job_id', 'server_id']

    @staticmethod
    def get_start_time(obj):
        return get_time(obj.start_time)

    @staticmethod
    def get_end_time(obj):
        return get_time(obj.end_time)

    def get_baseline(self, obj):
        baseline = None
        test_job_obj = self.context.get('view').test_job_obj
        test_type = get_test_type(test_job_obj)
        if test_type == '性能测试':
            # per_result = PerfResult.objects.filter(test_job_id=obj.job_id, test_suite_id=obj.test_suite_id,
            #                                        test_case_id=obj.test_case_id)
            per_result = self.context.get('view').suite_result.filter(test_case_id=obj.test_case_id)
            baseline_id = test_job_obj.baseline_id
            if per_result.exists() and per_result.first().compare_baseline:
                baseline_id = per_result.first().compare_baseline
            if Baseline.objects.filter(id=baseline_id).exists():
                baseline = Baseline.objects.get(id=baseline_id).name
        return baseline

    def get_baseline_job_id(self, obj):
        test_job_obj = self.context.get('view').test_job_obj

    @staticmethod
    def get_conf_name(obj):
        return TestCase.objects.get_value(id=obj.test_case_id) and TestCase.objects.get_value(id=obj.test_case_id).name

    @staticmethod
    def get_server_ip(obj):
        return get_job_case_run_server(obj.id)

    @staticmethod
    def get_server_id(obj):
        return get_job_case_run_server(obj.id, return_field='id')

    def get_result_data(self, obj):
        calc_result = dict()
        result, count_data = calc_job_case(obj, self.context.get('view').suite_result,
                                           self.context.get('view').test_type)
        if result:
            calc_result['result'] = result
        calc_result = {**calc_result, **count_data}
        return calc_result


class JobTestCaseResultSerializer(CommonSerializer):
    result = serializers.SerializerMethodField()
    skip_baseline_info = serializers.SerializerMethodField()
    bug = serializers.SerializerMethodField()

    class Meta:
        model = FuncResult
        fields = ['sub_case_name', 'result', 'id', 'note', 'match_baseline', 'description', 'bug',
                  'skip_baseline_info']

    def get_match_baseline(self, obj):
        if obj.sub_case_result == 2 and not obj.match_baseline:
            baseline_id = self.context['request'].baseline_id
            if baseline_id:
                if FuncBaselineDetail.objects.filter(
                        baseline_id=baseline_id, test_suite_id=obj.test_suite_id,
                        test_case_id=obj.test_case_id, sub_case_name=obj.sub_case_name).exists():
                    return True
        return obj.match_baseline

    def get_bug(self, obj):
        if obj.sub_case_result == 2 and not obj.bug:
            baseline_id = self.context['request'].baseline_id
            if baseline_id:
                sub_case_res = FuncBaselineDetail.objects.filter(
                    baseline_id=baseline_id, test_suite_id=obj.test_suite_id,
                    test_case_id=obj.test_case_id, sub_case_name=obj.sub_case_name)
                if sub_case_res:
                    return sub_case_res.first().bug
        return obj.bug

    def get_description(self, obj):
        if obj.sub_case_result == 2 and not obj.description:
            baseline_id = self.context['request'].baseline_id
            if baseline_id:
                sub_case_res = FuncBaselineDetail.objects.filter(
                    baseline_id=baseline_id, test_suite_id=obj.test_suite_id,
                    test_case_id=obj.test_case_id, sub_case_name=obj.sub_case_name)
                if sub_case_res:
                    return sub_case_res.first().description
        return obj.description

    @staticmethod
    def get_creator(obj):
        return TestJob.objects.get(id=obj.test_job_id).creator

    def get_skip_baseline_info(self, obj):
        baseline_id = self.context['request'].baseline_id
        baseline_obj = self.context['request'].baseline_obj
        if obj.match_baseline:
            if baseline_obj is not None:
                func_detail = FuncBaselineDetail.objects.filter(baseline_id=baseline_id,
                                                                test_suite_id=obj.test_suite_id,
                                                                test_case_id=obj.test_case_id,
                                                                sub_case_name=obj.sub_case_name,
                                                                impact_result=True).first()
                if func_detail is not None:
                    return {'server_provider': baseline_obj.server_provider,
                            'test_type': baseline_obj.test_type,
                            'test_suite_id': obj.test_suite_id,
                            'test_case_id': obj.test_case_id,
                            'baseline_id': baseline_id,
                            'sub_case_name': obj.sub_case_name
                            }
            else:
                func_detail = FuncBaselineDetail.objects.filter(source_job_id=obj.test_job_id,
                                                                test_suite_id=obj.test_suite_id,
                                                                test_case_id=obj.test_case_id,
                                                                sub_case_name=obj.sub_case_name,
                                                                impact_result=True).first()
                if func_detail is not None:
                    baseline_obj = Baseline.objects.filter(id=func_detail.baseline_id).first()
                    if baseline_obj is not None:
                        return {'server_provider': baseline_obj.server_provider,
                                'test_type': baseline_obj.test_type,
                                'test_suite_id': obj.test_suite_id,
                                'test_case_id': obj.test_case_id,
                                'baseline_id': baseline_id,
                                'sub_case_name': obj.sub_case_name
                                }

    @staticmethod
    def get_result(obj):
        return FUNC_CASE_RESULT_TYPE_MAP.get(obj.sub_case_result)


class JobTestCasePerResultSerializer(CommonSerializer):
    result = serializers.SerializerMethodField()
    cv_value = serializers.SerializerMethodField()
    value_list = serializers.SerializerMethodField()
    threshold = serializers.SerializerMethodField()
    baseline_cv_value = serializers.SerializerMethodField()
    baseline_value = serializers.SerializerMethodField()
    compare_result = serializers.SerializerMethodField()
    test_value = serializers.SerializerMethodField()
    skip_baseline_info = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()

    class Meta:
        model = PerfResult
        fields = ['metric', 'test_value', 'id', 'cv_value', 'max_value', 'min_value', 'value_list', 'baseline_cv_value',
                  'compare_result', 'track_result', 'match_baseline', 'result', 'threshold', 'baseline_value',
                  'skip_baseline_info', 'creator', 'unit']

    @staticmethod
    def get_creator(obj):
        return TestJob.objects.get(id=obj.test_job_id).creator

    @staticmethod
    def get_skip_baseline_info(obj):
        if obj.compare_baseline is not None:
            baseline_obj = Baseline.objects.filter(id=obj.compare_baseline).first()
            if baseline_obj is not None:
                perf_detail = PerfBaselineDetail.objects.filter(baseline_id=obj.compare_baseline,
                                                                test_suite_id=obj.test_suite_id,
                                                                test_case_id=obj.test_case_id,
                                                                metric=obj.metric).first()
                if perf_detail is not None and obj.match_baseline:
                    return {'server_provider': baseline_obj.server_provider,
                            'test_type': baseline_obj.test_type,
                            'test_suite_id': perf_detail.test_suite_id,
                            'test_case_id': perf_detail.test_case_id,
                            'baseline_id': perf_detail.baseline_id,
                            'server_sm_name': perf_detail.server_sm_name,
                            'server_instance_type': perf_detail.server_instance_type,
                            'server_sn': perf_detail.server_sn,
                            }

    @staticmethod
    def get_baseline_value(obj):
        if obj.baseline_value is not None:
            return '{0:.2f}'.format(float(obj.baseline_value))

    @staticmethod
    def get_compare_result(obj):
        if obj.compare_result is not None:
            return '{0:.2f}%'.format(float(obj.compare_result) * 100)

    @staticmethod
    def get_test_value(obj):
        if obj.test_value is not None:
            return '{0:.2f}'.format(float(obj.test_value))

    @staticmethod
    def get_result(obj):
        return PERF_CASE_RESULT_TYPE_MAP.get(obj.track_result)

    @staticmethod
    def get_cv_value(obj):
        if obj.cv_value:
            cv_value = obj.cv_value.split('±')[-1].strip('%')
            return '{0:.2f}%'.format(float(cv_value))

    @staticmethod
    def get_baseline_cv_value(obj):
        baseline_cv_value = None
        if obj.baseline_cv_value:
            baseline_cv_value = obj.baseline_cv_value.split('±')[-1]
        return baseline_cv_value

    @staticmethod
    def get_value_list(obj):
        return list(obj.value_list)

    @staticmethod
    def get_threshold(obj):
        threshold = None
        object_id = None
        object_type = ""
        if TestMetric.objects.filter(object_id=obj.test_case_id, object_type='case', name=obj.metric).exists():
            object_id = obj.test_case_id
            object_type = 'case'
        elif TestMetric.objects.filter(object_id=obj.test_suite_id, object_type='suite', name=obj.metric).exists():
            object_id = obj.test_suite_id
            object_type = 'suite'
        if object_id and object_type:
            cmp_threshold = TestMetric.objects.get(object_id=object_id, name=obj.metric,
                                                   object_type=object_type).cmp_threshold
            cv_threshold = TestMetric.objects.get(object_id=object_id, name=obj.metric,
                                                  object_type=object_type).cv_threshold
            threshold = '{}%/{}%'.format(str(cmp_threshold * 100), str(cv_threshold * 100))
        return threshold


class JobTestCaseVersionSerializer(CommonSerializer):
    class Meta:
        model = TestJob
        fields = ['kernel_version', 'rpm_info']


class JobTestCaseFileSerializer(CommonSerializer):
    dp_result_file = serializers.SerializerMethodField()

    class Meta:
        model = ResultFile
        fields = ['result_path', 'id', 'dp_result_file', 'result_file']

    @staticmethod
    def get_dp_result_file(obj):
        return obj.result_file + '$' + str(obj.id)


class JobMonitorItemSerializer(CommonSerializer):
    name = serializers.SlugField(required=True, max_length=64, trim_whitespace=True, help_text='string | 英文标识，唯一',
                                 validators=[UniqueValidator(queryset=JobMonitorItem.objects.all())])

    class Meta:
        model = JobMonitorItem
        exclude = ['is_deleted']


class JobTestProcessMonitorSerializer(CommonSerializer):
    class Meta:
        model = MonitorInfo
        exclude = ['is_deleted']


def insert_standalone(step, server_step, provider):
    if not step.server:
        return
    if step.server.isdigit():
        server = get_check_server_ip(step.server, provider)
    else:
        server = step.server
    job_suite = step.job_suite_id
    if job_suite in server_step['standalone']:
        server_step['standalone'][job_suite].append({
            'stage': PREPARE_STEP_STAGE_MAP.get(step.stage),
            'state': step.state,
            'result': get_result_map("test_prepare", step.result),
            'tid': step.tid,
            'server': server,
            'server_id': step.server,
            'gmt_created': datetime.strftime(step.gmt_created, "%Y-%m-%d %H:%M:%S"),
            'gmt_modified': datetime.strftime(step.gmt_modified, "%Y-%m-%d %H:%M:%S")
            if step.state != 'running' else None
        })
    else:
        server_step['standalone'][job_suite] = [{
            'stage': PREPARE_STEP_STAGE_MAP.get(step.stage),
            'state': step.state,
            'result': get_result_map("test_prepare", step.result),
            'server': server,
            'server_id': step.server,
            'tid': step.tid,
            'gmt_created': datetime.strftime(step.gmt_created, "%Y-%m-%d %H:%M:%S"),
            'gmt_modified': datetime.strftime(step.gmt_modified, "%Y-%m-%d %H:%M:%S")
            if step.state != 'running' else None
        }]


def get_check_server_ip(server_id, provider):
    server = None
    if provider == 'aligroup' and TestServerSnapshot.objects.filter(id=server_id).exists():
        server_snapshot = TestServerSnapshot.objects.get(id=server_id)
        server = server_snapshot.ip if server_snapshot.ip else server_snapshot.sn
    if provider == 'aliyun' and CloudServerSnapshot.objects.filter(id=server_id).exists():
        server_snapshot = CloudServerSnapshot.objects.get(id=server_id)
        server = server_snapshot.private_ip if server_snapshot.private_ip else server_snapshot.sn
    return server


def insert_cluster(server_step, provider, step, data_list):
    if provider == 'aligroup':
        server = TestServerSnapshot.objects.get(id=step.server).ip
    else:
        server = CloudServerSnapshot.objects.get(id=step.server).private_ip
    test_step_cluster_id = step.cluster_id
    test_cluster_snapshot = TestClusterSnapshot.objects.filter(id=test_step_cluster_id).first()
    if test_cluster_snapshot:
        source_cluster_id = test_cluster_snapshot.source_cluster_id
        test_cluster = TestCluster.objects.filter(id=source_cluster_id).first()
        if test_cluster:
            cluster_name = test_cluster.name
            if not cluster_name:
                cluster_name = TestCluster.objects.filter(id=test_cluster_snapshot, query_scope='deleted').first().name
            data = {
                'stage': PREPARE_STEP_STAGE_MAP.get(step.stage),
                'state': step.state,
                'result': step.result,
                'tid': step.tid,
                'gmt_created': datetime.strftime(step.gmt_created, "%Y-%m-%d %H:%M:%S"),
                'gmt_modified': datetime.strftime(step.gmt_modified, "%Y-%m-%d %H:%M:%S")
                if step.state != JobState.RUNNING else None,
            }
            if cluster_name in server_step['cluster']:
                if server in server_step['cluster'][cluster_name]:
                    if data not in server_step['cluster'][cluster_name][server]:
                        server_step['cluster'][cluster_name][server].append(data)
                else:
                    server_step['cluster'][cluster_name][server] = [data]
            else:
                server_step['cluster'][cluster_name] = dict()
                server_step['cluster'][cluster_name][server] = [data]
            data_list.append(data)
            data_list_new = sorted(data_list, key=lambda x: x['gmt_created'], reverse=True)
            server_step['data'] = data_list_new[0]


def get_test_type(obj):
    test_type_map = {
        'functional': '功能测试',
        'performance': '性能测试',
        'business': '业务测试',
        'stability': '稳定性测试'
    }
    return test_type_map.get(obj.test_type)


def get_time(time):
    return datetime.strftime(time, "%Y-%m-%d %H:%M:%S") if time else None


class JobSerializerForAPI(CommonSerializer):
    test_type = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    kernel_info = serializers.JSONField()
    rpm_info = serializers.JSONField()
    script_info = serializers.JSONField()
    notice_info = serializers.JSONField()
    env_info = serializers.JSONField()

    class Meta:
        model = TestJob
        exclude = ['is_deleted', 'iclone_info', 'build_pkg_info', 'monitor_info']

    @staticmethod
    def get_start_time(obj):
        return get_time(obj.start_time)

    @staticmethod
    def get_end_time(obj):
        return get_time(obj.end_time)

    @staticmethod
    def get_state(obj):
        state = obj.state
        if obj.state == 'pending_q':
            state = 'pending'
        return state

    @staticmethod
    def get_test_type(obj):
        test_type_map = {
            'functional': '功能测试',
            'performance': '性能测试',
            'business': '业务测试',
            'stability': '稳定性测试'
        }
        return test_type_map.get(obj.test_type)


class JobTestMachineFaultSerializer(CommonSerializer):
    class Meta:
        model = TestServerSnapshot
        fields = ['ip', 'sn', 'device_type', 'channel_type', 'state', 'real_state']


class CloudJobTestMachineFaultSerializer(CommonSerializer):
    class Meta:
        model = CloudServer
        fields = ['pub_ip', 'sn', 'channel_type', 'state', 'real_state']
