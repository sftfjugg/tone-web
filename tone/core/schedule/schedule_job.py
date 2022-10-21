import logging

from django.db import transaction, connection

from tone.core.common.redis_cache import redis_cache
from tone.models import TestPlan, PlanInstance, PlanStageRelation, PlanStageTestRelation, PlanStagePrepareRelation, \
    PlanInstanceStageRelation, PlanInstanceTestRelation, PlanInstancePrepareRelation, BLOCKING_STATEGY_CHOICES, \
    TestTemplate, JobType, datetime, Workspace
from tone.models.job.job_models import TestJob
from tone.core.handle.report_handle import ReportHandle

logger = logging.getLogger('test_plan')


class ScheduleJob(object):
    @classmethod
    def run(cls, *args, **kwargs):
        pass


class TestPlanScheduleJob(ScheduleJob):
    @classmethod
    def run(cls, plan_id):
        if not is_connection_usable():
            connection.close()
        lock_name = 'aps_schedule_lock{}'.format(plan_id)
        identifier = redis_cache.acquire_lock(lock_name)
        if identifier:
            plan = TestPlan.objects.filter(id=plan_id).first()
            if not plan:
                logger.info('test plan not exists, but schedule job not stop. plan_id:{}'.format(plan_id))
                redis_cache.release_lock(lock_name, identifier)
                return
            logger.info('TestPlanScheduleJob run. plan_id:{}. cron_info:{}'.format(plan_id, plan.cron_info))
            ws = Workspace.objects.filter(id=plan.ws_id).first()
            if not ws:
                logger.info('workspace not exists, but schedule job not stop. plan_id:{}'.format(plan_id))
                redis_cache.release_lock(lock_name, identifier)
                return
            with transaction.atomic():
                if plan.blocking_strategy == BLOCKING_STATEGY_CHOICES[0][0]:
                    plan_instance = cls._create_instance_data(plan)
                    cls._create_relation_data(plan, plan_instance)
                elif plan.blocking_strategy == BLOCKING_STATEGY_CHOICES[1][0]:
                    PlanInstance.objects.filter(plan_id=plan.id, state__in=['pending', 'running']
                                                ).update(state='stop')
                    plan_instance = cls._create_instance_data(plan)
                    cls._create_relation_data(plan, plan_instance)
                elif plan.blocking_strategy == BLOCKING_STATEGY_CHOICES[2][0]:
                    if not PlanInstance.objects.filter(plan_id=plan.id,
                                                       state__in=['pending', 'running']).exists():
                        plan_instance = cls._create_instance_data(plan)
                        cls._create_relation_data(plan, plan_instance)

            redis_cache.release_lock(lock_name, identifier)

    @staticmethod
    def _create_instance_data(plan):
        auto_count = PlanInstance.objects.filter(plan_id=plan.id, query_scope='all').count() + 1
        return PlanInstance.objects.create(
            run_mode='auto',
            state='pending',
            plan_id=plan.id,
            name='{}-{}'.format(plan.name, auto_count),
            baseline_info=plan.baseline_info,
            test_obj=plan.test_obj,
            kernel_version=plan.kernel_version,
            rpm_info=plan.rpm_info,
            build_pkg_info=plan.build_pkg_info,
            build_job_id=plan.build_job_id,
            env_info=plan.env_info,
            notice_info=plan.notice_info,
            ws_id=plan.ws_id,
            project_id=plan.project_id,
            creator=plan.creator,
            start_time=datetime.now(),
            auto_report=plan.auto_report,
            report_name=plan.report_name,
            report_tmpl_id=plan.report_tmpl_id,
            report_description=plan.report_description,
            group_method=plan.group_method,
            base_group=plan.base_group,
            stage_id=plan.stage_id,
        )

    @staticmethod
    def _create_relation_data(plan, plan_instance):
        plan_stages = PlanStageRelation.objects.filter(plan_id=plan.id)
        for stage in plan_stages:
            instance_stage = PlanInstanceStageRelation.objects.create(
                plan_instance_id=plan_instance.id,
                stage_name=stage.stage_name,
                stage_index=stage.stage_index,
                stage_type=stage.stage_type,
                impact_next=stage.impact_next
            )

            stage_tests = PlanStageTestRelation.objects.filter(plan_id=plan.id, stage_id=stage.id)
            for stage_test in stage_tests:
                template_obj = TestTemplate.objects.filter(id=stage_test.tmpl_id, query_scope='all').first()
                job_type = JobType.objects.filter(id=template_obj.job_type_id, query_scope='all').first()
                if not job_type:
                    continue
                test_type = job_type.test_type
                PlanInstanceTestRelation.objects.create(
                    plan_instance_id=plan_instance.id,
                    run_index=stage_test.run_index,
                    instance_stage_id=instance_stage.id,
                    tmpl_id=stage_test.tmpl_id,
                    test_type=test_type,
                    state='pending'
                )

            stage_prepares = PlanStagePrepareRelation.objects.filter(plan_id=plan.id, stage_id=stage.id)
            for stage_prepare in stage_prepares:
                PlanInstancePrepareRelation.objects.create(
                    plan_instance_id=plan_instance.id,
                    run_index=stage_prepare.run_index,
                    instance_stage_id=instance_stage.id,
                    extend_info=stage_prepare.prepare_info,
                    channel_type=stage_prepare.prepare_info.get('channel_type', 'staragent'),
                    ip=stage_prepare.prepare_info.get('ip', '').strip(),
                    sn=stage_prepare.prepare_info.get('sn', '').strip(),
                    script_info=stage_prepare.prepare_info.get('script'),
                    state='pending'
                )


def is_connection_usable():
    try:
        connection.connection.ping()
    except Exception as ex:
        logger.info("test plan check mysql is gone. ex is {}", ex)
        return False
    else:
        return True


def auto_job_report():
    report_job = TestJob.objects.filter(state__in=['fail', 'success', 'stop'], report_is_saved=0,
                                        report_name__isnull=False).order_by('-id').first()
    if report_job:
        ReportHandle(report_job.id).save_report()
