import logging

from django.conf import settings
from django.db import transaction

from tone.celery import app
from tone.core.utils.schedule_lock import lock_run_task
from tone.services.notice.core.notice_service import send_message
from tone.services.portal.sync_portal_task_servers import sync_portal_task
from tone.services.sys.server_services import auto_release_server
from tone.services.sys.sync_suite_task_servers import sync_suite_tone_task, sync_suite_desc_tone_task
from tone.services.sys.dashboard_services import calculate_benchmark_data

logger = logging.getLogger('schedule')


@app.task
@lock_run_task(60 * 5, 'sync_suite_case_toneagent')
def sync_suite_case_toneagent():
    """
    通过 Toneagent 端查询，定时同步suite，以及suite下的case数据到 SuiteData 和 CaseData 表中
    :return:
    """
    return sync_suite_tone_task()


@app.task
@lock_run_task(60 * 5, 'sync_suite_case_description')
def sync_suite_case_description():
    """
    定时同步suite 描述到 SuiteData 和 CaseData 表中
    :return:
    """
    return sync_suite_desc_tone_task()


@app.task
@lock_run_task(60 * 30, 'sync_test_farm')
def sync_data_portal():
    """同步数据到portal"""
    return sync_portal_task()


@app.task
@lock_run_task(60 * 1, 'auto_send_message')
@transaction.atomic
def auto_send_message():
    if settings.MSG_SWITCH_ON:
        send_message()


@app.task
@lock_run_task(60 * 1, 'auto_dashboard_benchmark_task')
def auto_dashboard_benchmark_task():
    calculate_benchmark_data()


@app.task
@lock_run_task(60 * 1, 'auto_release_server_task')
def auto_release_server_task():
    auto_release_server()
