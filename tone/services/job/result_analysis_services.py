# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import json
from datetime import datetime

from django.db import connection
from django.db.models import Q

from tone.models import FuncResult, TestJob, JobTagRelation, User, TestJobCase, PerfResult, JobTag, \
    Project
from tone.core.common.constant import FUNC_CASE_RESULT_TYPE_MAP
from tone.core.common.job_result_helper import get_job_case_run_server, date_add
from tone.core.common.services import CommonService
from tone.core.common.constant import ANALYSIS_SQL_MAP
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import AnalysisException


class PerfAnalysisService(CommonService):

    @staticmethod
    def get_metric(data):
        test_suite = data.get('test_suite_id', None)
        test_case = data.get('test_case_id', None)
        project_id = data.get('project_id')
        if not project_id:
            assert project_id, AnalysisException(ErrorCode.PROJECT_ID_NEED)
        test_job = TestJob.objects.filter(project_id=project_id)
        if test_job:
            test_job_id = test_job.last().id
            perf_res = PerfResult.objects.filter(test_suite_id=test_suite, test_case_id=test_case,
                                                 test_job_id=test_job_id).last()
            if not perf_res:
                return None
            metrics = PerfResult.objects.filter(test_job_id=perf_res.test_job_id, test_suite_id=test_suite,
                                                test_case_id=test_case).values_list('metric', flat=True)
            metric_list = sorted(list(set(metrics)))
            return metric_list

    def filter(self, data):
        metric_map = dict()
        project = data.get('project_id', None)
        test_suite = data.get('test_suite_id', None)
        test_case = data.get('test_case_id', None)
        metrics = data.get('metric', None)
        start_time = data.get('start_time', None)
        end_time = data.get('end_time', None)
        provider_env = data.get('provider_env', 'aligroup')
        tag = data.get('tag', None)
        assert project, AnalysisException(ErrorCode.PROJECT_ID_NEED)
        assert test_suite, AnalysisException(ErrorCode.TEST_SUITE_NEED)
        assert test_case, AnalysisException(ErrorCode.TEST_CASE_NEED)
        assert metrics, AnalysisException(ErrorCode.METRIC_NEED)
        assert start_time, AnalysisException(ErrorCode.START_TIME_NEED)
        assert end_time, AnalysisException(ErrorCode.END_TIME_NEED)
        end_time = date_add(end_time, 1)
        job_list = []
        with connection.cursor() as cursor:
            sql = self.get_sql(provider_env, tag)
            for metric in metrics:
                cursor.execute(
                    sql.format(project=project, test_suite=test_suite, test_case=test_case, metric=metric,
                               start_time=datetime.strptime(start_time, '%Y-%m-%d'),
                               end_time=datetime.strptime(end_time, '%Y-%m-%d'), tag=tag, provider_env=provider_env))
                rows = cursor.fetchall()
                if rows:
                    metric_data = self.get_metric_data(rows, provider_env)
                    result_data = self.get_result_data(metric_data, provider_env, start_time, end_time)
                    job_list = self.get_job_list(result_data, provider_env)
                    baseline_data = self.get_baseline_data(test_suite, test_case, metric, job_list)
                    metric_map[metric] = {
                        'result_data': result_data,
                        'baseline_data': baseline_data
                    }
                else:
                    metric_map[metric] = {
                        'result_data': {},
                        'baseline_data': {'value': '', 'cv_value': ''}
                    }
        res_data = {
            'job_list': job_list,
            'metric_map': metric_map
        }
        return res_data

    @staticmethod
    def get_baseline_data(test_suite, test_case, metric, job_list):
        baseline_data = {
            'value': None,
            'cv_value': None,
        }
        if job_list:
            job = job_list[0]
            perf_results = PerfResult.objects.filter(test_job_id=job.get('job_id'), test_suite_id=test_suite,
                                                     test_case_id=test_case, metric=metric)
            if perf_results.exists():
                perf_result = perf_results.first()
                baseline_data['value'] = perf_result.baseline_value
                baseline_data['cv_value'] = perf_result.baseline_cv_value
        return baseline_data

    # @staticmethod
    # def get_baseline_id(job_list, test_suite, test_case, metric):
    #     if not job_list:
    #         return None
    #     job = job_list[0]
    #     perf_results = PerfResult.objects.filter(test_job_id=job.get('job_id'), test_suite_id=test_suite,
    #                                              test_case_id=test_case, metric=metric)
    #     if perf_results.exists():
    #         perf_result = perf_results.first()
    #         return perf_result.compare_baseline if perf_result.compare_baseline != 0 else None
    #     else:
    #         return None

    @staticmethod
    def get_result_data(metric_data, provider_env, start_time, end_time):
        pack_data = dict()
        result_data = dict()
        if provider_env == 'aligroup':
            for data in metric_data:
                if data['server'] in pack_data:
                    pack_data[data['server']].append(data)
                else:
                    pack_data[data['server']] = [data]
            for key, value in pack_data.items():
                data_map = get_data_map(start_time, end_time)
                for _value in value:
                    if not data_map[_value['start_time'].split(' ')[0]] or \
                            data_map[_value['start_time'].split(' ')[0]].get('start_time') <= _value['start_time']:
                        data_map[_value['start_time'].split(' ')[0]] = _value
                result_data[key] = data_map
        else:
            data_map = get_data_map(start_time, end_time)
            for data in metric_data:
                if not data_map[data['start_time'].split(' ')[0]] or \
                        data_map[data['start_time'].split(' ')[0]].get('start_time') <= data['start_time']:
                    data_map[data['start_time'].split(' ')[0]] = data
                # if not (data['start_time'].split(' ')[0] in result_data and
                #         result_data[data['start_time'].split(' ')[0]]['start_time'] <= data['start_time']):
                #     result_data[data['start_time'].split(' ')[0]] = data
            result_data = data_map
        return result_data

    @staticmethod
    def get_metric_data(rows, provider_env):
        metric_data = list()
        if provider_env == 'aligroup':
            for row in rows:
                metric_data.append(
                    {
                        'job_id': row[0],
                        'job_name': row[1],
                        'start_time': datetime.strftime(row[2], "%Y-%m-%d %H:%M:%S"),
                        'end_time': datetime.strftime(row[3], "%Y-%m-%d %H:%M:%S"),
                        'commit_id': json.loads(row[4]).get('commit_id', None),
                        'creator': row[5] or row[6],
                        'server': row[7],
                        'value': row[8],
                        'cv_value': row[9],
                        'note': row[10],
                        'result_obj_id': row[11],
                    }
                )
        else:
            for row in rows:
                metric_data.append(
                    {
                        'job_id': row[0],
                        'job_name': row[1],
                        'start_time': datetime.strftime(row[2], "%Y-%m-%d %H:%M:%S"),
                        'end_time': datetime.strftime(row[3], "%Y-%m-%d %H:%M:%S"),
                        'commit_id': json.loads(row[4]).get('commit_id', None),
                        'creator': row[5] or row[6],
                        'server': row[7],
                        'value': row[8],
                        'cv_value': row[9],
                        'note': row[10],
                        'result_obj_id': row[11],
                        'instance_type': row[12],
                        'image': row[13],
                        'bandwidth': row[14],
                        'run_mode': row[15],
                    }
                )
        return metric_data

    @staticmethod
    def get_sql(provider_env, tag):
        if provider_env == 'aligroup' and tag:
            sql = ANALYSIS_SQL_MAP.get('group_perf_tag')
        elif provider_env == 'aliyun' and tag:
            sql = ANALYSIS_SQL_MAP.get('group_perf_aliyun_tag')
        elif provider_env == 'aliyun':
            sql = ANALYSIS_SQL_MAP.get('group_perf_aliyun')
        else:
            sql = ANALYSIS_SQL_MAP.get('group_perf')
        return sql

    @staticmethod
    def get_job_list(result_data, provider_env):
        job_id_list = list()
        job_list = list()
        if provider_env == 'aligroup':
            for value in result_data.values():
                for _value in value.values():
                    if _value and _value.get('job_id') not in job_id_list:
                        job_list.append({
                            'job_id': _value.get('job_id'),
                            'job_name': _value.get('job_name'),
                            'start_time': _value.get('start_time'),
                            'end_time': _value.get('end_time'),
                            'commit_id': _value.get('commit_id'),
                            'creator': _value.get('creator'),
                            'server': _value.get('server'),
                            'value': _value.get('value'),
                            'cv_value': _value.get('cv_value'),
                            'note': _value.get('note'),
                            'result_obj_id': _value.get('result_obj_id'),
                        })
                        job_id_list.append(_value.get('job_id'))
        else:
            for value in result_data.values():
                if value and value.get('job_id') not in job_id_list:
                    job_list.append({
                        'job_id': value.get('job_id'),
                        'job_name': value.get('job_name'),
                        'start_time': value.get('start_time'),
                        'end_time': value.get('end_time'),
                        'commit_id': value.get('commit_id'),
                        'creator': value.get('creator'),
                        'server': value.get('server'),
                        'value': value.get('value'),
                        'cv_value': value.get('cv_value'),
                        'note': value.get('note'),
                        'result_obj_id': value.get('result_obj_id'),
                    })
                    job_id_list.append(value.get('job_id'))
        return list(sorted(job_list, key=lambda x: x.get('job_id'), reverse=True))


class FuncAnalysisService(CommonService):

    @staticmethod
    def get_sub_case(data):
        test_suite = data.get('test_suite_id', None)
        test_case = data.get('test_case_id', None)
        fun_res = FuncResult.objects.filter(test_suite_id=test_suite, test_case_id=test_case).last()
        if not fun_res:
            return None
        sub_cases = FuncResult.objects.filter(test_job_id=fun_res.test_job_id, test_suite_id=test_suite,
                                              test_case_id=test_case).values('sub_case_name')
        sub_case_list = sorted(list(set([sub_case['sub_case_name'] for sub_case in sub_cases])))
        return sub_case_list

    def filter(self, data):
        project = data.get('project_id', None)
        test_suite = data.get('test_suite_id', None)
        test_case = data.get('test_case_id', None)
        sub_case_name = data.get('sub_case_name', None)
        start_time = data.get('start_time', None)
        end_time = data.get('end_time', None)
        show_type = data.get('show_type', 'pass_rate')
        tag = data.get('tag', None)
        assert project, AnalysisException(ErrorCode.PROJECT_ID_NEED)
        assert test_suite, AnalysisException(ErrorCode.TEST_SUITE_NEED)
        assert test_case, AnalysisException(ErrorCode.TEST_CASE_NEED)
        assert start_time, AnalysisException(ErrorCode.START_TIME_NEED)
        assert end_time, AnalysisException(ErrorCode.END_TIME_NEED)
        end_time = date_add(end_time, 1)
        func_results_q = Q(
            test_suite_id=test_suite,
            test_case_id=test_case,
            gmt_created__range=(start_time, end_time)
        )
        if show_type != 'pass_rate':
            func_results_q &= Q(sub_case_name=sub_case_name)
        func_job_ids = FuncResult.objects.filter(func_results_q).values_list('test_job_id', flat=True).distinct()
        job_queryset = TestJob.objects.filter(
            id__in=func_job_ids, project_id=project,
            state__in=['success', 'fail']).order_by('-id')
        job_li = list()
        ws_id = Project.objects.get(id=project).ws_id
        analytics_tag_id_set = {JobTag.objects.get(ws_id=ws_id, name='analytics').id}
        if tag:
            analytics_tag_id_set.add(tag)
        job_tag_list = JobTagRelation.objects.all()
        for job in job_queryset:
            job_tag_relation_ids = set()
            for job_tag in job_tag_list:
                if job_tag.job_id == job.id:
                    job_tag_relation_ids.add(job_tag.tag_id)
            if analytics_tag_id_set.issubset(job_tag_relation_ids):
                job_li.append(job)
        sub_case_map = self.get_sub_case_map(job_li, start_time, end_time)
        res_data = self.get_res_data(sub_case_map, test_suite, test_case, sub_case_name, show_type)
        return res_data

    @staticmethod
    def get_sub_case_map(queryset, start_time, end_time):
        sub_case_map = get_data_map(start_time, end_time)
        for job in queryset:
            if not sub_case_map[datetime.strftime(job.start_time, "%Y-%m-%d")]:
                get_case_map(sub_case_map, job)
        return sub_case_map

    @staticmethod
    def get_res_data(sub_case_map, test_suite, test_case, sub_case_name, show_type):
        job_list = list()
        case_map = dict()
        if show_type == 'pass_rate':
            for key, value in sub_case_map.items():
                if value:
                    func_queryset = FuncResult.objects.filter(test_job_id=value.get('job_id'), test_suite_id=test_suite,
                                                              test_case_id=test_case)
                    all_case = func_queryset.count()
                    pass_case = func_queryset.filter(sub_case_result=1).count()
                    job_case = TestJobCase.objects.get(job_id=value.get('job_id'), test_suite_id=test_suite,
                                                       test_case_id=test_case)
                    case_map[key] = {**value,
                                     **{'all_case': all_case, 'pass_case': pass_case,
                                        'pass_rate': pass_case / all_case, 'note': job_case.analysis_note}}
                    job_list.append(
                        {**value, **{'server': get_job_case_run_server(job_case.id), 'note': job_case.analysis_note,
                                     'result_obj_id': job_case.id}})
                else:
                    case_map[key] = value
        else:
            assert sub_case_name, AnalysisException(ErrorCode.SUB_CASE_NEED)
            for key, value in sub_case_map.items():
                if value:
                    job_case = TestJobCase.objects.filter(job_id=value.get('job_id'), test_suite_id=test_suite,
                                                          test_case_id=test_case).first()
                    func_result = FuncResult.objects.filter(test_job_id=value.get('job_id'), test_suite_id=test_suite,
                                                            test_case_id=test_case, sub_case_name=sub_case_name).first()
                    job_list.append(
                        {**value, **{'server': get_job_case_run_server(job_case.id), 'note': func_result.note},
                         'result_obj_id': func_result.id})
                    case_map[key] = {**value,
                                     **{'result': FUNC_CASE_RESULT_TYPE_MAP.get(func_result.sub_case_result),
                                        'note': func_result.note}}
                else:
                    case_map[key] = value
        res_data = {
            'job_list': job_list,
            'case_map': case_map,
        }
        return res_data


def get_data_map(start_time, end_time):
    end_time = date_add(end_time, -1)
    data_map = dict()
    while start_time < end_time:
        data_map[start_time] = None
        start_time = date_add(start_time, 1)
    data_map[end_time] = None
    return data_map


def get_case_map(sub_case_map, job):
    _sub_case_map = {
        'job_id': job.id,
        'job_name': job.name,
        'commit_id': job.build_pkg_info.get('commit_id'),
        'start_time': datetime.strftime(job.gmt_created, "%Y-%m-%d %H:%M:%S"),
        'end_time': datetime.strftime(job.gmt_modified, "%Y-%m-%d %H:%M:%S"),
        'creator': User.objects.get(id=job.creator).first_name or User.objects.get(
            id=job.creator).last_name,
    }
    sub_case_map[datetime.strftime(job.gmt_created, "%Y-%m-%d")] = _sub_case_map
