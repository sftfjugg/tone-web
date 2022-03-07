import logging
import traceback

import requests

from tone import settings
from tone.core.common.job_result_helper import calc_job
from tone.models import TestJob, TestSuite


logger = logging.getLogger('callback')


class CallBackType(object):
    JOB_RUNNING = 'job_running'
    JOB_COMPLETED = 'job_completed'
    SERVER_BROKEN = 'server_broken'


class JobCallBack(object):

    def __init__(self,
                 job_id, server_id=None, message_obj=None,
                 callback_type=CallBackType.JOB_COMPLETED
                 ):
        self.job_id = job_id
        self.server_id = server_id
        self.message_obj = message_obj
        self.callback_type = callback_type
        self.api = ''
        self.method = 'post'
        self.data = dict()
        self.job_link = ''

    def callback(self):
        self._init_data()
        self._construct_data()
        try:
            success, res = self._callback()
        except Exception as e:
            logger.error(traceback.format_exc())
            success = False
            res = f'callback failed: {e}'
        log_info = f'api:{self.api} | method:{self.method} | ' \
                   f'callback_type:{self.callback_type} | ' \
                   f'data:{self.data} | result:{success},{res}'
        logger.info(f'--- callback request info ---')
        logger.info(log_info)
        return success, res

    def _init_data(self):
        self.job = TestJob.objects.filter(id=self.job_id).first()
        self.api = self.job.callback_api
        self.job_link = self._joint_job_link()
        self.data = self._construct_data()

    def _joint_job_link(self):
        return f'{settings.APP_DOMAIN}/ws/{self.job.ws_id}/test_result/{self.job_id}'

    def _construct_data(self):
        if self.callback_type == CallBackType.JOB_RUNNING:
            return self.__construct_data_when_job_start_running()
        elif self.callback_type == CallBackType.JOB_COMPLETED:
            return self.__construct_data_when_job_completed()
        elif self.callback_type == CallBackType.SERVER_BROKEN:
            return self.__construct_data_when_server_broken()
        return dict()

    def _callback(self):
        if self.method.lower() == 'post':
            res = requests.post(self.api, json=self.data)
        else:
            res = requests.get(self.api, params=self.data)
        return True, res.text
    
    def __construct_data_when_job_start_running(self):
        return {
            'callback_type': self.callback_type,
            'callback_desc': 'Job开始执行',
            'callback_data': {
                'job_id': self.job_id,
                'job_status': 'running',
                'ws_id': self.job.ws_id,
                'job_link': self.job_link,
            }
        }

    def __construct_data_when_job_completed(self):
        return {
            'callback_type': self.callback_type,
            'callback_desc': 'Job执行完毕',
            'callback_data': {
                'job_id': self.job_id,
                'job_status': 'completed',
                'ws_id': self.job.ws_id,
                'job_link': self.job_link,
                'test_type': self.job.test_type,
                'job_statics': calc_job(self.job_id)
            }
        }

    def __construct_data_when_server_broken(self):
        if not self.message_obj:
            blocked_suite = []
        else:
            blocked_suite = self.message_obj.impact_suite
        blocked_suite = list(TestSuite.objects.filter(
            id__in=blocked_suite).values_list('name', flat=True))
        return {
            'callback_type': self.callback_type,
            'callback_desc': '机器broken，请检查机器是否正常',
            'callback_data': {
                'job_id': self.job_id,
                'job_status': 'running',
                'ws_id': self.job.ws_id,
                'job_link': self.job_link,
                'broken_server_id': self.server_id,
                'broken_server_ip': self.message_obj.machine_ip,
                'broken_server_sn': self.message_obj.machine_sn,
                'blocked_suite': blocked_suite
            }
        }
