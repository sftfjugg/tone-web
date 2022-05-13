# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import json

from tone.models import TestJob, TestJobCase, TestSuite, TestCase, PerfResult
from tone.core.utils.helper import CommResp
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.error_catch import api_catch_error
from tone.core.common.verify_token import token_required
from tone.core.common.job_result_helper import calc_job, get_job_case_server, get_job_case_run_server, calc_job_case


def _replace_statics_key(case_statics):
    if 'count' in case_statics:
        case_statics['total'] = case_statics.pop('count')
    if 'case_count' in case_statics:
        case_statics['total'] = case_statics.pop('case_count')
    if 'case_success' in case_statics:
        case_statics['success'] = case_statics.pop('case_success')
    if 'case_fail' in case_statics:
        case_statics['fail'] = case_statics.pop('case_fail')
    if 'case_skip' in case_statics:
        case_statics['skip'] = case_statics.pop('case_skip')
    return case_statics


@api_catch_error
@token_required
def job_query(request):
    """ api to query task
        example:
        curl -H 'Content-Type: application/json' -X POST -d '{"task_id": 215}' http://localhost:8000/api/task_query/
    """
    resp = CommResp()
    req_info = json.loads(request.body)
    job_id = req_info.get('job_id', None)
    assert job_id, ValueError(ErrorCode.JOB_NEED)
    job = TestJob.objects.get(id=job_id) if TestJob.objects.filter(id=job_id) else None
    assert job, ValueError(ErrorCode.TEST_JOB_NONEXISTENT)
    resp_data = {
        'job_id': job_id,
        'job_state': 'pending' if job.state == 'pending_q' else job.state,
        'test_type': job.test_type
    }
    statics = calc_job(job_id)
    statics['total'] = statics.pop('count')
    result_data = list()
    job_cases = TestJobCase.objects.filter(job_id=job_id)
    for job_case in job_cases:
        test_suite = TestSuite.objects.get(id=job_case.test_suite_id)
        test_case = TestCase.objects.get(id=job_case.test_case_id)
        ip, is_instance = get_job_case_server(job_case.id)
        case_state, case_statics = calc_job_case(job_case.id, is_api=True)
        case_statics = _replace_statics_key(case_statics)
        result_item = {
            'test_suite_id': test_suite.id,
            'test_suite': test_suite.name,
            'test_case_id': test_case.id,
            'test_case': test_case.name,
            'result_statistics': case_statics,
            'case_server': {
                'config_server': ip,
                'server_provider': job_case.server_provider,
                'is_instance': bool(is_instance),
                'run_server': get_job_case_run_server(job_case.id),
            }
        }
        if job.test_type == 'performance':
            metric_results = PerfResult.objects.filter(test_job_id=job.id, test_case_id=job_case.test_case_id)
            result_list = list()
            for metric_result in metric_results:
                result_list.append(
                    {
                        'metric': metric_result.metric,
                        'test_value': metric_result.test_value,
                        'cv_value': metric_result.cv_value,
                        'max_value': metric_result.max_value,
                        'min_value': metric_result.min_value,
                        'value_list': metric_result.value_list,
                        'baseline_value': metric_result.baseline_value,
                        'compare_result': metric_result.compare_result,
                        'track_result': metric_result.track_result
                    }
                )
            result_item['case_result'] = result_list
        result_data.append(result_item)
        # case_state
        if job_case.state in ['pending', 'running']:
            result_item['case_state'] = job_case.state
        elif job.test_type == 'performance':
            result_item['case_state'] = 'complete'
        else:
            result_item['case_state'] = case_state

    resp_data['result_statistics'] = statics
    resp_data['job_result'] = result_data
    resp.data = resp_data
    resp.result = True
    return resp.json_resp()
