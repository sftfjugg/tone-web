# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from tone.core.utils.common_utils import kernel_info_format
from django.db.models import Q
from tone.models import TestJob, TestJobSuite, TestJobCase, JobTagRelation, JobTag, FuncResult
from tone.core.utils.helper import CommResp
from tone.core.common.expection_handler.error_catch import api_catch_error
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.job_result_helper import get_job_case_server, get_custom_server, get_server_object_id


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
    job_config['kernel_info'] = kernel_info_format(job_config['kernel_info'])
    suite_config = list()
    tag_config = [tag.tag_id for tag in JobTagRelation.objects.filter(job_id=job_id) if
                  JobTag.objects.filter(id=tag.tag_id, source_tag='custom_tag').exists()]
    if not data.get('notice', None):
        job_config['notice_info'] = list()
    is_all_case = True if not data.get('suite') or data.get('suite') == '1' else False
    if is_all_case:
        job_suites = TestJobSuite.objects.filter(job_id=job_id)
    else:
        job_suites = TestJobSuite.objects.filter(job_id=job_id, state='fail')
    for job_suite in job_suites:
        case_config = list()
        if is_all_case:
            job_cases = TestJobCase.objects.filter(job_id=job_id, test_suite_id=job_suite.test_suite_id)
        else:
            fail_case_id_list = FuncResult.objects.filter(test_job_id=job_id, sub_case_result=2,
                                                          match_baseline=0).values_list('test_case_id',
                                                                                        flat=True).distinct()
            all_case_id_list = FuncResult.objects.filter(test_job_id=job_id).values_list('test_case_id',
                                                                                         flat=True).distinct()
            q = Q()
            q &= Q(job_id=job_id)
            q &= Q(test_suite_id=job_suite.test_suite_id)
            q &= (Q(test_case_id__in=fail_case_id_list) | ~Q(test_case_id__in=all_case_id_list))
            job_cases = TestJobCase.objects.filter(q)
        for job_case in job_cases:
            ip = get_job_case_server(job_case.id, data=data)[0] if data.get('inheriting_machine') else \
                get_job_case_server(job_case.id, is_config=True)[0]
            is_instance = get_job_case_server(job_case.id, data=data)[1] if data.get('inheriting_machine') else \
                get_job_case_server(job_case.id, is_config=True)[1]
            server_is_deleted = get_job_case_server(job_case.id, data=data)[2] if data.get('inheriting_machine') else \
                get_job_case_server(job_case.id, is_config=True)[2]
            server_deleted = get_job_case_server(job_case.id, data=data)[3] if data.get('inheriting_machine') else \
                get_job_case_server(job_case.id, is_config=True)[3]
            case_config.append({
                'id': job_case.id,
                'test_case_id': job_case.test_case_id,
                'repeat': job_case.repeat,
                'customer_server': get_custom_server(job_case.id),
                'server_object_id': None if ip == '随机' else get_server_object_id(job_case),
                'server_tag_id': list() if not job_case.server_tag_id else [
                    int(tag_id) for tag_id in job_case.server_tag_id.split(',') if tag_id.isdigit()],
                'env_info': job_case.env_info,
                'need_reboot': job_case.need_reboot,
                'setup_info': job_case.setup_info,
                'cleanup_info': job_case.cleanup_info,
                'console': job_case.console,
                'monitor_info': job_case.monitor_info,
                'priority': job_case.priority,
                'ip': ip,
                'is_instance': is_instance,
                'server_is_deleted': server_is_deleted,
                'server_deleted': server_deleted
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
