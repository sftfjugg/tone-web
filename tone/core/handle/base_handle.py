# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import time
from abc import ABCMeta, abstractmethod

from django.db import transaction
from datetime import datetime

from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import JobTestException
from tone.core.utils.verify_tools import check_ip
from tone.models import TestServer, TestClusterServer, CloudServer, TestServerSnapshot, Product, Project, TestSuite, \
    CloudServerSnapshot, TestCluster, CloudAk
from tone.core.common.job_result_helper import get_server_ip_sn
from tone.services.sys.server_services import CloudServerService


class BaseHandle(metaclass=ABCMeta):

    def __init__(self, data, operator=None, obj=None):
        self.obj = obj
        self.data = data
        self.operator = operator
        self.data_dic, self.case_list, self.suite_list, self.tag_list = dict(), list(), list(), list()
        self.data_from = data.get('data_from', 'custom')
        self.ws_id = None
        self.template_obj = None
        self.job_obj = None
        self.provider = None
        self.server_map = dict()
        self.default_server = data.get('default_server')
        self.default_cluster = data.get('default_cluster')
        self.default_cloud_server = data.get('default_cloud_server')

    def __getattr__(self, item):
        return self.data.get(item)

    def init(self):
        if self.obj:
            self.data_dic['creator'] = self.obj.creator
            self.data_dic['id'] = self.obj.id
            self.data_dic['update_user'] = self.operator.id
        else:
            self.data_dic['creator'] = self.operator.id

    def return_result(self):
        """
        返回数据结果容器
        """
        with transaction.atomic():
            self.init()
            self.check_data_from()
            self.pack_custom()
            self.pack_custom_suite_case()
            self.suite_list = sorted(self.suite_list, key=lambda x: x.get('priority'), reverse=True)
            sorted_suite = [tmp_suite.get('test_suite_id') for tmp_suite in self.suite_list]
            self.case_list = sorted(
                self.case_list,
                key=lambda x: (-sorted_suite.index(x.get('test_suite_id')), x.get('priority')), reverse=True)
            if '{date}' in self.data_dic['name']:
                self.data_dic['name'] = self.data_dic['name'].replace('{date}', '_' + str(datetime.now().date()))
            return self.data_dic, self.case_list, self.suite_list, self.tag_list

    def check_data_from(self):
        if self.data_from not in ['custom', 'plan', 'template', 'import', 'rerun']:
            raise JobTestException(ErrorCode.DATA_FORM_ERROR)

    @abstractmethod
    def pack_custom(self):
        pass

    @abstractmethod
    def pack_custom_suite_case(self):
        pass

    def pack_suite(self, suite, provider):
        """
        组装JobTestSuite数据
        """
        suite_dic = dict()
        self.suite_param(suite_dic, suite)
        self.suite_list.append(suite_dic)
        test_cases = suite.get('cases', list())
        if not isinstance(test_cases, list):
            assert test_cases, JobTestException(ErrorCode.CASES_LIST)
        for case in test_cases:
            self.pack_case(case, suite, provider)

    def pack_case(self, case, suite, provider):
        """
        组装JobTestCase数据
        """
        case_dict = dict()
        run_mode = TestSuite.objects.get(id=suite.get('test_suite')).run_mode
        self.check_server_param(case_dict, run_mode, case, provider)
        case_dict.update(
            {
                'test_suite_id': suite.get('test_suite'),
                'test_case_id': case.get('test_case'),
                'repeat': case.get('repeat', 1),
                'server_provider': self.provider,
                'need_reboot': case.get('need_reboot', False),
                'console': case.get('console', False),
                'setup_info': case.get('setup_info', None),
                'monitor_info': case.get('monitor_info', list()),
                'server_object_id': case.get('server_object_id'),
                'server_tag_id': ','.join([str(i) for i in case.get('server_tag_id')])
                if case.get('server_tag_id') else '',
                'priority': case.get('priority', 10),
                'cleanup_info': case.get('cleanup_info', None),
                'env_info': self.pack_env_info(case.get('env_info')) if case.get('env_info') else dict()
            }
        )
        self.case_list.append(case_dict)

    @staticmethod
    def suite_param(suite_dic, suite):
        """
        组装job suite 关联数据
        """
        if not suite.get('test_suite'):
            raise JobTestException(ErrorCode.TEST_SUITE_NEED)
        suite_dic['test_suite_id'] = suite.get('test_suite')
        suite_dic.update(
            {
                'setup_info': suite.get('setup_info', None),  # TODO 校验case
                'need_reboot': suite.get('need_reboot', False),
                'cleanup_info': suite.get('cleanup_info', None),
                'console': suite.get('console', False),
                'monitor_info': suite.get('monitor_info', list()),
                'priority': suite.get('priority', 10),
            }
        )

    @staticmethod
    def pack_notice_info(email=None, ding=None, subject=None):
        """
        组装notice_info信息
        """
        notice_info = list()
        if email:
            email_data = {'type': 'email', "to": email}
            if subject:
                email_data['subject'] = subject
            notice_info.append(email_data)
        if ding:
            ding_data = {'type': 'ding', "to": ding}
            if subject:
                ding_data['subject'] = subject
            notice_info.append(ding_data)
        return notice_info

    @staticmethod
    def pack_env_info(data):
        """
        组装env_info
        """
        if not data:
            return dict()
        env_data = dict()
        env_info_li = data.split(',')
        for info in env_info_li:
            item = info.split('=', 1)
            if ' ' in item[1]:
                env_data[item[0]] = item[1]
            else:
                env_data[item[0]] = item[1].strip("'").strip('"')
        return env_data

    def _check_cluster_server_param(self, case_dict, run_mode, case, provider):
        case_dict['run_mode'] = run_mode
        if not case.get('server'):
            return
        cluster_id = case.get('server').get('cluster')
        if self.default_cluster:
            test_cluster = TestCluster.objects.filter(name=self.default_cluster)
            return test_cluster.first().id if test_cluster.exists() else cluster_id
        else:
            self.check_cluster(cluster_id, provider)
            case_dict['server_object_id'] = cluster_id
        return

    def _set_default_server(self, case_dict, provider):
        if self.provider == 'aligroup':
            server_object = TestServer.objects.filter(ip=self.default_server)
        else:
            if check_ip(self.default_server):
                server_object = CloudServer.objects.filter(pub_ip=self.default_server)
            else:
                server_object = CloudServer.objects.filter(template_name=self.default_server)
        if server_object.exists():
            if server_object.first().ws_id != self.data_dic['ws_id']:
                raise JobTestException(ErrorCode.SERVER_NOT_IN_THIS_WS)
            case_dict['server_object_id'] = server_object.first().id
        else:
            customer_server = self.default_server
            if TestServer.objects.filter(ip=customer_server.get('custom_ip')).exists():
                raise JobTestException(ErrorCode.SERVER_USED_BY_OTHER_WS)
            self.package_customer_server(
                customer_server.get('custom_ip'),
                customer_server.get('custom_channel'),
                provider, case_dict)

    def _get_default_cloud_server(self):
        cloud_server_config = self.default_cloud_server.copy()
        access_id = cloud_server_config.pop('access_id')
        access_key = cloud_server_config.pop('access_key')
        instance_id = cloud_server_config.get('instance_id')
        if self.data_dic.get('cloud_snapshot_id'):
            return self.data_dic['cloud_snapshot_id']
        ak = CloudAk.objects.filter(
            access_id=access_id,
            access_key=access_key,
            ws_id=self.data_dic.get('ws_id')
        )
        if not ak.exists():
            raise JobTestException(ErrorCode.AK_NOT_CORRECT)
        ak_obj = ak.first()
        if not instance_id:
            # 根据server config实时创建机器实例
            server_snapshot_obj = self.__create_cloud_config_snapshot(ak_obj, cloud_server_config)
        else:
            # 使用已有实例
            server_snapshot_obj = self.__create_cloud_instance_snapshot(ak_obj, cloud_server_config)
        return server_snapshot_obj.id

    def __create_cloud_config_snapshot(self, ak_obj, cloud_server_config):
        cloud_server_config.update({
            'is_instance': False,
            'ak_id': ak_obj.id,
            'provider': ak_obj.provider,
            'manufacturer': ak_obj.provider,
            'ws_id': self.data_dic.get('ws_id'),
            'kernel_version': '',
            'console_type': '',
            'console_conf': '',
            'private_ip': '',
            'pub_ip': '',
            'description': '',
            'template_name': f'{ak_obj.provider}_server_{time.time()}'
        })
        cloud_server_config.setdefault('bandwidth', 10)
        cloud_server_config.setdefault('storage_size', 40)
        cloud_server_config.setdefault('storage_number', 0)
        cloud_server_config.setdefault('system_disk_size', 50)
        cloud_server_config.setdefault('storage_type', 'cloud_ssd')
        cloud_server_config.setdefault('system_disk_category', 'cloud_ssd')
        return CloudServerSnapshot.objects.create(**cloud_server_config)

    def __create_cloud_instance_snapshot(self, ak_obj, cloud_server_config):
        driver, provider = CloudServerService().get_ali_driver(
            ak_obj.id, region=cloud_server_config.get('region'))
        if not driver:
            return False, 'provider driver is none'
        instance, disk_info = driver.get_instance(cloud_server_config.get('instance_id'))
        if not instance:
            raise JobTestException(ErrorCode.AK_NOT_CORRECT)
        pub_ip = instance['public_ips'][0] if instance['public_ips'] \
            else instance['extra']['eip_address']['ip_address']
        cloud_server_instance = dict(
            job_id=0,
            parent_server_id=0,
            is_instance=True,
            ak_id=ak_obj.id,
            region=cloud_server_config.get('region'),
            zone=cloud_server_config.get('zone'),
            instance_id=cloud_server_config.get('instance_id'),
            manufacturer=ak_obj.provider,
            ws_id=self.data_dic.get('ws_id'),
            channel_type='toneagent',
            release_rule=cloud_server_config.get('release_rule', 0),
            provider=ak_obj.provider,
            state='Available',
            image=instance.get('image'),
            instance_name=instance.get('name'),
            hostname=instance.get('hostname'),
            bandwidth=instance.get('bandwidth'),
            instance_type=instance.get('instance_type'),
            storage_type=disk_info.get('data_disk_category'),
            storage_size=disk_info.get('data_disk_size'),
            storage_number=disk_info.get('data_disk_count'),
            sn=instance.get('serial_number'),
            private_ip=instance.get('private_ips')[0],
            pub_ip=pub_ip
        )
        return CloudServerSnapshot.objects.create(**cloud_server_instance)

    def check_server_param(self, case_dict, run_mode, case, provider):
        """
        检测server参数
        """
        if run_mode == 'cluster':
            return self._check_cluster_server_param(case_dict, run_mode, case, provider)
        if self.default_server:
            self._set_default_server(case_dict, provider)
            if 'server' in case:
                case.pop('server')
            return
        if self.default_cloud_server:
            case_dict['server_snapshot_id'] = self._get_default_cloud_server()
        server_config = case.get('server', {}) or case.get('customer_server', {})
        if server_config.get('id'):
            self.check_server(server_config.get('id'), provider)
            case_dict['server_object_id'] = server_config.get('id')
        elif server_config.get('ip') or server_config.get('custom_ip'):
            custom_ip = server_config.get('ip') or server_config.get('custom_ip')
            channel_type = server_config.get('channel_type') or server_config.get('custom_channel', 'staragent')
            if custom_ip:
                self.package_customer_server(custom_ip, channel_type, provider, case_dict)
        elif server_config.get('tag'):
            case_dict['server_tag_id'] = server_config.get('tag')
        elif server_config.get('config'):
            self.check_server(server_config.get('config'), provider)
            case_dict['server_object_id'] = server_config.get('config')
        elif server_config.get('instance'):
            self.check_server(server_config.get('instance'), provider)
            case_dict['server_object_id'] = server_config.get('instance')
        pass

    def package_customer_server(self, custom_ip, channel_type, provider, case_dict):
        if custom_ip not in self.server_map:
            ip, sn = get_server_ip_sn(custom_ip, channel_type)
            if channel_type == 'staragent':
                server_snapshot = TestServerSnapshot.objects.create(ip=ip, channel_type=channel_type, sn=sn,
                                                                    in_pool=False, ws_id=self.ws_id) \
                    if provider == 'aligroup' \
                    else CloudServerSnapshot.objects.create(
                    pub_ip=ip, channel_type=channel_type, sn=sn, in_pool=False, ws_id=self.ws_id)
            else:
                server_snapshot = TestServerSnapshot.objects.create(ip=ip, channel_type=channel_type, tsn=sn,
                                                                    in_pool=False, ws_id=self.ws_id) \
                    if provider == 'aligroup' \
                    else CloudServerSnapshot.objects.create(pub_ip=ip, channel_type=channel_type, sn=sn,
                                                            in_pool=False, ws_id=self.ws_id)
            self.server_map[custom_ip] = server_snapshot.id
        case_dict['server_snapshot_id'] = self.server_map[custom_ip]

    def check_server(self, server, provider, is_cluster=False):
        """
        检查机器是否为可用状态
        """
        server_obj = TestServer.objects.filter(
            id=server, ws_id=self.ws_id).first() if provider == 'aligroup' else CloudServer.objects.filter(
            id=server).first()
        if not server_obj:
            raise JobTestException(ErrorCode.SERVER_NONEXISTENT)
        if server_obj.state not in ['Available', 'Occupied', 'Reserved']:
            raise JobTestException(ErrorCode.SERVER_STATUS)
        if not is_cluster:
            server_obj.spec_use = 2
        server_obj.save()

    def check_cluster(self, cluster, provider):
        """
        指定集群：检查集群机器是否为可用状态
        """
        if not cluster:
            return
        cluster_server_obj = TestClusterServer.objects.filter(cluster_id=cluster, cluster_type=provider)
        if not cluster_server_obj.exists():
            raise JobTestException(ErrorCode.CLUSTER_NO_SERVER)
        for cluster_server in cluster_server_obj:
            self.check_server(cluster_server.server_id, provider, is_cluster=True)

    @staticmethod
    def get_product(project_id):
        """
        获取product_id
        """
        if not Project.objects.filter(id=project_id).exists():
            raise JobTestException(ErrorCode.NO_PROJECT)
        if not Product.objects.filter(id=Project.objects.get(id=project_id).product_id).exists():
            raise JobTestException(ErrorCode.NO_PRODUCT)
        project = Project.objects.get(id=project_id)
        return project.product_id

    def get_report_info(self):
        """
        report_name
        """
        report_name = self.data.get('report_name', None)
        report_template_id = self.data.get('report_template', None)
        return report_name, report_template_id
