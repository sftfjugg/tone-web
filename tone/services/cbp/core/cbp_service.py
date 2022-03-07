import base64
import json
import logging
import time

import requests
from django.conf import settings

from tone.models import BuildJob, User
from tone.services.cbp.conf.constant import BuildKernelStatus

logger = logging.getLogger('schedule')


class CBPService(object):

    def cbp_task_run(self):
        pending_tasks = BuildJob.objects.filter(state=BuildKernelStatus.PENDING)
        for task in pending_tasks:
            self._run_task(task)

    def cbp_task_check(self):
        running_tasks = BuildJob.objects.filter(state=BuildKernelStatus.RUNNING)
        for task in running_tasks:
            self._check_task(task)

    def _run_task(self, task):
        result = self._send_request(task, 'create')
        logger.error('send cbp task...cbp_task_id:{}, result:{}'.format(task.id, result))
        if result['code'] != 200:
            logger.error('send cbp task failed.cbp_task_id:{}, result:{}'.format(task.id, result))
            task.status = BuildKernelStatus.FAIL
            task.msg = result['msg']
            task.save()
            return
        if result['data']['has_cache']:
            result_data = result['data']['caches'][0]
            self._update_task_status(task,
                                     cbp_id=result_data['id'],
                                     tid=result_data['event_id'],
                                     build_log=result_data['log'],
                                     build_msg=result_data['msg'],
                                     rpm_list=result['data']['rpm'])
        else:
            task.state = BuildKernelStatus.RUNNING
            task.cbp_id = result['data']['id']
            task.save()

    def _check_task(self, task):
        result = self._send_request(task, 'query')
        logger.error('query cbp task...cbp_task_id:{}, result:{}'.format(task.id, result))
        if result['code'] != 200:
            logger.error('query cbp task failed.cbp_task_id:{}; result:{}'.format(task.id, result))
            return
        if result['data']['status'] not in ['success', 'fail']:
            return
        success = False if result['data']['status'] == 'fail' else True
        result_data = result['data']
        self._update_task_status(task,
                                 cbp_id=result_data['id'],
                                 tid=result_data['event_id'],
                                 build_log=result_data['log'],
                                 build_msg=result_data['msg'],
                                 rpm_list=result_data.get('rpm_list'),
                                 success=success)

    @staticmethod
    def _send_request(task, action):
        cbp_task_api = '{}/api/?_to_link=service/cbp/task/'.format(settings.GOLDMINE_DOMAIN)
        username = User.objects.get(id=task.creator).username if task.creator else ''
        token = settings.CBP_API_TOKEN
        token_info = '{}|{}|{}'.format(
            username, token, time.time()
        )
        secret_token = base64.b64encode(token_info.encode('utf-8')).decode('utf-8')
        if action == 'create':
            data = {
                'name': task.name,
                'repo': task.git_repo,
                'branch': task.git_branch,
                'commit': task.git_commit,
                'arch': task.arch,
                'builder_branch': task.builder_branch,
                'build_config': task.build_config,
                'caller': 'T-one',
                'task_type': 'base',
                'token': secret_token
            }
            headers = {'Content-Type': 'application/json'}
            resp = requests.post(cbp_task_api, headers=headers, data=json.dumps(data), verify=False)
        else:
            params = {
                'token': secret_token,
                'id': task.cbp_id,
                'query_type': 'detail'
            }
            resp = requests.get(cbp_task_api, params=params, verify=False)
        return resp.json()

    @staticmethod
    def _update_task_status(build_task, success=True, **kwargs):
        logger.info('cbp service: _update_task_status: {}'.format(kwargs))
        build_task.state = BuildKernelStatus.SUCCESS if success else BuildKernelStatus.FAIL
        build_task.cbp_id = kwargs.get('cbp_id')
        build_task.tid = kwargs.get('tid')
        build_task.rpm_list = kwargs.get('rpm_list')
        build_task.build_log = kwargs.get('build_log')
        build_task.build_msg = kwargs.get('build_msg')
        build_task.save()
