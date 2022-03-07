# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import asyncio

from tone.core.common.constant import FUNC_CASE_RESULT_TYPE_MAP
from tone.models import FuncResult


async def get_sub_case_list(func_results, suite, conf, compare_job_li):
    sub_case_list = list()
    tasks = [asyncio.create_task(get_sub_case_result(func_result, suite, conf, compare_job_li, sub_case_list)) for
             func_result in func_results]
    if tasks:
        await asyncio.wait(tasks)
    return sub_case_list


async def get_sub_case_result(func_result, suite, conf, compare_job_li, sub_case_list):
    sub_case_name = func_result.sub_case_name
    result = FUNC_CASE_RESULT_TYPE_MAP.get(func_result.sub_case_result)
    sub_case_result = {
        'sub_case_name': sub_case_name,
        'result': result,
        'compare_data': get_func_compare_data(suite, conf, sub_case_name, compare_job_li),
    }
    sub_case_list.append(sub_case_result)


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
