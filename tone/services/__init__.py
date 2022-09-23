from apscheduler.schedulers.background import BackgroundScheduler
from tone.core.schedule.schedule_job import auto_job_report

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
scheduler.add_job(func=auto_job_report, max_instances=10, trigger='interval', minutes=5)
scheduler.start()
