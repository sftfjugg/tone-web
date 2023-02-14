# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import json
from tone.core.utils.common_utils import query_all_dict
from tone.core.utils.tone_thread import ToneThread
from tone.models import TestCase, TestDomain, TestSuite, DomainRelation
from tone.core.utils.helper import CommResp
from tone.core.common.expection_handler.error_catch import api_catch_error
from tone.core.common.constant import DEFAULT_DOMAIN


@api_catch_error
def get_domain_info(request):
    resp = CommResp()
    suite_list = json.loads(request.body)
    resp.data = get_domain_group_v1(suite_list)
    return resp.json_resp()


def _get_domain_group(conf, res_data):
    conf_obj = TestCase.objects.get_value(id=conf)
    domains = DomainRelation.objects.filter(object_type='case', object_id=conf)
    suite_id = conf_obj.test_suite_id
    test_type = TestSuite.objects.get_value(id=suite_id).test_type
    if test_type in res_data:
        if domains.exists():
            for _domain in domains:
                domain = TestDomain.objects.get_value(id=_domain.domain_id).name
                insert_conf(domain, res_data, test_type, suite_id, conf)
        else:
            domain = DEFAULT_DOMAIN
            insert_conf(domain, res_data, test_type, suite_id, conf)


def get_domain_group(conf_list):
    res_data = {'functional': dict(), 'performance': dict()}
    thread_tasks = []
    for conf in conf_list:
        thread_tasks.append(
            ToneThread(_get_domain_group, (conf, res_data))
        )
        thread_tasks[-1].start()
    for thread_task in thread_tasks:
        thread_task.join()
    return res_data


def get_domain_group_v1(suite_list):
    res_data = {'functional': dict(), 'performance': dict(), 'business': dict()}
    conf_id_list = list()
    sql_filter = '1=1'
    suite_id_list = list()
    for suite in suite_list:
        if suite.get('is_all'):
            if suite.get('suite_id') not in suite_id_list:
                suite_id_list.append(suite.get('suite_id'))
        else:
            conf_id_list.extend(suite.get('conf_list'))
    if len(suite_id_list) > 0:
        sql_filter += ' and a.test_suite_id in (' + ','.join(str(e) for e in suite_id_list) + ')'
    if len(conf_id_list) > 0:
        sql_filter += ' or a.id in (' + ','.join(str(e) for e in conf_id_list) + ')'
    if len(suite_id_list) == 0 and len(conf_id_list) == 0:
        test_case_list = list()
    else:
        raw_sql = 'SELECT a.id,a.test_suite_id,b.test_type,d.name as domain FROM test_case a LEFT JOIN ' \
                  'test_suite b ON a.test_suite_id=b.id LEFT JOIN domain_relation c ON ' \
                  'c.object_type="case" AND c.object_id=a.id LEFT JOIN test_domain d ON ' \
                  'c.domain_id=d.id WHERE a.is_deleted=0 AND b.is_deleted=0 AND c.is_deleted=0 AND' \
                  ' d.is_deleted=0 AND (' + sql_filter + \
                  ') UNION SELECT a.id,a.test_suite_id,b.test_type,"其他" as domain FROM test_case' \
                  ' a LEFT JOIN test_suite b ' \
                  'ON a.test_suite_id=b.id WHERE a.id NOT IN (SELECT object_id from domain_relation WHERE ' \
                  'object_type="case" AND is_deleted=0) AND a.is_deleted=0 AND b.is_deleted=0 AND ' \
                  '(' + sql_filter + ')'
        test_case_list = query_all_dict(raw_sql)
    for test_case in test_case_list:
        insert_conf(test_case.get('domain'), res_data, test_case.get('test_type'), test_case.get('test_suite_id'),
                    test_case.get('id'))
    return res_data


def insert_conf(domain, res_data, test_type, suite_id, conf):
    if domain in res_data[test_type]:
        if suite_id in res_data[test_type][domain]:
            if conf not in res_data[test_type][domain][suite_id]:
                res_data[test_type][domain][suite_id].append(conf)
        else:
            res_data[test_type][domain][suite_id] = [conf]
    else:
        res_data[test_type][domain] = {suite_id: [conf]}
