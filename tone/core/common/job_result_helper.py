# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import json
import requests
from django.db.models import Count, Case, When, Q
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
        count = len(per_results)
        increase = len(list(filter(lambda x: x.track_result == 'increase', per_results)))
        decline = len(list(filter(lambda x: x.track_result == 'decline', per_results)))
        normal = len(list(filter(lambda x: x.track_result == 'normal', per_results)))
        invalid = len(list(filter(lambda x: x.track_result == 'invalid', per_results)))
        na = count - increase - decline - normal - invalid
        result = {'count': count, 'increase': increase, 'decline': decline, 'normal': normal, 'invalid': invalid,
                  'na': na}
    elif test_type == BUSINESS:
        job_case_queryset = TestJobCase.objects.filter(job_id=job_id)
        count = len(job_case_queryset)
        fail = len(list(filter(lambda x: x.state == 'fail', job_case_queryset)))
        skip = len(list(filter(lambda x: x.state == 'skip', job_case_queryset)))
        success = len(list(filter(lambda x: x.state == 'success', job_case_queryset)))
        result = {'count': count, 'success': success, 'fail': fail, 'skip': skip}
    else:
        sub_case_result = FuncResult.objects.filter(test_job_id=job_id).values_list('sub_case_result', flat=True)
        sub_case_result_list = list(sub_case_result)
        count = len(sub_case_result_list)
        success = sub_case_result_list.count(1)
        fail = sub_case_result_list.count(2)
        skip = sub_case_result_list.count(5)
        warn = sub_case_result_list.count(6)
        result = {'count': count, 'success': success, 'fail': fail, 'skip': skip, 'warn': warn}
    return result


def calc_job_suite(job_id, test_suite_id, ws_id, test_type, test_result=None):
    """
    统计JobSuite结果及数据
    """
    count_data = dict()
    result = None
    if test_type == PERFORMANCE:
        per_result = test_result
        count = len(per_result)
        increase = len(list(filter(lambda x: x.track_result == 'increase', per_result)))
        decline = len(list(filter(lambda x: x.track_result == 'decline', per_result)))
        normal = len(list(filter(lambda x: x.track_result == 'normal', per_result)))
        invalid = len(list(filter(lambda x: x.track_result == 'invalid', per_result)))

        na = count - increase - decline - normal - invalid
        count_data['count'] = count
        count_data['increase'] = increase
        count_data['decline'] = decline
        count_data['normal'] = normal
        count_data['invalid'] = invalid
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
        baseline_id = TestJob.objects.get_value(id=job_id).baseline_id
        impact_baseline = calc_impact_baseline(func_result, baseline_id, ws_id, job_id)
        conf_count = len(func_result)
        conf_fail = len(list(
            filter(lambda x: x.sub_case_result == 2 and not x.match_baseline, func_result))) + impact_baseline
        conf_skip = len(list(filter(lambda x: x.sub_case_result == 5, func_result)))
        conf_warn = len(list(filter(lambda x: x.sub_case_result == 6, func_result)))
        if conf_fail > 0:
            result = 'fail'
        elif conf_count > 0 and conf_fail == 0:
            result = 'success'
            count_case = TestJobCase.objects.filter(job_id=job_id,
                                                    test_suite_id=test_suite_id).count()
            if count_case > conf_count:
                # 如果conf在FuncResult表中没有测试结果，则该suite状态也是fail
                result = 'fail'
        else:
            result = '-'
        count_data['conf_count'] = conf_count
        count_data['conf_success'] = len(list(filter(lambda x: x.sub_case_result == 1, func_result)))
        count_data['conf_fail'] = len(list(filter(lambda x: x.sub_case_result == 2, func_result)))
        count_data['conf_warn'] = conf_warn
        count_data['conf_skip'] = conf_skip
    return result, count_data


def calc_job_case(job_case, suite_result, test_type, is_api=False):
    """
    统计JobCase结果及数据
    """
    count_data = dict()
    result = None
    if test_type == PERFORMANCE:
        per_result = suite_result.filter(test_case_id=job_case.test_case_id).values_list('track_result', flat=True)
        per_result = list(per_result)
        count = len(per_result)
        increase = per_result.count('increase')
        decline = per_result.count('decline')
        normal = per_result.count('normal')
        invalid = per_result.count('invalid')
        na = count - increase - decline - normal - invalid
        count_data['count'] = count
        count_data['increase'] = increase
        count_data['decline'] = decline
        count_data['normal'] = normal
        count_data['invalid'] = invalid
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
        func_result = suite_result.filter(test_case_id=job_case.test_case_id)
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
        count_data['case_warn'] = func_result.filter(sub_case_result='6').count()
        count_data['case_skip'] = case_skip
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
            _get_server_inheriting_machine(is_config, job_case_id, obj)
        else:
            _get_server_no_inheriting_machine(is_config, job_case, obj, server_provider)
    return obj.server, obj.is_instance, obj.server_is_deleted, obj.server_deleted


def _get_server_no_inheriting_machine(is_config, job_case, obj, server_provider):
    if job_case.server_tag_id:
        obj.is_instance = None
        server_tag_id_list = str(job_case.server_tag_id).split(',')
        obj.server = ','.join(ServerTag.objects.filter(id__in=server_tag_id_list).values_list('name', flat=True)) \
            if ServerTag.objects.filter(id__in=server_tag_id_list).exists() else None
    elif job_case.server_snapshot_id and server_provider == 'aligroup' and \
            not TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).in_pool:
        obj.server = TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).ip if \
            TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).ip else \
            TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).sn
    elif not is_config and job_case.server_snapshot_id and server_provider == 'aliyun' and \
            CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id).exists():
        cloud_server = CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id)
        obj.server = _get_server_for_aliyun_not_config(cloud_server)
    else:
        obj.is_instance = None
        obj.server = '随机'


def _get_server_inheriting_machine(is_config, job_case_id, obj):
    job_case = TestJobCase.objects.get(id=job_case_id)
    server_provider = job_case.server_provider
    if job_case.server_tag_id:
        _get_tag_server(job_case, obj)
    elif job_case.server_snapshot_id and server_provider == 'aligroup' and \
            TestServerSnapshot.objects.get(id=job_case.server_snapshot_id).in_pool:
        test_server = TestServerSnapshot.objects.filter(id=job_case.server_snapshot_id).first()
        obj.server = test_server.ip if test_server else None
        _get_server_is_deleted(server_provider, test_server, obj)
    elif not is_config and job_case.server_snapshot_id and server_provider == 'aliyun' and \
            CloudServerSnapshot.objects.filter(id=job_case.server_snapshot_id).exists():
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
        obj.server_deleted = [{'ip': server_list[0][0],
                               'sn': server_list[0][1]}]
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
            server_snapshot_id = TestStep.objects.get(job_case_id=job_case_id, stage='run_case').server
            server = TestServerSnapshot.objects.filter(id=server_snapshot_id)
            if server.exists():
                return __get_server_value(server, server_provider, return_field)
    elif run_mode == 'cluster' and server_provider == 'aliyun':
        test_step = TestStep.objects.filter(job_case_id=job_case_id, stage='run_case')
        if test_step.exists():
            server_snapshot_id = TestStep.objects.get(job_case_id=job_case_id, stage='run_case').server
            server = CloudServerSnapshot.objects.filter(id=server_snapshot_id)
            if server.exists():
                return __get_server_value(server, server_provider, return_field)
    if not server:
        server = None
    return server


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


class ServerData:
    is_instance = 0
    server = None
    server_is_deleted = False
    server_deleted = []


def get_suite_conf_metric_v1(suite_id, suite_name, base_index, group_list, suite_value, is_all):
    conf_list = list()
    suite_obj = {
        'suite_name': suite_name,
        'suite_id': suite_id,
        'compare_count': list(),
        'base_count': list()
    }
    thread_tasks = []
    base_job_list = group_list.pop(base_index)
    duplicate_conf = base_job_list.get('duplicate_conf')
    if is_all:
        for job_id in base_job_list.get('job_list'):
            case_list = PerfResult.objects.filter(test_job_id=job_id, test_suite_id=suite_id).\
                extra(select={'test_case_name': 'test_case.name'},
                      tables=['test_case'],
                      where=["perf_result.test_case_id = test_case.id"]).\
                values_list('test_job_id', 'test_case_id', 'test_case_name').distinct()
            for case_info in case_list:
                thread_tasks.append(
                    ToneThread(_get_suite_conf_metric_v1, (suite_id, case_info[1], case_info[2], suite_obj, group_list,
                                                           case_info[0], base_index))
                )
                thread_tasks[-1].start()
    else:
        for job_id in base_job_list.get('job_list'):
            for case_info in suite_value:
                thread_tasks.append(
                    ToneThread(_get_suite_conf_metric_v1, (suite_id, case_info['conf_id'], case_info['conf_name'],
                                                           suite_obj, group_list, job_id, base_index))
                )
                thread_tasks[-1].start()
    for thread_task in thread_tasks:
        thread_task.join()
        conf_obj = thread_task.get_result()
        if conf_obj:
            if _check_has_duplicate(duplicate_conf, conf_obj['conf_id']):
                if _check_duplicate_hit(duplicate_conf, conf_obj['conf_id'], conf_obj['obj_id']):
                    conf_list.append(conf_obj)
            else:
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


def _get_suite_conf_metric_v1(suite_id, conf_id, conf_name, suite_obj, group_list, base_job_id, base_index):
    perf_results = PerfResult.objects.all(). \
        extra(select={'cv_threshold': 'test_track_metric.cv_threshold',
                      'cmp_threshold': 'test_track_metric.cmp_threshold',
                      'direction': 'test_track_metric.direction'},
              tables=['test_track_metric'],
              where=["perf_result.test_job_id=%s", "perf_result.test_suite_id=%s",
                     "perf_result.test_case_id=%s",
                     "test_track_metric.name = perf_result.metric",
                     "test_track_metric.cv_threshold > 0",
                     "test_track_metric.is_deleted = 0",
                     "(object_type='case' AND object_id=%s) or (object_type='suite' AND object_id=%s)"],
              order_by=['test_track_metric.object_type'],
              params=[base_job_id, suite_id, conf_id, conf_id, suite_id]).distinct()
    if not perf_results.exists():
        return
    if not suite_obj.get('compare_count'):
        suite_obj['compare_count'] = [{'all': 0, 'increase': 0, 'decline': 0} for _ in range(len(group_list))]
    if not suite_obj.get('base_count'):
        suite_obj['base_count'] = {'all': perf_results.count(), 'increase': 0, 'decline': 0}
    else:
        suite_obj['base_count']['all'] += perf_results.count()
    compare_job_list = list()
    compare_result_li = list()
    conf_compare_data = list()
    for compare_job in group_list:
        duplicate_conf = compare_job.get('duplicate_conf')
        has_duplicate = _check_has_duplicate(duplicate_conf, conf_id)
        job_list = compare_job.get('job_list')
        if not has_duplicate and len(compare_job.get('job_list')) > 0:
            for job_id in compare_job.get('job_list'):
                if PerfResult.objects.filter(test_job_id=job_id, test_suite_id=suite_id, test_case_id=conf_id).exists():
                    job_list = [job_id]
                    compare_job_list.append(job_id)
                    break
        group_compare = None
        for job_id in job_list:
            compare_result = None
            if has_duplicate:
                if _check_duplicate_hit(duplicate_conf, conf_id, job_id):
                    compare_job_list.append(job_id)
                    group_compare = compare_result = PerfResult.objects.filter(test_job_id=job_id,
                                                                               test_suite_id=suite_id,
                                                                               test_case_id=conf_id)
            else:
                group_compare = compare_result = PerfResult.objects. \
                    filter(test_job_id=job_id, test_suite_id=suite_id, test_case_id=conf_id)
            if compare_result:
                compare_result_li.append(compare_result)
        if not group_compare:
            compare_result_li.append(dict())
        compare_job_id = list(set(compare_job.get('job_list')) & set(compare_job_list))
        conf_compare_data.append(dict({
            'is_job': 1,
            'obj_id': compare_job_id[0] if len(compare_job_id) > 0 else compare_job.get('job_list')[0]
        }))
    conf_compare_data.insert(base_index, dict({
        'is_job': 1,
        'obj_id': base_job_id
    }))
    conf_obj = {
        'conf_id': conf_id,
        'conf_name': conf_name,
        'is_job': 1,
        'obj_id': base_job_id,
        'conf_compare_data': conf_compare_data,
        'metric_list': get_metric_list_v1(perf_results, compare_result_li, suite_obj['compare_count'], base_index),
    }
    if not conf_obj['metric_list']:
        return
    return conf_obj


def get_metric_list_v1(perf_results, compare_result_li, compare_count, base_index):
    metric_list = list()
    for perf_result in perf_results:
        metric = perf_result.metric
        exist_metric_list = [m for m in metric_list if m['metric'] == metric]
        if len(exist_metric_list) > 0:
            continue
        unit = perf_result.unit
        test_value = round(float(perf_result.test_value), 2)
        cv_value = perf_result.cv_value
        base_metric = {
                'test_value': test_value,
                'cv_value': cv_value.split('±')[-1] if cv_value else None,
                'max_value': perf_result.max_value,
                'min_value': perf_result.min_value,
                'value_list': perf_result.value_list
            }
        compare_data = get_compare_data_v1(metric, test_value, perf_result, compare_result_li, compare_count)
        compare_data.insert(base_index, base_metric)
        metric_obj = {
            'metric': metric,
            'test_value': test_value,
            'cv_threshold': perf_result.cv_threshold,
            'cmp_threshold': perf_result.cmp_threshold,
            'unit': unit,
            'direction': perf_result.direction,
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
            perf_results = compare_result.filter(metric=metric)
            if perf_results.exists():
                perf_result = perf_results.first()
                value = round(float(perf_result.test_value), 2)
                group_data['test_value'] = value
                group_data['cv_value'] = perf_result.cv_value.split('±')[-1]
                group_data['max_value'] = perf_result.max_value
                group_data['min_value'] = perf_result.min_value
                group_data['compare_value'], group_data['compare_result'] = \
                    get_compare_result(test_value, value, base_perf_result.direction, base_perf_result.cmp_threshold,
                                       group_data['cv_value'], base_perf_result.cv_threshold)
                group_data['value_list'] = perf_result.value_list
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
    duplicate_conf = base_job_list.get('duplicate_conf', [])
    conf_list = list()
    q = Q(test_job_id__in=base_job_list.get('job_list'), test_suite_id=suite_id)
    if not is_all:
        conf_id_list = list()
        for conf in suite_info:
            conf_id_list.append(conf.get('conf_id'))
        q &= Q(test_case_id__in=conf_id_list)
    case_list = FuncResult.objects.filter(q).extra(select={'test_case_name': 'test_case.name'},
                                                   tables=['test_case'],
                                                   where=["func_result.test_case_id = test_case.id"]). \
        values_list('test_job_id', 'test_case_id', 'test_case_name').distinct(). \
        annotate(success_case=Count(Case(When(sub_case_result=1, then=0))),
                 fail_case=Count(Case(When(sub_case_result=2, then=0))),
                 total_count=Count('test_case_id'))
    for test_job_id in base_job_list.get('job_list'):
        for case_info in case_list.filter(test_job_id=test_job_id):
            all_case = case_info[5]
            success_case = case_info[3]
            fail_case = case_info[4]
            conf_id = case_info[1]
            conf_name = case_info[2]
            duplicate_jobs = [duplicate_data for duplicate_data in duplicate_conf
                              if duplicate_data['conf_id'] == conf_id]
            duplicate_job_id = test_job_id
            if len(duplicate_jobs) == 1:
                duplicate_job_id = duplicate_jobs[0]['job_id']
            func_results = FuncResult.objects.filter(Q(test_job_id=duplicate_job_id) & Q(test_case_id=conf_id)).\
                values_list('sub_case_name', 'sub_case_result').distinct()
            exist_conf = [conf for conf in conf_list if conf['conf_id'] == conf_id]
            if exist_conf and len(exist_conf) > 0:
                continue
            base_data = {
                'all_case': all_case,
                'obj_id': duplicate_job_id,
                'success_case': success_case,
                'fail_case': fail_case,
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
                # 'conf_compare_data': [compare for compare in compare_data if compare['obj_id'] == duplicate_job_id],
                'sub_case_list': get_sub_case_list_v1(func_results[:200], suite_id, conf_id, group_job_list, base_index)
            }
            suite_obj['base_count']['all_case'] += all_case
            suite_obj['base_count']['success_case'] += success_case
            suite_obj['base_count']['fail_case'] += fail_case
            if _check_has_duplicate(duplicate_conf, case_info[0]):
                d_conf = [d for d in duplicate_conf if case_info[0] == d['conf_id']]
                if len(d_conf) > 0 and case_info.filter(test_job_id=d_conf[0]['job_id']).count() > 0:
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
    sub_case_name = func_result[0]
    result = FUNC_CASE_RESULT_TYPE_MAP.get(func_result[1])
    compare_data = get_func_compare_data_v1(suite, conf, sub_case_name, compare_job_li)
    if len(compare_data) == 0:
        compare_data.insert(0, '')
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
        func_results = FuncResult.objects.filter(test_job_id__in=compare_job.get('job_list'), test_suite_id=suite,
                                                 test_case_id=conf, sub_case_name=sub_case_name)
        if func_results.exists():
            func_result = func_results.first()
            group_data = FUNC_CASE_RESULT_TYPE_MAP.get(func_result.sub_case_result)
        if has_duplicate > 0:
            d_conf = [d for d in duplicate_conf if conf == d['conf_id']]
            if len(d_conf) > 0 and func_results.filter(test_job_id=d_conf[0]['job_id']).count() > 0:
                compare_data.append(group_data)
            else:
                compare_data.append(group_data)
        else:
            compare_data.append(group_data)
    return compare_data


def get_conf_compare_data_v1(compare_objs, suite_id, conf_id, compare_count):
    compare_data = list()
    for idx, group_obj in enumerate(compare_objs):
        _compare_count = {
            'all_case': 0,
            'success_case': 0,
            'fail_case': 0,
        }
        group_data = {
            'all_case': 0,
            'success_case': 0,
            'fail_case': 0,
        }
        if not group_obj:
            compare_data.append(group_data)
            compare_count.append(_compare_count)
            continue
        duplicate_conf = group_obj.get('duplicate_conf')
        has_duplicate = False
        if duplicate_conf and len(duplicate_conf) > 0:
            has_duplicate = True
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
        if has_duplicate > 0:
            d_conf = [d for d in duplicate_conf if conf_id == d['conf_id']]
            if len(d_conf) > 0 and func_results.filter(test_job_id=d_conf[0]['job_id']).count() > 0:
                group_data['obj_id'] = d_conf[0]['job_id']
                compare_data.append(group_data)
            else:
                group_data['obj_id'] = group_obj.get('job_list')[0]
                compare_data.append(group_data)
        else:
            group_data['obj_id'] = group_obj.get('job_list')[0]
            compare_data.append(group_data)
    return compare_data
