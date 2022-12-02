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
        real_day_of_week = cls.day_of_week_format(day_of_week)
        job = scheduler.add_job(job_function, trigger='cron', args=args, minute=minute, hour=hour,
                                day=day, month=month, day_of_week=real_day_of_week,
                                misfire_grace_time=600)
        ScheduleMap.objects.create(schedule_job_id=job.id, object_id=args[0])

    @classmethod
    def day_of_week_format(cls, day_of_week):
        # 此方法为了解决添加定时任务时格式效验和实际运行定时任务两个模块对day_of_week差异
        # 添加定时任务效验定时任务格式使用CronTrigger.from_crontab(cron_express)，该模块中1-6代表周一到周六，0代表周天
        # 实际使用scheduler.add_job添加定时任务时，day_of_week参数中，0代表周一，1代表周二，2代表周三，***，5代表周六，6代表周天
        real_day_of_week = ""
        for i in day_of_week:
            if not i.isdigit():
                real_day_of_week += i
            else:
                real_day_of_week += str((int(i) + 6) % 7)
        return real_day_of_week

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
