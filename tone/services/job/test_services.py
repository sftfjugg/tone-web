# _*_ coding:utf-8 _*_
# flake8: noqa
"""
Module Description:
Date:
Author: Yfh
"""
import json
from datetime import datetime

import yaml
from django.db.models import Q
from django.db import transaction, connection

from tone.core.common.services import CommonService
from tone.core.common.constant import MonitorType
from tone.core.utils.permission_manage import check_operator_permission
from tone.core.utils.verify_tools import check_contains_chinese
from tone.models import TestJob, TestJobCase, TestJobSuite, JobCollection, TestServerSnapshot, CloudServerSnapshot, \
    PerfResult, TestServer, CloudServer, BaseConfig
from tone.models import JobType, User, FuncResult, Baseline, BuildJob, Project, Product, ReportObjectRelation, \
    Report, MonitorInfo, Workspace, TestSuite, TestCase, ServerTag, ReportTemplate, TestCluster, TestStep
from tone.models.sys.config_models import JobTagRelation, JobTag
from tone.core.handle.job_handle import JobDataHandle
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import JobTestException
from tone.serializers.job.test_serializers import get_time
from tone.settings import cp


class JobTestService(CommonService):

    @staticmethod
    def query_display_count(data, filter_queryset, operator):
        ws_id = data.get('ws_id')
        queryset = TestJob.objects.filter(ws_id=ws_id)
        ws_job = queryset.count()
        collection_jobs = JobCollection.objects.filter(user_id=operator)
        collect_job_set = set(collection_jobs.values_list('job_id', flat=True))
        my_job = queryset.filter(creator=operator).count()
        collection_job = queryset.filter(id__in=collect_job_set).count()
        all_job = filter_queryset.count()
        pending_job = filter_queryset.filter(state__in=['pending', 'pending_q']).count()
        running_job = filter_queryset.filter(state='running').count()
        success_job = filter_queryset.filter(state='success').count()
        fail_job = filter_queryset.filter(state='fail').count()
        update_data = {
            'ws_job': ws_job,
            'all_job': all_job,
            'running_job': running_job,
            'pending_job': pending_job,
            'success_job': success_job,
            'fail_job': fail_job,
            'my_job': my_job,
            'collection_job': collection_job,
        }
        return update_data

    @staticmethod
    def check_data_param(data):
        return data

    @staticmethod
    def check_time_fmt(date_dict):
        start_time = '2020-10-23 15:29:08'
        end_time = '2040-10-23 15:29:08'
        res = [start_time, end_time]
        for idx, tmp_time in enumerate(['start_time', 'end_time']):
            try:
                res[idx] = datetime.strptime(date_dict.get(tmp_time), '%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
        return res

    def db_filter_job(self, data, operator):  # noqa: C901
        data = self.check_data_param(data)
        page_num = int(data.get('page_num', 1))
        page_size = int(data.get('page_size', 20))
        res = []
        create_name_map = {}
        project_name_map = {}
        product_name_map = {}
        test_type_map = {
            'functional': '功能测试',
            'performance': '性能测试',
            'business': '业务测试',
            'stability': '稳定性测试'
        }
        collection_jobs = JobCollection.objects.filter(user_id=operator)
        collect_job_set = set(collection_jobs.values_list('job_id', flat=True))
        query_sql = []
        if data.get('tab') == 'my' or data.get('my_job'):
            query_sql.append('AND creator="{}"'.format(operator))
        if data.get('tab') == 'collection' or data.get('collection'):
            if collect_job_set:
                query_sql.append('AND id IN ({})'.format(','.join(str(job_id) for job_id in collect_job_set)))
            else:
                return res, 0
        if data.get('name'):
            query_sql.append('AND name LIKE "%{}%"'.format(data.get('name')))
        if data.get('job_id'):
            job_id = data.get('job_id')
            if isinstance(job_id, int):
                pass
            else:
                if not job_id.isdigit():
                    job_id = 0
            query_sql.append('AND id="{}"'.format(job_id))
        if data.get('state'):
            state_list = data.get('state').split(',')
            if 'pending' in state_list:
                state_list.append('pending_q')
            if len(state_list) == 1:
                query_sql.append('AND state="{}"'.format(state_list[0]))
            else:
                query_sql.append('AND state IN {}'.format(tuple(state_list)))
        if data.get('search'):
            search = data.get('search')
            users = User.objects.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search)).values('id')
            user_ids = [user['id'] for user in users]
            job_types = JobType.objects.filter(name=search).values('id')
            job_type_ids = [job_type['id'] for job_type in job_types]
            query_sql.append(
                'AND (name LIKE "%{0}%" OR id like "%{0}%")'.format(
                    search, job_type_ids, user_ids))
            if user_ids:
                query_sql.append('OR creator IN ({})'.format(','.join(str(user_id) for user_id in user_ids)))
            if job_type_ids:
                query_sql.append('OR job_type_id IN ({})'.format(','.join(str(type_id) for type_id in job_type_ids)))
        if data.get('test_suite'):
            test_suite = json.loads(data.get('test_suite'))
            test_suites = TestJobSuite.objects.filter(test_suite_id__in=test_suite).values('job_id')
            job_ids = [test_suite['job_id'] for test_suite in test_suites]
            if job_ids:
                query_sql.append('AND id IN ({})'.format(','.join(str(job_id) for job_id in job_ids)))
            else:
                query_sql.append('AND id=0')
        if data.get('server'):
            server = data.get('server')
            server_objs = TestServerSnapshot.objects.filter(ip=server)
            cloud_server_objs = CloudServerSnapshot.objects.filter(private_ip=server)
            id_li = list(set([obj.job_id for obj in server_objs]) | set([obj.job_id for obj in cloud_server_objs]))
            if id_li:
                query_sql.append('AND id IN ({})'.format(','.join(str(job_id) for job_id in id_li)))
            else:
                query_sql.append('AND id=0')
        if data.get('tags'):
            tags = json.loads(data.get('tags'))
            job_tags = JobTagRelation.objects.filter(tag_id__in=tags).values('job_id')
            job_ids = [job_tag['job_id'] for job_tag in job_tags]
            if job_ids:
                query_sql.append('AND id IN ({})'.format(','.join(str(job_id) for job_id in job_ids)))
            else:
                query_sql.append('AND id=0')
        if data.get('fail_case'):
            fail_case = data.get('fail_case').split(',')
            fail_cases = FuncResult.objects.filter(sub_case_name__in=fail_case, sub_case_result=2)
            job_ids = [fail_case.test_job_id for fail_case in fail_cases]
            if job_ids:
                query_sql.append('AND id IN ({})'.format(','.join(str(job_id) for job_id in job_ids)))
            else:
                query_sql.append('AND id=0')
        if data.get('creation_time'):
            creation_time = data.get('creation_time')
            creation_time = json.loads(creation_time)
            start_time, end_time = self.check_time_fmt(creation_time)
            query_sql.append('AND start_time BETWEEN "{}" AND "{}"'.format(start_time, end_time))
        if data.get('completion_time'):
            completion_time = data.get('completion_time')
            completion_time = json.loads(completion_time)
            start_time, end_time = self.check_time_fmt(completion_time)
            end_state = tuple(['stop', 'fail', 'success'])
            query_sql.append(
                'AND end_time BETWEEN "{}" AND "{}" AND state IN {}'.format(start_time, end_time, end_state))
        if data.get('filter_id'):
            query_sql.append('AND NOT id IN ({})'.format(data.get('filter_id')))
        if data.get('creators'):
            creators = json.loads(data.get('creators'))
            query_sql.append('AND creator IN ({})'.format(','.join(str(creator) for creator in creators)))
        filter_fields = ['project_id', 'job_type_id', 'product_id', 'server_provider', 'test_type', 'product_version',
                         'ws_id']
        for filter_field in filter_fields:
            if data.get(filter_field):
                query_sql.append('AND {}="{}"'.format(filter_field, data.get(filter_field)))
        extend_sql = ' '.join(query_sql)
        func_view_config = BaseConfig.objects.filter(config_type='ws', ws_id=data.get('ws_id'),
                                                     config_key='FUNC_RESULT_VIEW_TYPE').first()
        with connection.cursor() as cursor:
            search_sql = """
            SELECT 
            A.id,
            A.name,
            A.ws_id,
            A.state,
            A.state_desc,
            A.test_type,
            A.test_result,
            A.project_id,
            A.product_id,
            A.creator,
            A.callback_api,
            A.start_time,
            A.end_time,
            A.gmt_created,
            A.report_name,
            A.report_template_id,
            A.server_provider,
            A.product_version,
            A.created_from, A.baseline_id
            FROM test_job A
            RIGHT JOIN (
            SELECT id FROM test_job
            WHERE is_deleted=0 and ws_id='{}' {} ORDER BY id DESC LIMIT {}, {}) B
            ON A.id=B.id ORDER BY B.id DESC
            """.format(data.get('ws_id'), extend_sql, (page_num - 1) * page_size, page_size)

            cursor.execute(search_sql)
            rows = cursor.fetchall()
            for row_data in rows:
                job_id = row_data[0]
                creator = row_data[9]
                project_id = row_data[7]
                product_id = row_data[8]
                server_provider = row_data[16]
                creator_name = self.get_expect_name(User, create_name_map, creator)
                res.append({
                    'id': job_id,
                    'name': row_data[1],
                    'ws_id': row_data[2],
                    'state': self.get_job_state(job_id, row_data[5], row_data[19], row_data[3], func_view_config),
                    'state_desc': row_data[4],
                    'test_type': test_type_map.get(row_data[5]),
                    'test_result': row_data[6],
                    'project_id': project_id,
                    'product_id': product_id,
                    'creator': creator,
                    'callback_api': row_data[10],
                    'start_time': get_time(row_data[11]),
                    'end_time': get_time(row_data[12]),
                    'gmt_created': get_time(row_data[13]),
                    'report_name': row_data[14],
                    'report_template_id': row_data[15],
                    'server_provider': server_provider,
                    'product_version': row_data[17],
                    'created_from': row_data[18],
                    'creator_name': creator_name,
                    'project_name': self.get_expect_name(Project, project_name_map, project_id),
                    'product_name': self.get_expect_name(Product, product_name_map, product_id),
                    'server': self.get_job_server(server_provider, job_id),
                    'collection': True if job_id in collect_job_set else False,
                    'report_li': self.get_report_li(job_id, create_name_map),
                })
            total = 0
            query_total = """
            SELECT COUNT(id) FROM test_job WHERE is_deleted=0 {} ORDER BY id DESC""".format(extend_sql)
            cursor.execute(query_total)
            rows = cursor.fetchall()
            if rows:
                total = rows[0][0]
        return res, total

    def get_job_state(self, test_job_id, test_type, baseline_id, state, func_view_config):
        if state == 'pending_q':
            state = 'pending'
        if test_type == 'functional' and (state == 'fail' or state == 'success'):
            if func_view_config and func_view_config.config_value == '2':
                func_result = FuncResult.objects.filter(test_job_id=test_job_id)
                if func_result.count() == 0:
                    state = 'fail'
                    return state
                func_result_list = FuncResult.objects.filter(test_job_id=test_job_id, sub_case_result=2)
                if func_result_list.count() == 0:
                    state = 'success'
                else:
                    if baseline_id and func_result_list.filter(match_baseline=0).count() > 0:
                        state = 'fail'
                    else:
                        state = 'success'
        return state

    @staticmethod
    def get_job_server(server_provider, job_id):
        server = None
        if server_provider == 'aligroup':
            if TestServerSnapshot.objects.filter(job_id=job_id).count() == 1:
                server = TestServerSnapshot.objects.get(job_id=job_id).ip
        else:
            if CloudServerSnapshot.objects.filter(job_id=job_id).count() == 1:
                server = CloudServerSnapshot.objects.get(job_id=job_id).private_ip
        return server

    def get_report_li(self, job_id, create_name_map):
        report_li = []
        report_relation_queryset = ReportObjectRelation.objects.filter(object_type='job', object_id=job_id)
        if report_relation_queryset.exists():
            report_id_list = report_relation_queryset.values_list('report_id')
            report_queryset = Report.objects.filter(id__in=report_id_list)
            report_li = [{
                'id': report.id,
                'name': report.name,
                'creator': report.creator,
                'creator_name': self.get_expect_name(User, create_name_map, report.creator),
                'gmt_created': datetime.strftime(report.gmt_created, "%Y-%m-%d %H:%M:%S"),
            } for report in report_queryset]
        return report_li

    @staticmethod
    def get_expect_name(target_model, name_map, target_id):
        if target_id in name_map:
            return name_map.get(target_id)

        target_obj = target_model.objects.filter(id=target_id).first()
        target_name = None
        if target_obj is not None:
            if target_model == User:
                target_name = target_obj.first_name if target_obj.first_name else target_obj.last_name
            else:
                target_name = target_obj.name
        name_map[target_id] = target_name
        return target_name

    @staticmethod  # noqa: C901
    def filter(queryset, data, operator):
        q = Q()
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        q &= Q(project_id=data.get('project_id')) if data.get('project_id') else q
        q &= Q(job_type_id=data.get('job_type_id')) if data.get('job_type_id') else q
        q &= Q(name__icontains=data.get('name')) if data.get('name') else q
        q &= Q(product_id=data.get('product_id')) if data.get('product_id') else q
        q &= Q(server_provider=data.get('server_provider')) if data.get('server_provider') else q
        q &= Q(test_type=data.get('test_type')) if data.get('test_type') else q
        q &= Q(product_version=data.get('product_version')) if data.get('product_version') else q
        if data.get('state'):
            if data.get('state') == 'pending':
                q &= Q(state__in=['pending', 'pending_q'])
            else:
                q &= Q(state__in=data.get('state').split(','))
        if data.get('job_id'):
            job_id = data.get('job_id')
            if isinstance(job_id, int):
                pass
            else:
                if not job_id.isdigit():
                    job_id = 0
            q &= Q(id=job_id)
        if data.get('search'):
            search = data.get('search')
            users = User.objects.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search)).values('id')
            user_ids = [user['id'] for user in users]
            job_types = JobType.objects.filter(name=search).values('id')
            job_type_ids = [job_type['id'] for job_type in job_types]
            q &= Q(name__icontains=search) | Q(id__icontains=search) | Q(job_type_id__in=job_type_ids) | Q(
                creator__in=user_ids)
        if data.get('test_suite'):
            test_suite = json.loads(data.get('test_suite'))
            test_suites = TestJobSuite.objects.filter(test_suite_id__in=test_suite).values('job_id')
            job_ids = [test_suite['job_id'] for test_suite in test_suites]
            q &= Q(id__in=job_ids)
        if data.get('creators'):
            creators = json.loads(data.get('creators'))
            q &= Q(creator__in=creators)
        if data.get('tags'):
            tags = json.loads(data.get('tags'))
            job_tags = JobTagRelation.objects.filter(tag_id__in=tags).values('job_id')
            job_ids = [job_tag['job_id'] for job_tag in job_tags]
            q &= Q(id__in=job_ids)
        if data.get('fail_case'):
            fail_case = data.get('fail_case').split(',')
            fail_cases = FuncResult.objects.filter(sub_case_name__in=fail_case, sub_case_result=2)
            job_ids = [fail_case.test_job_id for fail_case in fail_cases]
            q &= Q(id__in=job_ids)
        if data.get('creation_time'):
            creation_time = data.get('creation_time')
            creation_time = json.loads(creation_time)
            start_time = datetime.strptime(creation_time.get('start_time', '2010-10-23 15:29:08'), '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(creation_time.get('end_time', '2040-10-23 15:29:08'), '%Y-%m-%d %H:%M:%S')
            q &= Q(start_time__range=(start_time, end_time))
        if data.get('completion_time'):
            completion_time = data.get('completion_time')
            completion_time = json.loads(completion_time)
            start_time = datetime.strptime(completion_time.get('start_time', '2010-10-23 15:29:08'),
                                           '%Y-%m-%d %H:%M:%S')
            end_time = datetime.strptime(completion_time.get('end_time', '2040-10-23 15:29:08'), '%Y-%m-%d %H:%M:%S')
            q &= Q(end_time__range=(start_time, end_time))
            q &= Q(state__in=['stop', 'fail', 'success'])
        if data.get('my_job') or data.get('tab') == 'my':
            q &= Q(creator=operator.id)
        if data.get('server'):
            server = data.get('server')
            server_objs = TestServerSnapshot.objects.filter(ip=server)
            cloud_server_objs = CloudServerSnapshot.objects.filter(pub_ip=server)
            id_li = list(set([obj.job_id for obj in server_objs]) | set([obj.job_id for obj in cloud_server_objs]))
            q &= Q(id__in=id_li)
        if data.get('collection') or data.get('tab') == 'collection':
            my_collection = JobCollection.objects.filter(user_id=operator.id)
            id_li = [obj.job_id for obj in my_collection]
            q &= Q(id__in=id_li)
        if data.get('filter_id'):
            queryset = queryset.exclude(id__in=data.get('filter_id').split(','))
        return queryset.filter(q)

    def update(self, data, operator):
        pass

    def check_delete_permission(self, operator, job_id_li):
        for job_id in job_id_li:
            self.check_id(job_id)
            test_job = TestJob.objects.filter(id=job_id).first()
            if not check_operator_permission(operator, test_job):
                return False
        return True

    def delete(self, data, operator):  # noqa: C901
        job_id = data.get('job_id')
        job_id_li = data.get('job_id_li', list())
        if job_id:
            job_id_li.append(job_id)
        if not self.check_delete_permission(operator, job_id_li):
            return False, '无权限删除非自己创建的job'
        pending_jobs = TestJob.objects.filter(
            id__in=job_id_li, state__in=['pending', 'pending_q']
        )
        group_pending_jobs = pending_jobs.filter(server_provider='aligroup')
        yun_pending_jobs = pending_jobs.filter(server_provider='aliyun')
        group_server_ids = TestJobCase.objects.filter(
            job_id__in=group_pending_jobs.values_list('id', flat=True)
        ).values_list('server_object_id', flat=True)
        yun_server_ids = TestJobCase.objects.filter(
            job_id__in=yun_pending_jobs.values_list('id', flat=True)
        ).values_list('server_object_id', flat=True)
        with transaction.atomic():
            TestJob.objects.filter(id__in=job_id_li).delete()
            if group_server_ids:
                TestServer.objects.filter(id__in=group_server_ids).update(spec_use=0)
            if yun_server_ids:
                CloudServer.objects.filter(id__in=yun_server_ids).update(spec_use=0)
        return True, '删除成功'

    @staticmethod
    def create(data, operator):
        handler = JobDataHandle(data, operator)
        with transaction.atomic():
            data_dic, case_list, suite_list, tag_list = handler.return_result()
            test_job = TestJob.objects.create(**data_dic)
            for suite in suite_list:
                suite['job_id'] = test_job.id
                TestJobSuite.objects.create(**suite)
            for case in case_list:
                case['job_id'] = test_job.id
                TestJobCase.objects.create(**case)
            for tag in tag_list:
                JobTagRelation.objects.create(tag_id=tag, job_id=test_job.id)
            return test_job

    @staticmethod
    def check_id(job_id):
        obj = TestJob.objects.filter(id=job_id)
        if not obj.exists():
            raise JobTestException(ErrorCode.TEST_JOB_NONEXISTENT)


class JobTestConfigService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('job_id'):
            q &= Q(id=data.get('job_id'))
        else:
            raise JobTestException(ErrorCode.JOB_NEED)
        return queryset.filter(q)


class JobTestSummaryService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('job_id'):
            if not str(data.get('job_id')).isdigit():
                raise JobTestException(ErrorCode.TEST_JOB_NONEXISTENT)
            q &= Q(id=data.get('job_id'))
        else:
            raise JobTestException(ErrorCode.JOB_NEED)
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        return queryset.filter(q)


class JobTestPrepareService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('job_id'):
            q &= Q(id=data.get('job_id'))
        else:
            raise JobTestException(ErrorCode.JOB_NEED)
        return queryset.filter(q)

    @staticmethod
    def get_build_kernel(data):
        job_id = data.get('job_id')
        if not job_id:
            raise JobTestException(ErrorCode.JOB_NEED)
        test_job = TestJob.objects.filter(id=job_id).first()
        if not test_job:
            raise JobTestException(ErrorCode.TEST_JOB_NONEXISTENT)
        build_pkg_info = dict()
        code = 200
        if not test_job.build_pkg_info:
            code = 201
        else:
            build_job_id = test_job.build_job_id
            if build_job_id:
                build_job = BuildJob.objects.filter(id=build_job_id).first()
                if build_job:
                    cbp_link = ''
                    if build_job.cbp_id:
                        cbp_link = '{}/#/blank/cbp/detail?cbp_task_id={}'.format(
                            cp.get('goldmine_domain'), build_job.cbp_id)
                    build_pkg_info.update({
                        'name': build_job.name,
                        'state': build_job.state,
                        'git_repo': build_job.git_repo if build_job.git_repo else build_job.git_url,
                        'git_branch': build_job.git_branch,
                        'git_commit': build_job.git_commit,
                        'cbp_link': cbp_link,
                        'start_time': str(build_job.gmt_created).split('.')[0],
                    })
                    if build_job.rpm_list and len(build_job.rpm_list) == 3:
                        build_pkg_info.update({
                            'kernel_package': build_job.rpm_list[2],
                            'devel_package': build_job.rpm_list[1],
                            'headers_package': build_job.rpm_list[0],
                        })
                    if build_job.state in ['success', 'fail']:
                        build_pkg_info.update({
                            'end_time': str(build_job.gmt_modified).split('.')[0],
                        })
        return code, build_pkg_info


class JobTestProcessSuiteService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('job_id'):
            q &= Q(job_id=data.get('job_id'))
        else:
            raise JobTestException(ErrorCode.JOB_NEED)
        return queryset.filter(q)


class JobTestProcessCaseService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('job_id'):
            q &= Q(job_id=data.get('job_id'))
        else:
            raise JobTestException(ErrorCode.JOB_NEED)
        if data.get('test_suite_id'):
            q &= Q(test_suite_id=data.get('test_suite_id'))
        else:
            raise JobTestException(ErrorCode.TEST_SUITE_NEED)
        return queryset.filter(q)


class JobTestResultService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('job_id'):
            if not str(data.get('job_id')).isdigit():
                raise JobTestException(ErrorCode.TEST_JOB_NONEXISTENT)
            q &= Q(id=data.get('job_id'))
        else:
            raise JobTestException(ErrorCode.JOB_NEED)
        return queryset.filter(q)

    @staticmethod
    def filter_search(response, data):
        test_suites = response['data'][0]['test_suite']
        resp = []
        for test_suite in test_suites:
            if test_suite['test_type'] == '功能测试':
                if not data.get('state'):
                    resp.append(test_suite)
                elif test_suite['conf_{}'.format(data.get('state'))]:
                    resp.append(test_suite)
            else:
                if not data.get('state'):
                    resp.append(test_suite)
                elif test_suite[data.get('state')]:
                    resp.append(test_suite)
        return resp


class JobTestConfResultService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        job_id = data.get('job_id')
        suite_id = data.get('suite_id')
        assert job_id, JobTestException(ErrorCode.JOB_NEED)
        assert suite_id, JobTestException(ErrorCode.SUITE_NEED)
        q &= Q(job_id=data.get('job_id'))
        q &= Q(test_suite_id=data.get('suite_id'))
        q &= Q(state__in=['success', 'fail', 'stop', 'skip'])
        return queryset.filter(q)

    @staticmethod
    def filter_search(response, data):
        result_data = response['data']
        resp = []
        for result in result_data:
            test_type = TestJob.objects.filter(id=data.get('job_id')).first().test_type
            if test_type == 'functional':
                if not data.get('state'):
                    resp.append(dict(result))
                elif result['result_data']['case_{}'.format(data.get('state'))]:
                    resp.append(dict(result))
            else:
                if not data.get('state'):
                    resp.append(dict(result))
                elif result['result_data']['{}'.format(data.get('state'))]:
                    resp.append(dict(result))
        return resp


class JobTestCaseResultService(CommonService):
    @staticmethod
    def filter(queryset, request):
        data = request.GET
        q = Q()
        job_id = data.get('job_id')
        suite_id = data.get('suite_id')
        case_id = data.get('case_id')
        request.baseline_id = TestJob.objects.get_value(id=job_id).baseline_id
        baseline_obj = Baseline.objects.filter(id=request.baseline_id).first()
        request.baseline_obj = baseline_obj
        assert job_id, JobTestException(ErrorCode.JOB_NEED)
        assert suite_id, JobTestException(ErrorCode.SUITE_NEED)
        assert case_id, JobTestException(ErrorCode.CASE_NEED)
        q &= Q(test_job_id=job_id)
        q &= Q(test_suite_id=suite_id)
        q &= Q(test_case_id=case_id)
        q &= Q(sub_case_result=data.get('sub_case_result')) if data.get('sub_case_result') else q
        return sorted(queryset.filter(q), key=lambda x: (0 if x.sub_case_result == 2 else 1, x.id))


class JobTestCasePerResultService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        job_id = data.get('job_id')
        suite_id = data.get('suite_id')
        case_id = data.get('case_id')
        assert job_id, JobTestException(ErrorCode.JOB_NEED)
        assert suite_id, JobTestException(ErrorCode.SUITE_NEED)
        assert case_id, JobTestException(ErrorCode.CASE_NEED)
        q &= Q(test_job_id=job_id)
        q &= Q(test_suite_id=suite_id)
        q &= Q(test_case_id=case_id)
        if data.get('compare_result'):
            if data.get('compare_result') == 'na':
                # queryset.exclude(compare_result__in=['increase', 'decline', 'normal', 'invalid'])
                q &= ~Q(track_result__in=['increase', 'decline', 'normal', 'invalid'])
            else:
                q &= Q(track_result=data.get('compare_result'))
        return queryset.filter(q)


class JobTestCaseVersionService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        job_id = data.get('job_id')
        assert job_id, JobTestException(ErrorCode.JOB_NEED)
        q &= Q(id=job_id)

        return queryset.filter(q)


class JobTestCaseFileService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        job_id = data.get('job_id')
        suite_id = data.get('suite_id')
        case_id = data.get('case_id')
        assert job_id, JobTestException(ErrorCode.JOB_NEED)
        assert suite_id, JobTestException(ErrorCode.SUITE_NEED)
        assert case_id, JobTestException(ErrorCode.CASE_NEED)
        q &= Q(test_job_id=job_id)
        q &= Q(test_suite_id=suite_id)
        q &= Q(test_case_id=case_id)
        return queryset.filter(q)


class EditorNoteService(CommonService):
    @staticmethod
    def editor_note(data):
        editor_obj = data.get('editor_obj')
        note = data.get('note')
        if editor_obj not in ['job', 'test_job_suite', 'test_job_conf', 'test_job_case', 'perf_analysis',
                              'func_conf_analysis', 'func_case_analysis']:
            raise JobTestException(ErrorCode.EDITOR_OBJ_ERROR)
        if editor_obj == 'job':
            job_id = data.get('job_id')
            assert job_id, JobTestException(ErrorCode.ID_NEED)
            TestJob.objects.filter(id=job_id).update(note=note, not_update_time=True)
        elif editor_obj == 'test_job_suite':
            test_job_suite_id = data.get('test_job_suite_id')
            assert test_job_suite_id, JobTestException(ErrorCode.ID_NEED)
            TestJobSuite.objects.filter(id=test_job_suite_id).update(note=note, not_update_time=True)
        elif editor_obj == 'test_job_conf':
            test_job_conf_id = data.get('test_job_conf_id')
            assert test_job_conf_id, JobTestException(ErrorCode.ID_NEED)
            TestJobCase.objects.filter(id=test_job_conf_id).update(note=note, not_update_time=True)
        elif editor_obj == 'perf_analysis':
            result_obj_id = data.get('result_obj_id')
            assert result_obj_id, JobTestException(ErrorCode.ID_NEED)
            PerfResult.objects.filter(id=result_obj_id).update(note=note, not_update_time=True)
        elif editor_obj == 'func_conf_analysis':
            result_obj_id = data.get('result_obj_id')
            assert result_obj_id, JobTestException(ErrorCode.ID_NEED)
            TestJobCase.objects.filter(id=result_obj_id).update(analysis_note=note, not_update_time=True)
        elif editor_obj == 'func_case_analysis':
            result_obj_id = data.get('result_obj_id')
            assert result_obj_id, JobTestException(ErrorCode.ID_NEED)
            FuncResult.objects.filter(id=result_obj_id).update(note=note, not_update_time=True)
        else:
            test_job_case_id = data.get('test_job_case_id')
            assert test_job_case_id, JobTestException(ErrorCode.ID_NEED)
            FuncResult.objects.filter(id=test_job_case_id).update(note=note, not_update_time=True)


class JobCollectionService(CommonService):

    @staticmethod
    def create(data, operator):
        job_id = data.get('job_id')
        assert job_id, JobTestException(ErrorCode.JOB_NEED)
        if JobCollection.objects.filter(job_id=job_id, user_id=operator.id).exists():
            pass
        else:
            JobCollection.objects.create(job_id=job_id, user_id=operator.id)

    @staticmethod
    def delete(data, operator):
        job_id = data.get('job_id')
        assert job_id, JobTestException(ErrorCode.JOB_NEED)
        JobCollection.objects.filter(job_id=job_id, user_id=operator.id).delete()


class UpdateStateService(CommonService):
    def update_state(self, data, user_id):
        update_obj = data.get('editor_obj')
        state = data.get('state')
        operation_note = self._get_operation_note(user_id, state)
        if update_obj not in ['job', 'test_job_suite', 'test_job_conf']:
            raise JobTestException(ErrorCode.EDITOR_OBJ_ERROR)
        if update_obj == 'job':
            self._update_job_state(data, state, operation_note)
        elif update_obj == 'test_job_suite':
            self._update_suite_state(data, state, operation_note)
        elif update_obj == 'test_job_conf':
            self._update_conf_state(data, state, operation_note)

    @staticmethod
    def _get_operation_note(user_id, state):
        user = User.objects.filter(id=user_id)
        user_name = user.first().last_name if user.exists() else ''
        operation_note = f'{state} by {user_name}'
        return operation_note

    @staticmethod
    def _update_job_state(data, state, operation_note):
        job_id = data.get('job_id')
        assert job_id, JobTestException(ErrorCode.ID_NEED)
        if state not in ['stop']:
            raise JobTestException(ErrorCode.EDITOR_OBJ_ERROR)
        with transaction.atomic():
            TestJob.objects.filter(
                id=job_id,
                state__in=['running', 'pending', 'pending_q']
            ).update(state=state)
            TestJobCase.objects.filter(job_id=job_id).update(note=operation_note)

    @staticmethod
    def _update_suite_state(data, state, operation_note):
        test_job_suite_id = data.get('test_job_suite_id')
        if state not in ['stop', 'skip']:
            raise JobTestException(ErrorCode.EDITOR_OBJ_ERROR)
        assert test_job_suite_id, JobTestException(ErrorCode.ID_NEED)
        job_suite = TestJobSuite.objects.filter(
            id=test_job_suite_id,
            state__in=['running', 'pending']
        ).first()
        if not job_suite:
            raise JobTestException(ErrorCode.STOP_SUITE_ERROR)
        job_id = job_suite.job_id
        suite_id = job_suite.test_suite_id
        if state == 'stop':
            q = Q(job_id=job_id, test_suite_id=suite_id, state__in=['running', 'pending'])
        else:
            q = Q(job_id=job_id, test_suite_id=suite_id, state='pending')
        with transaction.atomic():
            TestJobCase.objects.filter(q).update(state=state, note=operation_note)
            if not TestJobCase.objects.filter(job_id=job_id, test_suite_id=suite_id, state='running').exists():
                TestJobSuite.objects.filter(id=test_job_suite_id).update(state=state)

    @staticmethod
    def _update_conf_state(data, state, operation_note):
        test_job_conf_id = data.get('test_job_conf_id')
        assert test_job_conf_id, JobTestException(ErrorCode.ID_NEED)
        if state not in ['stop', 'skip']:
            raise JobTestException(ErrorCode.EDITOR_OBJ_ERROR)
        if state == 'stop' and not TestJobCase.objects.filter(
                id=test_job_conf_id, state__in=['running', 'pending']
        ).exists():
            raise JobTestException(ErrorCode.STOP_CASE_ERROR)
        if state == 'skip' and not TestJobCase.objects.filter(
                id=test_job_conf_id, state__in=['running', 'pending']
        ).exists():
            raise JobTestException(ErrorCode.SKIP_CASE_ERROR)
        with transaction.atomic():
            TestJobCase.objects.filter(
                id=test_job_conf_id, state__in=['pending', 'running']
            ).update(state=state)
            TestJobCase.objects.filter(id=test_job_conf_id).update(note=operation_note)


class JobRerunService(CommonService):

    @staticmethod
    def filter(queryset, data):
        q = Q()
        job_id = data.get('job_id')
        assert job_id, JobTestException(ErrorCode.JOB_NEED)
        q &= Q(id=job_id)
        return queryset.filter(q)


class JobMonitorItemService(CommonService):
    @staticmethod
    def filter(queryset, data, operator):
        q = Q()
        q &= Q(name=data.get('name')) if data.get('name') else q
        return queryset.filter(q)


class JobTestProcessMonitorJobService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('job_id'):
            q &= Q(monitor_level=MonitorInfo.OBJECT_TYPE_CHOICES[0][0])
            q &= Q(object_id=data.get('job_id'))
        else:
            raise JobTestException(ErrorCode.JOB_NEED)
        return queryset.filter(q)

    @staticmethod
    def get_monitor_info_serializer(queryset, job_model, monitor_serializer):
        data = {
            'monitor_control': False,
            'result_list': []
        }
        # job监控以test_job.monitor_info为准
        if not job_model.monitor_info:
            return data
        monitor_info_temp = {}
        for job_monitor_info in job_model.monitor_info:
            if job_monitor_info.get('monitor_type') == MonitorType.CASE_MACHINE:
                monitor_info_temp[MonitorType.CASE_MACHINE] = job_monitor_info
            elif job_monitor_info.get('monitor_type') == MonitorType.CUSTOM_MACHINE:
                monitor_info_temp[job_monitor_info.get('ip')] = job_monitor_info
        for monitor_info in queryset:
            monitor_info_data = monitor_serializer(monitor_info).data
            ip = monitor_info_data.get('server')
            if ip in monitor_info_temp:
                monitor_info_data.update(monitor_info_temp.get(ip))
            else:
                monitor_info_data.update(monitor_info_temp.get(MonitorType.CASE_MACHINE))
            data['result_list'].append(monitor_info_data)
        data['monitor_control'] = True
        # monitor_info_temp = {}
        # for monitor_info in queryset:
        #     monitor_info_temp[monitor_info.server] = monitor_serializer(monitor_info).data
        # for job_monitor_info in job_model.monitor_info:
        #     job_monitor_info_server = job_monitor_info.get('ip')
        #     # test_job.monitor_info.ip/sn在monitor_info表中有无结果
        #     if job_monitor_info_server in monitor_info_temp:
        #         job_monitor_info.update(monitor_info_temp[job_monitor_info_server])
        #         job_monitor_info.update({'state': 1})
        #     else:
        #         job_monitor_info.update({'state': 0})
        #     data.append(job_monitor_info)
        return data


class JobDataConversionService(object):
    CONV_ID_TO_NAME = 'id_to_name'
    CONV_NAME_TO_ID = 'name_to_id'

    def __init__(self, job_data):
        self.job_data = job_data
        
    def id_conv_to_name(self):
        self.conv_field(self.CONV_ID_TO_NAME, 'project', Project)
        self.conv_field(self.CONV_ID_TO_NAME, 'baseline', Baseline)
        self.conv_field(self.CONV_ID_TO_NAME, 'job_type', JobType)
        self.conv_field(self.CONV_ID_TO_NAME, 'workspace', Workspace)
        self.conv_field(self.CONV_ID_TO_NAME, 'report_template', ReportTemplate)
        self.conv_test_config(self.CONV_ID_TO_NAME)
        self.conv_job_tag(self.CONV_ID_TO_NAME)
        return self.job_data

    def name_conv_to_id(self):
        self.conv_field(self.CONV_NAME_TO_ID, 'project', Project,
                        q=Q(ws_id=self.job_data.get('workspace')))
        self.conv_field(self.CONV_NAME_TO_ID, 'baseline', Baseline,
                        q=Q(ws_id=self.job_data.get('workspace')))
        self.conv_field(self.CONV_NAME_TO_ID, 'job_type', JobType,
                        q=Q(ws_id=self.job_data.get('workspace')))
        # self.conv_field(self.CONV_NAME_TO_ID, 'workspace', Workspace)
        self.conv_field(self.CONV_NAME_TO_ID, 'report_template', ReportTemplate,
                        q=Q(ws_id=self.job_data.get('workspace')))
        self.conv_test_config(self.CONV_NAME_TO_ID)
        self.conv_job_tag(self.CONV_NAME_TO_ID)
        return self.job_data

    def conv_field(self, conv_type, field_name, model, q=None):
        if not self.job_data.get(field_name):
            return
        if conv_type == self.CONV_ID_TO_NAME:
            obj = model.objects.filter(id=self.job_data[field_name])
            if q:
                obj = obj.filter(q)
            if not obj.exists():
                raise ValueError(f'指定的{field_name}ID({self.job_data[field_name]})不存在')
            self.job_data[field_name] = obj.first().name
        else:
            obj = model.objects.filter(name=self.job_data[field_name])
            if q:
                obj = obj.filter(q)
            if not obj.exists():
                raise ValueError(f'指定的{field_name}名称{self.job_data[field_name]}不存在')
            self.job_data[field_name] = obj.first().id

    def conv_test_config(self, conv_type):
        test_config = []
        if not self.job_data.get('test_config'):
            return
            # raise ValueError('test_config不能为空')
        for item in self.job_data['test_config']:
            if conv_type == self.CONV_ID_TO_NAME:
                self._conv_test_config_id_to_name(item, conv_type)
            else:
                self._conv_test_config_name_to_id(item, conv_type)
            test_config.append(item)
        self.job_data['test_config'] = test_config

    def conv_job_tag(self, conv_type):
        if not self.job_data.get('tags'):
            return
        tags = []
        for tag_item in self.job_data['tags']:
            if conv_type == self.CONV_ID_TO_NAME:
                tag = JobTag.objects.filter(id=tag_item)
                if not tag.exists():
                    raise ValueError(f'Job标签ID{tag_item}不存在')
                tags.append(tag.first().name)
            else:
                tag = JobTag.objects.filter(name=tag_item)
                if not tag.exists():
                    raise ValueError(f'Job标签名称{tag_item}不存在')
                tags.append(tag.first().id)
        self.job_data['tags'] = tags

    def conv_server(self, case_item, conv_type):
        server_config = case_item.get('server')
        if not server_config:
            if 'server' in case_item:
                case_item.pop('server')
            return
        if conv_type == self.CONV_ID_TO_NAME:
            self._conv_server_to_name(server_config, case_item)
        else:
            self._conv_server_name_to_id(server_config, case_item)

    def _conv_test_config_id_to_name(self, item, conv_type):
        suite = TestSuite.objects.filter(id=item.get('test_suite'), test_framework='tone')
        if not suite.exists():
            raise ValueError(f'Suite ID({item.get("test_suite")})不存在')
        item['test_suite'] = suite.first().name
        for case_item in item['cases']:
            case = TestCase.objects.filter(id=case_item.get('test_case'))
            if not case.exists():
                raise ValueError(f'Case ID({case.get("test_case")})不存在')
            case_item['test_case'] = case.first().name
            self.conv_server(case_item, conv_type)

    def _conv_test_config_name_to_id(self, item, conv_type):
        suite = TestSuite.objects.filter(name=item.get('test_suite'), test_framework='tone')
        if not suite.exists():
            raise ValueError(f'Suite名称({item.get("test_suite")})不存在')
        item['test_suite'] = suite.first().id
        for case_item in item['cases']:
            case = TestCase.objects.filter(name=case_item.get('test_case'), test_suite_id=suite.first().id)
            if not case.exists():
                raise ValueError(f'Case名称({case.get("test_case")})不存在')
            case_item['test_case'] = case.first().id
            self.conv_server(case_item, conv_type)

    @staticmethod
    def _conv_server_to_name(server_config, case_item):  # noqa: C901
        if server_config.get('id'):
            server = TestServer.objects.filter(id=server_config.get('id'))
            if not server.exists():
                raise ValueError(f'机器ID({server_config.get("id")})不存在')
            case_item['server'] = {'ip': server.first().ip}
        elif server_config.get('tag'):
            server_tag = ServerTag.objects.filter(id__in=server_config.get('tag'))
            if not server_tag.exists():
                raise ValueError(f'机器标签({server_config.get("tag")})不存在')
            case_item['server'] = {'tag': list(server_tag.values_list('name', flat=True))}
        # elif server_config.get('ip'):
        #     pass
        elif server_config.get('cluster'):
            cluster = TestCluster.objects.filter(id=server_config.get('cluster'))
            if not cluster.exists():
                raise ValueError(f'集群ID({server_config.get("cluster")})不存在')
            case_item['server'] = {'cluster': cluster.first().name}
        elif server_config.get('config'):
            config = CloudServer.objects.filter(id=server_config.get('config'))
            if not config.exists():
                raise ValueError(f'云上机器配置({server_config.get("config")})不存在')
            case_item['server'] = {'config': config.first().template_name}
        elif server_config.get('instance'):
            instance = CloudServer.objects.filter(id=server_config.get('instance'))
            if not instance.exists():
                raise ValueError(f'云上机器实例({server_config.get("instance")})不存在')
            case_item['server'] = {'instance': instance.first().instance_name}

    @staticmethod
    def _conv_server_name_to_id(server_config, case_item):  # noqa: C901
        if server_config and server_config.get('ip'):
            if not server_config.get('channel_type'):
                # yaml文本如果没有channel_type的传参，则认定为是机器池机器
                server = TestServer.objects.filter(ip=server_config.get('ip'))
                if not server.exists():
                    raise ValueError(f'机器IP({server_config.get("ip")})不存在')
                case_item['server'] = {
                    'id': server.first().id,
                    'ip': server.first().ip,
                    'name': server.first().ip
                }
            # else:
            #     # 非机器池场景，无需转换ip
            #     pass
        elif server_config.get('tag'):
            tag_id_list = list()
            tag_name_list = list()
            for tag in server_config.get('tag'):
                server_tag = ServerTag.objects.filter(name=tag)
                if not server_tag.exists():
                    raise ValueError(f'机器标签({server_config.get("tag")})不存在')
                tag_id_list.append(server_tag.first().id)
                tag_name_list.append(server_tag.first().name)
            case_item['server'] = {
                'tag': tag_id_list,
                'id': tag_id_list,
                'name': tag_name_list,
            }
        elif server_config.get('cluster'):
            cluster = TestCluster.objects.filter(name=server_config.get('cluster'))
            if not cluster.exists():
                raise ValueError(f'集群名称({server_config.get("cluster")})不存在')
            case_item['server'] = {
                'cluster': cluster.first().id,
                'id': cluster.first().id,
                'name': cluster.first().name
            }
        elif server_config.get('config'):
            config = CloudServer.objects.filter(template_name=server_config.get('config'))
            if not config.exists():
                raise ValueError(f'云上机器配置名称({server_config.get("config")})不存在')
            case_item['server'] = {
                'config': config.first().id,
                'id': config.first().id,
                'name': config.first().template_name
            }
        elif server_config.get('instance'):
            instance = CloudServer.objects.filter(instance_name=server_config.get('instance'))
            if not instance.exists():
                raise ValueError(f'云上机器实例({server_config.get("instance")})不存在')
            case_item['server'] = {
                'instance': instance.first().id,
                'id': instance.first().id,
                'ip': instance.first().private_ip,
                'name': instance.first().instance_name
            }

    def verify_field_value(self):
        # 中文校验
        for field_key in ['name', 'project', 'baseline']:
            if self.job_data.get(field_key) and check_contains_chinese(self.job_data.get(field_key)):
                return False, '{}格式不合法'.format(field_key)

        # repeat和priority范围校验
        if self.job_data.get('test_config'):
            for suite_item in self.job_data['test_config']:
                for case_item in suite_item.get('cases'):
                    if case_item.get('repeat') and (case_item.get('repeat') > 100 or case_item.get('repeat') < 1):
                        return False, 'repeat超出范围(1-1000)'
                    if case_item.get('priority') and (case_item.get('priority') > 100 or case_item.get('priority') < 1):
                        return False, '优先级超出范围(1-1000)'

        return True, None


class DataConversionService(CommonService):
    def json_conv_to_yaml(self, json_data, is_job_data=True):
        convertor = JobDataConversionService(job_data=json_data)
        if is_job_data:
            json_data = convertor.id_conv_to_name()
        if not json_data:
            return ''
        yaml_data = yaml.dump(json_data, allow_unicode=True, default_flow_style=False, sort_keys=False)
        print(yaml_data)
        return yaml_data

    def yaml_conv_to_json(self, yaml_data, workspace, is_job_data=True):
        json_data = yaml.load(yaml_data, Loader=yaml.FullLoader)
        if not json_data:
            return dict()
        json_data['workspace'] = workspace
        convertor = JobDataConversionService(job_data=json_data)
        if is_job_data:
            suc, msg = convertor.verify_field_value()
            if not suc:
                raise ValueError(msg)
            json_data = convertor.name_conv_to_id()
        return json_data
