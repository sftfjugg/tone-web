# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import json
from functools import reduce
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from queue import Queue
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import JobTestException

import requests
from django.db.models import Count, Case, When, Q
from django.db import connection
from tone.core.utils.common_utils import query_all_dict

from tone import settings
from tone.core.common.constant import FUNC_CASE_RESULT_TYPE_MAP
from tone.core.common.constant import PERFORMANCE, IP_PATTEN, BUSINESS
from tone.core.common.log_manager import get_logger
from tone.core.common.toneagent import tone_agent_info
from tone.core.utils.tone_thread import ToneThread
from tone.models import TestJobCase, TestJob, FuncResult, PerfResult, TestServerSnapshot, \
    CloudServerSnapshot, ServerTag, TestTmplCase, TestServer, PerfBaselineDetail, \
    CloudServer, TestMetric, FuncBaselineDetail, TestCluster, TestStep, BusinessResult, TestSuite, TestCase, \
    WorkspaceCaseRelation, BusinessSuiteRelation, TestBusiness, TestJobSuite

logger = get_logger('error')


def calc_job(job_id):
    """
    统计JobSuite结果
    """
    test_type = TestJob.objects.get(id=job_id).test_type
    if test_type == 'performance':
        count_dict, total = count_prefresult_state_num(job_id)
        na = total - count_dict.get('increase_count', 0) - count_dict.get('decline_count', 0) - count_dict.get(
            'normal_count', 0) - count_dict.get('invalid_count', 0)
        result = {'count': total, 'increase': count_dict.get('increase_count', 0), 'decline':
            count_dict.get('decline_count', 0), 'normal': count_dict.get('normal_count', 0), 'invalid':
                      count_dict.get('invalid_count', 0), 'na': na}
    elif test_type == BUSINESS:
        job_case_queryset = TestJobCase.objects.filter(job_id=job_id)
        count = len(job_case_queryset)
        fail = len(list(filter(lambda x: x.state == 'fail', job_case_queryset)))
        skip = len(list(filter(lambda x: x.state == 'skip', job_case_queryset)))
        success = len(list(filter(lambda x: x.state == 'success', job_case_queryset)))
        result = {'count': count, 'success': success, 'fail': fail, 'skip': skip}
    else:
        count_dict, total = count_funcresult_state_num(job_id)
        result = {'count': total, 'success': count_dict.get("1", 0),
                  'fail': count_dict.get("2", 0), 'skip': count_dict.get("5", 0), 'warn': count_dict.get("6", 0)}
    return result


def count_prefresult_state_num(job_id, test_suite_id=None, test_case_id=None):
    count_dict = {}
    search = """ and test_job_id={} """.format(job_id)
    if test_suite_id:
        search += """ and test_suite_id={} """.format(test_suite_id)
    if test_case_id:
        search += """ and test_case_id={} """.format(test_case_id)
    with connection.cursor() as cursor:
        search_sql = """
                SELECT track_result,COUNT(*)
                FROM perf_result  
                WHERE 
                id >=(SELECT id 
                    FROM perf_result 
                    WHERE 
                    is_deleted is False 
                    AND test_job_id={} 
                    ORDER BY `id` asc limit 0, 1) 
                and id<=(SELECT id 
                    FROM perf_result 
                    WHERE 
                    is_deleted is False AND test_job_id={} 
                    ORDER BY `id` desc limit 0, 1) 
                {} 
                and is_deleted is False 
                group by `track_result`
            """.format(job_id, job_id, search)
        cursor.execute(search_sql)
        count = cursor.fetchall()
        for i in count:
            count_dict[str(i[0])+'_count'] = i[1]
        total = sum(count_dict.values())
    return count_dict, total


def count_funcresult_state_num(job_id, test_suite_id=None, test_case_id=None):
    count_dict = {}
    search = """ and test_job_id={} """.format(job_id)
    if test_suite_id:
        search += """ and test_suite_id={} """.format(test_suite_id)
    if test_case_id:
        search += """ and test_case_id={} """.format(test_case_id)
    with connection.cursor() as cursor:
        search_sql = """
                SELECT sub_case_result,COUNT(*)
                FROM func_result  
                WHERE 
                id >=(SELECT id 
                    FROM func_result 
                    WHERE 
                    is_deleted is False 
                    AND test_job_id={} 
                    ORDER BY `id` asc limit 0, 1) 
                and id<=(SELECT id 
                    FROM func_result 
                    WHERE 
                    is_deleted is False AND test_job_id={} 
                    ORDER BY `id` desc limit 0, 1) 
                {} 
                and is_deleted is False 
                group by `sub_case_result`
            """.format(job_id, job_id, search)
        cursor.execute(search_sql)
        count = cursor.fetchall()
        for i in count:
            count_dict[str(i[0])] = i[1]
        total = count_dict.get("1", 0) + count_dict.get("2", 0) + count_dict.get("3", 0) + count_dict.get("4", 0) + \
                count_dict.get("5", 0) + count_dict.get("6", 0)
    return count_dict, total


def perse_func_result(job_id, sub_case_result, match_baseline):
    count_case_fail, count_total, count_fail, count_no_match_baseline = 0, 0, 0, 0
    id_sql = """
        id >= (
            SELECT
                id
            FROM
                func_result
            WHERE
               is_deleted is False
            AND test_job_id = {}
            ORDER BY
                id asc
            limit 0, 1
        )
        AND
        id <= (
            SELECT
                id
            FROM
                func_result
            WHERE
                is_deleted is False
                AND test_job_id = {}
            ORDER BY
                id desc
            limit 0, 1
        ) """.format(job_id, job_id)
    with connection.cursor() as cursor:
        search_sql = """
            SELECT COUNT(*) FROM test_job_case WHERE job_id={} AND state='fail'
            UNION ALL
            SELECT COUNT(*) FROM func_result WHERE test_job_id={} AND {}
            UNION ALL
            SELECT COUNT(*) FROM func_result  WHERE test_job_id={} AND sub_case_result={} AND {}
            UNION ALL
            SELECT COUNT(*) FROM func_result  WHERE test_job_id={} AND sub_case_result={} AND match_baseline={} AND {}
        """.format(job_id, job_id, id_sql, job_id, sub_case_result, id_sql, job_id, sub_case_result, match_baseline,
                   id_sql)
        cursor.execute(search_sql)
        result = cursor.fetchall()
        if result and len(result) == 4:
            count_case_fail, count_total, count_fail, count_no_match_baseline = result[0][0], result[1][0], result[2][
                0], result[3][0]
    return count_case_fail, count_total, count_fail, count_no_match_baseline


def calc_job_suite(job_id, test_suite_id, ws_id, test_type, test_result=None):
    """
    统计JobSuite结果及数据
    """
    count_data = dict()
    result = None
    if test_type == PERFORMANCE:
        count_dict, total = count_prefresult_state_num(job_id, test_suite_id)
        na = total - count_dict.get('increase_count', 0) - count_dict.get('decline_count', 0) - count_dict.get(
            'normal_count', 0) - count_dict.get('invalid_count', 0)
        count_data['count'] = total
        count_data['increase'] = count_dict.get('increase_count', 0)
        count_data['decline'] = count_dict.get('decline_count', 0)
        count_data['normal'] = count_dict.get('normal_count', 0)
        count_data['invalid'] = count_dict.get('invalid_count', 0)
        count_data['na'] = na
    elif test_type == BUSINESS:
        job_case_queryset = TestJobCase.objects.filter(job_id=job_id, test_suite_id=test_suite_id)
        conf_count = len(job_case_queryset)
        conf_fail = len(list(filter(lambda x: x.state == 'fail', job_case_queryset)))
        conf_skip = len(list(filter(lambda x: x.state == 'skip', job_case_queryset)))
        if conf_fail > 0:
            result = 'fail'
        elif conf_count > 0 and conf_fail == 0:
            result = 'success'
        else:
            result = '-'
        count_data['conf_count'] = conf_count
        count_data['conf_success'] = len(list(filter(lambda x: x.state == 'success', job_case_queryset)))
        count_data['conf_fail'] = conf_fail
        count_data['conf_skip'] = conf_skip
    else:
        func_result = test_result
        count_dict, total = count_funcresult_state_num(job_id, test_suite_id)
        count_data = {'conf_count': total, 'conf_success': count_dict.get("1", 0),
                      'conf_fail': count_dict.get("2", 0), 'conf_skip': count_dict.get("5", 0),
                      'conf_warn': count_dict.get("6", 0)}
        baseline_id = TestJob.objects.get_value(id=job_id).baseline_id
        conf_fail = func_result.filter(sub_case_result=2, match_baseline=False).count()
        if conf_fail > 0:
            result = 'fail'
        else:
            impact_baseline = calc_impact_baseline(func_result, baseline_id, ws_id, job_id)
            if impact_baseline > 0:
                result = 'fail'
            elif total > 0:
                result = 'success'
                count_case = TestJobCase.objects.filter(job_id=job_id,
                                                        test_suite_id=test_suite_id).count()
                if count_case > total:
                    # 如果conf在FuncResult表中没有测试结果，则该suite状态也是fail
                    result = 'fail'
            else:
                result = '-'
    return result, count_data


def calc_job_case(job_case, suite_result, test_type, is_api=False):
    """
    统计JobCase结果及数据
    """
    count_data = dict()
    result = None
    if test_type == PERFORMANCE:
        count_dict, total = count_prefresult_state_num(job_case.job_id, job_case.test_suite_id, job_case.test_case_id)
        na = total - count_dict.get('increase_count', 0) - count_dict.get('decline_count', 0) - count_dict.get(
            'normal_count', 0) - count_dict.get('invalid_count', 0)
        count_data['count'] = total
        count_data['increase'] = count_dict.get('increase_count', 0)
        count_data['decline'] = count_dict.get('decline_count', 0)
        count_data['normal'] = count_dict.get('normal_count', 0)
        count_data['invalid'] = count_dict.get('invalid_count', 0)
        count_data['na'] = na
    elif test_type == BUSINESS:
        if job_case.state not in ['fail', 'success']:
            result = 'fail' if is_api else '-'
        else:
            result = job_case.state
        business_result_queryset = BusinessResult.objects.filter(
            test_job_id=job_case.job_id, test_suite_id=job_case.test_suite_id, test_case_id=job_case.test_case_id)
        if business_result_queryset.exists():
            business_result = business_result_queryset.first()
            count_data['link'] = business_result.link
            count_data['ci_system'] = business_result.ci_system
            count_data['ci_result'] = business_result.ci_result
            count_data['ci_detail'] = business_result.ci_detail
    else:
        count_dict, total = count_funcresult_state_num(job_case.job_id, job_case.test_suite_id, job_case.test_case_id)
        count_data = {'case_count': total, 'case_success': count_dict.get("1", 0),
                      'case_fail': count_dict.get("2", 0), 'case_skip': count_dict.get("5", 0),
                      'case_warn': count_dict.get("6", 0)}
        baseline_id = TestJob.objects.get_value(id=job_case.job_id).baseline_id
        ws_id = TestJob.objects.get(id=job_case.job_id).ws_id
        func_result = suite_result.filter(test_case_id=job_case.test_case_id)
        case_fail = func_result.filter(sub_case_result='2', match_baseline=False).count()
        if case_fail > 0:
            result = 'fail'
        else:
            impact_baseline = calc_impact_baseline(func_result, baseline_id, ws_id, job_case.job_id)
            if impact_baseline > 0:
                result = 'fail'
            elif total > 0:
                result = 'success'
            else:
                result = 'fail' if is_api else '-'
    return result, count_data


def get_job_case_server(job_case_id, template=None, is_config=False, data=None):
    job_case = TestJobCase.objects.get(id=job_case_id) if not template else TestTmplCase.objects.get(id=job_case_id)
    run_mode = job_case.run_mode
    server_provider = job_case.server_provider
    obj = ServerData()
    if job_case.server_object_id and run_mode == 'standalone' and server_provider == 'aligroup':
        _get_server_for_aligroup_standalone(job_case, obj)
    elif job_case.server_object_id and run_mode == 'standalone' and server_provider == 'aliyun':
        _get_server_for_aliyun_standalone(job_case, obj)
    elif job_case.server_object_id and run_mode == 'cluster':
        _get_server_for_cluster(job_case, obj)
    else:
        if data and data.get('inheriting_machine'):
            _get_server_inheriting_machine(is_config, job_case_id, obj, run_mode)
        else:
            _get_server_no_inheriting_machine(is_config, job_case, obj, server_provider, run_mode)
    return obj.server, obj.is_instance, obj.server_is_deleted, obj.server_deleted


def _get_server_no_inheriting_machine(is_config, job_case, obj, server_provider, run_mode):
    if job_case.server_tag_id:
        obj.is_instance = None
        server_tag_id_list = str(job_case.server_tag_id).split(',')
        obj.server = ','.join(ServerTag.objects.filter(id__in=server_tag_id_list).values_list('name', flat=True)) \
            if ServerTag.objects.filter(id__in=server_tag_id_list).exists() else None
    elif run_mode == 'standalone' and job_case.server_snapshot_id and server_provider == 'aligroup' and \
            not TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).in_pool:
        obj.server = TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).ip if \
            TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).ip else \
            TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).sn
    elif not is_config and run_mode == 'standalone' and job_case.server_snapshot_id and server_provider == 'aliyun' \
            and CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id).exists():
        cloud_server = CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id)
        obj.server = _get_server_for_aliyun_not_config(cloud_server)
    else:
        obj.is_instance = None
        obj.server = '随机'


def _get_server_inheriting_machine(is_config, job_case_id, obj, run_mode):
    job_case = TestJobCase.objects.get(id=job_case_id)
    server_provider = job_case.server_provider
    if job_case.server_tag_id:
        _get_tag_server(job_case, obj)
    elif run_mode == 'standalone' and job_case.server_snapshot_id and server_provider == 'aligroup' and \
            TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).in_pool:
        test_server = TestServerSnapshot.objects.filter(id=job_case.server_snapshot_id).first()
        obj.server = test_server.ip if test_server else None
        _get_server_is_deleted(server_provider, test_server, obj)
    elif not is_config and run_mode == 'standalone' and job_case.server_snapshot_id and server_provider == 'aliyun' \
            and CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id).exists():
        cloud_server = CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id).first()
        obj.server = _get_server_for_aliyun_not_config(cloud_server)
        obj.is_instance = 1 if cloud_server.is_instance else 0
        _get_server_is_deleted(server_provider, cloud_server, obj)


def _get_server_for_aliyun_not_config(cloud_server):
    server = cloud_server.private_ip if cloud_server.private_ip else cloud_server.sn
    return server


def _get_server_for_cluster(job_case, obj):
    test_cluster = TestCluster.objects.filter(id=job_case.server_object_id)
    if test_cluster:
        obj.server = test_cluster.first().name
    else:
        server_list = TestCluster.objects.filter(id=job_case.server_object_id, query_scope='deleted')
        obj.server_is_deleted = True
        obj.server_deleted = [{'test_cluster': server_list.first().name}]


def _get_server_for_aliyun_standalone(job_case, obj):
    server_obj = CloudServer.objects.filter(id=job_case.server_object_id).first()
    if server_obj:
        obj.is_instance = 1 if server_obj.is_instance else 0
        obj.server = (server_obj.private_ip if obj.is_instance else server_obj.template_name) if \
            (server_obj.private_ip if obj.is_instance else server_obj.template_name) else server_obj.sn
    else:
        server_obj = CloudServer.objects.filter(id=job_case.server_object_id, query_scope='deleted').first()
        if server_obj and server_obj.is_instance:
            obj.server_is_deleted = True
            obj.server_deleted = [{'ip': server_obj.private_ip,
                                   'sn': server_obj.sn}]


def _get_server_for_aligroup_standalone(job_case, obj):
    test_server = TestServer.objects.filter(id=job_case.server_object_id).first()
    if not test_server:
        server_list = list(TestServer.objects.filter(id=job_case.server_object_id,
                                                     query_scope='deleted').values_list('ip', 'sn'))
        obj.server_is_deleted = True
        obj.server_deleted = [{'ip': '', 'sn': ''}]
        if server_list:
            obj.server_deleted = [{'ip': server_list[0][0], 'sn': server_list[0][1]}]
    else:
        obj.server = test_server.ip if test_server.ip else test_server.sn


def _get_tag_server(job_case, obj):
    server_provider = job_case.server_provider
    obj.is_instance = None
    if job_case.run_mode == 'cluster':
        server_tag_id_list = str(job_case.server_tag_id).split(',')
        server_tag_list = ServerTag.objects.filter(id__in=server_tag_id_list)
        if server_tag_list.exists() and len(server_tag_id_list) == len(server_tag_list):
            obj.server = ','.join(server_tag_list.values_list('name', flat=True))
        else:
            tag_list = ServerTag.objects.filter(id__in=server_tag_id_list, query_scope='deleted').values_list('name',
                                                                                                              flat=True)
            if tag_list:
                obj.server_deleted = [{'tag': ','.join(tag_list)}]
                obj.server = None
                obj.server_is_deleted = True
    else:
        if server_provider == 'aliyun' and not job_case.server_object_id and job_case.server_snapshot_id:
            cloud_server = CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id).first()
            obj.server = cloud_server.private_ip if cloud_server.private_ip else \
                TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).sn
            _get_server_is_deleted(server_provider, cloud_server, obj)
        if server_provider == 'aligroup' and not job_case.server_object_id and job_case.server_snapshot_id:
            test_server = TestServerSnapshot.objects.filter(id=job_case.server_snapshot_id).first()
            obj.server = test_server.ip if test_server else None
            _get_server_is_deleted(server_provider, test_server, obj)


def _get_server_is_deleted(server_provider, server_snapshot_object, obj):
    if server_snapshot_object and server_snapshot_object.source_server_id:
        if server_provider == 'aligroup':
            server_obj = TestServer.objects.filter(id=server_snapshot_object.source_server_id,
                                                   query_scope='deleted').first()
            if server_obj:
                obj.server_is_deleted = True
                obj.server_deleted = [{'ip': server_obj.ip,
                                       'sn': server_obj.sn}]
        if server_provider == 'aliyun':
            server_obj = CloudServer.objects.filter(id=server_snapshot_object.source_server_id,
                                                    query_scope='deleted').first()
            if server_obj:
                obj.server_is_deleted = True
                if server_obj.is_instance:
                    obj.server_deleted = [{'ip': server_obj.private_ip,
                                           'sn': server_obj.sn}]


def get_job_case_run_server(job_case_id, return_field='ip'):
    job_case = TestJobCase.objects.get(id=job_case_id)
    run_mode = job_case.run_mode
    server_provider = job_case.server_provider
    server = None
    if run_mode == 'standalone' and server_provider == 'aligroup':
        server = TestServerSnapshot.objects.filter(id=job_case.server_snapshot_id)
        if server.exists():
            return __get_server_value(server, server_provider, return_field)
    elif run_mode == 'standalone' and server_provider == 'aliyun':
        server = CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id)
        if server.exists():
            return __get_server_value(server, server_provider, return_field)
    elif run_mode == 'cluster' and server_provider == 'aligroup':
        test_step = TestStep.objects.filter(job_case_id=job_case_id, stage='run_case')
        if test_step.exists():
            server_snapshot_id = TestStep.objects.filter(job_case_id=job_case_id, stage='run_case').first().server
            server = TestServerSnapshot.objects.filter(id=server_snapshot_id)
            if server.exists():
                return __get_server_value(server, server_provider, return_field)
    elif run_mode == 'cluster' and server_provider == 'aliyun':
        test_step = TestStep.objects.filter(job_case_id=job_case_id, stage='run_case')
        if test_step.exists():
            server_snapshot_id = TestStep.objects.filter(job_case_id=job_case_id, stage='run_case').first().server
            server = CloudServerSnapshot.objects.filter(id=server_snapshot_id)
            if server.exists():
                return __get_server_value(server, server_provider, return_field)
    if not server:
        server = None
    return server


def get_test_config(test_job_id, detail_server=False):
    test_config = list()
    job_suites = TestJobSuite.objects.filter(job_id=test_job_id)
    job_cases = TestJobCase.objects.filter(job_id=test_job_id)
    for job_suite in job_suites:
        test_suite_name = TestSuite.objects.get_value(
                id=job_suite.test_suite_id) and TestSuite.objects.get_value(id=job_suite.test_suite_id).name
        obj_dict = {
            'test_suite_id': job_suite.test_suite_id,
            'test_suite_name': test_suite_name,
            'test_suite': test_suite_name,
            'need_reboot': job_suite.need_reboot,
            'setup_info': job_suite.setup_info,
            'cleanup_info': job_suite.cleanup_info,
            'monitor_info': list(job_suite.monitor_info),
            'priority': job_suite.priority,
            'run_mode': TestSuite.objects.get_value(id=job_suite.test_suite_id) and TestSuite.objects.get_value(
                id=job_suite.test_suite_id).run_mode,
        }
        if WorkspaceCaseRelation.objects.filter(test_type='business',
                                                test_suite_id=job_suite.test_suite_id,
                                                query_scope='all').exists():
            business_relation = BusinessSuiteRelation.objects.filter(test_suite_id=test_job_id,
                                                                     query_scope='all').first()
            if business_relation:
                test_business = TestBusiness.objects.filter(id=business_relation.business_id,
                                                            query_scope='all').first()
                if test_business:
                    obj_dict.update({'business_name': test_business.name})
        cases = list()
        for case in job_cases.filter(test_suite_id=job_suite.test_suite_id):
            ip = get_job_case_server(case.id, is_config=True)[0]
            is_instance = get_job_case_server(case.id, is_config=True)[1]
            test_case_name = TestCase.objects.get_value(id=case.test_case_id) and TestCase.objects.get_value(
                    id=case.test_case_id).name
            server_info = get_job_case_run_server(case.id, return_field='obj')
            server = ({
                'ip': ip
            })
            if detail_server and server_info:
                if type(server_info) is CloudServerSnapshot:
                    server = ({
                        'instance': server_info.instance_id
                    })
                else:
                    server['ip'] = server_info.ip
                server['distro'] = server_info.distro
                server['kernel_version'] = server_info.kernel_version
                server['glibc'] = server_info.glibc
                server['gcc'] = server_info.gcc
                server['memory_info'] = server_info.memory_info
                server['disk'] = server_info.disk
                server['cpu_info'] = server_info.cpu_info
                server['ether'] = server_info.ether
            cases.append({
                'test_case_id': case.test_case_id,
                'test_case_name': test_case_name,
                'test_case': test_case_name,
                'setup_info': case.setup_info,
                'cleanup_info': case.cleanup_info,
                'server_ip': ip,
                'server_id': server_info.id if server_info else None,
                'server_description': get_job_case_run_server(case.id, return_field='description'),
                'is_instance': is_instance,
                'need_reboot': case.need_reboot,
                'console': case.console,
                'monitor_info': list(case.monitor_info),
                'priority': case.priority,
                'env_info': dict(case.env_info),
                'repeat': case.repeat,
                'run_mode': case.run_mode,
                'server': server
            })
        obj_dict['cases'] = cases
        test_config.append(obj_dict)
    return test_config


def __get_server_value(server, server_provider, return_field):
    if return_field == 'ip':
        if server_provider == 'aligroup':
            return server.first().ip
        elif server_provider == 'aliyun':
            return server.first().private_ip
    elif return_field == 'id':
        return server.first().id
    elif return_field == 'description':
        return server.first().description


def get_server_ip_sn(server, channel_type):
    ip = server if IP_PATTEN.match(server) else None
    sn = None if IP_PATTEN.match(server) else server
    if ip and channel_type == 'otheragent':
        pass
    elif ip and channel_type == 'toneagent':
        agent_url = tone_agent_info(ip=server)
        res = json.loads(requests.get(url=agent_url, verify=False).text)
        if res['SUCCESS']:
            sn = res.get('RESULT').get('TSN')
        else:
            raise JobTestException(ErrorCode.TONE_AGENT_ERROR)
    elif sn and channel_type == 'otheragent':
        pass
    else:
        agent_url = tone_agent_info(tsn=server)
        res = json.loads(requests.get(url=agent_url, verify=False).text)
        if res['SUCCESS']:
            ip = res.get('RESULT').get('IP')
        else:
            raise JobTestException(ErrorCode.TONE_AGENT_ERROR)
    return ip, sn


def get_custom_server(job_case_id, template=None):
    job_case = TestJobCase.objects.get(id=job_case_id) if not template else TestTmplCase.objects.get(id=job_case_id)
    server_provider = job_case.server_provider
    if job_case.run_mode == 'cluster' or job_case.server_object_id or job_case.server_tag_id:
        return None
    if server_provider == 'aligroup' and job_case.server_snapshot_id and not TestServerSnapshot.objects.get(
            id=job_case.server_snapshot_id).in_pool:
        server_obj = TestServerSnapshot.objects.get(id=job_case.server_snapshot_id)
        server = {
            'custom_ip': server_obj.ip,
            'custom_sn': server_obj.sn if server_obj.channel_type == 'otheragent' else server_obj.tsn,
            'custom_channel': server_obj.channel_type,
        }
    else:
        server = None
    return server


def get_server_object_id(job_case):
    id = None
    if job_case.server_object_id:
        id = job_case.server_object_id
    else:
        if job_case.run_mode == 'cluster':
            id = None
        else:
            if job_case.server_snapshot_id:
                if job_case.server_provider == 'aligroup':
                    test_server = TestServerSnapshot.objects.filter(id=job_case.server_snapshot_id).first()
                else:
                    test_server = CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id).first()
                if test_server and test_server.source_server_id:
                    id = test_server.source_server_id
    return id


def date_add(date, day):
    _date = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=day)
    return datetime.strftime(_date, "%Y-%m-%d")


def get_suite_conf_metric(suite_id, suite_value):
    conf_list = list()
    suite_obj = {
        'suite_name': suite_value.get('suite_name'),
        'suite_id': suite_id,
        'compare_count': list(),
    }
    compare_job_li = []
    thread_tasks = []
    for conf_id, conf_value in suite_value.get('conf_dic').items():
        thread_tasks.append(
            ToneThread(_get_suite_conf_metric, (suite_id, conf_id, conf_value, compare_job_li, suite_obj))
        )
        thread_tasks[-1].start()
    for thread_task in thread_tasks:
        thread_task.join()
        conf_obj = thread_task.get_result()
        if conf_obj:
            conf_list.append(conf_obj)
    suite_obj['conf_list'] = conf_list
    return suite_obj


def _get_suite_conf_metric(suite_id, conf_id, conf_value, compare_job_li, suite_obj):
    obj_id = conf_value.get('obj_id')
    is_job = conf_value.get('is_job')
    if is_job:
        perf_results = PerfResult.objects.filter(test_job_id=obj_id, test_suite_id=suite_id, test_case_id=conf_id)
    else:
        return
    if not perf_results.exists():
        return
    for i in conf_value.get('compare_objs'):
        if i:
            compare_job = i.get('obj_id')
        else:
            compare_job = None
        if compare_job not in compare_job_li:
            compare_job_li.append(compare_job)
    if not suite_obj.get('compare_count'):
        suite_obj['compare_count'] = [{'all': 0, 'increase': 0, 'decline': 0} for _ in
                                      range(len(conf_value.get('compare_objs')))]
    metric_list = get_metric_list(perf_results, suite_id, conf_id, compare_job_li, suite_obj['compare_count'])
    has_data = False
    for metric_obj in metric_list:
        if metric_obj:
            has_data = True
            break
    if has_data:
        conf_obj = {
            'conf_name': conf_value.get('conf_name'),
            'conf_id': conf_id,
            'is_job': conf_value.get('is_job'),
            'obj_id': conf_value.get('obj_id'),
            'conf_compare_data': conf_value.get('compare_objs'),
            'metric_list': metric_list,
        }
    else:
        conf_obj = {}
    if not conf_obj['metric_list']:
        return
    return conf_obj


def get_metric_list(perf_results, suite, conf, compare_job_li, compare_count):
    metric_list = list()
    for perf_result in perf_results:
        metric = perf_result.metric
        unit = perf_result.unit
        if TestMetric.objects.filter(name=perf_result.metric, object_type='case', object_id=conf).exists():
            test_metric = TestMetric.objects.get(name=perf_result.metric, object_type='case', object_id=conf)
        elif TestMetric.objects.filter(name=perf_result.metric, object_type='suite', object_id=suite).exists():
            test_metric = TestMetric.objects.get(name=perf_result.metric, object_type='suite', object_id=suite)
        else:
            continue
        test_value = round(float(perf_result.test_value), 2)
        cv_value = perf_result.cv_value
        for compare_job in compare_job_li:
            if compare_job:
                metric_list.append(
                    {
                        'metric': metric,
                        'test_value': test_value,
                        'cv_value': cv_value.split('±')[-1] if cv_value else None,
                        'unit': unit,
                        'direction': test_metric.direction,
                        'cv_threshold': test_metric.cv_threshold,
                        'cmp_threshold': test_metric.cmp_threshold,
                        'max_value': perf_result.max_value,
                        'min_value': perf_result.min_value,
                        'value_list': perf_result.value_list,
                        'compare_data': get_compare_data(suite, conf, metric, test_value, test_metric.direction,
                                                         compare_job_li, test_metric.cmp_threshold,
                                                         test_metric.cv_threshold, compare_count),
                    }
                )
            else:
                metric_list.append(None)
    return metric_list


def get_compare_data(suite, conf, metric, test_value, direction, compare_job_li, cmp_threshold, cv_threshold,
                     compare_count):
    compare_data = list()
    for compare_job_index in range(len(compare_job_li)):
        group_data = dict()
        if compare_job_li[compare_job_index]:
            _count = compare_count[compare_job_index]
            perf_results = PerfResult.objects.filter(test_job_id=compare_job_li[compare_job_index], test_suite_id=suite,
                                                     test_case_id=conf, metric=metric)
            if perf_results.exists():
                perf_result = perf_results.first()
                value = round(float(perf_result.test_value), 2)
                group_data['test_value'] = value
                group_data['cv_value'] = perf_result.cv_value.split('±')[-1]
                group_data['max_value'] = perf_result.max_value
                group_data['min_value'] = perf_result.min_value
                group_data['compare_value'], group_data['compare_result'] = \
                    get_compare_result(test_value, value, direction, cmp_threshold, group_data['cv_value'],
                                       cv_threshold)
                group_data['value_list'] = perf_result.value_list
                _count['all'] += 1
                if group_data['compare_result'] == 'increase':
                    _count['increase'] += 1
                if group_data['compare_result'] == 'decline':
                    _count['decline'] += 1
            compare_data.append(group_data)
    return compare_data


def get_compare_result(base_test_value, compare_test_value, direction, cmp_threshold, cv_value, cv_threshold):
    try:
        if base_test_value == '0':
            return 'na', 'na'
        change_rate = (compare_test_value - base_test_value) / float(base_test_value)
        if float(cv_value.split('%')[0]) > cv_threshold * 100:
            res = 'invalid'
        else:
            if change_rate > cmp_threshold:
                res = 'increase' if direction == 'increase' else 'decline'
            elif change_rate < -cmp_threshold:
                res = 'decline' if direction == 'increase' else 'increase'
            else:
                res = 'normal'
        _change_rate = '%.2f%%' % (change_rate * 100)
    except Exception as err:
        logger.error(f"err: {err}")
        res = _change_rate = 'na'
    return _change_rate, res


def get_suite_conf_sub_case(suite_id, suite_value):
    suite_obj = {
        'suite_name': suite_value.get('suite_name'),
        'suite_id': suite_id,
        'base_count': {
            'all_case': 0,
            'success_case': 0,
            'fail_case': 0,
            'warn_case': 0,
        },
        'compare_count': list(),
    }
    conf_list = list()
    for conf_id, conf_value in suite_value.get('conf_dic').items():
        is_job = conf_value.get('is_job')
        obj_id = conf_value.get('obj_id')
        if is_job:
            func_results = FuncResult.objects.filter(test_job_id=obj_id, test_suite_id=suite_id, test_case_id=conf_id)
        else:
            continue  # todo 基线后续处理
        compare_job_li = list([0 if not i else i.get('obj_id') for i in conf_value.get('compare_objs')])
        compare_job_li.sort(key=[0 if not i else i.get('obj_id') for i in conf_value.get('compare_objs')].index)
        conf_obj = {
            'conf_name': conf_value.get('conf_name'),
            'conf_id': conf_id,
            'all_case': func_results.count(),
            'is_job': conf_value.get('is_job'),
            'obj_id': conf_value.get('obj_id'),
            'success_case': func_results.filter(sub_case_result=1).count(),
            'fail_case': func_results.filter(sub_case_result=2).count(),
            'warn_case': func_results.filter(sub_case_result=6).count(),
            'conf_compare_data': get_conf_compare_data(conf_value.get('compare_objs'), suite_id, conf_id,
                                                       suite_obj['compare_count']),
            'sub_case_list': get_sub_case_list(func_results[:200], suite_id, conf_id, compare_job_li),
            # todo 后期可对接口进行拆分做分页处理
            # 'sub_case_list': asyncio.run(get_sub_case_list(func_results, suite_id, conf_id, compare_job_li)),
        }
        suite_obj['base_count']['all_case'] += conf_obj['all_case']
        suite_obj['base_count']['success_case'] += conf_obj['success_case']
        suite_obj['base_count']['fail_case'] += conf_obj['fail_case']
        suite_obj['base_count']['warn_case'] += conf_obj['warn_case']
        conf_list.append(conf_obj)
    suite_obj['conf_list'] = conf_list
    return suite_obj


def get_sub_case_list(func_results, suite, conf, compare_job_li):
    sub_case_list = list()
    q = Queue()
    with ThreadPoolExecutor(max_workers=8) as t:
        for func_result in func_results:
            t.submit(concurrent_calc, func_result, suite, conf, compare_job_li, q)
    while not q.empty():
        sub_case_list.append(q.get())
    return sub_case_list


def concurrent_calc(func_result, suite, conf, compare_job_li, q):
    sub_case_name = func_result.sub_case_name
    result = FUNC_CASE_RESULT_TYPE_MAP.get(func_result.sub_case_result)
    q.put(
        {
            'sub_case_name': sub_case_name,
            'result': result,
            'compare_data': get_func_compare_data(suite, conf, sub_case_name, compare_job_li),
        }
    )


def get_func_compare_data(suite, conf, sub_case_name, compare_job_li):
    compare_data = list()
    for compare_job in compare_job_li:
        group_data = None
        if compare_job.get('is_baseline', 0):
            func_results = FuncBaselineDetail.objects.filter(baseline_id=compare_job.get('job_id'), test_suite_id=suite,
                                                             test_case_id=conf,
                                                             sub_case_name=sub_case_name)
        else:
            func_results = FuncResult.objects.filter(test_job_id=compare_job.get('job_id'), test_suite_id=suite,
                                                     test_case_id=conf,
                                                     sub_case_name=sub_case_name)
        if func_results.exists():
            func_result = func_results.first()
            if compare_job.get('is_baseline', 0):
                group_data = FUNC_CASE_RESULT_TYPE_MAP.get(2)
            else:
                group_data = FUNC_CASE_RESULT_TYPE_MAP.get(func_result.sub_case_result)
        compare_data.append(group_data)
    return compare_data


def calc_impact_baseline(result, baseline_id, ws_id, job_id):
    count = 0
    match_results = result.filter(sub_case_result='2', match_baseline=True)
    for match_result in match_results:
        if not (FuncBaselineDetail.objects.filter(baseline_id=baseline_id,
                                                  test_suite_id=match_result.test_suite_id,
                                                  test_case_id=match_result.test_case_id,
                                                  sub_case_name=match_result.sub_case_name, impact_result=1).exists() or
                FuncBaselineDetail.objects.filter(source_job_id=job_id,
                                                  test_suite_id=match_result.test_suite_id,
                                                  test_case_id=match_result.test_case_id,
                                                  sub_case_name=match_result.sub_case_name, impact_result=1).exists()):
            count += 1
    return count


def get_conf_compare_data(compare_objs, suite_id, conf_id, compare_count):
    compare_data = list()
    for idx, compare_obj in enumerate(compare_objs):
        _compare_count = {
            'all_case': 0,
            'success_case': 0,
            'fail_case': 0,
            'warn_case': 0,
        }
        group_data = compare_obj
        if not compare_obj:
            compare_data.append(group_data)
            compare_count.append(_compare_count)
            continue
        obj_id = compare_obj.get('obj_id')
        is_job = compare_obj.get('is_job')
        if is_job:
            func_results = FuncResult.objects.filter(test_job_id=obj_id, test_suite_id=suite_id, test_case_id=conf_id)
        else:
            return group_data
        if len(compare_count) < len(compare_objs):
            compare_count.append(_compare_count)
        compare_count[idx]['all_case'] += func_results.count()
        compare_count[idx]['success_case'] += func_results.filter(sub_case_result=1).count()
        compare_count[idx]['fail_case'] += func_results.filter(sub_case_result=2).count()
        compare_count[idx]['warn_case'] += func_results.filter(sub_case_result=6).count()
        group_data['all_case'] = func_results.count()
        group_data['success_case'] = func_results.filter(sub_case_result=1).count()
        group_data['fail_case'] = func_results.filter(sub_case_result=2).count()
        group_data['warn_case'] = func_results.filter(sub_case_result=6).count()
        compare_data.append(group_data)
    return compare_data


def splice_job_link(job):
    return f'{settings.APP_DOMAIN}/ws/{job.ws_id}/test_result/{job.id}'


def get_suite_conf_metric_v1(suite_id, suite_name, base_index, group_list, suite_value, is_all):
    conf_list = list()
    suite_obj = {
        'suite_name': suite_name,
        'suite_id': suite_id,
        'compare_count': list(),
        'base_count': list()
    }
    baseline_id_list = list()
    job_id_list = list()
    for group in group_list:
        if group.get('is_baseline'):
            baseline_id_list.extend(group.get('job_list'))
        else:
            job_id_list.extend(group.get('job_list'))
    case_id_list = list()
    if suite_value:
        for case_info in suite_value:
            case_id_list.append(case_info['conf_id'])
    case_id_sql = '' if is_all else ' AND a.test_case_id IN (' + ','.join(str(e) for e in case_id_list) + ')'
    baseline_result_list = None
    job_result_list = None
    if baseline_id_list:
        baseline_id_str = ','.join(str(e) for e in baseline_id_list)
        raw_sql = 'SELECT DISTINCT a.baseline_id as test_job_id,a.test_case_id,c.name as test_case_name,' \
                  'a.test_value,a.cv_value,a.max_value,a.value_list,a.metric,b.object_type,b.id,' \
                  'b.cv_threshold,b.cmp_threshold,b.direction,b.unit FROM perf_baseline_detail a LEFT JOIN ' \
                  'test_track_metric b ON a.metric = b.name AND ((b.object_type = "case" AND ' \
                  'b.object_id = a.test_case_id) or (b.object_type = "suite" AND ' \
                  'b.object_id = a.test_suite_id )) LEFT JOIN test_case c ON a.test_case_id=c.id WHERE ' \
                  'a.baseline_id IN (' + baseline_id_str + ') AND a.test_suite_id=' + str(suite_id) + case_id_sql + \
                  ' AND b.cv_threshold > 0 ORDER BY b.object_type,b.id desc'
        baseline_result_list = query_all_dict(raw_sql.replace('\'', ''), params=None)
    if job_id_list:
        job_id_str = ','.join(str(e) for e in job_id_list)
        raw_sql = 'SELECT DISTINCT a.test_job_id,a.test_case_id,c.name as test_case_name,a.test_value,' \
                  'a.cv_value,a.max_value,b.object_type,b.id,' \
                  'a.value_list,a.metric,b.cv_threshold,b.cmp_threshold,b.direction,b.unit FROM perf_result a ' \
                  'LEFT JOIN test_track_metric b ON a.metric = b.name AND ((b.object_type = "case" AND ' \
                  'b.object_id = a.test_case_id) or (b.object_type = "suite" AND ' \
                  'b.object_id = a.test_suite_id )) LEFT JOIN test_case c ON a.test_case_id=c.id' \
                  ' WHERE a.test_job_id IN (' + job_id_str + \
                  ') AND a.test_suite_id=' + str(suite_id) + case_id_sql + \
                  ' AND b.cv_threshold > 0 ORDER BY b.object_type,b.id desc'
        job_result_list = query_all_dict(raw_sql.replace('\'', ''), params=None)
    base_job_list = group_list.pop(base_index)
    base_is_baseline = base_job_list.get('is_baseline', 0)
    duplicate_conf = base_job_list.get('duplicate_conf')
    if is_all:
        if base_is_baseline:
            case_list = remove_duplicate_case(baseline_result_list, base_job_list.get('job_list'))
        else:
            case_list = remove_duplicate_case(job_result_list, base_job_list.get('job_list'))
    else:
        case_list = suite_value
    thread_tasks = []
    for case_info in case_list:
        if base_is_baseline:
            case_result_list = [result for result in baseline_result_list if result['test_case_id'] ==
                                case_info['conf_id']]
        else:
            case_result_list = [result for result in job_result_list if result['test_case_id'] == case_info['conf_id']]
        thread_tasks.append(
            ToneThread(_get_suite_conf_metric_v1, (case_info, suite_obj, group_list, base_index, base_is_baseline,
                                                   case_result_list, duplicate_conf, baseline_result_list,
                                                   job_result_list, base_job_list))
        )
        thread_tasks[-1].start()
    for thread_task in thread_tasks:
        thread_task.join()
        conf_obj = thread_task.get_result()
        if conf_obj:
            exist_list = [conf for conf in conf_list if conf['conf_id'] == conf_obj['conf_id']]
            if len(exist_list) == 0:
                conf_list.append(conf_obj)
    suite_obj['conf_list'] = conf_list
    base_metric_count = 0
    for metric in conf_list:
        base_metric_count += len(metric['metric_list'])
    if 'all' in suite_obj['base_count']:
        suite_obj['base_count']['all'] = base_metric_count
    return suite_obj


def remove_duplicate_case(job_result_list, job_list):
    job_case_list = [{'conf_id': result.get('test_case_id'), 'conf_name': result.get('test_case_name')} for result in
                     job_result_list if result.get('test_job_id') in job_list]
    return reduce(lambda x, y: x if y in x else x + [y], [[], ] + job_case_list)


def _check_has_duplicate(duplicate_conf, conf_id):
    if duplicate_conf:
        d_conf = [d for d in duplicate_conf if conf_id == d['conf_id']]
        if len(d_conf) > 0:
            return True
    return False


def _check_duplicate_hit(duplicate_conf, conf_id, test_job_id):
    d_conf = [d for d in duplicate_conf if conf_id == d['conf_id'] and test_job_id == d['job_id']]
    if len(d_conf) > 0:
        return True
    return False


def _get_suite_conf_metric_v1(conf_info, suite_obj, group_list, base_index, base_is_baseline, perf_results,
                              base_duplicate_conf, baseline_result_list, job_result_list, base_job_list):
    conf_id = conf_info['conf_id']
    if not suite_obj.get('compare_count'):
        suite_obj['compare_count'] = [{'all': 0, 'increase': 0, 'decline': 0} for _ in range(len(group_list))]
    if not suite_obj.get('base_count'):
        suite_obj['base_count'] = {'all': len(perf_results), 'increase': 0, 'decline': 0}
    else:
        suite_obj['base_count']['all'] += len(perf_results)
    compare_job_list = list()
    compare_result_li = list()
    conf_compare_data = list()
    base_is_job = 0 if base_is_baseline else 1
    for compare_job in group_list:
        duplicate_conf = compare_job.get('duplicate_conf')
        has_duplicate = _check_has_duplicate(duplicate_conf, conf_id)
        job_list = compare_job.get('job_list')
        is_baseline = compare_job.get('is_baseline', 0)
        is_job = 0 if is_baseline else 1
        if not has_duplicate and len(job_list) > 0:
            for job_id in job_list:
                if is_baseline:
                    job_result = [result for result in baseline_result_list if result['test_job_id'] == job_id
                                  and result['test_case_id'] == conf_id]
                else:
                    job_result = [result for result in job_result_list if result['test_job_id'] == job_id
                                  and result['test_case_id'] == conf_id]
                if len(job_result) > 0:
                    job_list = [job_id]
                    compare_job_list.append(job_id)
                    break
        group_compare = None
        for job_id in job_list:
            compare_result = None
            if is_baseline:
                job_result = [result for result in baseline_result_list if result['test_job_id'] == job_id
                              and result['test_case_id'] == conf_id]
            else:
                job_result = [result for result in job_result_list if result['test_job_id'] == job_id
                              and result['test_case_id'] == conf_id]
            if has_duplicate:
                if _check_duplicate_hit(duplicate_conf, conf_id, job_id):
                    compare_job_list.append(job_id)
                    group_compare = compare_result = job_result
            else:
                group_compare = compare_result = job_result
            if compare_result:
                compare_result_li.append(compare_result)
        if not group_compare:
            compare_result_li.append(dict())
        compare_job_id = list(set(job_list) & set(compare_job_list))
        conf_compare_data.append(dict({
            'is_job': is_job,
            'obj_id': compare_job_id[0] if len(compare_job_id) > 0 else job_list[0],
            'is_baseline': is_baseline
        }))
    base_job_id = base_job_list.get('job_list')[0]
    if _check_has_duplicate(base_duplicate_conf, conf_id):
        for perf_result in perf_results:
            if _check_duplicate_hit(base_duplicate_conf, conf_id, perf_result.get('test_job_id')):
                base_job_id = perf_result.get('test_job_id')
                break
    conf_compare_data.insert(base_index, dict({
        'is_job': base_is_job,
        'obj_id': base_job_id,
        'is_baseline': base_is_baseline
    }))
    conf_obj = {
        'conf_id': conf_id,
        'conf_name': conf_info['conf_name'],
        'is_job': base_is_job,
        'obj_id': base_job_id,
        'conf_compare_data': conf_compare_data,
        'metric_list': get_metric_list_v1(perf_results, compare_result_li, suite_obj['compare_count'], base_index,
                                          base_job_id),
    }
    if not conf_obj['metric_list']:
        return
    return conf_obj


def get_metric_list_v1(perf_results, compare_result_li, compare_count, base_index, base_job_id):
    metric_list = list()
    base_perf_result = [perf_result for perf_result in perf_results if perf_result.get('test_job_id') == base_job_id]
    for perf_result in base_perf_result:
        metric = perf_result.get('metric')
        exist_metric_list = [m for m in metric_list if m['metric'] == metric]
        if len(exist_metric_list) > 0:
            continue
        unit = perf_result.get('unit')
        test_value = round(float(perf_result.get('test_value')), 2)
        cv_value = perf_result.get('cv_value')
        base_metric = {
            'test_value': test_value,
            'cv_value': cv_value.split('±')[-1] if cv_value else None,
            'max_value': perf_result.get('max_value'),
            'min_value': perf_result.get('min_value'),
            'value_list': perf_result.get('value_list')
        }
        compare_data = get_compare_data_v1(metric, test_value, perf_result, compare_result_li, compare_count)
        compare_data.insert(base_index, base_metric)
        metric_obj = {
            'metric': metric,
            'test_value': test_value,
            'cv_threshold': perf_result.get('cv_threshold'),
            'cmp_threshold': perf_result.get('cmp_threshold'),
            'unit': unit,
            'direction': perf_result.get('direction'),
            'compare_data': compare_data
        }
        metric_list.append(metric_obj)
    return metric_list


def get_compare_data_v1(metric, test_value, base_perf_result, compare_result_li, compare_count):
    compare_data = list()
    compare_job_index = 0
    for compare_result in compare_result_li:
        group_data = dict()
        if compare_result:
            _count = compare_count[compare_job_index]
            perf_results = [compare for compare in compare_result if compare['metric'] == metric]
            if len(perf_results) > 0:
                perf_result = perf_results[0]
                value = round(float(perf_result.get('test_value')), 2)
                group_data['test_value'] = value
                group_data['cv_value'] = perf_result.get('cv_value').split('±')[-1]
                group_data['max_value'] = perf_result.get('max_value')
                group_data['min_value'] = perf_result.get('min_value')
                group_data['compare_value'], group_data['compare_result'] = \
                    get_compare_result(test_value, value, base_perf_result.get('direction'),
                                       base_perf_result.get('cmp_threshold'),
                                       group_data['cv_value'], base_perf_result.get('cv_threshold'))
                group_data['value_list'] = perf_result.get('value_list')
                _count['all'] += 1
                if group_data['compare_result'] == 'increase':
                    _count['increase'] += 1
                if group_data['compare_result'] == 'decline':
                    _count['decline'] += 1
        compare_data.append(group_data)
        compare_job_index += 1
    return compare_data


def get_suite_conf_sub_case_v1(suite_id, suite_name, base_index, group_job_list, suite_info, is_all):
    suite_obj = {
        'suite_name': suite_name,
        'suite_id': suite_id,
        'base_count': {
            'all_case': 0,
            'success_case': 0,
            'fail_case': 0,
        },
        'compare_count': list(),
    }
    base_job_list = group_job_list.pop(base_index)
    base_is_baseline = base_job_list.get('is_baseline', 0)
    duplicate_conf = base_job_list.get('duplicate_conf', [])
    conf_list = list()
    job_id_list = ','.join(str(e) for e in base_job_list.get('job_list'))
    if base_is_baseline:
        raw_sql = 'SELECT distinct a.baseline_id as test_job_id,a.test_case_id,b.name AS test_case_name, ' \
                  '0 AS success_case ,' \
                  'COUNT(a.test_case_id ) AS fail_case,' \
                  'COUNT(a.test_case_id ) AS total_count ' \
                  'FROM func_baseline_detail a LEFT JOIN test_case b ON a.test_case_id = b.id ' \
                  'WHERE a.is_deleted=0 AND a.test_suite_id=%s AND a.baseline_id IN (' + \
                  job_id_list + ') GROUP BY a.baseline_id, a.test_case_id'
    else:
        raw_sql = 'SELECT distinct a.test_job_id,a.test_case_id,b.name AS test_case_name, ' \
                  'SUM(case when a.sub_case_result=1 then 1 ELSE 0 END ) AS success_case ,' \
                  'SUM(case when a.sub_case_result=2 then 1 ELSE 0 END ) AS fail_case,' \
                  'COUNT(a.test_case_id ) AS total_count ' \
                  'FROM func_result a LEFT JOIN test_case b ON a.test_case_id = b.id ' \
                  'WHERE a.is_deleted=0 AND a.test_suite_id=%s AND a.test_job_id IN (' + \
                  job_id_list + ') GROUP BY a.test_job_id, a.test_case_id'
    if not is_all:
        conf_id_list = list()
        for conf in suite_info:
            conf_id_list.append(conf.get('conf_id'))
        conf_id_list_str = ','.join(str(e) for e in conf_id_list)
        raw_sql += ' AND a.test_case_id IN (' + conf_id_list_str + ')'
    case_list = query_all_dict(raw_sql.replace('\'', ''), [suite_id])
    for test_job_id in base_job_list.get('job_list'):
        for case_info in [c for c in case_list if c['test_job_id'] == test_job_id]:
            all_case = case_info['total_count']
            success_case = case_info['success_case']
            fail_case = case_info['fail_case']
            conf_id = case_info['test_case_id']
            conf_name = case_info['test_case_name']
            duplicate_jobs = [duplicate_data for duplicate_data in duplicate_conf
                              if duplicate_data['conf_id'] == conf_id]
            duplicate_job_id = test_job_id
            if len(duplicate_jobs) == 1:
                duplicate_job_id = duplicate_jobs[0]['job_id']
            if base_is_baseline:
                func_results = FuncBaselineDetail.objects. \
                    filter(Q(baseline_id=duplicate_job_id) & Q(test_case_id=conf_id)). \
                    values_list('sub_case_name', flat=True).distinct()
            else:
                func_results = FuncResult.objects.filter(Q(test_job_id=duplicate_job_id) & Q(test_case_id=conf_id)). \
                    values_list('sub_case_name', 'sub_case_result').distinct()
            exist_conf = [conf for conf in conf_list if conf['conf_id'] == conf_id]
            if exist_conf and len(exist_conf) > 0:
                continue
            base_data = {
                'all_case': all_case,
                'obj_id': duplicate_job_id,
                'success_case': success_case,
                'fail_case': fail_case,
                'is_baseline': base_is_baseline
            }
            compare_data = list()
            if len(group_job_list) > 0:
                conf_compare_data = get_conf_compare_data_v1(group_job_list, suite_id, conf_id,
                                                             suite_obj['compare_count'])
                if len(conf_compare_data) > 0:
                    compare_data.extend(conf_compare_data)
                else:
                    compare_data.insert(0, dict())
            compare_data.insert(base_index, base_data)
            conf_obj = {
                'conf_name': conf_name,
                'conf_id': conf_id,
                'conf_compare_data': compare_data,
                'sub_case_list': get_sub_case_list_v1(func_results[:200], suite_id, conf_id, group_job_list, base_index)
            }
            suite_obj['base_count']['all_case'] += all_case
            suite_obj['base_count']['success_case'] += success_case
            suite_obj['base_count']['fail_case'] += fail_case
            if _check_has_duplicate(duplicate_conf, conf_id):
                d_conf = [d for d in duplicate_conf if conf_id == d['conf_id']]
                if len(d_conf) > 0 and case_info['test_job_id'] == d_conf[0]['job_id']:
                    conf_list.append(conf_obj)
            else:
                conf_list.append(conf_obj)
    suite_obj['conf_list'] = conf_list
    return suite_obj


def get_sub_case_list_v1(func_results, suite, conf, compare_job_li, base_index):
    sub_case_list = list()
    q = Queue()
    with ThreadPoolExecutor(max_workers=8) as t:
        for func_result in func_results:
            t.submit(concurrent_calc_v1, func_result, suite, conf, compare_job_li, base_index, q)
    while not q.empty():
        sub_case_list.append(q.get())
    return sub_case_list


def concurrent_calc_v1(func_result, suite, conf, compare_job_li, base_index, q):
    if isinstance(func_result, tuple):
        sub_case_name = func_result[0]
        result = FUNC_CASE_RESULT_TYPE_MAP.get(func_result[1])
    else:
        sub_case_name = func_result
        result = FUNC_CASE_RESULT_TYPE_MAP.get(2)
    compare_data = get_func_compare_data_v1(suite, conf, sub_case_name, compare_job_li)
    compare_data.insert(base_index, result)
    q.put(
        {
            'sub_case_name': sub_case_name,
            # 'result': result,
            'compare_data': compare_data,
        }
    )


def get_func_compare_data_v1(suite, conf, sub_case_name, compare_job_li):
    compare_data = list()
    for compare_job in compare_job_li:
        group_data = ''
        duplicate_conf = compare_job.get('duplicate_conf', list())
        has_duplicate = False
        if len(duplicate_conf) > 0:
            has_duplicate = True
        is_baseline = compare_job.get('is_baseline', 0)
        if is_baseline:
            func_results = FuncBaselineDetail.objects.filter(baseline_id__in=compare_job.get('job_list'),
                                                             test_suite_id=suite,
                                                             test_case_id=conf, sub_case_name=sub_case_name)
        else:
            func_results = FuncResult.objects.filter(test_job_id__in=compare_job.get('job_list'), test_suite_id=suite,
                                                     test_case_id=conf, sub_case_name=sub_case_name)
        if func_results.exists():
            func_result = func_results.first()
            if is_baseline:
                group_data = FUNC_CASE_RESULT_TYPE_MAP.get(2)
            else:
                group_data = FUNC_CASE_RESULT_TYPE_MAP.get(func_result.sub_case_result)
        if has_duplicate > 0:
            d_conf = [d for d in duplicate_conf if conf == d['conf_id']]
            if is_baseline:
                job_result_count = func_results.filter(baseline_id=d_conf[0]['job_id']).count()
            else:
                job_result_count = func_results.filter(test_job_id=d_conf[0]['job_id']).count()
            if len(d_conf) > 0 and job_result_count > 0:
                compare_data.append(group_data)
            else:
                compare_data.append(group_data)
        else:
            compare_data.append(group_data)
    return compare_data


def get_conf_compare_data_v1(compare_objs, suite_id, conf_id, compare_count):
    compare_data = list()
    for idx, group_obj in enumerate(compare_objs):
        is_baseline = group_obj.get('is_baseline', 0)
        _compare_count = {
            'all_case': 0,
            'success_case': 0,
            'fail_case': 0,
        }
        group_data = {
            'all_case': 0,
            'success_case': 0,
            'fail_case': 0,
            'is_baseline': is_baseline
        }
        if not group_obj or len(group_obj.get('job_list')) == 0:
            compare_data.append(group_data)
            compare_count.append(_compare_count)
            continue
        duplicate_conf = group_obj.get('duplicate_conf')
        has_duplicate = False
        if duplicate_conf and len(duplicate_conf) > 0:
            has_duplicate = True
        if is_baseline:
            func_results = FuncBaselineDetail.objects.filter(baseline_id__in=group_obj.get('job_list'),
                                                             test_suite_id=suite_id,
                                                             test_case_id=conf_id). \
                values_list('baseline_id', 'test_case_id'). \
                annotate(total_count=Count('test_case_id'))
        else:
            func_results = FuncResult.objects.filter(test_job_id__in=group_obj.get('job_list'), test_suite_id=suite_id,
                                                     test_case_id=conf_id). \
                values_list('test_job_id', 'test_case_id'). \
                annotate(success_case=Count(Case(When(sub_case_result=1, then=0))),
                         fail_case=Count(Case(When(sub_case_result=2, then=0))),
                         total_count=Count('test_case_id'))
        all_case = 0
        success_case = 0
        fail_case = 0
        for compare_info in func_results:
            if is_baseline:
                all_case += compare_info[2]
                success_case += 0
                fail_case += compare_info[2]
            else:
                all_case += compare_info[4]
                success_case += compare_info[2]
                fail_case += compare_info[3]
        if len(compare_count) < len(compare_objs):
            compare_count.append(_compare_count)
        compare_count[idx]['all_case'] += all_case
        compare_count[idx]['success_case'] += success_case
        compare_count[idx]['fail_case'] += fail_case
        group_data['all_case'] = all_case
        group_data['success_case'] = success_case
        group_data['fail_case'] = fail_case
        obj_id = group_obj.get('job_list')[0]
        if len(func_results) > 0:
            obj_id = func_results[0][0]
        d_conf = [d for d in duplicate_conf if conf_id == d['conf_id']] if duplicate_conf else list()
        if has_duplicate > 0 and len(d_conf) > 0:
            if is_baseline:
                job_result_count = func_results.filter(baseline_id=d_conf[0]['job_id']).count()
            else:
                job_result_count = func_results.filter(test_job_id=d_conf[0]['job_id']).count()
            if job_result_count > 0:
                group_data['obj_id'] = d_conf[0]['job_id']
                compare_data.append(group_data)
            else:
                group_data['obj_id'] = obj_id
                compare_data.append(group_data)
        else:
            group_data['obj_id'] = obj_id
            compare_data.append(group_data)
    return compare_data


class ServerData:
    is_instance = 0
    server = None
    server_is_deleted = False
    server_deleted = []
