# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import json

from django.db.models import Q

from tone.core.utils.tone_thread import ToneThread
from tone.models import TestJob, PerfResult, TestJobCase, TestSuite, TestCase, FuncBaselineDetail, PerfBaselineDetail, \
    TestServerSnapshot, CloudServerSnapshot, User, CompareForm
from tone.core.common.job_result_helper import get_suite_conf_metric, get_suite_conf_sub_case, \
    get_metric_list
from tone.core.common.services import CommonService
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import AnalysisException


class CompareSuiteInfoService(CommonService):

    def filter(self, data):
        func_suite_dic, perf_suite_dic = dict(), dict()
        func_data = data.get('func_data', list())
        perf_data = data.get('perf_data', list())
        group_num = int(data.get('group_num', 0))
        self.pack_suite_dic(func_data, func_suite_dic, 'func')
        self.pack_suite_dic(perf_data, perf_suite_dic, 'perf')
        res_data = {
            'func_suite_dic': func_suite_dic,
            'perf_suite_dic': perf_suite_dic,
            'red_dot_count': self.get_red_dot_count(func_suite_dic, perf_suite_dic, group_num),
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
            case_id_list = TestJobCase.objects.filter(job_id=obj_id).values_list('test_case_id', flat=True)
            all_test_cases = list(TestCase.objects.filter(id__in=case_id_list).values_list('id', 'name'))
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
            'base_group': self.get_server_info(base_group.get('tag'), base_group.get('base_objs'), job_li),
            'compare_groups': [self.get_server_info(group.get('tag'), group.get('base_objs'), job_li) for group in
                               compare_groups],
            'job_li': list(set(job_li))
        }
        count_li = [len(_info.get('server_info')) for _info in env_info.get('compare_groups')]
        count_li.append(len(env_info.get('base_group').get('server_info')))
        count = max(count_li)
        env_info['count'] = count
        return env_info

    def get_server_info(self, tag, objs, job_li):  # nq  c901
        server_li = list()
        ip_li = list()
        for obj in objs:
            is_job = obj.get('is_job')
            obj_id = obj.get('obj_id')
            if is_job:
                job = TestJob.objects.get_value(id=obj_id)
                job_li.append(obj_id)
                self.package_li(server_li, ip_li, job)
            else:
                baselines = FuncBaselineDetail.objects.filter(baseline_id=obj_id) if obj.get(
                    'baseline_type') == 'func' else PerfBaselineDetail.objects.filter(baseline_id=obj_id)
                for baseline in baselines:
                    job = TestJob.objects.get_value(id=baseline.test_job_id)
                    self.package_li(server_li, ip_li, job)
        env_info = {
            'tag': tag,
            'server_info': server_li,
            'is_job': objs[0].get('is_job') if objs else None
        }
        return env_info

    @staticmethod
    def package_li(server_li, ip_li, job):
        snap_shot_objs = TestServerSnapshot.objects.filter(
            job_id=job.id) if job.server_provider == 'aligroup' else CloudServerSnapshot.objects.filter(job_id=job.id)
        for snap_shot_obj in snap_shot_objs:
            ip = snap_shot_obj.ip if job.server_provider == 'aligroup' else snap_shot_obj.private_ip
            if ip not in ip_li:
                if not (snap_shot_obj.distro or snap_shot_obj.rpm_list or snap_shot_obj.gcc):
                    continue
                server_li.append({
                    'ip/sn': ip,
                    'distro': snap_shot_obj.sm_name if job.server_provider == 'aligroup' else
                    snap_shot_obj.instance_type,
                    'os': snap_shot_obj.distro,
                    'rpm': snap_shot_obj.rpm_list.split('\n') if snap_shot_obj.rpm_list else list(),
                    'kernel': snap_shot_obj.kernel_version,
                    'gcc': snap_shot_obj.gcc,
                })
                ip_li.append(ip)


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
            job_id = conf_value.get('obj_id') if conf_value.get('is_job') else FuncBaselineDetail.objects.get_value(
                id=conf_value.get('obj_id')).test_job_id
            perf_results = PerfResult.objects.filter(test_job_id=job_id, test_suite_id=suite_id, test_case_id=conf_id)
            if not perf_results.exists():
                continue
            compare_job_li = [i.get('obj_id') for i in conf_value.get('compare_objs', list()) if i]
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
        q = Q()
        q &= Q(id=data.get('form_id')) if data.get('form_id') else q
        return queryset.filter(q)

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
            compare_form_obj = CompareForm.objects.create(
                req_form=form_data,
                hash_key=hash_key,
            )
            obj_id = compare_form_obj.id
        return obj_id, hash_key
