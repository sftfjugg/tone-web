# _*_ coding:utf-8 _*_
# flake8: noqa
"""
Module Description:
Date:
Author: Yfh
"""
import json
import logging
import shutil
import os
import stat
from datetime import datetime
import tarfile
import yaml
import requests
from django.db.models import Q
from django.db import transaction, connection
from itertools import chain
from threading import Thread

from tone.core.common.callback import CallBackType, JobCallBack
from tone.core.utils.common_utils import query_all_dict
from tone.core.common.enums.job_enums import JobCaseState, JobState
from tone.core.common.enums.ts_enums import TestServerState
from tone.core.common.info_map import get_result_map
from tone.core.common.services import CommonService
from tone.core.common.constant import MonitorType, PERFORMANCE, PREPARE_STEP_STAGE_MAP
from tone.core.utils.permission_manage import check_operator_permission
from tone.core.utils.tone_thread import ToneThread
from tone.core.utils.verify_tools import check_contains_chinese
from tone.models import TestJob, TestJobCase, TestJobSuite, JobCollection, TestServerSnapshot, CloudServerSnapshot, \
    PerfResult, TestServer, TestClusterServer, CloudServer, BaseConfig, TestClusterSnapshot, JobDownloadRecord
from tone.models import JobType, User, FuncResult, Baseline, BuildJob, Project, Product, ReportObjectRelation, \
    Report, MonitorInfo, Workspace, TestSuite, TestCase, ServerTag, ReportTemplate, TestCluster, TestStep, \
    PlanInstanceTestRelation
from tone.models.sys.config_models import JobTagRelation, JobTag
from tone.core.handle.job_handle import JobDataHandle
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import JobTestException
from tone.serializers.job.test_serializers import get_time, get_check_server_ip
from tone.settings import cp
from tone.core.common.redis_cache import runner_redis_cache
from tone.core.common.constant import OFFLINE_DATA_DIR
from tone.settings import MEDIA_ROOT
from tone.core.common.job_result_helper import get_test_config, perse_func_result
from tone.core.utils.sftp_client import sftp_client


logger = logging.getLogger()


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
        pass_test_type = ""
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
            input_state_list = data.get('state').split(',')
            if 'pass' in input_state_list:
                pass_test_type = 'functional'
            state_list = ['success' if state == 'pass' else state for state in input_state_list]
            if 'pending' in state_list:
                state_list.append('pending_q')
            if len(state_list) == 1:
                query_sql.append('AND state="{}"'.format(state_list[0]))
            else:
                query_sql.append('AND state IN {}'.format(tuple(state_list)))
        if data.get('search'):
            # 模糊搜索只包含以下维度：job_id, job_name, 创建人名字，job类型
            search = data.get('search')
            users = User.objects.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search)).values('id')
            user_ids = [user['id'] for user in users]
            job_types = JobType.objects.filter(name=search).values('id')
            job_type_ids = [job_type['id'] for job_type in job_types]
            search_sql = 'name LIKE "%{0}%" OR id like "%{0}%" '.format(search)
            if user_ids:
                search_sql += 'OR creator IN ({}) '.format(','.join(str(user_id) for user_id in user_ids))
            if job_type_ids:
                search_sql += 'OR job_type_id IN ({})'.format(','.join(str(type_id) for type_id in job_type_ids))
            query_sql.append(f'AND ({search_sql})')
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
        if data.get('test_type') or pass_test_type:
            test_type = data.get('test_type') if data.get('test_type') else pass_test_type
            query_sql.append('AND test_type="{}"'.format(test_type))
        filter_fields = ['project_id', 'job_type_id', 'product_id', 'server_provider', 'product_version',
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
            job_id_list = [row_data[0] for row_data in rows]
            test_server_shot = TestServerSnapshot.objects.filter(job_id__in=job_id_list)
            clould_server_shot = CloudServerSnapshot.objects.filter(job_id__in=job_id_list)
            fun_result = FuncResult.objects.filter(test_job_id__in=job_id_list)
            test_job_case = TestJobCase.objects.filter(job_id__in=job_id_list)
            report_obj = ReportObjectRelation.objects.filter(object_id__in=job_id_list)
            for row_data in rows:
                self._get_test_res(clould_server_shot, collect_job_set, create_name_map, fun_result, func_view_config,
                                   product_name_map, project_name_map, report_obj, res, row_data, test_job_case,
                                   test_server_shot, test_type_map)
            total = 0
            query_total = """
            SELECT COUNT(id) FROM test_job WHERE is_deleted=0 {} ORDER BY id DESC""".format(extend_sql)
            cursor.execute(query_total)
            rows = cursor.fetchall()
            if rows:
                total = rows[0][0]
        return res, total

    def _get_test_res(self, clould_server_shot, collect_job_set, create_name_map, fun_result, func_view_config,
                      product_name_map, project_name_map, report_obj, res, row_data, test_job_case, test_server_shot,
                      test_type_map):
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
            'state': self.get_job_state(job_id, row_data[5], row_data[3], func_view_config),
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
            'report_li': self.get_report_li(job_id, create_name_map)
        })

    def get_job_state(self, test_job_id, test_type, state, func_view_config):
        if state == 'pending_q':
            state = 'pending'
        if test_type == 'functional' and (state == 'fail' or state == 'success'):
            if func_view_config and func_view_config.config_value == '2':
                count_case_fail, count_total, count_fail, count_no_match_baseline = perse_func_result(test_job_id, 2, 0)
                if count_total == 0:
                    state = 'fail'
                    return state
                if count_case_fail > 0:
                    state = 'fail'
                else:
                    if count_fail == 0:
                        state = 'pass'
                    else:
                        if count_no_match_baseline > 0:
                            state = 'fail'
                        else:
                            state = 'pass'
        return state

    @staticmethod
    def get_job_server(server_provider, job_id):
        server = None
        if server_provider == 'aligroup':
            if TestServerSnapshot.objects.filter(job_id=job_id).count() == 1:
                server = TestServerSnapshot.objects.get(job_id=job_id).ip
        else:
            if CloudServerSnapshot.objects.filter(job_id=job_id).count() == 1:
                server = CloudServerSnapshot.objects.get(job_id=job_id).pub_ip
        return server

    def get_report_li(self, job_id, create_name_map):
        report_id_list = ReportObjectRelation.objects.filter(object_type='job', object_id=job_id).values_list(
            'report_id', flat=True)
        plan_relation = PlanInstanceTestRelation.objects.filter(job_id=job_id)
        if plan_relation.exists():
            plan_report_id_li = ReportObjectRelation.objects.filter(object_type='plan_instance',
                                                                    object_id=plan_relation[0].plan_instance_id). \
                values_list('report_id', flat=True)
            if len(plan_report_id_li) > 0:
                report_id_list = chain(report_id_list, plan_report_id_li)
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
            server_objs = TestServerSnapshot.objects.filter(Q(ip=server) | Q(sn=server))
            cloud_server_objs = CloudServerSnapshot.objects.filter(Q(pub_ip=server) | Q(sn=server))
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
        TestJob.objects.filter(id__in=job_id_li).delete()
        for job_id in job_id_li:
            ToneThread(release_server, (job_id,)).start()
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

    def download(self, test_job_id):
        if JobDownloadRecord.objects.filter(job_id=test_job_id).exists():
            JobDownloadRecord.objects.filter(job_id=test_job_id).update(state='running')
        else:
            JobDownloadRecord.objects.create(**dict({'job_id': test_job_id, 'state': 'running'}))
        upload_thread = Thread(target=self._post_background, args=(test_job_id,))
        upload_thread.start()

    def _post_background(self, test_job_id):
        try:
            offline_path = MEDIA_ROOT + OFFLINE_DATA_DIR
            if not os.path.exists(offline_path):
                os.makedirs(offline_path)
            job_path = offline_path + '/' + str(test_job_id)
            self.del_dir(job_path)
            os.makedirs(job_path)
            job_yaml = job_path + '/job.yaml'
            tar_file_name = '/job_%s.tar.gz' % test_job_id
            target_file = job_path + tar_file_name
            result_dir = job_path + '/result'
            if os.path.exists(result_dir):
                os.remove(result_dir)
            os.makedirs(result_dir)
            job = TestJob.objects.filter(id=test_job_id).first()
            if job:
                job_yaml_dict = dict(
                    name=job.name,
                    need_reboot=job.need_reboot,
                    test_config=get_test_config(test_job_id, detail_server=True)
                )
                with open(job_yaml, 'w', encoding='utf-8') as f:
                    yaml.dump(job_yaml_dict, f)
                raw_sql = 'SELECT a.result_path,a.result_file,b.name AS test_suite_name, c.name AS test_case_name ' \
                          'FROM result_file a left join test_suite b ON a.test_suite_id=b.id ' \
                          'LEFT JOIN test_case c ON a.test_case_id=c.id where test_job_id=%s'
                result_files = query_all_dict(raw_sql.replace('\'', ''), [test_job_id])
                for res_file in result_files:
                    oss_file = res_file['result_path'] + res_file['result_file']
                    local_suite_dir = os.path.join(result_dir, res_file['test_suite_name'])
                    if not os.path.exists(local_suite_dir):
                        os.makedirs(local_suite_dir)
                    local_case_dir = os.path.join(local_suite_dir, res_file['test_case_name'])
                    if not os.path.exists(local_case_dir):
                        os.makedirs(local_case_dir)
                    local_file = os.path.join(local_case_dir, res_file['result_file'])
                    file_dir = os.path.dirname(local_file)
                    if not os.path.exists(file_dir):
                        os.makedirs(file_dir)
                    self.download_file(oss_file, local_file)
                tf = tarfile.open(name=target_file, mode='w:gz')
                tf.add(job_yaml, arcname='job.yaml')
                tf.add(result_dir, arcname='result')
                tf.close()
                oss_file = OFFLINE_DATA_DIR + tar_file_name
                ftp_path = oss_file.replace(MEDIA_ROOT.strip('/'), '')
                res = sftp_client.upload_file(target_file, ftp_path)
                if res:
                    oss_link = 'http://' + sftp_client.host + ':' + str(sftp_client.proxy_port) + ftp_path
                    self.del_dir(job_path)
                    JobDownloadRecord.objects.filter(job_id=test_job_id).update(state='success', job_url=oss_link)
                else:
                    JobDownloadRecord.objects.filter(job_id=test_job_id).update(state='success', job_url='ftp upload fail.')
            else:
                JobDownloadRecord.objects.filter(job_id=test_job_id).update(state='fail', job_url='job not exists')
        except Exception as e:
            JobDownloadRecord.objects.filter(job_id=test_job_id).update(state='fail', job_url=str(e))

    def download_file(self, url, target_file):
        req = requests.get(url)
        with open(target_file, 'wb') as f:
            f.write(req.content)

    def del_dir(self, path):
        while 1:
            if not os.path.exists(path):
                break
            try:
                shutil.rmtree(path)
            except PermissionError as e:
                err_file_path = str(e).split("\'", 2)[1]
                if os.path.exists(err_file_path):
                    os.chmod(err_file_path, stat.S_IWUSR)


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

    @staticmethod
    def get_test_prepare(obj):
        date_list = []
        if not obj:
            return date_list
        steps = TestStep.objects.filter(job_id=obj.id, stage__in=PREPARE_STEP_STAGE_MAP.keys())
        cluster_id_list = steps.values_list('cluster_id', flat=True).distinct()
        provider = obj.server_provider
        for cluster_id in cluster_id_list:
            cluster_steps = steps.filter(cluster_id=cluster_id)
            if cluster_id:
                final_state = JobTestPrepareService.get_final_state(cluster_steps)
                cluster_name = JobPrepareInfo.get_cluster_name_for_test_cluster_snapshot_id(cluster_id)
                step_cluster = cluster_steps.order_by('gmt_created')
                last_step = step_cluster.last()
                step_end = cluster_steps.filter(state__in=['success', 'fail', 'stop']).order_by('-gmt_modified').first()
                final_stage = JobTestPrepareService.get_final_stage(final_state, last_step)
                date = {'server_type': 'cluster',
                        'server': cluster_name,
                        'stage': final_stage,
                        'state': final_state,
                        'result': get_result_map("test_prepare",
                                                 last_step.result) if last_step.state == 'running' else "",
                        'gmt_created': datetime.strftime(step_cluster.first().gmt_created, "%Y-%m-%d %H:%M:%S"),
                        'gmt_modified': datetime.strftime(step_end.gmt_modified, "%Y-%m-%d %H:%M:%S"
                                                          ) if step_end and step_end.gmt_modified else "",
                        'server_list': JobPrepareInfo.get_server_dict(cluster_steps, provider)
                        }
                date_list.append(date)
            else:
                server_id_list = cluster_steps.values_list('server', flat=True).distinct()
                for server_id in server_id_list:
                    server_steps = cluster_steps.filter(server=server_id)
                    final_state = JobTestPrepareService.get_final_state(server_steps)
                    server = JobPrepareInfo.get_server_ip_for_snapshot_id(provider, server_id)
                    step_server_order = server_steps.order_by('gmt_created')
                    last_step = step_server_order.last()
                    step_end = server_steps.filter(state__in=['success', 'fail', 'stop']).order_by(
                        '-gmt_modified').first()
                    final_stage = JobTestPrepareService.get_final_stage(final_state, last_step)
                    date = {'server_type': 'standalone',
                            'server': server,
                            'server_id': int(server_id),
                            'stage': final_stage,
                            'state': final_state,
                            'result': get_result_map("test_prepare",
                                                     last_step.result) if last_step.state == 'running' else "",
                            'gmt_created': datetime.strftime(step_server_order.first().gmt_created,
                                                             "%Y-%m-%d %H:%M:%S"),
                            'gmt_modified': datetime.strftime(step_end.gmt_modified, "%Y-%m-%d %H:%M:%S"
                                                              ) if step_end and step_end.gmt_modified else "",
                            'server_list': [JobPrepareInfo.get_server_step_info(provider, step) for step in
                                            server_steps]
                            }
                    date_list.append(date)
        return date_list

    @staticmethod
    def get_final_stage(final_state, last_step):
        final_stage = ""
        if final_state == "running":
            final_stage = PREPARE_STEP_STAGE_MAP.get(last_step.stage)
        elif final_state in ['fail', 'stop']:
            final_stage = 'done'
        elif final_state == 'success':
            if PREPARE_STEP_STAGE_MAP.get(last_step.stage) == PREPARE_STEP_STAGE_MAP['prepare']:
                final_stage = 'done'
            else:
                final_stage = PREPARE_STEP_STAGE_MAP.get(last_step.stage)
        return final_stage

    @staticmethod
    def get_final_state(cluster_steps):
        state_list = cluster_steps.values_list('state', flat=True).distinct()
        final_state = 'success'
        if 'fail' in state_list:
            final_state = 'fail'
        elif 'stop' in state_list:
            final_state = 'stop'
        elif 'running' in state_list:
            final_state = 'running'
        elif set(state_list) == {'success'}:
            final_state = 'success'
        return final_state


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
        if not data.get('state'):
            return test_suites
        else:
            resp = []
            for test_suite in test_suites:
                if not test_suite:
                    continue
                if test_suite['test_type'] == '功能测试':
                    if test_suite['conf_{}'.format(data.get('state'))]:
                        resp.append(test_suite)
                else:
                    if test_suite[data.get('state')]:
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
    def filter_search(result_data, data):
        if data.get('state'):
            test_type = TestJob.objects.filter(id=data.get('job_id')).first().test_type
            if test_type == 'functional':
                result_data = list(
                    filter(lambda x: x.get('result_data').get('case_{}'.format(data.get('state'))), result_data))
            else:
                result_data = list(
                    filter(lambda x: x.get('result_data').get('{}'.format(data.get('state'))), result_data))
        return result_data

    @staticmethod
    def get_test_job_obj(data):
        job_id = data.get('job_id')
        assert job_id, JobTestException(ErrorCode.JOB_NEED)
        return TestJob.objects.get(id=job_id)

    @staticmethod
    def get_perfresult(data, test_type):
        job_id = data.get('job_id')
        suite_id = data.get('suite_id')
        assert job_id, JobTestException(ErrorCode.JOB_NEED)
        assert suite_id, JobTestException(ErrorCode.SUITE_NEED)
        if test_type == PERFORMANCE:
            return PerfResult.objects.filter(test_job_id=job_id, test_suite_id=suite_id)
        else:
            return FuncResult.objects.filter(test_job_id=job_id, test_suite_id=suite_id)


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
        q &= Q(sub_case_name__contains=data.get('sub_case_name')) if data.get('sub_case_name') else q
        queryset = queryset.filter(q)
        return sorted(queryset, key=lambda x: (0 if x.sub_case_result == 2 else 1, x.id))


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
        return queryset.filter(q).order_by('gmt_created')


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

    def _update_job_state(self, data, state, operation_note):
        job_id = data.get('job_id')
        assert job_id, JobTestException(ErrorCode.ID_NEED)
        job_obj = TestJob.objects.filter(id=job_id).first()
        if job_obj.state not in [JobState.PENDING, JobState.PENDING_Q, JobState.RUNNING]:
            raise JobTestException(ErrorCode.STOP_JOB_ERROR[1])
        with transaction.atomic():
            TestJob.objects.filter(
                id=job_id,
                state__in=['running', 'pending', 'pending_q']
            ).update(state=state)
            self._operation_after_stop_job(job_obj, operation_note)

    @staticmethod
    def _operation_after_stop_job(job_obj, operation_note):
        # 1.将未运行suite/case状态改为skip
        TestJobSuite.objects.filter(
            job_id=job_obj.id,
            state=JobCaseState.PENDING
        ).update(state=JobCaseState.SKIP)
        TestJobCase.objects.filter(
            job_id=job_obj.id,
            state=JobCaseState.PENDING
        ).update(state=JobCaseState.SKIP)
        # 2.将正在运行的suite/case状态改为stop
        TestJobSuite.objects.filter(
            job_id=job_obj.id,
            state=JobCaseState.RUNNING
        ).update(state=JobCaseState.STOP)
        TestJobCase.objects.filter(
            job_id=job_obj.id,
            state=JobCaseState.RUNNING
        ).update(state=JobCaseState.STOP)
        # 3.写操作记录
        TestJobCase.objects.filter(
            job_id=job_obj.id
        ).update(note=operation_note)
        # 4.释放机器
        ToneThread(release_server, (job_obj.id,)).start()
        # 7.回调接口
        if job_obj.callback_api:
            JobCallBack(
                job_id=job_obj.id,
                callback_type=CallBackType.JOB_STOPPED
            ).callback()

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
        TestJobCase.objects.filter(
            id=test_job_conf_id, state__in=['pending', 'running']
        ).update(state=state)
        TestJobCase.objects.filter(id=test_job_conf_id).update(note=operation_note)


def release_server(test_job_id):
    # 1.释放单机机器
    for server_model in [TestServer, CloudServer]:
        server_model.objects.filter(
            occupied_job_id=test_job_id
        ).update(
            state=TestServerState.AVAILABLE,
            occupied_job_id=None
        )
    # 2.释放集群机器
    if TestJobCase.objects.filter(job_id=test_job_id, run_mode='cluster').exists():
        q = Q(occupied_job_id=test_job_id) | Q(occupied_job_id__isnull=True)
        TestCluster.objects.filter(q).update(is_occpuied=0, occupied_job_id=None)
    # 3.清除redis数据
    try:
        using_server = runner_redis_cache.hgetall('tone-runner-using_server')
        for key in using_server:
            if using_server[key] == str(test_job_id):
                runner_redis_cache.hdel('tone-runner-using_server', key)
    except Exception as e:
        logger.warning(f'release server from redis error: {e}')


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


class MachineFaultService(CommonService):
    @staticmethod
    def get_machine_fault(data):
        q = Q()
        if data.get('job_id'):
            if not str(data.get('job_id')).isdigit():
                raise JobTestException(ErrorCode.TEST_JOB_NONEXISTENT)
            job_id = data.get('job_id')
            server_provider = TestJob.objects.filter(id=job_id).first().server_provider
            cluster_server = TestJobCase.objects.filter(
                job_id=job_id, state__in=['pending', 'running'], run_mode='cluster').values('server_object_id')
            cluster_server_id = None
            if cluster_server:
                cluster_server_id = TestClusterServer.objects.filter(cluser_id__in=cluster_server).values('server_id')
            test_server = TestJobCase.objects.filter(
                job_id=job_id, state__in=['pending', 'running'], run_mode='standalone').values('server_object_id')
            if cluster_server_id:
                test_server.extend(cluster_server_id)
            if server_provider == 'aligroup':
                if test_server:
                    q = Q(id__in=test_server) & Q(state='Broken')
                    return TestServer.objects.filter(q)
                else:
                    test_server_snapshot = TestJobCase.objects.filter(
                        job_id=job_id, state__in=['pending', 'running']).values('server_snapshot_id')
                    q = Q(id__in=test_server_snapshot) & Q(state='Broken')
                    return TestServerSnapshot.objects.filter(q)
            else:
                if test_server:
                    q = Q(id__in=test_server) & Q(state='Broken')
                    return CloudServer.objects.filter(q)
                else:
                    cloud_server_snapshot = TestJobCase.objects.filter(
                        job_id=job_id, state__in=['pending', 'running']).values('server_snapshot_id')
                    q = Q(id__in=cloud_server_snapshot) & Q(state='Broken')
                    return CloudServerSnapshot.objects.filter(q)
        else:
            raise JobTestException(ErrorCode.JOB_NEED)


def package_server_list(job):
    server_li = list()
    ip_li = list()
    if not job:
        return server_li
    snap_shot_objs = TestServerSnapshot.objects.filter(
        job_id=job.id) if job.server_provider == 'aligroup' else CloudServerSnapshot.objects.filter(job_id=job.id)
    for snap_shot_obj in snap_shot_objs:
        ip = snap_shot_obj.ip if job.server_provider == 'aligroup' else snap_shot_obj.pub_ip
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
    return server_li


class JobPrepareInfo:
    @staticmethod
    def get_server_ip_for_snapshot_id(provider, server_id):
        if provider == 'aligroup':
            server = TestServerSnapshot.objects.get(id=server_id).ip
        else:
            server = CloudServerSnapshot.objects.get(id=server_id).private_ip
        return server

    @staticmethod
    def get_server_step_info(provider, step):
        return {
            'stage': PREPARE_STEP_STAGE_MAP.get(step.stage),
            'state': step.state,
            'result': get_result_map("test_prepare", step.result),
            'tid': step.tid,
            'log_file': step.log_file,
            'server_id': int(step.server) if step.server.isdigit() else None,
            'server_description': get_check_server_ip(step.server, provider,
                                                      return_field='description') if step.server.isdigit() else "",
            'gmt_created': datetime.strftime(step.gmt_created, "%Y-%m-%d %H:%M:%S"),
            'gmt_modified': datetime.strftime(step.gmt_modified, "%Y-%m-%d %H:%M:%S"
                                              ) if step.state in ['success', 'fail', 'stop'] else ""
        }

    @staticmethod
    def get_cluster_name_for_test_cluster_snapshot_id(test_step_cluster_id):
        test_cluster_snapshot = TestClusterSnapshot.objects.filter(id=test_step_cluster_id).first()
        cluster_name = ""
        if test_cluster_snapshot:
            source_cluster_id = test_cluster_snapshot.source_cluster_id
            test_cluster = TestCluster.objects.filter(id=source_cluster_id).first()
            if test_cluster:
                cluster_name = test_cluster.name
                if not cluster_name:
                    cluster_name = TestCluster.objects.filter(id=test_cluster_snapshot,
                                                              query_scope='deleted').first().name
        return cluster_name

    @staticmethod
    def get_server_dict(cluster_steps, provider):
        server_dict = {}
        server_id_list = cluster_steps.values_list('server', flat=True).distinct()
        for server_id in server_id_list:
            server_steps = cluster_steps.filter(server=server_id)
            server = JobPrepareInfo.get_server_ip_for_snapshot_id(provider, server_id)
            server_dict[server] = []
            for step in server_steps:
                server_dict[server].append(JobPrepareInfo.get_server_step_info(provider, step))
        return server_dict
