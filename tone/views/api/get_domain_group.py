# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import json
from django.db.models import Q
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
    res_data = {'functional': dict(), 'performance': dict()}
    conf_id_list = list()
    q = Q()
    suite_id_list = list()
    for suite in suite_list:
        if suite.get('is_all'):
            if suite.get('suite_id') not in suite_id_list:
                suite_id_list.append(suite.get('suite_id'))
        else:
            conf_id_list.extend(suite.get('conf_list'))
    if len(suite_id_list) > 0:
        q &= Q(test_suite_id__in=suite_id_list)
    if len(conf_id_list) > 0:
        q |= Q(id__in=conf_id_list)
    if len(suite_id_list) == 0 and len(conf_id_list) == 0:
        test_case_list = list()
    else:
        test_case_list = TestCase.objects.filter(q).extra(
            select={'test_type': 'test_suite.test_type',
                    'domain': 'test_domain.name'},
            tables=['domain_relation', 'test_suite', 'test_domain'],
            where=['object_type="case"',
                   'object_id=test_case.id',
                   'test_suite.id=test_case.test_suite_id',
                   'test_domain.id=domain_relation.domain_id',
                   'domain_relation.is_deleted=0',
                   'test_domain.is_deleted=0']
        )
    for test_case in test_case_list:
        insert_conf(test_case.domain, res_data, test_case.test_type, test_case.test_suite_id, test_case.id)
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
