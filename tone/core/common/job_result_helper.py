# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import json
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from queue import Queue

from tone import settings
from tone.core.common.toneagent import tone_agent_info
from tone.core.common.log_manager import get_logger
from tone.core.utils.tone_thread import ToneThread
from tone.models import TestJobSuite, TestJobCase, TestJob, FuncResult, PerfResult, TestServerSnapshot, \
    CloudServerSnapshot, ServerTag, TestTmplCase, TestServer, \
    CloudServer, TestMetric, FuncBaselineDetail, TestCluster, TestStep, BusinessResult, \
    TestSuite
from tone.core.common.constant import PERFORMANCE, IP_PATTEN, BUSINESS
from tone.core.common.constant import FUNC_CASE_RESULT_TYPE_MAP


logger = get_logger('error')


def calc_job(job_id):
    """
    统计JobSuite结果
    """
    test_type = TestJob.objects.get(id=job_id).test_type
    if test_type == 'performance':
        per_results = PerfResult.objects.filter(test_job_id=job_id)
        count = per_results.count()
        increase = per_results.filter(track_result='increase').count()
        decline = per_results.filter(track_result='decline').count()
        normal = per_results.filter(track_result='normal').count()
        invalid = per_results.filter(track_result='invalid').count()
        na = count - increase - decline - normal - invalid
        result = {'count': count, 'increase': increase, 'decline': decline, 'normal': normal, 'invalid': invalid,
                  'na': na}
    elif test_type == BUSINESS:
        job_case_queryset = TestJobCase.objects.filter(job_id=job_id)
        count = job_case_queryset.count()
        fail = job_case_queryset.filter(state='fail').count()
        skip = job_case_queryset.filter(state='skip').count()
        success = job_case_queryset.filter(state='success').count()
        result = {'count': count, 'success': success, 'fail': fail, 'skip': skip}
    else:
        func_result = FuncResult.objects.filter(test_job_id=job_id)
        success = func_result.filter(sub_case_result='1').count()
        fail = func_result.filter(sub_case_result='2').count()
        skip = func_result.filter(sub_case_result='5').count()
        count = func_result.count()
        result = {'count': count, 'success': success, 'fail': fail, 'skip': skip}
    return result


def calc_job_suite(job_suite_id, ws_id, test_type):
    """
    统计JobSuite结果及数据
    """
    job_suite = TestJobSuite.objects.get(id=job_suite_id)
    # test_type = TestJob.objects.get(id=job_suite.job_id).test_type
    count_data = dict()
    result = None
    if test_type == PERFORMANCE:
        per_result = PerfResult.objects.filter(test_job_id=job_suite.job_id, test_suite_id=job_suite.test_suite_id)
        count = per_result.count()
        increase = per_result.filter(track_result='increase').count()
        decline = per_result.filter(track_result='decline').count()
        normal = per_result.filter(track_result='normal').count()
        invalid = per_result.filter(track_result='invalid').count()
        na = count - increase - decline - normal - invalid
        count_data['count'] = count
        count_data['increase'] = increase
        count_data['decline'] = decline
        count_data['normal'] = normal
        count_data['invalid'] = invalid
        count_data['na'] = na
    elif test_type == BUSINESS:
        test_suite_id = job_suite.test_suite_id
        job_case_queryset = TestJobCase.objects.filter(job_id=job_suite.job_id, test_suite_id=test_suite_id)
        conf_count = job_case_queryset.count()
        conf_fail = job_case_queryset.filter(state='fail').count()
        conf_skip = job_case_queryset.filter(state='skip').count()
        if conf_fail > 0:
            result = 'fail'
        elif conf_count > 0 and conf_fail == 0:
            result = 'success'
        else:
            result = '-'
        count_data['conf_count'] = conf_count
        count_data['conf_success'] = job_case_queryset.filter(state='success').count()
        count_data['conf_fail'] = conf_fail
        count_data['conf_skip'] = conf_skip
    else:
        func_result = FuncResult.objects.filter(test_job_id=job_suite.job_id, test_suite_id=job_suite.test_suite_id)
        conf_count = func_result.count()
        baseline_id = TestJob.objects.get_value(id=job_suite.job_id).baseline_id
        impact_baseline = calc_impact_baseline(func_result, baseline_id, ws_id, job_suite.job_id)
        # conf_success = func_result.filter(sub_case_result='1').count() + impact_baseline
        conf_fail = func_result.filter(sub_case_result='2', match_baseline=False).count() + impact_baseline
        conf_skip = func_result.filter(sub_case_result='5').count()
        if conf_fail > 0:
            result = 'fail'
        elif conf_count > 0 and conf_fail == 0:
            result = 'success'
        else:
            result = '-'
        count_data['conf_count'] = conf_count
        count_data['conf_success'] = func_result.filter(sub_case_result='1').count()
        count_data['conf_fail'] = func_result.filter(sub_case_result='2').count()
        count_data['conf_skip'] = conf_skip
    return result, count_data


def calc_job_case(job_case_id, is_api=False):
    """
    统计JobCase结果及数据
    """
    job_case = TestJobCase.objects.get(id=job_case_id)
    test_type = TestSuite.objects.filter(id=job_case.test_suite_id, query_scope='all').first().test_type
    count_data = dict()
    result = None
    if test_type == PERFORMANCE:
        per_result = PerfResult.objects.filter(test_job_id=job_case.job_id, test_suite_id=job_case.test_suite_id,
                                               test_case_id=job_case.test_case_id)
        count = per_result.count()
        increase = per_result.filter(track_result='increase').count()
        decline = per_result.filter(track_result='decline').count()
        normal = per_result.filter(track_result='normal').count()
        invalid = per_result.filter(track_result='invalid').count()
        na = count - increase - decline - normal - invalid
        count_data['count'] = count
        count_data['increase'] = increase
        count_data['decline'] = decline
        count_data['normal'] = normal
        count_data['invalid'] = invalid
        count_data['na'] = na
    elif test_type == BUSINESS:
        job_case = TestJobCase.objects.filter(id=job_case_id).first()
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
        func_result = FuncResult.objects.filter(test_job_id=job_case.job_id, test_suite_id=job_case.test_suite_id,
                                                test_case_id=job_case.test_case_id)
        case_count = func_result.count()
        baseline_id = TestJob.objects.get_value(id=job_case.job_id).baseline_id
        ws_id = TestJob.objects.get(id=job_case.job_id).ws_id
        impact_baseline = calc_impact_baseline(func_result, baseline_id, ws_id, job_case.job_id)
        # case_success = func_result.filter(sub_case_result='1').count() + impact_baseline
        case_fail = func_result.filter(sub_case_result='2', match_baseline=False).count() + impact_baseline
        case_skip = func_result.filter(sub_case_result='5').count()
        if case_fail > 0:
            result = 'fail'
        elif case_count > 0 and case_fail == 0:
            result = 'success'
        else:
            result = 'fail' if is_api else '-'
        count_data['case_count'] = case_count
        count_data['case_success'] = func_result.filter(sub_case_result='1').count()
        count_data['case_fail'] = func_result.filter(sub_case_result='2').count()
        count_data['case_skip'] = case_skip
    return result, count_data


def get_job_case_server(job_case_id, template=None, is_config=False, data=None):
    job_case = TestJobCase.objects.get(id=job_case_id) if not template else TestTmplCase.objects.get(id=job_case_id)
    run_mode = job_case.run_mode
    server_provider = job_case.server_provider
    is_instance = 0
    server = None
    server_is_deleted = False
    server_deleted = []
    if data and data.get('inheriting_machine'):
        is_instance, server, server_deleted, server_is_deleted = _get_server_for_inheriting_machine(is_config,
                                                                                                    is_instance,
                                                                                                    job_case_id,
                                                                                                    server,
                                                                                                    server_deleted,
                                                                                                    server_is_deleted)
    elif job_case.server_object_id and run_mode == 'standalone' and server_provider == 'aligroup':
        server, server_deleted, server_is_deleted = _get_server_for_aligroup_standalone(job_case, server,
                                                                                        server_deleted,
                                                                                        server_is_deleted)
    elif job_case.server_object_id and run_mode == 'standalone' and server_provider == 'aliyun':
        is_instance, server, server_deleted, server_is_deleted = _get_server_for_aliyun_standalone(is_instance,
                                                                                                   job_case, server,
                                                                                                   server_deleted,
                                                                                                   server_is_deleted)
    elif job_case.server_object_id and run_mode == 'cluster':
        server, server_deleted, server_is_deleted = _get_server_for_cluster(job_case, server, server_deleted,
                                                                            server_is_deleted)
    elif job_case.server_tag_id:
        is_instance = None
        server_tag_id_list = str(job_case.server_tag_id).split(',')
        server = ','.join(ServerTag.objects.filter(id__in=server_tag_id_list).values_list('name', flat=True)) \
            if ServerTag.objects.filter(id__in=server_tag_id_list).exists else None
    elif job_case.server_snapshot_id and server_provider == 'aligroup' and \
            not TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).in_pool:
        server = TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).ip if \
            TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).ip else \
            TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).sn
    elif not is_config and job_case.server_snapshot_id and server_provider == 'aliyun' and \
            CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id).exists():
        server = _get_server_for_aliyun_not_config(job_case, server)
    else:
        is_instance = None
        server = '随机'
    return server, is_instance, server_is_deleted, server_deleted


def _get_server_for_inheriting_machine(is_config, is_instance, job_case_id, server, server_deleted, server_is_deleted):
    job_case = TestJobCase.objects.get(id=job_case_id)
    run_mode = job_case.run_mode
    server_provider = job_case.server_provider
    if job_case.server_object_id and run_mode == 'standalone' and server_provider == 'aligroup':
        server, server_deleted, server_is_deleted = _get_server_for_aligroup_standalone(job_case, server,
                                                                                        server_deleted,
                                                                                        server_is_deleted)
    elif job_case.server_object_id and run_mode == 'standalone' and server_provider == 'aliyun':
        is_instance, server, server_deleted, server_is_deleted = _get_server_for_aliyun_standalone(is_instance,
                                                                                                   job_case, server,
                                                                                                   server_deleted,
                                                                                                   server_is_deleted)
    elif job_case.server_object_id and run_mode == 'cluster':
        server, server_deleted, server_is_deleted = _get_server_for_cluster(job_case, server, server_deleted,
                                                                            server_is_deleted)
    elif job_case.server_tag_id:
        server, is_instance = get_tag_server(job_case)
    elif job_case.server_snapshot_id and server_provider == 'aligroup' and \
            TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).in_pool:
        server = TestServerSnapshot.objects.get(
            id=job_case.server_snapshot_id).ip if TestServerSnapshot. \
            objects.filter(id=job_case.server_snapshot_id).exists() else None
    elif not is_config and job_case.server_snapshot_id and server_provider == 'aliyun' and \
            CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id).exists():
        server = _get_server_for_aliyun_not_config(job_case, server)
    return is_instance, server, server_deleted, server_is_deleted


def _get_server_for_aliyun_not_config(job_case, server):
    server = CloudServerSnapshot.objects.get(id=job_case.server_snapshot_id).pub_ip if \
        CloudServerSnapshot.objects.get(id=job_case.server_snapshot_id).pub_ip else \
        CloudServerSnapshot.objects.get(id=job_case.server_snapshot_id).sn
    return server


def _get_server_for_cluster(job_case, server, server_deleted, server_is_deleted):
    test_cluster = TestCluster.objects.filter(id=job_case.server_object_id)
    if test_cluster:
        server = test_cluster.first().name
    else:
        server_list = TestCluster.objects.filter(id=job_case.server_object_id, query_scope='deleted')
        server_is_deleted = True
        server_deleted = [{'test_cluster': server_list.first().name}]
    return server, server_deleted, server_is_deleted


def _get_server_for_aliyun_standalone(is_instance, job_case, server, server_deleted, server_is_deleted):
    server_obj = CloudServer.objects.filter(id=job_case.server_object_id).first()
    if server_obj:
        is_instance = 1 if server_obj.is_instance else 0
        server = (server_obj.pub_ip if is_instance else server_obj.template_name) if \
            (server_obj.pub_ip if is_instance else server_obj.template_name) else server_obj.sn
    else:
        server_obj = CloudServer.objects.filter(id=job_case.server_object_id, query_scope='deleted').first()
        if server_obj.is_instance:
            server_is_deleted = True
            server_deleted = [{'ip': server_obj.pub_ip,
                               'sn': server_obj.sn}]
    return is_instance, server, server_deleted, server_is_deleted


def _get_server_for_aligroup_standalone(job_case, server, server_deleted, server_is_deleted):
    test_server = TestServer.objects.filter(id=job_case.server_object_id).first()
    if not test_server:
        server_list = list(TestServer.objects.filter(id=job_case.server_object_id,
                                                     query_scope='deleted').values_list('ip', 'sn'))
        server_is_deleted = True
        server_deleted = [{'ip': server_list[0][0],
                           'sn': server_list[0][1]}]
    else:
        server = test_server.ip if test_server.ip else test_server.sn
    return server, server_deleted, server_is_deleted


def get_tag_server(job_case, server=None):
    server_provider = job_case.server_provider
    is_instance = None
    if server_provider == 'aliyun' and not job_case.server_object_id and job_case.server_snapshot_id:
        cloud_server = CloudServerSnapshot.objects.get(id=job_case.server_snapshot_id)
        server = cloud_server.pub_ip if cloud_server.pub_ip else \
            TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).sn
    if server_provider == 'aligroup' and not job_case.server_object_id and job_case.server_snapshot_id:
        server = TestServerSnapshot.objects.get(
            id=job_case.server_snapshot_id).ip if TestServerSnapshot. \
            objects.filter(id=job_case.server_snapshot_id).exists() else None
    return server, is_instance


def get_job_case_run_server(job_case_id):
    job_case = TestJobCase.objects.get(id=job_case_id)
    run_mode = job_case.run_mode
    server_provider = job_case.server_provider
    server = None
    if run_mode == 'standalone' and server_provider == 'aligroup':
        server = TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).ip if TestServerSnapshot.objects.filter(
            id=job_case.server_snapshot_id).exists() else None
    elif run_mode == 'standalone' and server_provider == 'aliyun':
        server = CloudServerSnapshot.objects.get(
            id=job_case.server_snapshot_id).private_ip if CloudServerSnapshot.objects.filter(
            id=job_case.server_snapshot_id).exists() else None
    elif run_mode == 'cluster' and server_provider == 'aligroup':
        if TestStep.objects.filter(job_case_id=job_case_id, stage='run_case').exists():
            _server = TestStep.objects.filter(job_case_id=job_case_id, stage='run_case').last().server
            server = TestServerSnapshot.objects.get(id=_server).private_ip
    elif run_mode == 'cluster' and server_provider == 'aliyun':
        if TestStep.objects.filter(job_case_id=job_case_id, stage='run_case').exists():
            _server = TestStep.objects.filter(job_case_id=job_case_id, stage='run_case').last().server
            server = CloudServerSnapshot.objects.get(id=_server).private_ip
    else:
        pass
    return server


def get_server_ip_sn(server, channel_type):
    ip = server if IP_PATTEN.match(server) else None
    sn = None if IP_PATTEN.match(server) else server
    if ip and channel_type == 'staragent':
        pass
        # sn = json.loads(query_skyline_info('sn', condition="ip='{}'".
        #                                    format(server)).decode()).get('value').get('itemList')[0].get('sn')
    elif ip and channel_type == 'toneagent':
        agent_url = tone_agent_info(ip=server)
        res = json.loads(requests.get(url=agent_url, verify=False).text)
        sn = res.get('RESULT').get('TSN')
    elif sn and channel_type == 'staragent':
        pass
        # ip = json.loads(query_skyline_info('ip', condition="sn='{}'".
        #                                    format(server)).decode()).get('value').get('itemList')[0].get('ip')
    else:
        agent_url = tone_agent_info(tsn=server)
        res = json.loads(requests.get(url=agent_url, verify=False).text)
        ip = res.get('RESULT').get('IP')
    return ip, sn


def get_custom_server(job_case_id, template=None):
    job_case = TestJobCase.objects.get(id=job_case_id) if not template else TestTmplCase.objects.get(id=job_case_id)
    server_provider = job_case.server_provider
    if job_case.server_object_id or job_case.server_tag_id:
        return None
    if server_provider == 'aligroup' and job_case.server_snapshot_id and not TestServerSnapshot.objects.get(
            id=job_case.server_snapshot_id).in_pool:
        server_obj = TestServerSnapshot.objects.get(id=job_case.server_snapshot_id)
        server = {
            'custom_ip': server_obj.ip,
            'custom_sn': server_obj.sn if server_obj.channel_type == 'staragent' else server_obj.tsn,
            'custom_channel': server_obj.channel_type,
        }
    elif job_case.server_snapshot_id and not TestServerSnapshot.objects.get(
            id=job_case.server_snapshot_id).in_pool and server_provider == 'aligroup':
        server_obj = TestServerSnapshot.objects.get(id=job_case.server_snapshot_id)
        server = {
            'custom_ip': server_obj.private_ip,
            'custom_sn': server_obj.sn,
            'custom_channel': server_obj.channel_type,
        }
    else:
        server = None
    return server


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
        compare_job_li.append(compare_job)
    if not suite_obj.get('compare_count'):
        suite_obj['compare_count'] = [{'all': 0, 'increase': 0, 'decline': 0} for _ in
                                      range(len(conf_value.get('compare_objs')))]
    conf_obj = {
        'conf_name': conf_value.get('conf_name'),
        'conf_id': conf_id,
        'is_job': conf_value.get('is_job'),
        'obj_id': conf_value.get('obj_id'),
        'conf_compare_data': conf_value.get('compare_objs'),
        'metric_list': get_metric_list(perf_results, suite_id, conf_id, compare_job_li, suite_obj['compare_count']),
    }
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
            'conf_compare_data': get_conf_compare_data(conf_value.get('compare_objs'), suite_id, conf_id,
                                                       suite_obj['compare_count']),
            'sub_case_list': get_sub_case_list(func_results[:200], suite_id, conf_id, compare_job_li),
            # todo 后期可对接口进行拆分做分页处理
            # 'sub_case_list': asyncio.run(get_sub_case_list(func_results, suite_id, conf_id, compare_job_li)),
        }
        suite_obj['base_count']['all_case'] += conf_obj['all_case']
        suite_obj['base_count']['success_case'] += conf_obj['success_case']
        suite_obj['base_count']['fail_case'] += conf_obj['fail_case']
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
        func_results = FuncResult.objects.filter(test_job_id=compare_job, test_suite_id=suite, test_case_id=conf,
                                                 sub_case_name=sub_case_name)
        if func_results.exists():
            func_result = func_results.first()
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
        group_data['all_case'] = func_results.count()
        group_data['success_case'] = func_results.filter(sub_case_result=1).count()
        group_data['fail_case'] = func_results.filter(sub_case_result=2).count()
        compare_data.append(group_data)
    return compare_data


def splice_job_link(job):
    return f'{settings.APP_DOMAIN}/ws/{job.ws_id}/test_result/{job.id}'
