# flake8: noqa
import logging
import shutil
import traceback
import uuid
import re
import tarfile
import json
import time
import datetime
import os
import random
import string
import yaml
from threading import Thread
from django.db.models import Q
from django.db import transaction
from urllib.parse import unquote

from tone import settings
from tone.core.utils.sftp_client import sftp_client
from tone.models.job.upload_models import OfflineUpload
from tone.models.job.job_models import TestJob, TestJobCase, TestJobSuite, TestStep
from tone.models.sys.workspace_models import Project
from tone.models.sys.testcase_model import TestSuite, TestCase, TestMetric
from tone.models.sys.server_models import TestServer, TestServerSnapshot, CloudServer, CloudServerSnapshot,\
    TestCluster, TestClusterServer
from tone.models.job.result_models import FuncResult, PerfResult, ResultFile
from tone.models.sys.baseline_models import PerfBaselineDetail, Baseline
from tone.core.common.constant import OFFLINE_DATA_DIR, RESULTS_DATA_DIR
from tone.settings import MEDIA_ROOT, BASE_DIR
from tone.services.job.test_services import JobTestService

logger = logging.getLogger(__name__)


class OfflineDataUploadService(object):

    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('id'):
            q &= Q(id=data.get('id'))
        if data.get('name'):
            q &= Q(file_name__icontains=data.get('name'))
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        return queryset.filter(q)

    def post(self, data, file, operator):
        original_file_name = file.name
        file_bytes = file.read()
        code, msg, offline_upload_id = self._valid_params(data, file_bytes, original_file_name, operator)
        if code == 201:
            return code, msg
        upload_thread = Thread(target=self._post_background, args=(data, file_bytes, operator, offline_upload_id))
        upload_thread.start()
        return 200, ''

    def _valid_params(self, data, file_bytes, original_file_name, operator):
        if not operator or not operator.id:
            code = 201
            msg = '登录信息失效，请重新登录。'
            return code, msg, 0
        file_path = MEDIA_ROOT + OFFLINE_DATA_DIR
        if not os.path.exists(file_path):
            os.makedirs(file_path)
        file_name = file_path + '/' + str(uuid.uuid4()) + '.' + 'tar'
        open(file_name, 'wb').write(file_bytes)
        tmp_tar = tarfile.open(file_name, 'r')
        if not data.get('test_type') in ('functional', 'performance'):
            code = 201
            msg = '不支持的测试类型。'
            tmp_tar.close()
            os.remove(file_name)
            return code, msg, 0
        try:
            tmp_yaml = yaml.load(tmp_tar.extractfile('job.yaml').read(), Loader=yaml.FullLoader)
        except Exception as e:
            code = 201
            msg = f'job.yaml文件解析错误。{str(e)}'
            tmp_tar.close()
            os.remove(file_name)
            return code, msg, 0
        if 'test_config' not in tmp_yaml:
            code = 201
            msg = 'job.yaml需要test_config节点数据。'
            tmp_tar.close()
            os.remove(file_name)
            return code, msg, 0
        if data.get('server_type') not in ('aligroup', 'aliyun'):
            code = 201
            msg = '请求参数机器类型错误。'
            tmp_tar.close()
            os.remove(file_name)
            return code, msg, 0
        code, msg, _ = self._valid_server_param(tmp_tar, file_name, data, tmp_yaml['test_config'])
        if code == 201:
            return code, msg, 0
        tmp_tar.close()
        os.remove(file_name)
        upload_dict = dict()
        upload_dict['file_name'] = original_file_name
        upload_dict['file_link'] = ''
        upload_dict['project_id'] = data.get('project_id')
        upload_dict['baseline_id'] = data.get('baseline_id', 0)
        upload_dict['test_type'] = data.get('test_type')
        upload_dict['test_job_id'] = 0
        upload_dict['ws_id'] = data.get('ws_id')
        upload_dict['uploader'] = operator.id
        upload_dict['state'] = 'file'
        upload_dict['state_desc'] = '上传文件中'
        offline_upload = OfflineUpload.objects.create(**upload_dict)
        return 200, '', offline_upload.id

    def _valid_server_param(self, tmp_tar, file_name, data, yaml_test_config):
        code = 200
        msg = ''
        for test_suite in yaml_test_config:
            if 'cases' not in test_suite:
                code = 201
                msg = 'test_config下需要cases节点数据。'
                tmp_tar.close()
                os.remove(file_name)
                return code, msg, 0
            for test_case in test_suite['cases']:
                if 'server' not in test_case:
                    code = 201
                    msg = 'test_config下需要server节点数据。'
                    tmp_tar.close()
                    os.remove(file_name)
                    return code, msg, 0
                if not test_case['server']:
                    code = 201
                    msg = 'case下需要server节点数据。'
                    tmp_tar.close()
                    os.remove(file_name)
                    return code, msg, 0
                if data.get('server_type') == 'aligroup' and 'ip' not in test_case['server']:
                    code = 201
                    msg = '内网测试需要cases下ip节点数据。'
                    tmp_tar.close()
                    os.remove(file_name)
                    return code, msg, 0
                if data.get('server_type') == 'aliyun' and 'instance' not in test_case['server']:
                    code = 201
                    msg = '云上测试需要cases下instance节点数据。'
                    tmp_tar.close()
                    os.remove(file_name)
                    return code, msg, 0
        return code, msg, 0

    def _post_background(self, req_data, file_bytes, operator, offline_upload_id):
        file_name, oss_link = self.upload_tar(file_bytes)
        if not file_name:
            msg = 'sftp上传文件失败。'
            OfflineUpload.objects.filter(id=offline_upload_id).update(state='fail', state_desc=msg)
            return
        OfflineUpload.objects.filter(id=offline_upload_id).update(file_link=oss_link,
                                                                  state='running', state_desc='文件解析中')
        local_file = MEDIA_ROOT + file_name
        if not os.path.exists(local_file):
            msg = '上传文件 %s 不存在。' % local_file
            OfflineUpload.objects.filter(id=offline_upload_id).update(state='fail', state_desc=msg)
            return
        try:
            code, msg = self._upload_tar(local_file, req_data, offline_upload_id, operator)
            os.remove(local_file)
        except Exception as ex:
            code = 201
            traceback.print_exc()
            msg = '上传失败:%s.' % str(ex)
        if code == 201:
            OfflineUpload.objects.filter(id=offline_upload_id).update(state='fail', state_desc=msg)

    def _upload_tar(self, filename, req_data, offline_id, operator):
        ws_id = req_data.get('ws_id')
        baseline_id = req_data.get('baseline_id', 0)
        server_type = req_data.get('server_type')
        tar_file = tarfile.open(filename, 'r')
        test_type = req_data.get('test_type')
        ip = req_data.get('ip', '')
        args = yaml.load(tar_file.extractfile('job.yaml').read(), Loader=yaml.FullLoader)
        code, msg, test_config = self.handle_test_config(args['test_config'], test_type)
        if code == 201:
            tar_file.close()
            return code, msg
        job_data = self.build_job_data(args, req_data, test_config)
        with transaction.atomic():
            test_job = JobTestService().create(job_data, operator)
            if not test_job:
                code = 201
                msg = 'Job创建失败。'
                tar_file.close()
                return code, msg
            test_job_id = test_job.id

            code, msg, start_date, end_date = self.handle_result_file(baseline_id, tar_file, test_job_id, test_type, ip,
                                                                      args['test_config'], server_type, ws_id)
            if code == 201:
                tar_file.close()
                return code, msg
            TestJob.objects.filter(id=test_job_id).update(start_time=start_date, end_time=end_date)
            self._create_test_step(test_job_id)
            if code == 200:
                OfflineUpload.objects.filter(id=offline_id).update(test_job_id=test_job_id,
                                                                   state_desc='begin upload file to ftp.')
        code = self.upload_result_file(tar_file, test_job_id, test_type)
        if code == 200:
            OfflineUpload.objects.filter(id=offline_id).update(test_job_id=test_job_id, state='success',
                                                               state_desc='')
            msg = 'upload success.'
        tar_file.close()
        return code, msg

    def _save_server(self, args, server_type, test_job_id, ws_id, req_ip):
        server_id = 0
        server_snapshot_id = 0
        ip = args.get('ip', '')
        if req_ip:
            ip = req_ip
        if not ip:
            return server_id, server_snapshot_id
        if server_type == 'aligroup':
            server_id = self._save_server_info(ip, ws_id)
            server_snapshot_id = self._save_server_snapshot(ip, ws_id, test_job_id)
        elif server_type == 'aliyun':
            server_id = self._save_cloud_info(ip, ws_id, test_job_id)
            server_snapshot_id = self._save_cloud_snapshot(ip, ws_id, test_job_id)
        return server_id, server_snapshot_id

    def _save_cluster_server(self, server_list, server_type, test_job_id, ws_id):
        server_snapshot_id = 0
        test_cluster_obj = dict(
            name=''.join(random.sample(string.ascii_letters + string.digits, 18)),
            cluster_type=server_type,
            ws_id=ws_id,
            occupied_job_id=test_job_id
        )
        test_cluster = TestCluster.objects.create(**test_cluster_obj)
        for server_info in server_list:
            server_id = 0
            if server_type == 'aligroup':
                server_id = self._save_server_info(server_info, ws_id)
            elif server_type == 'aliyun':
                server_id = self._save_cloud_info(server_info, ws_id, test_job_id)
            test_cluster_server_obj = dict(
                cluster_id=test_cluster.id,
                server_id=server_id,
                cluster_type=server_type,
                role=server_info['role'],
                baseline_server=0,
                kernel_install=0
            )
            TestClusterServer.objects.create(**test_cluster_server_obj)
        return test_cluster.id, server_snapshot_id

    def build_job_data(self, job_info, data, test_config):
        job_data = dict()
        job_data['job_type_id'] = data.get('job_type_id')
        if 'name' in job_info and job_info['name']:
            job_data['name'] = job_info['name']
        job_data['state'] = 'success'
        job_data['cleanup_info'] = job_info.get('cleanup_info', '')
        job_data['kernel_info'] = job_info.get('kernel_info', dict())
        job_data['script_info'] = job_info.get('script_info', list())
        job_data['iclone_info'] = job_info.get('iclone_info', dict())
        job_data['rpm_info'] = job_info.get('rpm_info', list())
        job_data['env_info'] = job_info.get('env_info', dict())
        job_data['monitor_info'] = job_info.get('monitor_info', list())
        job_data['notice_info'] = job_info.get('notice_info', list())
        job_data['build_pkg_info'] = job_info.get('build_pkg_info', dict())
        job_data['need_reboot'] = job_info.get('need_reboot', 0)
        job_data['kernel_version'] = job_info.get('kernel_version', '')
        job_data['project_id'] = 0
        project = Project.objects.filter(id=data.get('project_id')).first()
        if project:
            job_data['project_id'] = project.id
        job_data['baseline_id'] = 0
        baseline = Baseline.objects.filter(name=data.get('baseline')).first()
        if baseline:
            job_data['baseline_id'] = baseline.id
        job_data['test_config'] = test_config
        job_data['data_from'] = 'import'
        job_data['test_result'] = self.get_suite_summary(test_config)
        return job_data

    def handle_test_config(self, tar_test_config, test_type):
        msg = ''
        code = 200
        test_config = list()
        for suite_obj in tar_test_config:
            suite_dict = dict()
            suite_name = suite_obj['test_suite']
            case_list = list()
            for case_obj in suite_obj['cases']:
                case_dict = dict()
                case_name = case_obj['test_case']
                test_suite = TestSuite.objects.filter(test_type=test_type, name=suite_name, test_framework='tone').first()
                if not test_suite:
                    continue
                test_case = TestCase.objects.filter(name=case_name, test_suite_id=test_suite.id).first()
                if not test_case:
                    code = 201
                    msg = 'case [%s] 不存在，请先同步用例。' % case_name
                    return code, msg, ''
                suite_dict['test_suite'] = test_suite.id
                suite_dict['state'] = 'success'
                case_dict['test_case'] = test_case.id
                case_dict['state'] = 'success'
                if not any(d['test_case'] == test_case.id for d in case_list):
                    case_list.append(case_dict)
                suite_dict['cases'] = case_list
                if not any(d['test_suite'] == test_suite.id for d in test_config):
                    test_config.append(suite_dict)
        return code, msg, test_config

    def handle_result_file(self, baseline_id, tar_file, test_job_id, test_type, req_ip, test_config, server_type, ws_id):
        msg = ''
        code = 200
        result_file_list = []
        start_date = datetime.datetime.now()
        end_date = datetime.datetime.fromtimestamp(86400)
        _timestamp = int(round(time.time() * 1000000))
        for filename in tar_file.getnames():
            in_file = tar_file.getmember(filename)
            if in_file.isfile() and filename.count('/') > 2 and filename.startswith('result'):
                tmp_list = filename.split('/')
                suite_name = tmp_list[1]
                case_short_name = tmp_list[2]
                test_suite = TestSuite.objects.filter(test_type=test_type, name=suite_name, test_framework='tone').first()
                if not test_suite:
                    continue
                test_case = TestCase.objects.filter(short_name=case_short_name, test_suite_id=test_suite.id).first()
                if not test_case:
                    return 201, '', 'case [%s] not exist error.' % case_short_name
                result_file = filename.split(case_short_name)[1][1:]
                local_dir = '%s%d/%s_%d/%s' % (MEDIA_ROOT, test_job_id, case_short_name, _timestamp, result_file)
                result_link = f'http://{settings.TONE_STORAGE_HOST}:{settings.TONE_STORAGE_PROXY_PORT}' \
                              f'{RESULTS_DATA_DIR}/{local_dir.strip(MEDIA_ROOT).strip(result_file)}'
                result_file = ResultFile(
                    test_job_id=test_job_id,
                    test_suite_id=test_suite.id,
                    test_case_id=test_case.id,
                    result_path=result_link,
                    result_file=result_file,
                    archive_file_id=0
                )
                result_file_list.append(result_file)
                if in_file.name.find('statistic.json') > -1:
                    avg_file = json.loads(tar_file.extractfile(filename).read())
                    tmp_start = datetime.datetime.fromtimestamp(avg_file['testinfo']['start'])
                    tmp_end = datetime.datetime.fromtimestamp(avg_file['testinfo']['end'])
                    if tmp_start < start_date:
                        start_date = tmp_start
                    if tmp_end > end_date:
                        end_date = tmp_end
                    suite_list = [suite_conf for suite_conf in test_config if suite_name == suite_conf['test_suite']]
                    if len(suite_list) > 0:
                        case_list = [case_conf for case_conf in suite_list[0]['cases'] if
                                     test_case.name == case_conf['test_case']]
                        if len(case_list) > 0:
                            server = case_list[0]['server']
                            server_id, server_snapshot_id = self._save_server(server, server_type, test_job_id, ws_id,
                                                                               req_ip)
                            TestJobCase.objects.filter(job_id=test_job_id, test_suite_id=test_suite.id,
                                                       test_case_id=test_case.id).update(
                                state='success', server_object_id=server_id,
                                server_snapshot_id=server_snapshot_id,
                                start_time=tmp_start, end_time=tmp_end)
                            TestJobSuite.objects.filter(job_id=test_job_id, test_suite_id=test_suite.id).\
                                update(state='success', start_time=tmp_start, end_time=tmp_end)
                    if test_type == 'performance':
                        code, msg = self.import_perf_avg(test_job_id, avg_file['results'], test_suite.id,
                                                         test_case.id, start_date, end_date, baseline_id)
                    else:
                        code, msg = self.import_func_avg(test_job_id, avg_file['results'], test_suite.id,
                                                         test_case.id, start_date, end_date)
        ResultFile.objects.bulk_create(result_file_list)
        return code, msg, start_date, end_date

    def upload_result_file(self, tar_file, test_job_id, test_type):
        code = 200
        _timestamp = int(round(time.time() * 1000000))
        for filename in tar_file.getnames():
            in_file = tar_file.getmember(filename)
            if in_file.isfile() and filename.count('/') > 2 and filename.startswith('result'):
                tmp_list = filename.split('/')
                suite_name = tmp_list[1]
                case_short_name = tmp_list[2]
                test_suite = TestSuite.objects.filter(test_type=test_type, name=suite_name, test_framework='tone').first()
                if not test_suite:
                    continue
                test_case = TestCase.objects.filter(short_name=case_short_name, test_suite_id=test_suite.id).first()
                if not test_case:
                    return 201, '', 'case [%s] not exist error.' % case_short_name
                result_file = filename.split(case_short_name)[1][1:]
                local_dir = '%s%d/%s_%d/%s' % (MEDIA_ROOT, test_job_id, case_short_name, _timestamp, result_file)
                if not os.path.exists(local_dir.rsplit('/', 1)[0]):
                    os.makedirs(local_dir.rsplit('/', 1)[0])
                open(local_dir, 'wb').write(tar_file.extractfile(filename).read())
                sftp_client.upload_file(local_dir, '/' + local_dir.replace(MEDIA_ROOT.strip('/'), RESULTS_DATA_DIR.strip('/')))
        shutil.rmtree(f'{MEDIA_ROOT}{test_job_id}')
        return code

    def _create_test_step(self, test_job_id):
        test_step_list = list()
        test_job_case_list = TestJobCase.objects.filter(job_id=test_job_id)
        for test_job_case in test_job_case_list:
            test_job_suite = TestJobSuite.objects.\
                filter(job_id=test_job_id, test_suite_id=test_job_case.test_suite_id).first()
            if test_job_suite:
                test_step_dict = TestStep(
                    job_id=test_job_id,
                    state='success',
                    stage='initcloud',
                    job_case_id=test_job_case.id,
                    job_suite_id=test_job_suite.id,
                    dag_step_id=0,
                    server=0
                )
                test_step_list.append(test_step_dict)
        TestStep.objects.bulk_create(test_step_list)

    def _save_server_info(self, ip, ws_id):
        test_server = TestServer.objects.filter(ip=ip, ws_id=ws_id).first()
        if not test_server:
            server_dict = dict(
                ip=ip,
                parent_server_id=0,
                device_type='phy_server',
                state='Available',
                real_state='Available',
                use_type='task',
                channel_state=False,
                owner=0,
                ws_id=ws_id,
                in_pool=True,
                spec_use=0
            )
            test_server = TestServer.objects.create(**server_dict)
        return test_server.id

    def _save_cloud_info(self, ip, ws_id, test_job_id):
        cloud_server = CloudServer.objects.filter(instance_id=ip, ws_id=ws_id).first()
        if not cloud_server:
            cloud_dict = dict(
                job_id=test_job_id,
                instance_id=ip,
                ws_id=ws_id,
                bandwidth=0,
                parent_server_id=0
            )
            cloud_server = CloudServer.objects.create(**cloud_dict)
        return cloud_server.id

    def _save_server_snapshot(self, ip, ws_id, test_job_id):
        test_server_snapshot = TestServerSnapshot.objects.filter(ip=ip, ws_id=ws_id).first()
        if not test_server_snapshot:
            server_dict = dict(
                ip=ip,
                ws_id=ws_id,
                job_id=test_job_id
            )
            test_server_snapshot = TestServerSnapshot.objects.create(**server_dict)
        return test_server_snapshot.id

    def _save_cloud_snapshot(self, ip, ws_id, test_job_id):
        cloud_server_snapshot = CloudServerSnapshot.objects.filter(job_id=test_job_id,
                                                                   instance_id=ip, ws_id=ws_id).first()
        if not cloud_server_snapshot:
            cloud_server_dict = dict(
                instance_id=ip,
                ws_id=ws_id,
                job_id=test_job_id
            )
            cloud_server_snapshot = CloudServerSnapshot.objects.create(**cloud_server_dict)
        return cloud_server_snapshot.id

    def _valid_tar(self, msg, result_file, tar_index):
        if 'rpmlist' not in tar_index:
            msg = 'miss rpmlist file'
        if 'tenv.text' not in tar_index:
            msg = 'miss tenv.text file'
        if 'tone_meta' not in tar_index:
            msg = 'miss tone_meta file'
        if 'version' not in tar_index:
            msg = 'miss version file'
        if result_file not in tar_index:
            msg = 'miss statistic.json file'
        return msg

    def import_func_avg(self, test_job_id, results, test_suite_id, test_case_id, start_date, end_date):
        func_obj_list = []
        for item in results:
            func_history = FuncResult.objects.filter(test_job_id=test_job_id, test_suite_id=test_suite_id,
                                                     test_case_id=test_case_id, sub_case_name=item['testcase']).first()
            if func_history:
                return 201, 'sub_case_name [%s] data is existed' % item['testcase']
            case_result = 5
            if 'Fail' not in item['matrix'] and 'Pass' in item['matrix']:
                case_result = 1
            elif 'Fail' in item['matrix']:
                case_result = 2
            func_obj = FuncResult(
                test_job_id=test_job_id,
                test_suite_id=test_suite_id,
                test_case_id=test_case_id,
                sub_case_name=item['testcase'],
                sub_case_result=case_result,
                match_baseline=0,
                gmt_created=start_date,
                gmt_modified=end_date,
                dag_step_id=0
            )
            func_obj_list.append(func_obj)
        FuncResult.objects.bulk_create(func_obj_list)
        return 200, ''

    def get_case_state(self, results, test_type):
        state = 'success'
        if test_type == 0:
            fail_count = 0
            skip_count = 0
            success_count = 0
            for item in results:
                if 'Pass' in item['matrix']:
                    success_count += 1
                if 'Fail' in item['matrix']:
                    fail_count += 1
                if 'Skip' in item['matrix']:
                    skip_count += 1
            if fail_count == 0 and success_count == 0 and skip_count > 0:
                state = 'skip'
            if fail_count > 0:
                state = 'fail'
            if fail_count == 0 and success_count > 0:
                state = 'success'
        return state

    def get_suite_summary(self, test_config):
        fail_count = 0
        skip_count = 0
        success_count = 0
        for suite in test_config:
            case_fail_count = 0
            case_skip_count = 0
            case_success_count = 0
            for case_info in suite['cases']:
                if case_info['state'] == 'skip':
                    case_skip_count += 1
                if case_info['state'] == 'fail':
                    case_fail_count += 1
                if case_info['state'] == 'success':
                    case_success_count += 1
            if case_fail_count == 0 and case_success_count == 0 and case_skip_count > 0:
                skip_count += 1
            if case_fail_count > 0:
                fail_count += 1
            if case_fail_count == 0 and case_success_count > 0:
                success_count += 1
        return '{"total": %d, "pass": %d, "fail": %d}' % (len(test_config), success_count, fail_count)

    def import_perf_avg(self, test_job_id, results, test_suite_id, test_case_id, start_date, end_date, baseline_id):
        perf_obj_list = []
        metric_obj_list = []
        for item in results:
            perf_history = PerfResult.objects.filter(test_job_id=test_job_id, test_suite_id=test_suite_id,
                                                     test_case_id=test_case_id, metric=item['metric']).first()
            if perf_history:
                return 201, 'metric [%s] 已存在，导入数据失败。' % item['metric']
            baseline_value = '0'
            baseline_cv_value = ''
            baseline = PerfBaselineDetail.objects.filter(baseline_id=baseline_id, test_job_id=test_job_id,
                                                         test_suite_id=test_suite_id, test_case_id=test_case_id,
                                                         metric=item['metric']).first()
            if baseline:
                baseline_value = baseline.value
                baseline_cv_value = baseline.cv_value
            compare_result = 0.00
            if baseline_value and float(baseline_value) > 0:
                compare_result = (float(item['average']) - float(baseline_value)) / float(baseline_value)
            track_result = self._get_cmp_result(compare_result, item, baseline_value, test_case_id, test_suite_id)
            perf_obj = PerfResult(
                test_job_id=test_job_id,
                test_suite_id=test_suite_id,
                test_case_id=test_case_id,
                metric=item['metric'],
                test_value=item['average'],
                unit=item['unit'],
                cv_value='±{0:.2f}%'.format(item['cv'] * 100),
                max_value=max(item['matrix']),
                min_value=min(item['matrix']),
                value_list=item['matrix'],
                repeat=len(item['matrix']),
                match_baseline=0,
                compare_baseline=baseline_id,
                baseline_value=baseline_value,
                baseline_cv_value=baseline_cv_value,
                compare_result=str(compare_result),
                track_result=track_result,
                gmt_created=start_date,
                gmt_modified=end_date,
                dag_step_id=0
            )
            perf_obj_list.append(perf_obj)
            metric_obj = TestMetric(
                name=item['metric'],
                object_type='case',
                object_id=test_case_id,
                cv_threshold=item['cv'],
                cmp_threshold=0,
                direction='increase',
                unit=item['unit']
            )
            if not TestMetric.objects.filter(object_id=test_case_id, object_type='case', name=item['metric']).exists():
                metric_obj_list.append(metric_obj)
        PerfResult.objects.bulk_create(perf_obj_list)
        TestMetric.objects.bulk_create(metric_obj_list)
        return 200, ''

    def _get_cmp_result(self, compare_result, item, baseline_value, test_case_id, test_suite_id):
        track_result = 'na'
        cmp_threshold = 0
        if baseline_value:
            test_metric = TestMetric.objects.filter(object_type='case', object_id=test_case_id,
                                                    name=item['metric']).first()
            if test_metric:
                cmp_threshold = test_metric.cmp_threshold
            else:
                test_metric = TestMetric.objects.filter(object_type='suite', object_id=test_suite_id,
                                                        name=item['metric']).first()
                if test_metric:
                    cmp_threshold = test_metric.cmp_threshold
            if cmp_threshold > 0:
                if -cmp_threshold <= compare_result <= cmp_threshold:
                    track_result = 'normal'
                elif -cmp_threshold > compare_result:
                    track_result = 'decline'
                elif compare_result > cmp_threshold:
                    track_result = 'increase'
        return track_result

    def upload_tar(self, file_bytes):
        file_name = str(uuid.uuid4()) + '.' + 'tar'
        local_dir = MEDIA_ROOT + file_name
        if not os.path.exists(MEDIA_ROOT):
            os.makedirs(MEDIA_ROOT)
        open(local_dir, 'wb').write(file_bytes)
        server_dir = f'{OFFLINE_DATA_DIR}/{file_name}'
        ret = sftp_client.upload_file(local_dir, server_dir)
        # os.remove(local_dir)
        if ret:
            file_link = 'http://{}:{}{}/{}'.format(
                settings.TONE_STORAGE_HOST,
                settings.TONE_STORAGE_PROXY_PORT,
                OFFLINE_DATA_DIR,
                file_name
            )
            return file_name, file_link
        return '', ''

    def delete(self, pk):
        OfflineUpload.objects.filter(id=pk).delete()
