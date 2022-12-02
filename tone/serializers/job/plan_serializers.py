# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author:
"""
import json

from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models import TestPlan, User, PlanStageRelation, PlanStagePrepareRelation, \
    PlanStageTestRelation, TestTemplate, PlanInstance, PlanInstanceStageRelation, PlanInstancePrepareRelation, \
    PlanInstanceTestRelation, TestJob, Baseline, Project, Product, BuildJob, ReportObjectRelation, Report, datetime, \
    ReportTemplate
from tone.services.plan.plan_services import PlanService


class TestPlanSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    next_time = serializers.SerializerMethodField()
    cron_info = serializers.SerializerMethodField()

    class Meta:
        model = TestPlan
        fields = ['id', 'name', 'cron_info', 'enable', 'creator', 'creator_name', 'gmt_created', 'next_time']

    @staticmethod
    def get_cron_info(obj):
        if obj.cron_schedule:
            return obj.cron_info

    @staticmethod
    def get_next_time(obj):
        next_time = PlanService().get_plan_next_time(obj.id)
        if next_time is not None:
            next_time = next_time.strftime('%Y-%m-%d %H:%M:%S').split('+')[0]
        return next_time

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name


class TestPlanDetailSerializer(CommonSerializer):
    rpm_info = serializers.SerializerMethodField()
    env_info = serializers.SerializerMethodField()
    scripts = serializers.SerializerMethodField()
    env_prep = serializers.SerializerMethodField()
    test_config = serializers.SerializerMethodField()
    build_pkg_info = serializers.JSONField()
    kernel_info = serializers.JSONField()
    func_baseline = serializers.SerializerMethodField()
    func_baseline_name = serializers.SerializerMethodField()
    perf_baseline = serializers.SerializerMethodField()
    perf_baseline_name = serializers.SerializerMethodField()
    func_baseline_aliyun = serializers.SerializerMethodField()
    func_baseline_aliyun_name = serializers.SerializerMethodField()
    perf_baseline_aliyun = serializers.SerializerMethodField()
    perf_baseline_aliyun_name = serializers.SerializerMethodField()
    notice_name = serializers.SerializerMethodField()
    ding_talk_info = serializers.SerializerMethodField()
    email_info = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    next_time = serializers.SerializerMethodField()
    report_template_id = serializers.SerializerMethodField()
    report_template_name = serializers.SerializerMethodField()
    report_name = serializers.SerializerMethodField()
    base_group_info = serializers.SerializerMethodField()

    class Meta:
        model = TestPlan
        fields = ['id', 'name', 'project_id', 'project_name', 'description', 'func_baseline', 'func_baseline_name',
                  'perf_baseline', 'perf_baseline_name', 'test_obj', 'kernel_version', 'kernel_info',
                  'build_pkg_info', 'rpm_info', 'env_info', 'notice_name', 'ding_talk_info', 'email_info',
                  'cron_schedule', 'cron_info', 'blocking_strategy', 'enable', 'env_prep', 'test_config', 'next_time',
                  'auto_report', 'report_name', 'report_description', 'report_template_id', 'report_template_name',
                  'group_method', 'base_group', 'base_group_info', 'func_baseline_aliyun', 'func_baseline_aliyun_name',
                  'perf_baseline_aliyun', 'perf_baseline_aliyun_name', 'stage_id', 'scripts', 'creator']

    @staticmethod
    def get_base_group_info(obj):
        base_group_info = {}
        if obj.base_group is not None:
            if obj.group_method == 'job':
                tmp_stage_id = obj.stage_id or 1
                plan_stage = PlanStageRelation.objects.filter(plan_id=obj.id, stage_type='test_stage',
                                                              stage_index=tmp_stage_id).first()
                stage_name = None if not plan_stage else plan_stage.stage_name
                test_template = TestTemplate.objects.filter(id=obj.base_group).first()
                if test_template is not None:
                    base_group_info.update({
                        'group_method': 'job',
                        'base_group': obj.base_group,
                        'template_name': test_template.name,
                        'stage_id': obj.stage_id,
                        'stage_name': stage_name,
                    })
            elif obj.group_method == 'stage':
                plan_stage = PlanStageRelation.objects.filter(plan_id=obj.id, stage_type='test_stage',
                                                              stage_index=obj.base_group).first()
                if plan_stage is not None:
                    base_group_info.update({
                        'group_method': 'stage',
                        'base_group': obj.base_group,
                        'stage_name': plan_stage.stage_name,
                    })

        return base_group_info

    @staticmethod
    def get_report_name(obj):
        if obj.auto_report and not obj.report_name:
            return '{plan_name}_report-{report_seq_id}'
        return obj.report_name

    @staticmethod
    def get_report_template_id(obj):
        return obj.report_tmpl_id

    @staticmethod
    def get_report_template_name(obj):
        if obj.report_tmpl_id:
            return ReportTemplate.objects.filter(id=obj.report_tmpl_id, query_scope='all').first().name

    @staticmethod
    def get_next_time(obj):
        next_time = PlanService().get_plan_next_time(obj.id)
        if next_time is not None:
            next_time = next_time.strftime('%Y-%m-%d %H:%M:%S').split('+')[0]
        return next_time

    @staticmethod
    def get_project_name(obj):
        project_name = None
        project_obj = Project.objects.filter(id=obj.project_id).first()
        if project_obj is not None:
            product_obj = Product.objects.filter(id=project_obj.product_id).first()
            project_name = project_obj.name
            if project_obj is not None:
                project_name = '{}({})'.format(project_name, product_obj.name)
        return project_name

    @staticmethod
    def get_notice_name(obj):
        if obj.notice_info:
            return obj.notice_info[0].get('subject')

    @staticmethod
    def get_ding_talk_info(obj):
        if obj.notice_info:
            for notice in obj.notice_info:
                if notice.get('type') == 'ding':
                    return notice.get('to')

    @staticmethod
    def get_email_info(obj):
        if obj.notice_info:
            for notice in obj.notice_info:
                if notice.get('type') == 'email':
                    return notice.get('to')

    @staticmethod
    def get_func_baseline(obj):
        func_baseline = None
        if obj.baseline_info:
            func_baseline = obj.baseline_info.get('func_baseline', None)
        return func_baseline

    def get_func_baseline_name(self, obj):
        return self.get_baseline_name(obj, 'func_baseline')

    def get_perf_baseline_name(self, obj):
        return self.get_baseline_name(obj, 'perf_baseline')

    def get_func_baseline_aliyun_name(self, obj):
        return self.get_baseline_name(obj, 'func_baseline_aliyun')

    def get_perf_baseline_aliyun_name(self, obj):
        return self.get_baseline_name(obj, 'perf_baseline_aliyun')

    @staticmethod
    def get_baseline_name(obj, baseline_type):
        baseline_name = None
        if obj.baseline_info:
            baseline_id = obj.baseline_info.get(baseline_type, None)
            if baseline_id:
                baseline_obj = Baseline.objects.filter(id=baseline_id).first()
                if baseline_obj is not None:
                    baseline_name = baseline_obj.name
        return baseline_name

    @staticmethod
    def get_perf_baseline(obj):
        perf_baseline = None
        if obj.baseline_info:
            perf_baseline = obj.baseline_info.get('perf_baseline', None)
        return perf_baseline

    @staticmethod
    def get_perf_baseline_aliyun(obj):
        perf_baseline = None
        if obj.baseline_info:
            perf_baseline = obj.baseline_info.get('perf_baseline_aliyun', None)
        return perf_baseline

    @staticmethod
    def get_func_baseline_aliyun(obj):
        perf_baseline = None
        if obj.baseline_info:
            perf_baseline = obj.baseline_info.get('func_baseline_aliyun', None)
        return perf_baseline

    @staticmethod
    def get_rpm_info(obj):
        if isinstance(obj.rpm_info, list):
            return ','.join(obj.rpm_info)
        return obj.rpm_info if obj.rpm_info else ''

    @staticmethod
    def get_env_info(obj):
        if isinstance(obj.env_info, dict):
            return ','.join(['{}={}'.format(key, value) for key, value in obj.env_info.items()])
        return obj.env_info

    @staticmethod
    def get_scripts(obj):
        return obj.script_info

    @staticmethod
    def get_env_prep(obj):
        """获取测试准备配置"""
        prepare_stage = PlanStageRelation.objects.filter(plan_id=obj.id, stage_type='prepare_env').first()
        if prepare_stage is None:
            return None
        prepare_list = PlanStagePrepareRelation.objects.filter(plan_id=obj.id, stage_id=prepare_stage.id)
        if not prepare_list:
            return None
        prepare_config = {'machine_info': []}
        run_index_list = prepare_list.values_list('run_index', 'prepare_info')
        for run_index, prepare_info in sorted(run_index_list):
            prepare_config['machine_info'].append(prepare_info)
        prepare_config.update({'name': prepare_stage.stage_name})
        return prepare_config

    @staticmethod
    def get_test_config(obj):
        """获取测试配置"""
        test_stage_list = PlanStageRelation.objects.filter(plan_id=obj.id, stage_type='test_stage')
        stage_index_list = test_stage_list.values_list('id', 'stage_index', 'stage_name', 'impact_next')
        if not stage_index_list:
            return None
        test_config = list()
        for stage_id, stage_index, stage_name, impact_next in sorted(stage_index_list):
            template_list = list()
            stage_test_list = PlanStageTestRelation.objects.filter(plan_id=obj.id, stage_id=stage_id)
            stage_test_index_list = stage_test_list.values_list('run_index', 'tmpl_id')
            for run_index, tmpl_id in sorted(stage_test_index_list):
                tmp_template = TestTemplate.objects.filter(id=tmpl_id).first()
                if tmp_template is None:
                    continue
                template_list.append({
                    'id': tmpl_id,
                    'name': tmp_template.name
                })
            test_config.append({
                'name': stage_name,
                'template': template_list,
                'impact_next': impact_next,
            })
        return test_config


class PlanViewSerializer(CommonSerializer):
    trigger_count = serializers.SerializerMethodField()
    success_count = serializers.SerializerMethodField()
    fail_count = serializers.SerializerMethodField()
    next_time = serializers.SerializerMethodField()
    job_total = serializers.SerializerMethodField()

    class Meta:
        model = TestPlan
        fields = ['id', 'name', 'trigger_count', 'success_count', 'fail_count', 'next_time', 'description', 'job_total']

    @staticmethod
    def get_job_total(obj):
        plan_instance = PlanInstance.objects.filter(plan_id=obj.id).first()
        if plan_instance is not None:
            return PlanInstanceTestRelation.objects.filter(
                plan_instance_id=plan_instance.id, job_id__isnull=False).values_list('job_id', flat=True)
        return list()

    @staticmethod
    def get_next_time(obj):
        next_time = PlanService().get_plan_next_time(obj.id)
        if next_time is not None:
            next_time = next_time.strftime('%Y-%m-%d %H:%M:%S').split('+')[0]
        return next_time

    @staticmethod
    def get_trigger_count(obj):
        return PlanInstance.objects.filter(plan_id=obj.id).count()

    @staticmethod
    def get_success_count(obj):
        return PlanInstance.objects.filter(plan_id=obj.id, state='success').count()

    @staticmethod
    def get_fail_count(obj):
        return PlanInstance.objects.filter(plan_id=obj.id, state='fail').count()


class PlanResultSerializer(CommonSerializer):
    trigger_name = serializers.SerializerMethodField()
    job_total = serializers.SerializerMethodField()
    start_time = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    statistics = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    report_template_id = serializers.SerializerMethodField()
    report_li = serializers.SerializerMethodField()
    report_template_name = serializers.SerializerMethodField()

    class Meta:
        model = PlanInstance
        fields = ['id', 'name', 'state', 'statistics', 'run_mode', 'trigger_name', 'creator', 'start_time',
                  'end_time', 'job_total', 'state_desc', 'auto_report', 'report_name', 'report_description',
                  'report_template_id', 'report_li', 'report_template_name', 'group_method', 'base_group']

    @staticmethod
    def get_report_li(obj):
        ReportObjectRelation.objects.filter()
        report_li = []
        report_id_list = ReportObjectRelation.objects.filter(object_type='plan_instance',
                                                             object_id=obj.id).values_list('report_id')
        if report_id_list:
            report_queryset = Report.objects.filter(id__in=report_id_list)
            report_li = [{
                'id': report.id,
                'name': report.name,
                'creator': report.creator,
                'gmt_created': datetime.strftime(report.gmt_created, "%Y-%m-%d %H:%M:%S"),
            } for report in report_queryset]
        return report_li

    @staticmethod
    def get_report_template_id(obj):
        return obj.report_tmpl_id

    @staticmethod
    def get_report_template_name(obj):
        if obj.report_tmpl_id:
            return ReportTemplate.objects.filter(id=obj.report_tmpl_id, query_scope='all').first().name

    @staticmethod
    def get_end_time(obj):
        if obj.end_time:
            return str(obj.end_time).split('.')[0]

    @staticmethod
    def get_statistics(obj):
        if obj.statistics:
            return obj.statistics
        else:
            if obj.state in ['success', 'fail']:
                job_id_list = PlanInstanceTestRelation.objects.filter(plan_instance_id=obj.id, job_id__isnull=False
                                                                      ).values_list('job_id', flat=True)
                result = {'total': 0, 'pass': 0, 'fail': 0}
                for tmp_job_id in job_id_list:
                    tmp_job = TestJob.objects.filter(id=tmp_job_id, query_scope='all').first()
                    test_result = tmp_job.test_result
                    if test_result:
                        tmp_result = json.loads(test_result)
                        result['total'] = result['total'] + tmp_result['total']
                        result['pass'] = result['pass'] + tmp_result['pass']
                        result['fail'] = result['fail'] + tmp_result['fail']
                return result

    @staticmethod
    def get_state(obj):
        if obj.state == 'pending_q':
            return 'pending'
        return obj.state

    @staticmethod
    def get_start_time(obj):
        if obj.start_time:
            return str(obj.start_time).split('.')[0]

    @staticmethod
    def get_job_total(obj):
        return PlanInstanceTestRelation.objects.filter(
            plan_instance_id=obj.id, job_id__isnull=False).values_list('job_id', flat=True)

    @staticmethod
    def get_trigger_name(obj):
        trigger_name = None
        if obj.run_mode == 'auto':
            trigger_name = '自动触发'
        else:
            creator = User.objects.filter(id=obj.creator).first()
            if creator:
                trigger_name = creator.first_name if creator.first_name else creator.last_name
        return trigger_name


class PlanResultDetailSerializer(CommonSerializer):
    prepare_result = serializers.SerializerMethodField()
    test_result = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    env_info = serializers.SerializerMethodField()
    rpm_info = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    build_pkg_info = serializers.JSONField()
    kernel_info = serializers.JSONField()
    start_time = serializers.SerializerMethodField()
    build_result = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    end_time = serializers.SerializerMethodField()
    plan_config_info = serializers.SerializerMethodField()
    report_template_id = serializers.SerializerMethodField()
    report_li = serializers.SerializerMethodField()
    report_template_name = serializers.SerializerMethodField()

    class Meta:
        model = PlanInstance
        fields = ['id', 'name', 'state', 'statistics', 'start_time', 'end_time', 'prepare_result', 'test_result',
                  'creator_name', 'kernel_version', 'kernel_info', 'rpm_info', 'build_pkg_info',
                  'env_info', 'description', 'note', 'project_name', 'build_result', 'plan_config_info', 'auto_report',
                  'report_name', 'report_description', 'report_template_id', 'report_li', 'report_template_name',
                  'group_method', 'base_group']

    @staticmethod
    def get_report_li(obj):
        ReportObjectRelation.objects.filter()
        report_li = []
        report_id_list = ReportObjectRelation.objects.filter(object_type='plan_instance',
                                                             object_id=obj.id).values_list('report_id')
        if report_id_list:
            report_queryset = Report.objects.filter(id__in=report_id_list)
            report_li = [{
                'id': report.id,
                'name': report.name,
                'creator': report.creator,
                'gmt_created': datetime.strftime(report.gmt_created, "%Y-%m-%d %H:%M:%S"),
            } for report in report_queryset]
        return report_li

    @staticmethod
    def get_report_template_id(obj):
        return obj.report_tmpl_id

    @staticmethod
    def get_report_template_name(obj):
        if obj.report_tmpl_id:
            return ReportTemplate.objects.filter(id=obj.report_tmpl_id, query_scope='all').first().name

    @staticmethod
    def get_plan_config_info(obj):
        plan_obj = TestPlan.objects.filter(id=obj.plan_id).first()
        if plan_obj is not None:
            return TestPlanDetailSerializer(plan_obj, many=False).data

    @staticmethod
    def get_end_time(obj):
        if obj.end_time:
            return str(obj.end_time).split('.')[0]

    @staticmethod
    def get_state(obj):
        if obj.state == 'pending_q':
            return 'pending'
        return obj.state

    @staticmethod
    def get_build_result(obj):
        if obj.build_job_id is not None:
            build_result = dict()
            build_kernel_obj = BuildJob.objects.filter(id=obj.build_job_id).first()
            if build_kernel_obj:
                if obj.state in ('success', 'fail', 'stop') and build_kernel_obj.state in ['pending', 'pending_q']:
                    state = 'stop'
                else:
                    state = build_kernel_obj.state
                build_result.update({
                    'state': state,
                    'build_url': build_kernel_obj.build_url,
                    'build_log': build_kernel_obj.build_log,
                    'build_msg': build_kernel_obj.build_msg,
                    'rpm_list': build_kernel_obj.rpm_list,
                })
            return build_result

    @staticmethod
    def get_start_time(obj):
        if obj.start_time:
            return str(obj.start_time).split('.')[0]

    @staticmethod
    def get_project_name(obj):
        project_name = None
        project_obj = Project.objects.filter(id=obj.project_id).first()
        if project_obj is not None:
            product_obj = Product.objects.filter(id=project_obj.product_id).first()
            project_name = project_obj.name
            if project_obj is not None:
                project_name = '{}({})'.format(project_name, product_obj.name)
        return project_name

    @staticmethod
    def get_description(obj):
        description = None
        if TestPlan.objects.filter(id=obj.plan_id).exists():
            description = TestPlan.objects.get(id=obj.plan_id).description
        return description

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_prepare_result(obj):
        prepare_stage = PlanInstanceStageRelation.objects.filter(plan_instance_id=obj.id,
                                                                 stage_type='prepare_env').first()
        if prepare_stage is None:
            return None
        prepare_list = PlanInstancePrepareRelation.objects.filter(plan_instance_id=obj.id,
                                                                  instance_stage_id=prepare_stage.id)
        if not prepare_list:
            return None
        prepare_result = {'machine_info': []}
        run_index_list = prepare_list.values_list('run_index', 'extend_info', 'state', 'result')
        stage_state_list = list()
        for run_index, prepare_info, state, result in sorted(run_index_list):
            prepare_info.update({
                'state': state,
                'result': result if result else '',
            })
            prepare_result['machine_info'].append(prepare_info)
            stage_state_list.append(state)
        stage_state = 'pending'
        if 'fail' in set(stage_state_list):
            stage_state = 'fail'
        elif 'running' in set(stage_state_list):
            stage_state = 'running'
        elif set(stage_state_list) == {'success'}:
            stage_state = 'success'
        prepare_result.update({'name': prepare_stage.stage_name, 'stage_state': stage_state})
        return prepare_result

    def get_test_result(self, obj):
        """获取测试配置"""
        test_stage_list = PlanInstanceStageRelation.objects.filter(plan_instance_id=obj.id, stage_type='test_stage')
        stage_index_list = test_stage_list.values_list('id', 'stage_index', 'stage_name', 'impact_next')
        if not stage_index_list:
            return None
        test_result = list()
        last_impact = False
        for stage_id, stage_index, stage_name, impact_next in sorted(stage_index_list):
            job_state_list = list()
            template_list = list()
            stage_test_list = PlanInstanceTestRelation.objects.filter(plan_instance_id=obj.id,
                                                                      instance_stage_id=stage_id)
            stage_test_index_list = stage_test_list.values_list('run_index', 'tmpl_id', 'job_id')
            for run_index, tmpl_id, job_id in sorted(stage_test_index_list):
                tmp_template = TestTemplate.objects.filter(id=tmpl_id).first()
                if tmp_template is None:
                    continue
                template_result = {
                    'tmpl_id': tmpl_id,
                    'tmpl_name': tmp_template.name,
                    'job_id': None,
                    'job_name': None,
                    'job_state': 'stop' if obj.state in ('success', 'fail', 'stop') else None,
                    'job_result': None,
                }
                # 查询job运行结果  运行状态  统计数量
                job_obj = TestJob.objects.filter(id=job_id).first()
                if job_obj is not None:
                    template_result.update({
                        'job_id': job_obj.id,
                        'job_name': job_obj.name,
                        'job_state': job_obj.state,
                        'job_result': job_obj.test_result,
                    })
                    job_state_list.append(job_obj.state)
                template_list.append(template_result)

            stage_state = self.get_stage_state(job_state_list, obj)
            test_result.append({
                'name': stage_name,
                'stage_state': stage_state if not last_impact else 'stop',
                'template_result': template_list,
                'impact_next': impact_next,
            })
            if stage_state == 'fail' and impact_next:
                last_impact = impact_next
        return test_result

    @staticmethod
    def get_stage_state(job_state_list, obj):
        stage_state = 'pending'
        if 'fail' in set(job_state_list) or 'skip' in set(job_state_list):
            stage_state = 'fail'
        elif 'running' in set(job_state_list):
            stage_state = 'running'
        elif set(job_state_list) == {'success'}:
            stage_state = 'success'
        if obj.state in ('success', 'fail', 'stop') and stage_state == 'pending':
            stage_state = 'stop'
        return stage_state

    @staticmethod
    def get_env_info(obj):
        if isinstance(obj.env_info, dict):
            return '\n'.join(['{}={}'.format(key, value) for key, value in obj.env_info.items()])
        return obj.env_info

    @staticmethod
    def get_rpm_info(obj):
        if isinstance(obj.rpm_info, list):
            return '\n'.join(obj.rpm_info)
        return obj.rpm_info
