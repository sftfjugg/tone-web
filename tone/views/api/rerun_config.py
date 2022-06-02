# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from tone.models import TestJob, TestJobSuite, TestJobCase, JobTagRelation, JobTag
from tone.core.utils.helper import CommResp
from tone.core.common.expection_handler.error_catch import api_catch_error
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.job_result_helper import get_job_case_server, get_custom_server


@api_catch_error
def config_query(request):
    resp = CommResp()
    data = request.GET
    job_id = data.get('job_id', None)
    assert job_id, ValueError(ErrorCode.JOB_NEED)
    jobs = TestJob.objects.filter(id=job_id)
    if not jobs.exists():
        raise ValueError(ErrorCode.TEST_JOB_NONEXISTENT)
    else:
        job = jobs.first()
    job_config = job.to_dict()
    job_config['baseline'] = job_config.get('baseline_id')
    job_config['baseline_job_id'] = job_config.get('baseline_job_id')
    suite_config = list()
    tag_config = [tag.tag_id for tag in JobTagRelation.objects.filter(job_id=job_id) if
                  JobTag.objects.filter(id=tag.tag_id, source_tag='custom_tag').exists()]
    if not data.get('notice', None):
        job_config['notice_info'] = list()
    if data.get('suite', None):
        job_suites = TestJobSuite.objects.filter(job_id=job_id)
        for job_suite in job_suites:
            case_config = list()
            job_cases = TestJobCase.objects.filter(job_id=job_id, test_suite_id=job_suite.test_suite_id)
            for job_case in job_cases:
                case_config.append({
                    'id': job_case.id,
                    'test_case_id': job_case.test_case_id,
                    'repeat': job_case.repeat,
                    'customer_server': get_custom_server(job_case.id),
                    'server_object_id': job_case.server_object_id,
                    'server_tag_id': list() if not job_case.server_tag_id else [
                        int(tag_id) for tag_id in job_case.server_tag_id.split(',') if tag_id.isdigit()],
                    'env_info': job_case.env_info,
                    'need_reboot': job_case.need_reboot,
                    'setup_info': job_case.setup_info,
                    'cleanup_info': job_case.cleanup_info,
                    'console': job_case.console,
                    'monitor_info': job_case.monitor_info,
                    'priority': job_case.priority,
                    'ip': get_job_case_server(job_case.id, is_config=True)[0],
                    'is_instance': get_job_case_server(job_case.id, is_config=True)[1],
                })
            suite_config.append({
                'id': job_suite.id,
                'test_suite_id': job_suite.test_suite_id,
                'need_reboot': job_suite.need_reboot,
                'setup_info': job_suite.setup_info,
                'cleanup_info': job_suite.cleanup_info,
                'monitor_info': job_suite.monitor_info,
                'priority': job_suite.priority,
                'cases': case_config,
            })
    job_config['tags'] = tag_config
    job_config['test_config'] = suite_config
    resp.data = job_config
    return resp.json_resp()
