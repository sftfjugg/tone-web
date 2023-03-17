# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import copy
import random
import string
from datetime import datetime

from tone.core.utils.common_utils import kernel_info_format
from tone.core.utils.verify_tools import check_ip
from tone.models import Project, TestJob, JobType, TestTemplate, TestTmplCase, TestTmplSuite, \
    TemplateTagRelation, JobTagRelation, TestJobCase, TestJobSuite, TestServerSnapshot, CloudServerSnapshot, \
    TestServer, CloudServer, TestCluster, JobTag
from tone.core.handle.base_handle import BaseHandle
from tone.core.common.constant import MonitorType
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import JobTestException
from tone.core.common.job_result_helper import get_server_ip_sn


class JobDataHandle(BaseHandle):

    def pack_custom(self):  # noqa: C901
        """
        组装data_dic、tag_list数据
        """
        if self.data_from == 'custom':
            self.data_dic['job_type_id'] = job_type_id = self.data.get('job_type')
            assert job_type_id, JobTestException(ErrorCode.TYPE_ID_LACK)
            self.ws_id = JobType.objects.get(id=job_type_id).ws_id
            self.data_dic['ws_id'] = self.ws_id
            job_type = JobType.objects.get(id=job_type_id)
            self.data_dic['name'] = self.job_format(self.data)
            if self.data.get('baseline'):
                self.data_dic['baseline_id'] = self.data.get('baseline')
            self.data_dic['baseline_job_id'] = self.data.get('baseline_job_id')
            if self.data.get('cleanup_info'):
                self.data_dic['cleanup_info'] = self.data.get('cleanup_info')
            if self.data.get('tags') and isinstance(self.data.get('tags'), list):
                [self.tag_list.append(tag) for tag in self.data.get('tags')]
            if self.data.get('iclone_info'):
                iclone_info = self.data.get('iclone_info')
                creator_name = self.operator.first_name if self.operator.first_name else self.operator.last_name
                iclone_info['create_from'] = creator_name
                self.data_dic['iclone_info'] = self.data.get('iclone_info')
            else:
                self.data_dic['iclone_info'] = dict()
            self.data_dic['kernel_info'] = self.data.get('kernel_info', dict())
            self.data_dic['build_pkg_info'] = self.data.get('build_pkg_info', dict())
            self.data_dic['script_info'] = self.data.get('script_info', list())
            self.data_dic['rpm_info'] = self.calibration_rpm_data(self.data.get('rpm_info', list()))
            self.data_dic['monitor_info'] = self.restructure_monitor_info(self.data.get('monitor_info', list()))
            self.data_dic['need_reboot'] = self.data.get('need_reboot', False)
            self.data_dic['console'] = self.data.get('console', False)
            self.data_dic['callback_api'] = self.data.get('callback_api')
            self.data_dic['report_name'], self.data_dic['report_template_id'] = self.get_report_info()
            notice_info = self.data.get('notice_info', None)
            if notice_info:
                self.data_dic['notice_info'] = notice_info
            else:
                self.data_dic['notice_info'] = self.pack_notice_info(email=self.data.get('email', None),
                                                                     ding=self.data.get('ding_token', None),
                                                                     subject=self.data.get('notice_subject', None))
            self.data_dic['kernel_version'] = self.data_dic['show_kernel_version'] = self.data.get('kernel_version')
            self.data_dic['env_info'] = self.pack_env_info(self.data.get('env_info')) if self.data.get(
                'env_info') else dict()
            self.data_dic['server_provider'] = self.provider = job_type.server_type
            self.data_dic['test_type'] = job_type.test_type
            if self.data.get('project'):
                project_id = self.data.get('project')
            else:
                project_id = Project.objects.filter(is_default=True, ws_id=self.ws_id).first().id \
                    if Project.objects.filter(is_default=True, ws_id=self.ws_id).exists() else None
            self.data_dic['project_id'] = project_id
            self.data_dic['product_id'] = self.get_product(self.data_dic['project_id'])
            self.data_dic['note'] = self.data.get('note', '')
        elif self.data_from == 'template':
            api = self.data.get('api', None)
            template_id = self.data.get('template_id')
            assert template_id, JobTestException(ErrorCode.TEMPLATE_NEED)
            if not TestTemplate.objects.filter(id=template_id).exists():
                raise JobTestException(ErrorCode.TEMPLATE_DUPLICATION)
            template_obj = TestTemplate.objects.get(id=template_id)
            self.template_obj = template_obj
            self.data_dic['tmpl_id'] = template_obj.id
            self.data_dic['baseline_id'] = self.data.get('baseline', template_obj.baseline_id)
            self.data_dic['baseline_job_id'] = self.data.get('baseline_job_id', template_obj.baseline_job_id)
            self.data_dic['cleanup_info'] = self.data.get('cleanup_info', template_obj.cleanup_info)
            if self.data.get('tags') and isinstance(self.data.get('tags'), list):
                [self.tag_list.append(tag) for tag in self.data.get('tags')]
            else:
                tag_id_list = [tag.tag_id for tag in TemplateTagRelation.objects.filter(template_id=template_id)]
                tags = [tag_id for tag_id in tag_id_list if JobTag.objects.filter(id=tag_id).exists()]
                self.tag_list.extend(tags)
            if self.data.get('name'):
                if '{date}' in self.data.get('name'):
                    self.data_dic['name'] = self.data.get('name').replace('{date}', '_' + str(datetime.now().date()))
                else:
                    self.data_dic['name'] = self.data.get('name')
            elif template_obj.job_name:
                self.data_dic['name'] = template_obj.job_name
            else:
                self.data_dic['name'] = ''.join(random.sample(string.ascii_letters + string.digits, 18))
            self.data_dic['job_type_id'] = job_type_id = template_obj.job_type_id
            if self.data.get('iclone_info'):
                iclone_info = self.data.get('iclone_info')
                creator_name = self.operator.first_name if self.operator.first_name else self.operator.last_name
                iclone_info['create_from'] = creator_name
                self.data_dic['iclone_info'] = self.data.get('iclone_info')
            else:
                self.data_dic['iclone_info'] = template_obj.iclone_info
            kernel_info = self.data.get('kernel_info')
            if not kernel_info:
                kernel_info = template_obj.kernel_info
            else:
                if 'scripts' not in kernel_info and template_obj.kernel_info and \
                        'scripts' in template_obj.kernel_info and template_obj.kernel_info['scripts']:
                    kernel_info['scripts'] = template_obj.kernel_info['scripts']
            kernel_info = kernel_info_format(kernel_info)
            self.data_dic['kernel_info'] = kernel_info
            self.data_dic['build_pkg_info'] = self.data.get('build_pkg_info', template_obj.build_pkg_info)
            self.data_dic['script_info'] = self.data.get('script_info', template_obj.script_info)
            self.data_dic['rpm_info'] = self.calibration_rpm_data(self.data.get('rpm_info', template_obj.rpm_info))
            self.data_dic['monitor_info'] = self.restructure_monitor_info(template_obj.monitor_info)
            self.data_dic['callback_api'] = self.data.get('callback_api', template_obj.callback_api)
            self.data_dic['report_name'], self.data_dic['report_template_id'] = self.get_report_info()
            self.data_dic['need_reboot'] = self.data.get('need_reboot',
                                                         template_obj.need_reboot) if api else self.data.get(
                'need_reboot', False)
            self.data_dic['console'] = self.data.get('console', template_obj.console) if api else self.data.get(
                'console', False)
            self.data_dic['report_name'] = self.data.get('report_name', template_obj.report_name)
            self.data_dic['report_template_id'] = self.data.get('report_template_id', template_obj.report_template_id)
            notice_info = self.data.get('notice_info', None)
            if notice_info:
                self.data_dic['notice_info'] = notice_info
            else:
                if (self.data.get('email') or self.data.get('ding_token')) and api:
                    self.data_dic['notice_info'] = self.pack_notice_info(email=self.data.get('email', None),
                                                                         ding=self.data.get('ding_token', None),
                                                                         subject=self.data.get('notice_subject', None))
                else:
                    self.data_dic['notice_info'] = template_obj.notice_info
            self.data_dic['kernel_version'] = self.data_dic['show_kernel_version'] = self.data.get('kernel_version',
                                                                                                   template_obj.kernel_version)
            if api:
                template_env = copy.deepcopy(template_obj.env_info)
                template_env.update(self.pack_env_info(self.data.get('env_info')))
                self.data_dic['env_info'] = template_env
            else:
                self.data_dic['env_info'] = self.pack_env_info(self.data.get('env_info'))
            assert job_type_id, JobTestException(ErrorCode.TYPE_ID_LACK)
            self.ws_id = JobType.objects.get(id=job_type_id).ws_id
            self.data_dic['ws_id'] = self.ws_id
            job_type = JobType.objects.get(id=job_type_id)
            self.data_dic['server_provider'] = self.provider = job_type.server_type
            self.data_dic['test_type'] = job_type.test_type
            project_id = self.data.get('project', template_obj.project_id) if api else self.data.get('project')
            if project_id:
                self.data_dic['project_id'] = project_id
            else:
                self.data_dic['project_id'] = Project.objects.filter(is_default=True, ws_id=self.ws_id).first().id \
                    if Project.objects.filter(is_default=True, ws_id=self.ws_id).exists() else None
            self.data_dic['product_id'] = self.get_product(self.data_dic['project_id'])
            self.data_dic['note'] = self.data.get('note', '')
        elif self.data_from == 'rerun':
            job_id = self.data.get('job_id')
            self.data_dic['source_job_id'] = job_id
            self.data_dic['baseline_id'] = self.data.get('baseline')
            self.data_dic['baseline_job_id'] = self.data.get('baseline_job_id')
            self.data_dic['cleanup_info'] = self.data.get('cleanup_info')
            if self.data.get('tags') and isinstance(self.data.get('tags'), list):
                [self.tag_list.append(tag) for tag in self.data.get('tags')]
            self.data_dic['name'] = self.job_format(self.data)
            self.data_dic['job_type_id'] = job_type_id = self.data.get('job_type')
            if self.data.get('iclone_info'):
                iclone_info = self.data.get('iclone_info')
                creator_name = self.operator.first_name if self.operator.first_name else self.operator.last_name
                iclone_info['create_from'] = creator_name
                self.data_dic['iclone_info'] = self.data.get('iclone_info')
            else:
                self.data_dic['iclone_info'] = dict()
            self.data_dic['kernel_info'] = self.data.get('kernel_info', dict())
            self.data_dic['build_pkg_info'] = self.data.get('build_pkg_info', dict())
            self.data_dic['script_info'] = self.data.get('script_info', list())
            self.data_dic['rpm_info'] = self.calibration_rpm_data(self.data.get('rpm_info', list()))
            self.data_dic['monitor_info'] = self.restructure_monitor_info(self.data.get('monitor_info', list()))
            self.data_dic['callback_api'] = self.data.get('callback_api')
            self.data_dic['need_reboot'] = self.data.get('need_reboot', False)
            self.data_dic['report_name'], self.data_dic['report_template_id'] = self.get_report_info()
            self.data_dic['console'] = self.data.get('console', False)
            self.data_dic['notice_info'] = self.pack_notice_info(email=self.data.get('email', None),
                                                                 ding=self.data.get('ding_token', None),
                                                                 subject=self.data.get('notice_subject', None))
            self.data_dic['kernel_version'] = self.data_dic['show_kernel_version'] = self.data.get('kernel_version')
            self.data_dic['env_info'] = self.pack_env_info(self.data.get('env_info'))
            assert job_type_id, JobTestException(ErrorCode.TYPE_ID_LACK)
            self.ws_id = JobType.objects.get(id=job_type_id).ws_id
            self.data_dic['ws_id'] = self.ws_id
            job_type = JobType.objects.get(id=job_type_id)
            self.data_dic['server_provider'] = self.provider = job_type.server_type
            self.data_dic['test_type'] = job_type.test_type
            project_id = self.data.get('project')
            if project_id:
                self.data_dic['project_id'] = project_id
            else:
                self.data_dic['project_id'] = Project.objects.filter(is_default=True, ws_id=self.ws_id).first().id \
                    if Project.objects.filter(is_default=True, ws_id=self.ws_id).exists() else None
            self.data_dic['product_id'] = self.get_product(self.data_dic['project_id'])
        elif self.data_from == 'import':
            self.data_dic['job_type_id'] = job_type_id = self.data.get('job_type_id')
            assert job_type_id, JobTestException(ErrorCode.TYPE_ID_LACK)
            self.ws_id = JobType.objects.get(id=job_type_id).ws_id
            self.data_dic['ws_id'] = self.ws_id
            self.data_dic['state'] = self.data.get('state')
            job_type = JobType.objects.get(id=job_type_id)
            self.data_dic['name'] = self.job_format(self.data)
            if self.data.get('baseline_id'):
                self.data_dic['baseline_id'] = self.data.get('baseline_id')
            self.data_dic['baseline_job_id'] = self.data.get('baseline_job_id')
            if self.data.get('cleanup_info'):
                self.data_dic['cleanup_info'] = self.data.get('cleanup_info')
            if self.data.get('tags') and isinstance(self.data.get('tags'), list):
                [self.tag_list.append(tag) for tag in self.data.get('tags')]
            if self.data.get('iclone_info'):
                iclone_info = self.data.get('iclone_info')
                creator_name = self.operator.first_name if self.operator.first_name else self.operator.last_name
                iclone_info['create_from'] = creator_name
                self.data_dic['iclone_info'] = iclone_info
            else:
                self.data_dic['iclone_info'] = dict()
            self.data_dic['kernel_info'] = self.data.get('kernel_info', dict())
            self.data_dic['build_pkg_info'] = self.data.get('build_pkg_info', dict())
            self.data_dic['script_info'] = self.data.get('script_info', list())
            self.data_dic['rpm_info'] = self.calibration_rpm_data(self.data.get('rpm_info', list()))
            self.data_dic['monitor_info'] = self.data.get('monitor_info', list())
            self.data_dic['need_reboot'] = self.data.get('need_reboot', False)
            self.data_dic['console'] = self.data.get('console', False)
            self.data_dic['callback_api'] = self.data.get('callback_api')
            self.data_dic['report_name'], self.data_dic['report_template_id'] = self.get_report_info()
            self.data_dic['notice_info'] = self.pack_notice_info(email=self.data.get('email_notice', None),
                                                                 ding=self.data.get('ding_msg', None),
                                                                 subject=self.data.get('notice_name', None))
            self.data_dic['kernel_version'] = self.data_dic['show_kernel_version'] = self.data.get('kernel_version')
            self.data_dic['env_info'] = self.pack_env_info(self.data.get('env_info')) if self.data.get(
                'env_info') else dict()
            self.data_dic['server_provider'] = self.provider = job_type.server_type
            self.data_dic['test_type'] = job_type.test_type
            product_version = self.data.get('product_version', None)
            project_id = self.data.get('project_id')
            if not product_version:
                if self.data.get('project_id'):
                    project = Project.objects.filter(id=project_id).first()
                    if project and not product_version:
                        product_version = project.product_version
                else:
                    project_id = Project.objects.filter(is_default=True, ws_id=self.ws_id).first().id \
                        if Project.objects.filter(is_default=True, ws_id=self.ws_id).exists() else None
            self.data_dic['project_id'] = project_id
            self.data_dic['product_version'] = product_version
            self.data_dic['product_id'] = self.get_product(self.data_dic['project_id'])
            self.data_dic['start_time'] = self.data.get('start_time')
            self.data_dic['end_time'] = self.data.get('end_time')
            self.data_dic['test_result'] = self.data.get('test_result')
            self.data_dic['created_from'] = 'offline'
        else:
            pass

        if self.data_dic.get('project_id') and not self.data.get('product_version', None):
            project = Project.objects.get(id=self.data_dic['project_id'])
            self.data_dic['product_version'] = project.product_version

    @staticmethod
    def create_new_snapshot(origin_server_snapshot_id, server_model, snapshot_map):
        if not origin_server_snapshot_id:
            return
        if origin_server_snapshot_id not in snapshot_map:
            snapshot_server = server_model.objects.filter(id=origin_server_snapshot_id).first()
            if snapshot_server is None:
                return
            snapshot_server.id = None
            snapshot_server.save()
            snapshot_map[origin_server_snapshot_id] = snapshot_server.id
            return snapshot_server.id
        else:
            return snapshot_map.get(origin_server_snapshot_id)

    def pack_custom_suite_case(self):  # noqa: C901
        """
        组装JobTest Suite Case关联数据
        """
        provider = self.provider
        server_model = TestServerSnapshot if provider == 'aligroup' else CloudServerSnapshot
        if self.data_from in ['custom', 'rerun']:
            test_config = self.data.get('test_config')
            assert test_config, JobTestException(ErrorCode.TEST_CONF_NEED)
            if not isinstance(test_config, list):
                assert test_config, JobTestException(ErrorCode.TEST_CONF_LIST)
            for suite in test_config:
                self.pack_suite(suite, provider)
        elif self.data_from == 'template':
            template_obj = self.template_obj
            if self.data.get('test_config'):
                for suite in self.data.get('test_config'):
                    self.pack_suite(suite, provider)
            else:
                template_suites = TestTmplSuite.objects.filter(tmpl_id=template_obj.id)
                template_cases = TestTmplCase.objects.filter(tmpl_id=template_obj.id)
                if not template_cases.exists():
                    JobTestException(ErrorCode.TEMPLATE_JOB_NEED_CASE)
                [self.suite_list.append({
                    'test_suite_id': suite.test_suite_id,
                    'need_reboot': suite.need_reboot,
                    'setup_info': suite.setup_info,
                    'cleanup_info': suite.cleanup_info,
                    'console': suite.console,
                    'monitor_info': suite.monitor_info,
                    'priority': suite.priority,
                })
                    for suite in template_suites]
                snapshot_map = {}
                [self.case_list.append({
                    'test_case_id': case.test_case_id,
                    'test_suite_id': case.test_suite_id,
                    'run_mode': case.run_mode,
                    'server_provider': self.provider,
                    'repeat': case.repeat,
                    'server_object_id': self.get_server_obj(case),
                    'server_tag_id': case.server_tag_id,
                    'server_snapshot_id': self.create_server_snapshot() or self.create_new_snapshot(
                        case.server_snapshot_id, server_model, snapshot_map),
                    'env_info': case.env_info,
                    'need_reboot': case.need_reboot,
                    'setup_info': case.setup_info,
                    'cleanup_info': case.cleanup_info,
                    'console': case.console,
                    'monitor_info': case.monitor_info,
                    'priority': case.priority,
                })
                    for case in template_cases]
        elif self.data_from == 'import':
            test_config = self.data.get('test_config')
            assert test_config, JobTestException(ErrorCode.TEST_CONF_NEED)
            if not isinstance(test_config, list):
                assert test_config, JobTestException(ErrorCode.TEST_CONF_LIST)
            for suite in test_config:
                self.pack_suite(suite, provider)
        else:
            pass

    @staticmethod
    def calibration_rpm_data(rpm_data):
        """[{"pos": "before", "rpm": "http://a.rpm,http://b.rpm"}]
        -> [{"pos": "before", "rpm": "http://a.rpm\nhttp://b.rpm"}]"""
        return [
            {'pos': item['pos'], 'rpm': item['rpm'].replace(',', '\n')}
            for item in rpm_data
        ]

    def create_server_snapshot(self):
        if self.default_server and isinstance(self.default_server, dict):
            custom_ip = self.default_server.get('custom_ip')
            if custom_ip not in self.server_map:
                channel = self.default_server.get('custom_channel', 'otheragent')
                ip, sn = get_server_ip_sn(custom_ip, channel)
                if channel == 'otheragent':
                    server_snapshot = TestServerSnapshot.objects.create(ip=ip, channel_type=channel, sn=sn,
                                                                        in_pool=False, ws_id=self.ws_id) \
                        if self.provider == 'aligroup' \
                        else CloudServerSnapshot.objects.create(
                        pub_ip=ip, channel_type=channel, sn=sn, in_pool=False, ws_id=self.ws_id)
                else:
                    server_snapshot = TestServerSnapshot.objects.create(ip=ip, channel_type=channel, tsn=sn,
                                                                        in_pool=False, ws_id=self.ws_id) \
                        if self.provider == 'aligroup' \
                        else CloudServerSnapshot.objects.create(pub_ip=ip, channel_type=channel, sn=sn,
                                                                in_pool=False, ws_id=self.ws_id)
                self.server_map[custom_ip] = server_snapshot.id
            return self.server_map[custom_ip]
        elif self.default_cloud_server:
            instance_id = self.default_cloud_server.get('instance_id')
            if self.cloud_server_map.get(instance_id):
                return self.cloud_server_map.get(instance_id)
            else:
                server_snapshot_id = self._get_default_cloud_server()
                self.cloud_server_map[instance_id] = server_snapshot_id
                return server_snapshot_id

    def get_server_obj(self, case):
        if case.run_mode == 'cluster':
            if self.default_cluster:
                test_cluster = TestCluster.objects.filter(name=self.default_cluster)
                if test_cluster.exists():
                    return test_cluster.first().id
            else:
                return case.server_object_id
        else:
            if self.default_server:
                if isinstance(self.default_server, str):
                    if self.provider == 'aligroup':
                        server_object = TestServer.objects.filter(ip=self.default_server)
                    else:
                        if check_ip(self.default_server):
                            server_object = CloudServer.objects.filter(pub_ip=self.default_server)
                        else:
                            server_object = CloudServer.objects.filter(template_name=self.default_server)
                    if server_object.exists():
                        return server_object.first().id
            else:
                return case.server_object_id

    @staticmethod
    def restructure_monitor_info(monitor_info):
        new_monitor_info = []
        case_machine_limit = 1
        case_machine_num = 0
        for i in monitor_info:
            # 保证字典顺序, 并且只要自己想要的数据
            tmp = {}
            monitor_type = i.get('monitor_type')
            if monitor_type == MonitorType.CASE_MACHINE:
                case_machine_num += 1
                if case_machine_num > case_machine_limit:
                    raise JobTestException(ErrorCode.CASE_MACHINE_NUM_ERROR)
            elif monitor_type == MonitorType.CUSTOM_MACHINE:
                ip_or_sn = i.get('server')
                if not ip_or_sn:
                    raise JobTestException(ErrorCode.MONITOR_IP_OR_SN_ERROR)
                try:
                    ip, sn = get_server_ip_sn(ip_or_sn, 'otheragent')
                except (TypeError, Exception):
                    raise JobTestException(ErrorCode.MONITOR_IP_OR_SN_ERROR)
                tmp.update({
                    'server': ip_or_sn,
                    'ip': ip,
                    'sn': sn
                })
            metric_category = i.get('metric_category', list())
            tmp.update({
                'metric_category': metric_category,
                'monitor_type': monitor_type
            })
            new_monitor_info.append(tmp)
        return new_monitor_info

    @staticmethod
    def job_format(data):
        data_dic = {}
        if data.get('name'):
            if '{date}' in data.get('name'):
                data_dic['name'] = data.get('name').replace('{date}', '_' + str(datetime.now().date()))
            else:
                data_dic['name'] = data.get('name')
        else:
            data_dic['name'] = ''.join(random.sample(string.ascii_letters + string.digits, 18))
        return data_dic['name']