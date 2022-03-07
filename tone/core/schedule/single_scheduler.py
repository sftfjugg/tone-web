from django_apscheduler.jobstores import DjangoJobStore

from tone.core.schedule.background_scheduler import DistributedBackgroundScheduler

scheduler = DistributedBackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")
scheduler._daemon = False
scheduler.start()
