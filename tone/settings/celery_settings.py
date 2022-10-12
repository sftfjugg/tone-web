from datetime import timedelta

CELERY_TIMEZONE = 'Asia/Shanghai'
DJANGO_CELERY_BEAT_TZ_AWARE = False
CELERY_FORCE_EXECV = True

CELERY_BEAT_SCHEDULE = {
    'auto_sync_suite_30_minutes': {
        'task': 'tone.tasks.sync_suite_case_toneagent',
        'schedule': timedelta(seconds=1800),
    },
    'auto_sync_suite_description_1_hour': {
        'task': 'tone.tasks.sync_suite_case_description',
        'schedule': timedelta(seconds=3600),
    },
    'auto_sync_data_to_portal': {
        'task': 'tone.tasks.sync_data_portal',
        'schedule': timedelta(seconds=1800),
    },
    'auto_send_message': {
        'task': 'tone.tasks.auto_send_message',
        'schedule': timedelta(seconds=30),
    },
    'auto_dashboard_benchmark_task': {
        'task': 'tone.tasks.auto_dashboard_benchmark_task',
        'schedule': timedelta(seconds=3600),
    },
    'auto_release_server_task': {
        'task': 'tone.tasks.auto_release_server_task',
        'schedule': timedelta(minutes=30),
    }
}
