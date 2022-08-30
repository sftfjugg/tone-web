# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import copy
import json
from datetime import datetime
from django.db.models import Q, Count

from tone.core.utils.tone_thread import ToneThread
from tone.models import TestJob, PerfResult, TestJobCase, TestSuite, TestCase, FuncBaselineDetail, PerfBaselineDetail, \
    TestServerSnapshot, CloudServerSnapshot, User, CompareForm, FuncResult, Project, BaseConfig, Product, \
    TestJobSuite
from tone.core.common.job_result_helper import get_suite_conf_metric, get_suite_conf_sub_case, \
    get_metric_list, get_suite_conf_metric_v1, get_suite_conf_sub_case_v1
from tone.core.common.services import CommonService
from tone.services.job.test_services import JobTestService
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import AnalysisException


class CompareSuiteInfoService(CommonService):

    def filter(self, data):
        func_suite_dic, perf_suite_dic = dict(), dict()
        func_data = data.get('func_data')
        perf_data = data.get('perf_data')
        self.pack_suite_dic(func_data, func_suite_dic)
        self.pack_suite_dic(perf_data, perf_suite_dic)
        res_data = {
            'func_suite_dic': func_suite_dic,
            'perf_suite_dic': perf_suite_dic,
        }
        return res_data

    def pack_suite_dic(self, data, data_dic):
        base_obj_li = data.get('base_job')
        self.package_base_data(base_obj_li, data_dic)

    def package_base_data(self, base_obj_li, data_dic):
        all_test_suites = TestJobCase.objects.filter(job_id__in=base_obj_li). \
            extra(select={'test_suite_name': 'test_suite.name'},
                  tables=['test_suite'],
                  where=["test_suite.id = test_job_case.test_suite_id"])
        for test_suite in all_test_suites:
            if test_suite.test_suite_id not in data_dic:
                data_dic[test_suite.test_suite_id] = {
                    'suite_name': test_suite.test_suite_name,
                    'suite_id': test_suite.test_suite_id,
                    'test_job_id': [test_suite.job_id]
                }
            else:
                if test_suite.job_id not in data_dic[test_suite.test_suite_id]['test_job_id']:
                    data_dic[test_suite.test_suite_id]['test_job_id'].append(test_suite.job_id)

    def package_compare_data(self, compare_groups, data_dic, test_type):
        for compare_group in compare_groups:
            self._package_compare_data(data_dic, compare_group)

    def _package_compare_data(self, data_dic, obj_id):
        compare_obj_li = list()
        job_obj_dict = dict()
        if obj_id not in job_obj_dict:
            job_data = self.get_obj(obj_id, 1)
            job_obj_dict.setdefault(obj_id, job_data)
        else:
            job_data = job_obj_dict.get(obj_id)
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


class CompareConfInfoService(CommonService):
    def filter(self, data):
        suite_id = data.get('suite_id')
        test_job_list = data.get('test_job_id')
        res_data = {
            'conf_dic': self.package_conf_data(test_job_list, suite_id)
        }
        return res_data

    def package_conf_data(self, test_job_list, suite_id):
        test_case_data = dict()
        case_id_list = TestJobCase.objects.filter(job_id__in=test_job_list, test_suite_id=suite_id).\
            values_list('test_case_id', flat=True).distinct()
        all_test_cases = list(TestCase.objects.filter(id__in=case_id_list).values_list('id', 'name'))
        for job_case in all_test_cases:
            case_id = job_case[0]
            test_case_data[case_id] = {
                'conf_name': job_case[1],
                'conf_id': job_case[0]
            }
        return test_case_data


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
                    'glibc': snap_shot_obj.glibc,
                    'memory_info': snap_shot_obj.memory_info,
                    'disk': snap_shot_obj.disk,
                    'cpu_info': snap_shot_obj.cpu_info,
                    'ether': snap_shot_obj.ether,
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
        for group_data in data['allGroupData']:
            if 'members' in group_data:
                job_id_list.extend(group_data.get('members'))
        result = CompareFormService.__get_job_infos(job_id_list)
        for group_data in data['allGroupData']:
            member_list = list()
            if 'members' not in group_data:
                group_data['members'] = member_list
                continue
            for job_id in group_data.get('members'):
                member_list.append(result[job_id])
            group_data['members'] = member_list

    @staticmethod
    def __get_job_infos(ids):
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
        jobs = TestJob.objects.filter(id__in=ids)
        fun_result = FuncResult.objects.filter(test_job_id__in=ids)
        test_job_case = TestJobCase.objects.filter(job_id__in=ids)
        # report_obj = ReportObjectRelation.objects.filter(object_id__in=ids)
        test_server_shot = TestServerSnapshot.objects.filter(job_id__in=ids)
        cloud_server_shot = CloudServerSnapshot.objects.filter(job_id__in=ids)
        for job in jobs:
            name_list.append(job.creator)
            project_list.append(job.project_id)
            product_list.append(job.product_id)
        create_name_map = CompareFormService.__get_objects_name_map(User, name_list)
        project_name_map = CompareFormService.__get_objects_name_map(Project, project_list)
        product_name_map = CompareFormService.__get_objects_name_map(Product, product_list)
        for job in jobs:
            job_data = job.to_dict()
            func_view_config = BaseConfig.objects.filter(config_type='ws', ws_id=job_data.get('ws_id'),
                                                         config_key='FUNC_RESULT_VIEW_TYPE').first()
            job_data.update({
                'state': JobTestService().get_job_state(fun_result, test_job_case, job.id, job.test_type, job.state,
                                                        func_view_config),
                'test_type': test_type_map.get(job.test_type),
                'creator_name': create_name_map[job.creator],
                'start_time': datetime.strftime(job.start_time, "%Y-%m-%d %H:%M:%S") if job.start_time else None,
                'end_time': datetime.strftime(job.end_time, "%Y-%m-%d %H:%M:%S") if job.end_time else None,
                'gmt_created': datetime.strftime(job.gmt_created, "%Y-%m-%d %H:%M:%S") if job.gmt_created else None,
                # 'report_li': JobTestService().get_report_li(report_obj, job.id, create_name_map),
                'project_name': project_name_map[job.project_id],
                'product_name': product_name_map[job.product_id],
                'server': JobTestService().get_job_server(test_server_shot, cloud_server_shot, job.server_provider,
                                                          job.id)
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
        for group in group_jobs:
            group['suite_list'] = list()
            job_id_list.extend(group.get('test_job_id'))
        conf_list = list()
        suite_id_list = list()
        job_index = 0
        compare_job_list = list()
        for group in group_jobs:
            if job_index != base_index:
                compare_job_list.extend(group.get('test_job_id'))
            job_index += 1
        compare_suite_list = TestJobSuite.objects.filter(job_id__in=compare_job_list).\
            values_list('test_suite_id', flat=True).distinct()
        for compare_suite in compare_suite_list:
            suite_list.append(dict({
                "suite_id": compare_suite,
                "is_all": 1
            }))
        if len(suite_list) == 0:
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
        if test_type == 'functional':
            pass
        else:
            model_result = PerfResult
            model_table = 'perf_result'
        q = Q(test_job_id__in=job_id_list)
        if len(suite_id_list) > 0:
            q &= Q(test_suite_id__in=suite_id_list)
        if len(conf_list) > 0:
            q &= Q(test_case_id__in=conf_list)
        if len(conf_list) == 0 and len(suite_id_list) == 0:
            job_case_list = list()
            duplicate_case_id_list = list()
        else:
            job_case_list = model_result.objects.filter(q).values_list('test_job_id', 'test_suite_id', 'test_case_id').distinct()
            duplicate_case_id_list = model_result.objects.filter(q). \
                extra(select={'test_suite_name': 'test_suite.name',
                              'test_case_name': 'test_case.name'},
                      tables=['test_suite', 'test_case'],
                      where=["test_suite.id = " + model_table + ".test_suite_id",
                             "test_case.id = " + model_table + ".test_case_id"]). \
                values_list('test_suite_id', 'test_case_id', 'test_suite_name', 'test_case_name'). \
                annotate(dcount=Count('test_case_id')).filter(dcount__gt=1)
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
