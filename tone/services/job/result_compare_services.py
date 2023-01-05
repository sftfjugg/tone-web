# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import copy
import json

from datetime import datetime
from itertools import chain
from django.db.models import Q, Count

from tone.core.utils.common_utils import query_all_dict
from tone.models import TestJob, PerfResult, TestJobCase, TestSuite, TestCase, FuncBaselineDetail, PerfBaselineDetail, \
    CompareForm, FuncResult, Project, BaseConfig, Product, \
    TestJobSuite, User, Baseline
from tone.core.common.job_result_helper import get_suite_conf_metric, get_suite_conf_sub_case, \
    get_metric_list, get_suite_conf_metric_v1, get_suite_conf_sub_case_v1
from tone.core.common.services import CommonService
from tone.services.job.test_services import JobTestService
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import AnalysisException
from tone.core.handle.report_handle import get_server_info


class CompareSuiteInfoService(CommonService):

    def filter(self, data):
        func_suite_dic, perf_suite_dic = dict(), dict()
        func_data = data.get('func_data')
        perf_data = data.get('perf_data')
        self.pack_suite_dic(func_data, func_suite_dic, 1)
        self.pack_suite_dic(perf_data, perf_suite_dic, 0)
        res_data = {
            'func_suite_dic': func_suite_dic,
            'perf_suite_dic': perf_suite_dic,
        }
        return res_data

    def pack_suite_dic(self, data, data_dic, is_func):
        base_obj_li = data.get('base_job')
        if len(base_obj_li) == 0:
            return
        is_baseline = data.get('is_baseline', 0)
        base_id_list = ','.join(str(e) for e in base_obj_li)
        uniq_id = 'baseline_id' if is_baseline else 'job_id'
        if is_baseline:
            detail_table = 'func_baseline_detail' if is_func else 'perf_baseline_detail'
            raw_sql = 'SELECT a.test_suite_id,a.baseline_id, b.name AS test_suite_name ' \
                      'FROM ' + detail_table + ' a LEFT JOIN test_suite b ON a.test_suite_id = b.id ' \
                      'WHERE a.is_deleted=0 and b.is_deleted=0 and a.baseline_id IN (' + \
                      base_id_list + ')'
        else:
            raw_sql = 'SELECT a.test_suite_id,a.job_id, b.name AS test_suite_name ' \
                      'FROM test_job_case a LEFT JOIN test_suite b ON a.test_suite_id = b.id ' \
                      'WHERE a.is_deleted=0 and b.is_deleted=0 and a.job_id IN (' + \
                      base_id_list + ')'
        all_test_suites = query_all_dict(raw_sql.replace('\'', ''), params=None)
        for test_suite in all_test_suites:
            if test_suite['test_suite_id'] not in data_dic:
                data_dic[test_suite['test_suite_id']] = {
                    'suite_name': test_suite['test_suite_name'],
                    'suite_id': test_suite['test_suite_id'],
                    'test_job_id': [test_suite[uniq_id]],
                    'is_baseline': is_baseline
                }
            else:
                if test_suite[uniq_id] not in data_dic[test_suite['test_suite_id']]['test_job_id']:
                    data_dic[test_suite['test_suite_id']]['test_job_id'].append(test_suite[uniq_id])

    def get_red_dot_count(self, func_suite_dic, perf_suite_dic, group_num):
        count_li = [0 for _ in range(group_num)]
        self.calc_red_dot(func_suite_dic, count_li)
        self.calc_red_dot(perf_suite_dic, count_li)
        return {'base_group': count_li[0], 'compare_groups': count_li[1:]}

    @staticmethod
    def calc_red_dot(data, count_li):
        for suite_key, suite_value in data.items():
            for conf_key, conf_value in suite_value.get('conf_dic').items():
                if len(conf_value.get('base_obj_li')) > 1:
                    count_li[0] += 1
                compare_groups = conf_value.get('compare_groups', list())
                for i in range(len(compare_groups)):
                    if len(compare_groups[i]) > 1:
                        count_li[i + 1] += 1

    @staticmethod
    def get_obj(obj_id, is_job):
        obj_data = {'obj_id': obj_id, 'is_job': is_job}
        if is_job:
            test_job = TestJob.objects.get(id=obj_id)
            name = test_job.name
            obj_data['name'] = name
        return obj_data


class CompareConfInfoService(CommonService):
    def filter(self, data):
        suite_id = data.get('suite_id')
        test_job_list = data.get('test_job_id')
        is_baseline = data.get('is_baseline', 0)
        job_id_list = ','.join(str(e) for e in test_job_list)
        test_case_data = dict()
        if is_baseline:
            raw_sql = 'SELECT distinct a.test_case_id,b.name AS conf_name FROM func_baseline_detail a ' \
                      'LEFT JOIN test_case b ON a.test_case_id= b.id WHERE a.is_deleted=0 AND ' \
                      'b.is_deleted=0 and a.test_suite_id=%s AND a.baseline_id IN (' + job_id_list + ') UNION ' \
                      'SELECT distinct a.test_case_id,b.name AS conf_name FROM perf_baseline_detail a ' \
                      'LEFT JOIN test_case b ON a.test_case_id= b.id WHERE a.is_deleted=0 AND ' \
                      'b.is_deleted=0 and a.test_suite_id=%s AND a.baseline_id IN (' + job_id_list + ')'
            all_test_cases = query_all_dict(raw_sql.replace('\'', ''), [suite_id, suite_id])
        else:
            raw_sql = 'SELECT distinct a.test_case_id,b.name AS conf_name FROM test_job_case a ' \
                      'LEFT JOIN test_case b ON a.test_case_id= b.id WHERE a.is_deleted=0 AND ' \
                      'b.is_deleted=0 and a.test_suite_id=%s AND a.job_id IN (' + job_id_list + ')'
            all_test_cases = query_all_dict(raw_sql.replace('\'', ''), [suite_id])
        for job_case in all_test_cases:
            case_id = job_case['test_case_id']
            test_case_data[case_id] = {
                'conf_name': job_case['conf_name'],
                'conf_id': job_case['test_case_id']
            }
        res_data = {
            'conf_dic': test_case_data
        }
        return res_data


class CompareEnvInfoService(CommonService):

    def filter(self, data):
        base_group = data.get('base_group', None)
        compare_groups = data.get('compare_groups', list())
        assert base_group, AnalysisException(ErrorCode.BASE_JOB_NEED)
        env_info = self.get_env_info(base_group, compare_groups)
        return env_info

    def get_env_info(self, base_group, compare_groups):
        job_li = list()
        env_info = {
            'base_group': get_server_info(base_group.get('tag'), base_group.get('base_objs')),
            'compare_groups': [get_server_info(group.get('tag'), group.get('base_objs')) for group in
                               compare_groups],
            'job_li': list(set(job_li))
        }
        count_li = [len(_info.get('server_info')) for _info in env_info.get('compare_groups')]
        count_li.append(len(env_info.get('base_group').get('server_info')))
        count = max(count_li)
        env_info['count'] = count
        return env_info


class CompareListService(CommonService):
    """
    结果对比列表数据
    """

    def get_suite_compare_data(self, data):
        suite_id = data.get('suite_id')
        suite_info = data.get('suite_info')
        test_type = TestSuite.objects.get(id=suite_id).test_type
        if test_type == 'functional':
            result_data = get_suite_conf_sub_case(suite_id, suite_info)
        else:
            result_data = get_suite_conf_metric(suite_id, suite_info)
        result_data = result_data if data.get('show_type', 1) == 1 else self.regroup_data(result_data)
        return result_data

    @staticmethod
    def regroup_data(data):
        res = data['conf_list']
        metric_dic = dict()
        for conf in res:
            for metric in conf['metric_list']:
                res_data = {
                    'conf_name': conf['conf_name'],
                    'conf_id': conf['conf_id'],
                    "test_value": metric['test_value'],
                    "unit": metric['unit'],
                    "direction": metric['direction'],
                    "compare_data": metric['compare_data']
                }
                if metric['metric'] in metric_dic:
                    metric_dic[metric['metric']].append(res_data)
                else:
                    metric_dic[metric['metric']] = [res_data]
        del data['conf_list']
        data['metric_dic'] = metric_dic
        return data

    def get_suite_compare_data_v1(self, data):
        suite_id = data.get('suite_id')
        suite_name = data.get('suite_name')
        base_index = data.get('base_index')
        group_job_list = data.get('group_jobs')
        res_group_job = copy.deepcopy(group_job_list)
        duplicate_data = data.get('duplicate_data')
        if duplicate_data and (type(duplicate_data) is list and len(duplicate_data) > 0):
            for group_job in group_job_list:
                group_job['duplicate_conf'] = list()
                group_job['duplicate_conf']. \
                    extend([d for d in duplicate_data if d['job_id'] in group_job.get('job_list')])
        is_all = data.get('is_all')
        suite_info = data.get('conf_info')
        test_suite = TestSuite.objects.filter(id=suite_id).first()
        if not test_suite:
            return dict()
        test_type = test_suite.test_type
        if test_type == 'functional':
            result_data = \
                get_suite_conf_sub_case_v1(suite_id, suite_name, base_index, group_job_list, suite_info, is_all)
        else:
            result_data = get_suite_conf_metric_v1(suite_id, suite_name, base_index, group_job_list, suite_info, is_all)
        result_data['test_type'] = test_type
        result_data = result_data if data.get('show_type', 1) == 1 else self.regroup_data(result_data)
        result_data['group_jobs'] = res_group_job
        if len(res_group_job) > 0 and len(res_group_job[0]['job_list']) > 0:
            job = TestJob.objects.filter(id=res_group_job[0]['job_list'][0]).first()
            if job:
                result_data['ws_id'] = job.ws_id
        return result_data

    def filter(self, data):
        func_suite_dic = data.get('func_suite_dic')
        perf_suite_dic = data.get('perf_suite_dic')
        perf_data_result = self.get_data_list(perf_suite_dic, 'perf') if perf_suite_dic else None
        func_data_result = self.get_data_list(func_suite_dic, 'func') if func_suite_dic else None
        result_data = {
            'perf_data_result': perf_data_result,
            'func_data_result': func_data_result,
        }
        return result_data

    @staticmethod
    def get_data_list(base_group, test_type):
        suite_list = list()
        function_map = {
            'perf': get_suite_conf_metric,
            'func': get_suite_conf_sub_case,
        }
        if base_group.get('async_request'):
            suite_obj = function_map.get(test_type)(suite_id=base_group['suite_id'],
                                                    suite_value=base_group['suite_info'])
            suite_list.append(suite_obj)
            return suite_list
        else:
            for key, value in base_group.items():
                suite_obj = function_map.get(test_type)(key, value)
                suite_list.append(suite_obj)
            return suite_list


class CompareChartService(CommonService):
    """
    结果对比列表数据
    """

    def filter(self, data):
        base_suite_obj = data.get('base_suite_obj')
        show_type = data.get('show_type')
        assert base_suite_obj, AnalysisException(ErrorCode.BASE_SUITE_OBJ_NEED)
        result_data = self.get_data_list(base_suite_obj, show_type)
        result_data = result_data if data.get('show_type', 1) == 1 else self.regroup_data(result_data)
        return result_data

    @staticmethod
    def get_data_list(base_suite_obj, show_type):
        suite_id = base_suite_obj.get('suite_id')
        suite_name = base_suite_obj.get('suite_name')
        conf_dic = base_suite_obj.get('conf_dic')
        result_data = {
            'suite_id': suite_id,
            'suite_name': suite_name,
            'show_type': show_type,
        }
        conf_list = list()
        for conf_id, conf_value in conf_dic.items():
            job_id = conf_value.get('obj_id') if conf_value.get('is_job') else (FuncBaselineDetail.objects.get_value(
                id=conf_value.get('obj_id')).test_job_id if FuncBaselineDetail.objects.get_value(
                id=conf_value.get('obj_id')) else None)
            perf_results = None
            if not job_id and len(conf_value.get('compare_objs')) > 0:
                test_job = TestJob.objects.filter(id=conf_value.get('compare_objs')[0].get('obj_id')).first()
                if test_job:
                    perf_results = PerfBaselineDetail.objects.filter(baseline_id=test_job.baseline_id,
                                                                     test_suite_id=suite_id, test_case_id=conf_id)
            else:
                perf_results = PerfResult.objects.filter(test_job_id=job_id, test_suite_id=suite_id,
                                                         test_case_id=conf_id)
            if not job_id and len(conf_value.get('compare_objs')) > 0:
                test_job = TestJob.objects.filter(id=conf_value.get('compare_objs')[0].get('obj_id')).first()
                if test_job:
                    perf_results = PerfBaselineDetail.objects.filter(baseline_id=test_job.baseline_id,
                                                                     test_suite_id=suite_id, test_case_id=conf_id)
            else:
                perf_results = PerfResult.objects.filter(test_job_id=job_id, test_suite_id=suite_id,
                                                         test_case_id=conf_id)
            if not perf_results.exists():
                continue
            compare_job_li = [i.get('obj_id') for i in conf_value.get('compare_objs', list()) if i]  # todo 基线后续处理
            compare_count = [{'all': 0, 'increase': 0, 'decline': 0} for _ in
                             range(len(conf_value.get('compare_objs')))]
            conf_obj = {
                'conf_name': conf_value.get('conf_name'),
                'conf_id': conf_id,
                'metric_list': get_metric_list(perf_results, suite_id, conf_id, compare_job_li, compare_count),
            }
            conf_obj['metric_count'] = len(conf_obj['metric_list'])
            if not conf_obj['metric_list']:
                continue
            conf_list.append(conf_obj)
        result_data['conf_list'] = conf_list
        return result_data

    @staticmethod
    def regroup_data(data):
        res = data['conf_list']
        metric_dic = dict()
        for conf in res:
            for metric in conf['metric_list']:
                res_data = {
                    'conf_name': conf['conf_name'],
                    'conf_id': conf['conf_id'],
                    "test_value": metric['test_value'],
                    "unit": metric['unit'],
                    "direction": metric['direction'],
                    "compare_data": metric['compare_data']
                }
                if metric['metric'] in metric_dic:
                    metric_dic[metric['metric']].append(res_data)
                else:
                    metric_dic[metric['metric']] = [res_data]
        del data['conf_list']
        data['metric_dic'] = metric_dic
        return data


class CompareFormService(CommonService):
    """
    结果对比表单数据
    """

    @staticmethod
    def filter(queryset, data):
        if 'form_id' in data and queryset.filter(id=data.get('form_id')).exists():
            form_info = queryset.filter(id=data.get('form_id'))[0].req_form
            if form_info.get('testDataParam'):
                for key_dic in form_info.get('testDataParam').keys():
                    func_dic = form_info.get('testDataParam').get(key_dic)
                    for key in func_dic.keys():
                        if 'suite_id' in func_dic[key]:
                            break
                        else:
                            job_id = 0
                            group_jobs = list()
                            if func_dic[key].get('conf_dic'):
                                for dic_key in func_dic[key].get('conf_dic').keys():
                                    if func_dic[key].get('conf_dic')[dic_key]:
                                        job_id = func_dic[key].get('conf_dic')[dic_key].get('obj_id')
                                        group_jobs.append({'job_list': [job_id], 'is_baseline': 0})
                                        for compare_job in func_dic[key].get('conf_dic')[dic_key].get('compare_objs'):
                                            group_jobs.append(
                                                {'job_list': [compare_job.get('obj_id')], 'is_baseline': 0})
                                        break
                            func_dic[key]['suite_id'] = key
                            func_dic[key]['test_job_id'] = [job_id]
                            func_dic[key]['is_baseline'] = 0
                            func_dic[key]['base_index'] = form_info.get('baselineGroupIndex')
                            func_dic[key]['group_jobs'] = group_jobs
                            func_dic[key]['duplicate_data'] = list()
                            func_dic[key]['is_all'] = 1
            return form_info
        else:
            return dict()

    @staticmethod
    def create(data, operator):
        from hashlib import blake2b
        h = blake2b(digest_size=20)
        form_data = data.get('form_data', dict())
        assert isinstance(form_data, dict), ValueError('form_data must be dict')
        h.update(json.dumps(form_data).encode())
        hash_key = h.hexdigest()
        if CompareForm.objects.filter(hash_key=hash_key).exists():
            obj_id = CompareForm.objects.filter(hash_key=hash_key).first().id
        else:
            CompareFormService.__fetch_job_ids(form_data)
            compare_form_obj = CompareForm.objects.create(
                req_form=form_data,
                hash_key=hash_key,
            )
            obj_id = compare_form_obj.id
        return obj_id, hash_key

    @staticmethod
    def __fetch_job_ids(data):
        job_id_list = list()
        base_id_list = list()
        for group_data in data['allGroupData']:
            if 'members' in group_data:
                if group_data.get('type', 'job') == 'job':
                    job_id_list.extend(group_data.get('members'))
                else:
                    base_id_list.extend(group_data.get('members'))
        result = CompareFormService.__get_job_infos(job_id_list, 'job')
        base_result = CompareFormService.__get_job_infos(base_id_list, 'baseline')
        for group_data in data['allGroupData']:
            member_list = list()
            if 'members' not in group_data:
                group_data['members'] = member_list
                continue
            for job_id in group_data.get('members'):
                if group_data.get('type', 'job') == 'job':
                    if job_id in result.keys():
                        member_list.append(result[job_id])
                else:
                    if job_id in base_result.keys():
                        member_list.append(base_result[job_id])
            group_data['members'] = member_list

    @staticmethod
    def __get_job_infos(ids, job_type):
        job_dict = dict()
        if not ids:
            return job_dict
        test_type_map = {
            'functional': '功能测试',
            'performance': '性能测试',
            'business': '业务测试',
            'stability': '稳定性测试'
        }
        name_list, project_list, product_list = list(), list(), list()
        if job_type == 'job':
            jobs = TestJob.objects.filter(id__in=ids)
        else:
            jobs = Baseline.objects.filter(id__in=ids)
        for job in jobs:
            name_list.append(job.creator)
            if job_type == 'job':
                project_list.append(job.project_id)
                product_list.append(job.product_id)
        create_name_map = CompareFormService.__get_objects_name_map(User, name_list)
        project_name_map = CompareFormService.__get_objects_name_map(Project, project_list)
        product_name_map = CompareFormService.__get_objects_name_map(Product, product_list)
        for job in jobs:
            job_data = job.to_dict()
            func_view_config = BaseConfig.objects.filter(config_type='ws', ws_id=job_data.get('ws_id'),
                                                         config_key='FUNC_RESULT_VIEW_TYPE').first()
            if job_type == 'job':
                job_data.update({
                    'state': JobTestService().get_job_state(job.id, job.test_type, job.state, func_view_config),
                    'test_type': test_type_map.get(job.test_type),
                    'creator_name': create_name_map[job.creator],
                    'start_time': datetime.strftime(job.start_time, "%Y-%m-%d %H:%M:%S") if job.start_time else None,
                    'end_time': datetime.strftime(job.end_time, "%Y-%m-%d %H:%M:%S") if job.end_time else None,
                    'gmt_created': datetime.strftime(job.gmt_created, "%Y-%m-%d %H:%M:%S") if job.gmt_created else None,
                    'project_name': project_name_map[job.project_id],
                    'product_name': product_name_map[job.product_id],
                    'server': JobTestService().get_job_server(job.server_provider, job.id)
                })
            else:
                job_data.update({
                    'test_type': test_type_map.get(job.test_type),
                    'creator_name': create_name_map.get(job.creator, None),
                    'gmt_created': datetime.strftime(job.gmt_created, "%Y-%m-%d %H:%M:%S") if job.gmt_created else None
                })
            job_dict[job.id] = job_data
        return job_dict

    @staticmethod
    def __get_objects_name_map(target_model, ids):
        target_dict = dict()
        targets = target_model.objects.filter(id__in=ids)
        for target in targets:
            if target_model == User:
                target_dict[target.id] = target.first_name if target.first_name else target.last_name
            else:
                target_dict[target.id] = target.name
        return target_dict


class CompareDuplicateService(CommonService):
    def get(self, data):
        base_index = data.get('base_index', 0)
        suite_list = data.get('suite_list')
        group_jobs = data.get('group_jobs')
        job_id_list = list()
        base_id_list = list()
        for group in group_jobs:
            group['suite_list'] = list()
            if group.get('is_baseline', 0):
                base_id_list.extend(group.get('test_job_id'))
            else:
                job_id_list.extend(group.get('test_job_id'))
        conf_list = list()
        suite_id_list = list()
        job_index = 0
        compare_job_list = list()
        compare_base_list = list()
        for group in group_jobs:
            if job_index != base_index:
                if group.get('is_baseline', 0):
                    compare_base_list.extend(group.get('test_job_id'))
                else:
                    compare_job_list.extend(group.get('test_job_id'))
            job_index += 1
        compare_suite_list = TestJobSuite.objects.filter(job_id__in=compare_job_list). \
            values_list('test_suite_id', flat=True).distinct()
        for compare_suite in compare_suite_list:
            suite_list.append(dict({
                "suite_id": compare_suite,
                "is_all": 1
            }))
        if len(compare_base_list) > 0:
            compare_base_func_suite_list = FuncBaselineDetail.objects.filter(baseline_id__in=compare_base_list). \
                values_list('test_suite_id', flat=True).distinct()
            for compare_suite in compare_base_func_suite_list:
                suite_list.append(dict({
                    "suite_id": compare_suite,
                    "is_all": 1
                }))
            compare_base_perf_suite_list = PerfBaselineDetail.objects.filter(baseline_id__in=compare_base_list). \
                values_list('test_suite_id', flat=True).distinct()
            for compare_suite in compare_base_perf_suite_list:
                suite_list.append(dict({
                    "suite_id": compare_suite,
                    "is_all": 1
                }))
        if not suite_list or len(suite_list) == 0:
            return dict()
        for suite_info in suite_list:
            if not suite_info.get('is_all'):
                conf_list.extend(suite_info['conf_list'])
            else:
                suite_id_list.append(suite_info['suite_id'])
        test_suite = TestSuite.objects.filter(id=suite_list[0]['suite_id']).first()
        if not test_suite:
            return dict()
        test_type = test_suite.test_type
        model_result = FuncResult
        model_table = 'func_result'
        base_result = FuncBaselineDetail
        base_table = 'func_baseline_detail'
        if test_type == 'performance':
            model_result = PerfResult
            model_table = 'perf_result'
            base_result = PerfBaselineDetail
            base_table = 'perf_baseline_detail'
        q = Q(test_job_id__in=job_id_list)
        base_q = Q(baseline_id__in=base_id_list)
        if len(suite_id_list) > 0:
            q &= Q(test_suite_id__in=suite_id_list)
            if len(base_id_list) > 0:
                base_q &= Q(test_suite_id__in=suite_id_list)
        if len(conf_list) > 0:
            q &= Q(test_case_id__in=conf_list)
            if len(base_id_list) > 0:
                base_q &= Q(test_case_id__in=suite_id_list)
        if len(conf_list) == 0 and len(suite_id_list) == 0:
            job_case_list = list()
            duplicate_case_id_list = list()
            base_case_list = list()
        else:
            job_case_list = model_result.objects.filter(q).values_list('test_job_id', 'test_suite_id',
                                                                       'test_case_id').distinct()
            duplicate_case_id_list = model_result.objects.filter(q). \
                extra(select={'test_suite_name': 'test_suite.name',
                              'test_case_name': 'test_case.name'},
                      tables=['test_suite', 'test_case'],
                      where=["test_suite.id = " + model_table + ".test_suite_id",
                             "test_case.id = " + model_table + ".test_case_id"]). \
                values_list('test_suite_id', 'test_case_id', 'test_suite_name', 'test_case_name'). \
                annotate(dcount=Count('test_case_id')).filter(dcount__gt=1)
            if len(base_id_list) > 0:
                base_case_list = base_result.objects.filter(base_q).values_list('baseline_id', 'test_suite_id',
                                                                                'test_case_id').distinct()
                job_case_list = chain(job_case_list, base_case_list)
                duplicate_base_case_id_list = base_result.objects.filter(base_q). \
                    extra(select={'test_suite_name': 'test_suite.name',
                                  'test_case_name': 'test_case.name'},
                          tables=['test_suite', 'test_case'],
                          where=["test_suite.id = " + base_table + ".test_suite_id",
                                 "test_case.id = " + base_table + ".test_case_id"]). \
                    values_list('test_suite_id', 'test_case_id', 'test_suite_name', 'test_case_name'). \
                    annotate(dcount=Count('test_case_id')).filter(dcount__gt=1)
                if len(duplicate_base_case_id_list) > 0:
                    duplicate_case_id_list = chain(duplicate_case_id_list, duplicate_base_case_id_list)
        job_list = TestJob.objects.filter(id__in=job_id_list). \
            extra(select={'user_name': 'user.username'},
                  tables=['user'],
                  where=["user.id = test_job.creator"])
        job_list_obj = dict()
        for test_job in job_list:
            job_res = dict(
                job_id=test_job.id,
                job_name=test_job.name,
                create_user=test_job.user_name
            )
            job_list_obj[test_job.id] = job_res
        base_list_obj = dict()
        if len(base_id_list) > 0:
            base_list = Baseline.objects.filter(id__in=base_id_list). \
                extra(select={'user_name': 'user.username'},
                      tables=['user'],
                      where=["user.id = baseline.creator"])
            for baseline in base_list:
                base_res = dict(
                    job_id=baseline.id,
                    job_name=baseline.name,
                    create_user=baseline.user_name
                )
                base_list_obj[baseline.id] = base_res
        for duplicate_data in duplicate_case_id_list:
            test_suite_id = duplicate_data[0]
            test_case_id = duplicate_data[1]
            test_suite_name = duplicate_data[2]
            test_case_name = duplicate_data[3]
            suite_job_id_list = list()
            [suite_job_id_list.append(job_case[0]) for job_case in job_case_list
             if job_case[1] == test_suite_id and job_case[2] == test_case_id and
             job_case[0] not in suite_job_id_list]
            groups = [g for g in group_jobs if len(self.get_sub_list(suite_job_id_list, g['test_job_id'])) > 1]
            if len(groups) == 0:
                continue
            for group in groups:
                suite_res_job_id_list = [job_id for job_id in group['test_job_id'] if job_id in suite_job_id_list]
                suite_res_list = group['suite_list']
                job_res_list = list()
                if group.get('is_baseline', 0):
                    for job_id in suite_res_job_id_list:
                        job_info = base_list_obj.get(job_id)
                        if job_info:
                            job_res_list.append(job_info)
                else:
                    for job_id in suite_res_job_id_list:
                        job_info = job_list_obj.get(job_id)
                        if job_info:
                            job_res_list.append(job_info)
                suite_res_li = [s for s in suite_res_list if s['suite_id'] == test_suite_id]
                conf_info = dict()
                conf_info['conf_id'] = test_case_id
                conf_info['conf_name'] = test_case_name
                conf_info['job_list'] = job_res_list
                suite_res = dict()
                if len(suite_res_li) > 0:
                    suite_res = suite_res_li[0]
                    suite_res['conf_list'].append(conf_info)
                else:
                    suite_res['suite_id'] = test_suite_id
                    suite_res['suite_name'] = test_suite_name
                    conf_list = list()
                    conf_list.append(conf_info)
                    suite_res['conf_list'] = conf_list
                    suite_res_list.append(suite_res)
        for group in group_jobs:
            duplicate_count = 0
            for suite_res in group['suite_list']:
                duplicate_count += len(suite_res['conf_list'])
            group['desc'] = '注：%s个conf有重复job数据' % duplicate_count
            del group['test_job_id']
        return {'duplicate_data': group_jobs}

    def get_sub_list(self, source, dest):
        res = list()
        for m in source:
            for n in dest:
                if n == m:
                    res.append(n)
        return res


class CompareSuiteInfoOldService(CommonService):

    def filter(self, data):
        func_suite_dic, perf_suite_dic = dict(), dict()
        func_data = data.get('func_data', list())
        perf_data = data.get('perf_data', list())
        self.pack_suite_dic(func_data, func_suite_dic, 'func')
        self.pack_suite_dic(perf_data, perf_suite_dic, 'perf')
        res_data = {
            'func_suite_dic': func_suite_dic,
            'perf_suite_dic': perf_suite_dic,
        }
        return res_data

    def pack_suite_dic(self, data, data_dic, test_type):
        base_obj_li = data.get('base_obj_li', list())
        compare_groups = data.get('compare_groups', list())
        self.package_base_data(base_obj_li, data_dic, test_type)
        self.package_compare_data(compare_groups, data_dic, test_type)

    def package_base_data(self, base_obj_li, data_dic, test_type):
        for base_obj in base_obj_li:
            obj_id = base_obj.get('obj_id')
            is_job = base_obj.get('is_job')
            test_job_data = dict()
            if is_job:
                job_cases = TestJobCase.objects.filter(job_id=obj_id)
                test_job = TestJob.objects.get(id=obj_id)
                test_job_data['name'] = test_job.name
                test_job_data['is_job'] = is_job
                test_job_data['obj_id'] = obj_id
            else:
                job_cases = FuncBaselineDetail.objects.filter(
                    baseline_id=obj_id) if test_type == 'func' else PerfBaselineDetail.objects.filter(
                    baseline_id=obj_id)
            all_test_suites = list(TestSuite.objects.values_list('id', 'name'))
            all_test_cases = list(TestCase.objects.values_list('id', 'name'))
            for job_case in job_cases:
                suite_id = job_case.test_suite_id
                case_id = job_case.test_case_id
                for temp_test_suite in all_test_suites:
                    if temp_test_suite[0] == suite_id:
                        cur_test_suite = temp_test_suite
                        break
                else:
                    continue

                for temp_test_case in all_test_cases:
                    if temp_test_case[0] == case_id:
                        cur_test_case = temp_test_case
                        break
                else:
                    continue

                if suite_id in data_dic:
                    if case_id in data_dic[suite_id]['conf_dic']:
                        data_dic[suite_id]['conf_dic'][case_id]['base_obj_li'].append(test_job_data)
                    else:
                        data_dic[suite_id]['conf_dic'][case_id] = {
                            'conf_name': cur_test_case[1],
                            'conf_id': cur_test_case[0],
                            'is_job': is_job,
                            'base_obj_li': [test_job_data],
                            'obj_id': obj_id if is_job else job_case.id,
                            'compare_groups': list(),
                        }
                else:
                    data_dic[suite_id] = {
                        'suite_name': cur_test_suite[1],
                        'suite_id': cur_test_suite[0],
                        'conf_dic': {
                            case_id: {
                                'conf_name': cur_test_case[1],
                                'conf_id': cur_test_case[0],
                                'base_obj_li': [test_job_data],
                                'compare_groups': list(),
                            }
                        }
                    }

    def package_compare_data(self, compare_groups, data_dic, test_type):
        for compare_group in compare_groups:
            self._package_compare_data(data_dic, test_type, compare_group)

    def _package_compare_data(self, data_dic, test_type, compare_group):
        compare_obj_li = list()
        job_obj_dict = dict()
        for compare_obj in compare_group:
            obj_id = compare_obj.get('obj_id')
            is_job = compare_obj.get('is_job')
            if obj_id not in job_obj_dict:
                job_data = self.get_obj(obj_id, is_job)
                job_obj_dict.setdefault(obj_id, job_data)
            else:
                job_data = job_obj_dict.get(obj_id)
            if is_job:
                compare_obj_li.append(job_data)
            else:
                pass
        for suite_key, suite_value in data_dic.items():
            for conf_key, conf_value in suite_value.get('conf_dic', dict()).items():
                conf_value.get('compare_groups', list()).append(compare_obj_li)

    def get_red_dot_count(self, func_suite_dic, perf_suite_dic, group_num):
        count_li = [0 for _ in range(group_num)]
        self.calc_red_dot(func_suite_dic, count_li)
        self.calc_red_dot(perf_suite_dic, count_li)
        return {'base_group': count_li[0], 'compare_groups': count_li[1:]}

    @staticmethod
    def calc_red_dot(data, count_li):
        for suite_key, suite_value in data.items():
            for conf_key, conf_value in suite_value.get('conf_dic').items():
                if len(conf_value.get('base_obj_li')) > 1:
                    count_li[0] += 1
                compare_groups = conf_value.get('compare_groups', list())
                for i in range(len(compare_groups)):
                    if len(compare_groups[i]) > 1:
                        count_li[i + 1] += 1

    @staticmethod
    def get_obj(obj_id, is_job):
        obj_data = {'obj_id': obj_id, 'is_job': is_job}
        if is_job:
            test_job = TestJob.objects.get(id=obj_id)
            name = test_job.name
            creator = User.objects.get(id=test_job.creator)
            creator_name = creator.first_name if creator.first_name else creator.last_name
            obj_data['name'] = name
            obj_data['creator'] = creator_name
        return obj_data


class CompareListOldService(CommonService):

    def filter(self, data):
        func_suite_dic = data.get('func_suite_dic')
        perf_suite_dic = data.get('perf_suite_dic')
        perf_data_result = self.get_data_list(perf_suite_dic, 'perf') if perf_suite_dic else None
        func_data_result = self.get_data_list(func_suite_dic, 'func') if func_suite_dic else None
        result_data = {
            'perf_data_result': perf_data_result,
            'func_data_result': func_data_result,
        }
        return result_data

    @staticmethod
    def get_data_list(base_group, test_type):
        suite_list = list()
        function_map = {
            'perf': get_suite_conf_metric,
            'func': get_suite_conf_sub_case,
        }
        if base_group.get('async_request'):
            suite_obj = function_map.get(test_type)(suite_id=base_group['suite_id'],
                                                    suite_value=base_group['suite_info'])
            suite_list.append(suite_obj)
            return suite_list
        else:
            for key, value in base_group.items():
                suite_obj = function_map.get(test_type)(key, value)
                suite_list.append(suite_obj)
            return suite_list
