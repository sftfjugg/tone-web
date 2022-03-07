import logging
from datetime import datetime

from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger

from tone.core.schedule.schedule_job import ScheduleJob
from tone.core.schedule.single_scheduler import scheduler
from tone.models.plan.schedule_models import ScheduleMap

logger = logging.getLogger('test_plan')


class ScheduleHandle(ScheduleJob):

    @classmethod
    def add_crontab_job(cls, job_function, expression, args=None, next_run_time=datetime.now()):
        """
        expression:
        https://apscheduler.readthedocs.io/en/latest/modules/triggers/cron.html#module-apscheduler.triggers.cron
        """
        minute, hour, day, month, day_of_week = expression.split(' ')
        if day_of_week.isdigit():
            day_of_week = (int(day_of_week) + 6) % 7
        job = scheduler.add_job(job_function, trigger='cron', args=args, minute=minute, hour=hour,
                                day=day, month=month, day_of_week=day_of_week,
                                misfire_grace_time=600)
        ScheduleMap.objects.create(schedule_job_id=job.id, object_id=args[0])

    @classmethod
    def add_standard_job(cls, job_function, trigger_type, **kwargs):
        scheduler.add_job(job_function, trigger_type, misfire_grace_time=3600, **kwargs)

    @classmethod
    def pause_job(cls, job_id=None, obj_id=None, obj_type='plan'):
        if not job_id and obj_id:
            job_id = ScheduleMap.objects.get(object_type=obj_type, object_id=obj_id).schedule_job_id
        scheduler.pause_job(job_id)

    @classmethod
    def resume_job(cls, job_id=None, obj_id=None, obj_type='plan'):
        if not job_id and obj_id:
            job_id = ScheduleMap.objects.get(object_type=obj_type, object_id=obj_id).schedule_job_id
        scheduler.resume_job(job_id)

    @classmethod
    def remove_job(cls, job_id=None, obj_id=None, obj_type='plan'):
        if not job_id and obj_id:
            job_id = ScheduleMap.objects.get(object_type=obj_type, object_id=obj_id).schedule_job_id
        try:
            scheduler.remove_job(job_id)
        except JobLookupError:
            pass
        ScheduleMap.objects.filter(schedule_job_id=job_id, object_id=obj_id).delete(really_delete=True)
