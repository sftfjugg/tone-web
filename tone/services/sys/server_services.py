# flake8: noqa
import base64
import logging
import uuid
import re
from datetime import datetime

import requests
from django.db.models import Q

from tone import settings
from tone.core.common.constant import SERVER_REAL_STATE_PUT_MAP
from tone.core.common.info_map import get_result_map
from tone.core.common.services import CommonService
from tone.core.common.toneagent import server_check, remove_server_from_toneagent, deploy_agent_by_ecs_assistant, \
    add_server_to_toneagent, QueryTaskRequest
from django.db import transaction
from tone.core.common.operation_log import operation
from tone.core.common.enums.ts_enums import TestServerEnums, TestServerState
from tone.core.cloud.aliyun.ecs_driver import EcsDriver
from tone.core.cloud.aliyun.eci_driver import EciDriver
from tone.core.utils.common_utils import pack_env_infos
from tone.models import TestServer, CloudServer, ServerTag, ServerTagRelation, \
    TestCluster, TestClusterServer, CloudAk, CloudImage, User, Workspace, TestTmplCase, TestTemplate, \
    TestServerSnapshot, CloudServerSnapshot, ReleaseServerRecord
from tone.settings import TONEAGENT_DOMAIN

error_logger = logging.getLogger('error')
scheduler_logger = logging.getLogger('scheduler')


def update_owner(data):
    """
    根据emp_id，从集团添加/修改owner
    :param data: request.data字典
    :return: None
    """
    emp_id = data.get('emp_id')
    if emp_id is not None:
        # tone数据库存在 emp_id, 查询user_id, 否则先添加用户
        user = User.objects.filter(emp_id=emp_id.upper()).first()
        data.update({'owner': user.id})


class TestServerService(CommonService):
    attr_base = ('sn', 'hostname', 'app_group', 'app_state', 'security_domain', 'idc',
                 'manufacturer', 'device_mode', 'sm_name')
    attr_more = ('kernel', 'arch', 'cpu', 'memory', 'network', 'memory_device', 'net_device')

    @staticmethod
    def filter(queryset, data):
        q = TestServerService._get_search_q(data)
        if data.get('tag'):
            server_id_list = ServerTagRelation.objects.filter(object_type=TestServerEnums.OBJECT_TYPE_CHOICES[1][0],
                                                              server_tag_id__in=data.getlist('tag')). \
                order_by('object_id').values_list('object_id', flat=True).distinct()
            q &= Q(id__in=server_id_list)
        if data.get('cluster_id'):
            server_id_list = TestClusterServer.objects.filter(cluster_id=data.get('cluster_id')).values_list(
                'server_id', flat=True)
            q &= Q(id__in=server_id_list)
        return queryset.filter(q)

    @staticmethod
    def filter_specify_machine(queryset, data):
        q = Q()
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        if data.get('state'):
            q &= Q(state__in=data.getlist('state'))
        if data.get('app_group'):
            q &= Q(app_group=data.get('app_group'))
            # q &= Q(app_group__icontains=data.get('app_group'))
        return queryset.filter(q)

    @staticmethod
    def _get_search_q(data):
        flag = False
        q = Q(in_pool=1)
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        if data.get('ip'):
            q &= Q(ip__icontains=data.get('ip'))
            flag = True
        if data.get('sn'):
            q &= Q(sn__icontains=data.get('sn'))
            flag = True
        if data.get('name'):
            q &= Q(name__icontains=data.get('name'))
            flag = True
        if data.get('sm_name'):
            q &= Q(sm_name__icontains=data.get('sm_name'))
            flag = True
        if data.get('app_group'):
            q &= Q(app_group__icontains=data.get('app_group'))
            flag = True
        if data.get('description'):
            q &= Q(description__icontains=data.get('description'))
            flag = True
        if data.get('idc'):
            q &= Q(idc__icontains=data.get('idc'))
            flag = True
        if data.get('owner'):
            if data.get('owner').isdigit():
                q &= Q(owner=data.get('owner'))
            else:
                user = User.objects.filter(Q(last_name__icontains=data.get('owner')) |
                                           Q(first_name__icontains=data.get('owner'))).values_list('id', flat=True)
                q &= Q(owner__in=user)
            flag = True
        if data.get('channel_type'):
            channel_type_list = data.get('channel_type').split(',')
            q &= Q(channel_type__in=channel_type_list)
            flag = True
        if data.get('device_type'):
            device_type_list = data.get('device_type').split(',')
            q &= Q(device_type__in=device_type_list)
            flag = True
        for item in ['state', 'real_state']:
            if data.get(item):
                search_list = data.getlist(item)
                if item == 'real_state':
                    search_list = [SERVER_REAL_STATE_PUT_MAP.get(i) for i in data.getlist(item)]
                q &= Q(**{'{}__in'.format(item): search_list})
                flag = True
        tags = data.getlist('tags')
        if len(tags) == 1 and tags != ['']:
            tag_list_id = ServerTagRelation.objects.filter(server_tag_id__in=tags) \
                .values_list('object_id', flat=True)
            object_id = TestServer.objects.filter(ws_id=data.get('ws_id'), id__in=tag_list_id) \
                .values_list('id', flat=True)
            q &= Q(id__in=object_id)
            flag = True
        if len(tags) >= 2:
            object_id_list = []
            tags = [int(tag) for tag in tags]
            test_server_id_list = TestServer.objects.filter(ws_id=data.get('ws_id')).values_list('id', flat=True)
            for test_server_id in test_server_id_list:
                server_id_list = ServerTagRelation.objects.filter(object_id=test_server_id).values_list(
                    'server_tag_id', flat=True)
                if set(tags) <= set(server_id_list):
                    object_id_list.append(test_server_id)
            q &= Q(id__in=object_id_list)
            flag = True
        if not flag:
            q &= Q(parent_server_id__isnull=True)
        data.flag = flag
        return q

    def add_group_server(self, post_data):
        if 'ips' not in post_data:
            return False, 'ip is required'
        if 'owner' not in post_data:
            return False, 'owner is required'
        if 'ws_id' not in post_data:
            return False, 'ws_id is required'
        update_owner(post_data)
        for ip in post_data.get('ips'):
            # 向tone-agent平台注册机器
            add_agent_result = add_server_to_toneagent(ip)
            if not add_agent_result.get("SUCCESS"):
                return False, add_agent_result.get('RESULT') or add_agent_result.get('msg')
            tsn = add_agent_result['RESULT']['TSN']
            test_server = TestServer.objects.create(
                ip=ip,
                tsn=tsn,
                state=post_data.get('state', 'Available'),
                owner=post_data.get('owner'),
                ws_id=post_data.get('ws_id'),
                channel_type=post_data.get('channel_type', 'toneagent'),
                description=post_data.get('description', ''),
                sn=uuid.uuid4(),
            )
            if 'tags' in post_data:
                ServerTagRelationService().add_tag_relation(
                    post_data['tags'], test_server.id,
                    TestServerEnums.OBJECT_TYPE_CHOICES[1][0],
                    TestServerEnums.RUN_ENV_CHOICES[0][0]
                )
        return True, f'add servers({post_data.get("ips")}) success'

    def create(self, post_data, operator):
        if 'ips' not in post_data:
            return False, 'ip is required'
        if 'state' not in post_data:
            return False, 'state is required'
        if 'owner' not in post_data:
            return False, 'owner is required'
        if 'ws_id' not in post_data:
            return False, 'ws_id is required'
        if 'description' not in post_data:
            post_data['description'] = ''
        ips = post_data['ips']
        success, msg = self.add_server(ips, post_data, 1, operator)
        instance = get_result_map("add_machine", msg)
        return success, instance

    def _mul_add_server(self, server_ips, post_data, in_pool, msg):
        """多机器分线程添加"""
        for server_ip in server_ips:
            if TestServer.objects.filter(ip=server_ip, ws_id=post_data.get('ws_id'), in_pool=False).first():
                msg.append(server_ip + ' existed in cluster;')
                continue
            if TestServer.objects.filter(ip=server_ip, ws_id=post_data.get('ws_id')).first():
                msg.append(server_ip + 'existed;')
                continue
            _, channel_state, _ = self.get_channel_state(
                {'ip': server_ip, 'channel_type': post_data.get('channel_type', 'ToneAgent')})
            test_server = TestServer.objects.create(
                ip=server_ip,
                state=post_data['state'],
                description=post_data['description'],
                owner=post_data['owner'],
                ws_id=post_data['ws_id'],
                channel_state=channel_state,
                channel_type=post_data.get('channel_type', 'ToneAgent'),
                in_pool=in_pool)
            server_tag_service = ServerTagRelationService()
            if 'tags' in post_data:
                server_tag_service.add_tag_relation(post_data['tags'], test_server.id,
                                                    TestServerEnums.OBJECT_TYPE_CHOICES[1][0],
                                                    TestServerEnums.RUN_ENV_CHOICES[0][0])
            return True, 'success'

    def add_server(self, ips, post_data, in_pool, operator):
        ip_list = []
        sn_list = []
        for ip in ips:
            if ip:
                if re.match(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', ip) is None:
                    sn_list.append(ip)
                else:
                    ip_list.append(ip)
        if len(ips) == 0:
            return False, '机器未找到'
        return self._mul_add_server(ips, post_data, in_pool, operator)

    @staticmethod
    def get_channel_state(data):
        channel_state = False
        code, _, agent_info = server_check(data.get('ip'), tsn=data.get('tsn'))
        if code == 200 and agent_info['RESULT']['STATUS'] == 'online':
            channel_state = True
        return code, channel_state, agent_info

    def _set_attr_more(self, server, test_server):
        for attr in self.attr_more:
            setattr(test_server, attr, server.get(attr, ''))

    def update_server(self, server_id):
        test_server = TestServer.objects.filter(id=server_id).first()
        if not test_server:
            return False, '机器不存在'
        success = True
        msg = '机器更新成功'
        test_server.save()
        return success, msg

    @staticmethod
    def batch_update_server(data, operator):
        server_ids = data.get('server_ids', [])
        description = data.get('description')
        tags = data.get('tags', [])
        server_tag_service = ServerTagRelationService()
        for server_id in server_ids:
            if description is not None:
                TestServer.objects.filter(id=server_id).update(
                    # owner=owner,
                    description=description,
                )
            if tags:
                server_tag_service.add_tag_relation(tags, server_id,
                                                    TestServerEnums.OBJECT_TYPE_CHOICES[1][0],
                                                    TestServerEnums.RUN_ENV_CHOICES[0][0])
        return 200, '批量修改成功'

    def _set_attr_base(self, server, test_server):
        for attr in self.attr_base:
            setattr(test_server, attr, server.get(attr, ''))

    @staticmethod
    def update(data, pk, user_id):
        test_server = TestServer.objects.filter(id=pk)
        if test_server is None:
            return False, 'server 不存在'
        if test_server.first().state != data.get('state') and \
                test_server.first().state == TestServerEnums.SERVER_STATE_CHOICES[1][0]:
            return False, '机器被占用，不可修改状态'
        # 机器状态为 Occupied 时，不能修改 控制通道、机器名称、使用状态
        if test_server.first().state == TestServerEnums.SERVER_STATE_CHOICES[1][1] and data.get('channel_type'):
            return False, 'Occupied时：控制通道、机器、使用状态不能编辑'
        update_owner(data)
        allow_update = ['channel_type', 'state', 'owner', 'description', 'name', 'description']
        update_data = dict()
        for update_field in allow_update:
            if data.get(update_field) is not None:
                update_data[update_field] = data.get(update_field)

        server_tag_service = ServerTagRelationService()
        with transaction.atomic():
            operation_li = list()
            values_li = list()
            for key in update_data:
                values_li.append((key, getattr(test_server.first(), key), update_data[key]))
            server_tag_service.update_tag_log('aligroup', 'standalone', pk, data.get('tags', []), values_li)
            test_server.update(**update_data)
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_test_server',
                'pid': pk,
                'operation_type': 'update',
                'table': TestServer._meta.db_table,
                'values_li': values_li
            }
            operation_li.append(log_data)
            operation(operation_li)
        if 'tags' in data:
            server_tag_service.add_tag_relation(data.get('tags'), pk, TestServerEnums.OBJECT_TYPE_CHOICES[1][0],
                                                TestServerEnums.RUN_ENV_CHOICES[0][0])
        return True, 'success'

    @staticmethod
    def deploy(post_data):
        if 'deploy_user' not in post_data or 'deploy_pass' not in post_data:
            return False, '参数错误。'
        test_server = TestServer.objects.filter(id=post_data['server_id'])
        if test_server:
            if test_server.first().channel_state:
                return False, 'agent 已部署'
            test_server.update(channel_state=True)
        else:
            return False, '部署失败，机器不存在'
        return True, ''

    def delete(self, data, pk, user_id):
        with transaction.atomic():
            test_server = TestServer.objects.filter(id=pk)
            if len(test_server) == 0:
                return 201, '机器不存在'
            if test_server.first().spec_use == 1 and TestClusterServer.objects.filter(server_id=pk,
                                                                                      cluster_type='aligroup').exists():
                return 201, '机器被集群使用'
            elif test_server.first().spec_use == 2:
                return 201, '机器被job使用'
            if test_server.first().state == 'Occupied':
                return 201, '机器被占用'
            # 当物理机下面有虚拟机时，不允许直接删除物理机
            if TestServer.objects.filter(parent_server_id=test_server.first().id).exists():
                return 201, '物理机下面有虚拟机, 不允许删除'
            TestTmplCase.objects.filter(server_provider='aligroup',
                                        run_mode='standalone',
                                        server_object_id=pk).update(server_object_id=None)
            # 调用接口，将机器从toneagent系统移除
            try:
                server = test_server.first()
                remove_server_from_toneagent(server.ip, server.tsn)
            except Exception as e:
                error_logger.error(f'remove server from toneagent failed!server:'
                                   f'{server.ip}, error:{str(e)}')
            TestServer.objects.filter(id=pk).delete()
            operation_li = list()
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_server_tag',
                'pid': pk,
                'operation_type': 'delete',
                'table': TestServer._meta.db_table
            }
            operation_li.append(log_data)
            operation(operation_li)
            TestClusterServer.objects.filter(server_id=pk, cluster_type='aligroup').delete()
            return 200, ''

    def test_one_server_check(self, ip, channel_type, ws_id):
        errors_sn, msg_sn, success_sn = [], '', []
        errors_ip, msg_ip, success_ip = [], '', []
        ip_list = []
        sn_list = []
        success = 200
        res_errors_sn, res_msg_sn, res_errors_ip, res_msg_ip = \
            self.check_db_existed(channel_type, ip, ip_list, sn_list, ws_id=ws_id)
        if res_msg_ip or res_msg_sn:
            return 201, [(res_msg_ip or res_msg_sn).strip('；'), '']
        errors_sn += res_errors_sn
        errors_ip += res_errors_ip
        msg_sn += res_msg_sn
        msg_ip += res_msg_ip
        if channel_type == 'toneagent':
            for ip in ip_list:
                code, _, res = server_check(ip)
                if code == 200:
                    success_ip.append(ip)
                else:
                    errors_ip.append(ip)
                    msg_ip += 'ip: {} output: {}'.format(ip, res)
            for tsn in sn_list:
                code, _, res = server_check(tsn)
                if code == 200:
                    success_sn.append(tsn)
                else:
                    errors_sn.append(tsn)
                    msg_sn += 'sn: {} output: {}'.format(tsn, res)
        errors = errors_sn + errors_ip
        msg = ['', '']
        if len(errors) > 0:
            msg = ['查询%s失败!' % channel_type, ' %s %s' % (msg_ip.strip('；'), msg_sn.strip('；'))]
            success = 201
        return success, msg

    def test_server_check(self, ips, channel_type, server_id=None, ws_id=None):
        errors_sn, msg_sn, success_sn = [], '', []
        errors_ip, msg_ip, success_ip = [], '', []
        ip_list = []
        sn_list = []
        for ip in ips:
            res_errors_sn, res_msg_sn, res_errors_ip, res_msg_ip = \
                self.check_db_existed(channel_type, ip, ip_list, sn_list, server_id, ws_id)
            errors_sn += res_errors_sn
            errors_ip += res_errors_ip
            msg_sn += res_msg_sn
            msg_ip += res_msg_ip
        if channel_type == 'toneagent':
            for ip in ip_list:
                code, _, res = server_check(ip)
                if code == 200:
                    success_ip.append(ip)
                else:
                    errors_ip.append(ip)
                    msg_ip += 'ip: {} output: {}'.format(ip, res)
            for tsn in sn_list:
                code, _, res = server_check(tsn)
                if code == 200:
                    success_sn.append(tsn)
                else:
                    errors_sn.append(tsn)
                    msg_sn += 'sn: {} output: {}'.format(tsn, res)
        errors = errors_sn + errors_ip
        success = success_sn + success_ip
        # 错误信息：基础 + 详情
        msg = ['', '']
        if len(errors) > 0:
            msg = ['查询%s失败!' % channel_type, ' %s %s' % (msg_ip.strip('；'), msg_sn.strip('；'))]
        return success, errors, msg

    @staticmethod
    def check_db_existed(channel_type, ip, ip_list, sn_list, server_id=None, ws_id=None):  # noqa: C901
        errors_sn, msg_sn, errors_ip, msg_ip = [], '', [], ''
        if re.match(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}', ip) is None:
            if channel_type == 'otheragent':
                server_obj = TestServer.objects.filter(sn=ip).first()
                if server_obj and (server_id is None or server_id is not None
                                   and str(server_obj.id) != server_id) and ws_id != server_obj.ws_id:
                    errors_sn.append(ip)
                    workspace_obj = Workspace.objects.filter(id=server_obj.ws_id).first()
                    show_name = '' if not workspace_obj else workspace_obj.show_name
                    msg_sn += 'sn [%s] 已在其他空间 %s 使用；' % (ip, show_name)
                elif server_obj and (server_id is None or server_id is not None and str(server_obj.id) != server_id):
                    errors_sn.append(ip)
                    workspace_obj = Workspace.objects.filter(id=server_obj.ws_id).first()
                    show_name = '' if not workspace_obj else workspace_obj.show_name
                    spec_info = f'Workspace: {show_name} '
                    msg_sn += 'sn [%s] 已在 %s 单机/集群中使用(机器池中)；' % (ip, spec_info)
                else:
                    sn_list.append(ip.strip())
            else:
                server_obj = TestServer.objects.filter(tsn=ip).first()
                if server_obj and (server_id is None or server_id is not None
                                   and str(server_obj.id) != server_id) and ws_id != server_obj.ws_id:
                    errors_sn.append(ip)
                    workspace_obj = Workspace.objects.filter(id=server_obj.ws_id).first()
                    show_name = '' if not workspace_obj else workspace_obj.show_name
                    msg_sn += 'tsn [%s] 已在其他空间 %s 使用；' % (ip, show_name)
                elif server_obj and (server_id is None or server_id is not None and str(server_obj.id) != server_id):
                    errors_sn.append(ip)
                    workspace_obj = Workspace.objects.filter(id=server_obj.ws_id).first()
                    show_name = '' if not workspace_obj else workspace_obj.show_name
                    spec_info = f'Workspace: {show_name} '
                    msg_sn += 'sn [%s] 已在 %s 单机/集群中使用(机器池中)；' % (ip, spec_info)
                else:
                    sn_list.append(ip.strip())
        else:
            server_obj = TestServer.objects.filter(ip=ip).first()
            if server_obj and (server_id is None or server_id is not None
                               and str(server_obj.id) != server_id) and ws_id != server_obj.ws_id:
                errors_ip.append(ip)
                workspace_obj = Workspace.objects.filter(id=server_obj.ws_id).first()
                show_name = '' if not workspace_obj else workspace_obj.show_name
                msg_ip += 'ip [%s] 已在其他空间 %s 使用；' % (ip, show_name)
            elif server_obj and (server_id is None or server_id is not None and str(server_obj.id) != server_id):
                errors_ip.append(ip)
                workspace_obj = Workspace.objects.filter(id=server_obj.ws_id).first()
                show_name = '' if not workspace_obj else workspace_obj.show_name
                spec_info = f'Workspace: {show_name} '
                msg_sn += 'sn [%s] 已在 %s 单机/集群中使用(机器池中)；' % (ip, spec_info)
            else:
                ip_list.append(ip.strip())
        return errors_sn, msg_sn, errors_ip, msg_ip

    def server_channel_check(self, data):
        return self.test_one_server_check(data.get('ip'), data.get('channel_type'), data.get('ws_id'))

    @staticmethod
    def get_app_group(data):
        ws_id = data.get('ws_id')
        q = Q(in_pool=True)
        if ws_id:
            q &= Q(ws_id=ws_id)
        return TestServer.objects.filter(q).values_list('app_group', flat=True).distinct()

    @staticmethod
    def del_server_confirm(data):
        server_id = data.get('server_id')
        run_mode = data.get('run_mode', 'standalone')
        server_provider = data.get('server_provider', 'aligroup')
        template_id_list = TestTmplCase.objects.filter(server_provider=server_provider,
                                                       run_mode=run_mode,
                                                       server_object_id=server_id).values_list('tmpl_id', flat=True)
        return TestTemplate.objects.filter(id__in=template_id_list)

    @staticmethod
    def get_vm_server(data):
        server_id = data.get('server_id')
        phy_server = TestServer.objects.filter(id=server_id).first()
        if phy_server is not None:
            item_list = []
            added_server = TestServer.objects.filter(parent_server_id=server_id).values_list('ip', flat=True)
            item_list = [item for item in item_list if item.get('ip') not in added_server]
            return 200, item_list
        return 201, '物理机不存在'

    def add_vm_server(self, data, user_id):
        parent_id = data.get('server_id')
        phy_server = TestServer.objects.filter(id=parent_id).first()
        if not phy_server:
            return False, '物理机不存在'
        ips = data.get('ips')
        post_data = {}
        if 'ws_id' not in data:
            return False, 'ws_id is required'
        post_data['state'] = 'Available' if not data.get('state') else data.get('state')
        post_data['owner'] = user_id if not data.get('owner') else data.get('owner')
        post_data['tags'] = data.get('tags', [])
        post_data['ws_id'] = data.get('ws_id')
        post_data['description'] = data.get('description', '')
        post_data['channel_type'] = data.get('channel_type', phy_server.channel_type)
        return self.add_server(ips, post_data, 1, user_id)


class CloudServerService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if not data.get('in_pool'):
            q &= Q(in_pool=True)
        if data.get('cluster_id'):
            server_id_list = TestClusterServer.objects.filter(cluster_id=data.get('cluster_id')).values_list(
                'server_id', flat=True)
            q &= Q(id__in=server_id_list)
        if data.get('tags'):
            server_id_list = ServerTagRelation.objects.filter(object_type=TestServerEnums.OBJECT_TYPE_CHOICES[1][0],
                                                              server_tag_id__in=data.getlist('tags')). \
                order_by('object_id').values_list('object_id', flat=True).distinct()
            q &= Q(id__in=server_id_list)
        if data.get('owner'):
            q &= Q(owner__in=data.getlist('owner'))
        if data.get('is_instance'):
            if data.get('is_instance') == "true":
                is_instance = True
            else:
                is_instance = False
            q &= Q(is_instance=is_instance)
        if data.get('server_conf'):
            if data.get('is_instance') == "true":
                q &= Q(instance_name__icontains=data.get('server_conf'))
            else:
                q &= Q(template_name__icontains=data.get('server_conf'))
        if data.get('description'):
            q &= Q(description__icontains=data.get('description'))
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        for item in ['state', 'real_state']:
            if data.get(item):
                state_list = data.getlist(item)
                if item == 'real_state':
                    state_list = [SERVER_REAL_STATE_PUT_MAP.get(i) for i in data.getlist(item)]
                q &= Q(**{'{}__in'.format(item): state_list})
        if data.get('release_rule'):
            q &= Q(release_rule=data.get('release_rule'))
        if data.get('manufacturer_ak_name'):
            cloud_ak_id = CloudAk.objects.filter(name__icontains=data.get('manufacturer_ak_name')).values_list('id',
                                                                                                               flat=True)
            q &= Q(Q(ak_id__in=cloud_ak_id) | Q(manufacturer__icontains=data.get('manufacturer_ak_name')))
        if data.get('region_zone'):
            q &= Q(Q(region__icontains=data.get('region_zone')) | Q(zone__icontains=data.get('region_zone')))
        if data.get('instance_type'):
            q &= Q(instance_type__icontains=data.get('instance_type'))
        if data.get('image'):
            q &= Q(image__icontains=data.get('image'))
        if data.get('bandwidth'):
            q &= Q(bandwidth=data.get('bandwidth'))
        if data.get('storage_type'):
            storage_type_list = data.get('storage_type').split(',')
            q &= Q(storage_type__in=storage_type_list)
        if data.get('release_rule'):
            q &= Q(release_rule=data.get('release_rule'))
        if data.get('channel_type'):
            channel_type_list = data.get('channel_type').split(',')
            q &= Q(channel_type__in=channel_type_list)
        if data.get('private_ip'):
            q &= Q(private_ip__icontains=data.get('private_ip'))
        if data.get('sn'):
            q &= Q(sn__icontains=data.get('sn'))
        if data.get('instance_id'):
            q &= Q(instance_id__icontains=data.get('instance_id'))
        return queryset.filter(q)

    @staticmethod
    def check_instance(post_data):
        ws_id = post_data.get('ws_id')
        if 'is_instance' not in post_data:
            return False, '参数错误'
        if int(post_data['is_instance']):
            instance_server = CloudServer.objects.filter(instance_id=post_data.get('instance_id')).first()
            if instance_server:
                workspace = Workspace.objects.filter(id=instance_server.ws_id).first()
                if workspace:
                    return False, f'该机器实例已经存在于【{workspace.show_name}】Workspace下！'
                else:
                    return False, '该机器实例已存在'
        else:
            if post_data.get('cluster_server_id') or post_data.get('cloud_server_id'):
                if post_data.get('cluster_server_id'):
                    cluster_server_id = post_data.get('cluster_server_id')
                    cluster_server = TestClusterServer.objects.filter(id=cluster_server_id).first()
                    if not cluster_server:
                        return False, 'cluster_server not existed'
                    server_id = cluster_server.server_id
                else:
                    server_id = post_data.get('cloud_server_id')
                if CloudServer.objects.filter(ws_id=ws_id, is_instance=0,
                                              template_name=post_data.get('name')).exists() and \
                        CloudServer.objects.filter(
                            ws_id=ws_id, is_instance=0,
                            template_name=post_data.get('name')).first().id != int(server_id):
                    cloud_server_id = CloudServer.objects.filter(
                        ws_id=ws_id, is_instance=0, template_name=post_data.get('name')).first().id
                    if TestClusterServer.objects.filter(server_id=cloud_server_id):
                        cluster_id = TestClusterServer.objects.filter(
                            server_id=cloud_server_id).first().cluster_id
                        cluster_name = TestCluster.objects.filter(id=cluster_id).first().name
                        return False, '配置名称已存在于{}集群中'.format(cluster_name)
            else:
                if CloudServer.objects.filter(ws_id=ws_id, is_instance=0, template_name=post_data.get('name')).exists():
                    cloud_server_id = CloudServer.objects.filter(
                        ws_id=ws_id, is_instance=0, template_name=post_data.get('name')).first().id
                    if TestClusterServer.objects.filter(server_id=cloud_server_id):
                        cluster_id = TestClusterServer.objects.filter(
                            server_id=cloud_server_id).first().cluster_id
                        cluster_name = TestCluster.objects.filter(id=cluster_id).first().name
                        return False, '配置名称已存在于{}集群中'.format(cluster_name)
        return True, 'success'

    def create(self, post_data, user_id):
        success, msg = self.check_instance(post_data)
        if not success:
            return False, msg
        is_instance = post_data['is_instance']
        update_owner(post_data)
        cloud_ak = CloudAk.objects.get(id=post_data.get('ak_id'))
        create_data = dict(
            job_id=0,
            parent_server_id=0,
            is_instance=is_instance,
            region=post_data['region'],
            zone=post_data['zone'],
            ak_id=post_data['ak_id'],
            manufacturer=post_data['manufacturer'],
            owner=post_data['owner'],
            description=post_data['description'],
            ws_id=post_data['ws_id'],
            channel_type=post_data.get('channel_type', 'toneagent'),
            release_rule=0 if not post_data.get('release_rule') else 1,
            provider='aliyun_ecs' if cloud_ak is None else cloud_ak.provider,
            state=post_data.get('state', 'Available')
        )
        if is_instance:
            create_data['instance_id'] = post_data['instance_id']
            create_data['instance_name'] = post_data['name']
            private_ip = post_data.get('private_ip', '')
            driver, provider = self.get_ali_driver(post_data['ak_id'], post_data['region'], post_data['zone'])
            if not driver:
                return False, 'provider driver is none'
            instance, disk_info = driver.get_instance(post_data['instance_id'], post_data['zone'])
            if not instance:
                return False, 'instance is none'
            if provider == TestServerEnums.CLOUD_SERVER_PROVIDER_CHOICES[0][0]:
                bandwidth = driver.get_bandwidth(post_data['instance_id'], post_data['region'])
                pub_ip = instance['public_ips'][0] if instance['public_ips'] \
                    else instance['extra']['eip_address']['ip_address']
                private_ip = instance.get('private_ips')[0]
                create_data.update(
                    image=instance.get('image'),
                    bandwidth=bandwidth,
                    instance_type=instance.get('instance_type'),
                    storage_type=disk_info.get('data_disk_category'),
                    storage_size=disk_info.get('data_disk_size'),
                    storage_number=disk_info.get('data_disk_count'),
                    sn=instance.get('serial_number'),
                    private_ip=private_ip,
                    pub_ip=pub_ip
                )
            else:
                image = ''
                instance_type = ''
                pub_ip = ''
                if instance and len(instance['Containers']) > 0 and 'Image' in instance['Containers'][0]:
                    image = instance['Containers'][0]['Image']
                    instance_type = '%dC%dG' % (int(instance['Cpu']), int(instance['Memory']))
                    private_ip = private_ip if private_ip else instance['IntranetIp']
                    pub_ip = instance['InternetIp']
                create_data.update(
                    image=image,
                    bandwidth=0,
                    instance_type=instance_type,
                    storage_type='',
                    storage_size='',
                    storage_number='',
                    sn='',
                    private_ip=private_ip,
                    pub_ip=pub_ip
                )
            add_agent_result = add_server_to_toneagent(private_ip, pub_ip)
            if not add_agent_result.get("SUCCESS"):
                return False, add_agent_result.get('RESULT') or add_agent_result.get('msg')
            tsn = add_agent_result['RESULT']['TSN']
            create_data.update({'tsn': tsn})
        else:
            temp_data = dict(
                template_name=post_data['name'],
                image=post_data['image'],
                image_name=post_data.get('image_name'),
                bandwidth=post_data['bandwidth'],
                release_rule=post_data['release_rule'],
                instance_type=post_data['instance_type'],
                storage_type=post_data.get('storage_type', 'cloud_efficiency'),
                storage_size=post_data.get('storage_size', '0'),
                storage_number=post_data.get('storage_number', '0'),
                system_disk_category=post_data.get('system_disk_category', 'cloud_efficiency'),
                system_disk_size=post_data.get('system_disk_size', '50'),
                extra_param=post_data.get('extra_param', dict())
            )
            create_data.update(temp_data)
        cloud_server = CloudServer.objects.create(**create_data)
        with transaction.atomic():
            operation_li = list()
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_cloud_server',
                'pid': cloud_server.id,
                'operation_type': 'create',
                'table': CloudServer._meta.db_table
            }
            operation_li.append(log_data)
            operation(operation_li)
        if 'tags' in post_data:
            server_tag_service = ServerTagRelationService()
            server_tag_service.add_tag_relation(post_data['tags'], cloud_server.id,
                                                TestServerEnums.OBJECT_TYPE_CHOICES[1][0],
                                                TestServerEnums.RUN_ENV_CHOICES[1][0])
        return True, cloud_server

    @staticmethod
    def update(data, pk, user_id):
        cloud_server = CloudServer.objects.filter(id=pk)
        if not cloud_server:
            return False, '云上机器不存在'
        update_owner(data)
        update_data = dict(
            owner=data.get('owner', cloud_server.first().owner),
            description=data.get('description'),
            channel_type=data.get('channel_type', cloud_server.first().channel_type),
            state=data.get('state', cloud_server.first().state)
        )
        private_ip = data.get('private_ip')
        if private_ip:
            update_data.update({'private_ip': private_ip})
        is_instance = cloud_server.first().is_instance
        ws_id = CloudServer.objects.get(id=pk).ws_id
        if not is_instance:
            if CloudServer.objects.filter(template_name=data.get('name'), ws_id=ws_id).exists() and \
                    CloudServer.objects.filter(template_name=data.get('name'), ws_id=ws_id).first().id != pk:
                return False, '配置名称已存在'

            cloud_ak = CloudAk.objects.filter(id=data.get('ak_id'), query_scope='all').first()
            temp_data = dict(
                template_name=data.get('name'),
                ak_id=data.get('ak_id'),
                manufacturer=data.get('manufacturer'),
                region=data.get('region'),
                zone=data.get('zone'),
                image=data.get('image'),
                image_name=data.get('image_name'),
                bandwidth=data.get('bandwidth'),
                release_rule=data.get('release_rule'),
                instance_type=data.get('instance_type'),
                storage_type=data.get('storage_type'),
                storage_size=data.get('storage_size'),
                storage_number=data.get('storage_number'),
                system_disk_category=data.get('system_disk_category', 'cloud_efficiency'),
                system_disk_size=data.get('system_disk_size', '50'),
                extra_param=data.get('extra_param', dict()),
                provider='aliyun_ecs' if cloud_ak is None else cloud_ak.provider
            )
            update_data.update(temp_data)
        server_tag_service = ServerTagRelationService()
        with transaction.atomic():
            operation_li = list()
            values_li = list()
            for key in update_data:
                values_li.append((key, getattr(cloud_server.first(), key), update_data[key]))
            server_tag_service.update_tag_log('aliyun', 'standalone', pk, data.get('tags', []), values_li)
            cloud_server.update(**update_data)
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_cloud_server',
                'pid': pk,
                'operation_type': 'update',
                'table': CloudServer._meta.db_table,
                'values_li': values_li
            }
            operation_li.append(log_data)
            operation(operation_li)
        if 'tags' in data:
            server_tag_service.add_tag_relation(data.get('tags'), pk, TestServerEnums.OBJECT_TYPE_CHOICES[1][0],
                                                TestServerEnums.RUN_ENV_CHOICES[1][0])
        return True, cloud_server.first()

    def delete(self, data, pk, user_id):
        is_release = data.get('is_release', True)
        cloud_server_queryset = CloudServer.objects.filter(id=pk)
        cloud_server = cloud_server_queryset.first()
        try:
            if cloud_server.is_instance and is_release:
                success, msg = release_cloud_server(cloud_server)
                if success:
                    self.delete_cloud_server(pk, user_id)
                    # 调用接口，将机器从toneagent系统移除
                    try:
                        remove_server_from_toneagent(cloud_server.private_ip, cloud_server.tsn)
                    except Exception as e:
                        error_logger.error(f'remove server from toneagent failed!server:'
                                           f'{cloud_server.private_ip}, error:{str(e)}')
                    return True, '机器是否成功({})'.format(msg)
                return False, msg
            else:
                self.delete_cloud_server(pk, user_id)
                return True, 'success'
        except IndexError:
            self.delete_cloud_server(pk, user_id)
            return True, 'server has been released'
        except Exception as e:
            msg = 'release server error:{}'.format(str(e))
            return False, msg

    @staticmethod
    def delete_cloud_server(pk, user_id):
        with transaction.atomic():
            TestTmplCase.objects.filter(server_provider='aliyun',
                                        run_mode='standalone',
                                        server_object_id=pk).update(server_object_id=None)
            CloudServer.objects.filter(id=pk).delete()
            operation_li = list()
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_cloud_server',
                'pid': pk,
                'operation_type': 'delete',
                'table': CloudServer._meta.db_table
            }
            operation_li.append(log_data)
            operation(operation_li)
            TestClusterServer.objects.filter(server_id=pk, cluster_type='aliyun').delete()

    @staticmethod
    def get_image_list(data):
        image_list = []
        cloud_ak = CloudAk.objects.filter(id=data.get('ak_id'), query_scope='all')
        if cloud_ak.exists():
            ak_obj = cloud_ak.first()
            images = CloudImage.objects.filter(ak_id=data.get('ak_id'), region=data.get('region'))
            if images:
                image_list = [
                    {
                        'id': tmp_img.image_id,
                        'name': tmp_img.image_name,
                        'owner_alias': 'self',
                        'os_name': tmp_img.os_name,
                        'platform': tmp_img.platform
                    }
                    for tmp_img in images
                ]
            if ak_obj.provider != TestServerEnums.CLOUD_SERVER_PROVIDER_CHOICES[1][0]:
                ecs_driver = EcsDriver(
                    ak_obj.access_id,
                    ak_obj.access_key,
                    data.get('region'),
                    data.get('zone')
                )
                image_list.extend(ecs_driver.get_images(data.get('instance_type')))
            return list(sorted(image_list, key=lambda x: (x.get('id', '') or x.get('name', ''))))

    @staticmethod
    def get_ali_driver(ak_id, region='cn-hangzhou', zone=''):
        cloud_ak = CloudAk.objects.filter(id=ak_id)
        if cloud_ak.exists():
            ak_obj = cloud_ak.first()
            if ak_obj.provider == TestServerEnums.CLOUD_SERVER_PROVIDER_CHOICES[1][0]:
                driver = EciDriver(ak_obj.access_id, ak_obj.access_key, region, zone)
            else:
                driver = EcsDriver(ak_obj.access_id, ak_obj.access_key, region, zone,
                                   resource_group_id=ak_obj.resource_group_id)
            return driver, ak_obj.provider
        else:
            return None, None

    def get_region_list(self, data):
        if not data.get('ak_id'):
            return False, '未选择AK，请先选择'
        driver, provider = self.get_ali_driver(data.get('ak_id'))
        if not driver:
            return False, '连接云服务器失败'
        regions = driver.get_regions()
        if regions:
            return True, regions
        return False, 'AK配置密钥不正确'

    def get_zone_list(self, data):
        driver, provider = self.get_ali_driver(data.get('ak_id'), data.get('region'))
        if not driver:
            return []
        try:
            zones = driver.get_zones()
            return [{'id': i.get('id'), 'name': i.get('name')} for i in zones]
        except Exception:
            return []

    def get_instance_type(self, data):
        driver, provider = self.get_ali_driver(data.get('ak_id'), data.get('region'), data.get('zone'))
        if not driver:
            return []
        if provider == TestServerEnums.CLOUD_SERVER_PROVIDER_CHOICES[0][0]:
            try:
                instance_types = driver.show_instance_type(zone=data.get('zone'))
                return instance_types
            except Exception:
                return []
        return []

    def get_aliyun_server(self, data):
        driver, provider = self.get_ali_driver(data.get('ak_id'), data.get('region'), data.get('zone'))
        if not driver:
            return []
        instances = driver.get_instances(region=data.get('region'), zone=data.get('zone'))
        if instances:
            if provider == TestServerEnums.CLOUD_SERVER_PROVIDER_CHOICES[0][0]:
                image = []
                for instance in instances:
                    private_ips = instance['private_ips'][0]
                    image.append({
                        'id': instance['id'],
                        'name': instance['name'],
                        'ip': private_ips
                    })
            else:
                image = [{'id': i['ContainerGroupId'], 'name': i['Containers'][0]['Name'],
                          'ip': i['InternetIp']} for i in instances]
            return list(sorted(image, key=lambda x: (x.get('id', '') or x.get('name', ''))))
        else:
            return instances

    def get_disk_categories(self, data):
        driver, provider = self.get_ali_driver(data.get('ak_id'), data.get('region'), data.get('zone'))
        if not driver:
            return []
        if provider == TestServerEnums.CLOUD_SERVER_PROVIDER_CHOICES[0][0]:
            zones_info = driver.get_zones()
            category_list = []
            for item in zones_info:
                category_list = []
                category_mapping = {
                    'cloud_efficiency': '高效云盘',
                    'cloud_ssd': 'SSD云盘',
                    'ephemeral_ssd': '本地SSD盘',
                    'cloud_essd': 'ESSD云盘',
                    'cloud': '普通云盘',
                    'cloud_auto': 'ESSD AutoPL云盘'
                }
                if item.get('id') == data.get('zone'):
                    available_disk_categories = item.get('available_disk_categories')
                    for category in available_disk_categories:
                        category_list.append({
                            'title': category_mapping.get(category, 'SSD云盘'),
                            'value': category
                        })
                    break
            return category_list
        return []


class CloudAkService(CommonService):
    @staticmethod
    def base_filter(data):
        q = Q()
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        if data.get('id'):
            q &= Q(id=data.get('id'))
        if data.get('name'):
            q &= Q(name__icontains=data.get('name'))
        if data.get('provider'):
            q &= Q(provider__in=data.getlist('provider'))
        if data.get('access_id'):
            q &= Q(access_id__icontains=data.get('access_id'))
        if data.get('access_key'):
            q &= Q(access_key__icontains=data.get('access_key'))
        if data.get('enable') in ['True', 'False', 'true', 'false']:
            q &= Q(enable='True' if data.get('enable') in ['true', 'True'] else 'False')
        if data.get('creator'):
            q &= Q(creator__in=data.getlist('creator'))
        if data.get('update_user'):
            q &= Q(update_user__in=data.getlist('update_user'))
        return q

    def filter(self, queryset, data):
        order_by = list()
        q = self.base_filter(data)
        if "gmt_created" in data.get('gmt_created', []):
            order_by.append('{}gmt_created'.format('-' if '-' in data.get('gmt_created') else ''))
        if 'gmt_modified' in data.get('gmt_modified', []):
            order_by.append('{}gmt_modified'.format('-' if '-' in data.get('gmt_modified') else ''))
        return order_by, queryset.filter(q)

    @staticmethod
    def create(data, operator):
        creator = operator.id
        ws_id = data.get('ws_id')
        name = data.get('name')
        provider = data.get('provider')
        access_id = data.get('access_id')
        access_key = data.get('access_key')
        if not all([ws_id, name, provider, access_id, access_key]):
            return False, 'The necessary parameters not exist'
        cloud_ak = CloudAk.objects.filter(ws_id=ws_id, name=name, provider=provider).first()
        if cloud_ak is not None:
            return False, 'cloud ak already exists'
        form_fields = ['name', 'provider', 'access_id', 'access_key', 'ws_id', 'description',
                       'enable', 'resource_group_id', 'vm_quota']
        create_data = dict()
        for field in form_fields:
            create_data.update({field: data.get(field)})
        create_data.update({'creator': creator})
        cloud_ak = CloudAk.objects.create(**create_data)
        return True, cloud_ak

    @staticmethod
    def update(data, operator):
        update_user = operator.id
        ak_id = data.get('id')
        ws_id = data.get('ws_id')
        name = data.get('name')
        provider = data.get('provider')
        if not all([ak_id, ws_id, name, provider]):
            return False, 'The necessary parameters not exist'
        cloud_ak = CloudAk.objects.filter(ws_id=ws_id, name=name, provider=provider).first()
        if cloud_ak is not None and str(cloud_ak.id) != str(ak_id):
            return False, 'cloud ak name existed'
        cloud_ak = CloudAk.objects.filter(id=ak_id)
        if cloud_ak.first() is None:
            return False, 'cloud ak not exists'
        allow_modify_fields = ['name', 'provider', 'access_id', 'access_key', 'description',
                               'enable', 'resource_group_id', 'vm_quota']
        update_data = dict()
        for field in allow_modify_fields:
            if data.get(field):
                if field in ['access_id', 'access_key'] and '*' in field:
                    continue
                update_data.update({field: data.get(field)})
        update_data.update({'update_user': update_user})
        cloud_ak.update(**update_data)
        return True, cloud_ak.first()

    @staticmethod
    def delete(data):
        CloudAk.objects.filter(id__in=data.get('id_list', [])).delete()


class CloudImageService(CommonService):
    @staticmethod
    def base_filter(data):
        q = Q()
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        if data.get('ak_id'):
            q &= Q(ak_id__in=data.get('ak_id'))
        if data.get('region'):
            q &= Q(region__icontains=data.get('region'))
        if data.get('provider'):
            q &= Q(provider__in=data.getlist('provider'))
        if data.get('image_name'):
            q &= Q(image_name__icontains=data.get('image_name'))
        if data.get('image_id'):
            q &= Q(image_id__icontains=data.get('image_id'))
        if data.get('image_version'):
            q &= Q(image_version__icontains=data.get('image_version'))
        if data.get('platform'):
            q &= Q(platform__icontains=data.get('platform'))
        if data.get('creator'):
            q &= Q(creator__in=data.getlist('creator'))
        return q

    def filter(self, queryset, data):
        order_by = list()
        q = self.base_filter(data)
        if data.get('update_user'):
            q &= Q(update_user__in=data.getlist('update_user'))
        if "gmt_created" in data.get('gmt_created', []):
            order_by.append('{}gmt_created'.format('-' if '-' in data.get('gmt_created') else ''))
        if 'gmt_modified' in data.get('gmt_modified', []):
            order_by.append('{}gmt_modified'.format('-' if '-' in data.get('gmt_modified') else ''))
        return order_by, queryset.filter(q)

    @staticmethod
    def create(data, operator):
        creator = operator.id
        cloud_image = CloudImage.objects.filter(ws_id=data.get('ws_id'),
                                                ak_id=data.get('ak_id'),
                                                provider=data.get('provider'),
                                                region=data.get('region'),
                                                image_name=data.get('image_name')).first()
        if cloud_image is not None:
            return False, 'cloud image already exists'
        form_fields = ['ws_id', 'ak_id', 'provider', 'region', 'public_type', 'usage_type', 'login_user', 'image_id',
                       'image_name', 'image_version', 'image_size', 'os_name', 'os_type', 'os_arch', 'platform']
        create_data = dict()
        for field in form_fields:
            create_data.update({field: data.get(field, '')})
        create_data.update({'creator': creator, 'public_type': data.get('public_type', 0)})
        cloud_image = CloudImage.objects.create(**create_data)
        return True, cloud_image

    @staticmethod
    def update(data, operator):
        update_user = operator.id
        cloud_image = CloudImage.objects.filter(id=data.get('id'))
        if cloud_image.first() is None:
            return False, 'cloud image not exists'
        allow_modify_fields = ['ak_id', 'provider', 'region', 'public_type', 'usage_type', 'login_user', 'image_id',
                               'image_name', 'image_version', 'image_size', 'os_name', 'os_type', 'os_arch', 'platform']
        update_data = dict()
        for field in allow_modify_fields:
            if data.get(field):
                update_data.update({field: data.get(field)})
        update_data.update({'update_user': update_user})
        cloud_image.update(**update_data)
        return True, cloud_image.first()

    @staticmethod
    def delete(data):
        CloudImage.objects.filter(id__in=data.get('id_list', [])).delete()


class TestClusterService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('name'):
            q &= Q(name__contains=data.get('name'))
        if data.get('tags'):
            server_id_list = ServerTagRelation.objects.filter(object_type='cluster',
                                                              server_tag_id__in=data.getlist('tags')). \
                order_by('object_id').values_list('object_id', flat=True).distinct()
            q &= Q(id__in=server_id_list)
        if data.get('cluster_type'):
            q &= Q(cluster_type=data.get('cluster_type'))
        if data.get('is_instance'):
            q &= Q(is_instance=data.get('is_instance'))
        if data.get('owner'):
            q &= Q(owner__in=data.getlist('owner'))
        if data.get('description'):
            q &= Q(description__contains=data.get('description'))
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        if data.get('name'):
            return sorted(queryset.filter(q), key=lambda x: 0 if x.name == data.get('name') else 1)
        return queryset.filter(q)

    def create(self, post_data, user_id):
        if 'description' not in post_data:
            post_data['description'] = ''
        test_cluster = TestCluster.objects.filter(name=post_data['name'], ws_id=post_data['ws_id']).first()
        if test_cluster:
            return False, '集群已存在'
        is_instance = post_data.get('is_instance') if post_data.get('is_instance') else 1
        update_owner(post_data)
        create_data = dict(
            name=post_data['name'],
            cluster_type=post_data['cluster_type'],
            owner=post_data['owner'],
            ws_id=post_data['ws_id'],
            description=post_data['description'],
            is_instance=is_instance
        )
        test_cluster = TestCluster.objects.create(**create_data)
        with transaction.atomic():
            operation_li = list()
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_cluster_aligroup'
                if post_data['cluster_type'] == TestServerEnums.RUN_ENV_CHOICES[0][0] else 'machine_cluster_aliyun',
                'pid': test_cluster.id,
                'operation_type': 'create',
                'table': TestCluster._meta.db_table
            }
            operation_li.append(log_data)
            operation(operation_li)
        if 'tags' in post_data:
            server_tag_service = ServerTagRelationService()
            server_tag_service.add_tag_relation(post_data['tags'], test_cluster.id,
                                                TestServerEnums.OBJECT_TYPE_CHOICES[0][0], post_data['cluster_type'])
        return True, test_cluster

    @staticmethod
    def update(data, pk, user_id):
        test_cluster = TestCluster.objects.filter(id=pk)
        if test_cluster is None:
            pass
        update_owner(data)
        update_data = dict(
            name=data.get('name'),
            owner=data.get('owner'),
            description=data.get('description')
        )
        server_tag_service = ServerTagRelationService()
        with transaction.atomic():
            operation_li = list()
            values_li = list()
            for key in update_data:
                values_li.append((key, getattr(test_cluster.first(), key), update_data[key]))
            server_tag_service.update_tag_log(test_cluster.first().cluster_type, 'cluster',
                                              pk, data.get('tags', []), values_li)
            test_cluster.update(**update_data)
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_cluster_aligroup'
                if test_cluster.first().cluster_type == TestServerEnums.RUN_ENV_CHOICES[0][0]
                else 'machine_cluster_aliyun',
                'pid': pk,
                'operation_type': 'update',
                'table': TestCluster._meta.db_table,
                'values_li': values_li
            }
            operation_li.append(log_data)
            operation(operation_li)
        # 修改标签为空
        if data.get('tags') == list():
            ServerTagRelation.objects.filter(object_type=TestServerEnums.OBJECT_TYPE_CHOICES[0][0],
                                             object_id=pk).delete()
        if data.get('tags'):
            server_tag_service.add_tag_relation(data.get('tags'), pk, TestServerEnums.OBJECT_TYPE_CHOICES[0][0],
                                                test_cluster.first().cluster_type)
        return True, test_cluster.first()

    def delete(self, data, pk, user_id):
        with transaction.atomic():
            test_cluster = TestCluster.objects.filter(id=pk)
            if test_cluster:
                operation_li = list()
                log_data = {
                    'creator': user_id,
                    'operation_object': 'machine_cluster_aligroup'
                    if test_cluster.first().cluster_type == TestServerEnums.RUN_ENV_CHOICES[0][0]
                    else 'machine_cluster_aliyun',
                    'pid': pk,
                    'operation_type': 'delete',
                    'table': TestCluster._meta.db_table
                }
                operation_li.append(log_data)
                TestTmplCase.objects.filter(server_provider=test_cluster.first().cluster_type,
                                            run_mode='cluster',
                                            server_object_id=pk).update(server_object_id=None)
                if test_cluster.first().cluster_type == TestServerEnums.RUN_ENV_CHOICES[0][0]:
                    cluster_servers = TestClusterServer.objects.filter(
                        cluster_id=pk, cluster_type='aligroup').values_list('server_id', flat=True)
                    TestServer.objects.filter(id__in=cluster_servers, in_pool=0).delete()
                TestCluster.objects.filter(id=pk).delete()
                server_ids = list(TestClusterServer.objects.filter(cluster_id=pk).values_list('server_id', flat=True))
                CloudServer.objects.filter(id__in=server_ids, in_pool=0).delete()
                TestClusterServer.objects.filter(cluster_id=pk).delete()
                operation(operation_li)

    def get_cloud_type(self, pk):
        server_list = TestClusterServer.objects.filter(cluster_id=pk).values_list('server_id', flat=True)
        if server_list:
            cloud_server = CloudServer.objects.filter(id__in=server_list)
            if cloud_server:
                if cloud_server.first().is_instance:
                    return 1
                else:
                    return 2
            else:
                return 0
        else:
            return 0


class TestClusterServerService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('cluster_id'):
            q &= Q(cluster_id=data.get('cluster_id'))
        return queryset.filter(q)

    @staticmethod
    def create_test_server(post_data, user_id):
        if TestClusterServer.objects.filter(cluster_id=post_data['cluster_id'],
                                            var_name=post_data['var_name']).exists():
            return False, '变量名已存在'
        test_server = TestServer.objects.\
            filter((Q(ip=post_data['ip']) | Q(sn=post_data['ip'])) & Q(ws_id=post_data['ws_id']))
        update_owner(post_data)
        if test_server:
            server_id = test_server.first().id
        else:
            # 2020/12/28 修改内网集群中添加内网单机不存在机器, 机器未加入单机池：in_pool=0
            post_data['description'] = '从集群添加非资源机'
            test_server_service = TestServerService()
            success, msg = test_server_service.add_server([post_data['ip']], post_data, 0, user_id)
            if success:
                test_server = TestServer.objects.filter(
                    (Q(ip=post_data['ip']) | Q(sn=post_data['ip'])) & Q(ws_id=post_data['ws_id']))
                server_id = test_server.first().id
            else:
                return success, msg
        # 集群下添加第一个机器时，角色为local
        if not TestClusterServer.objects.filter(cluster_id=post_data['cluster_id']).exists():
            post_data['role'] = 'local'
            post_data['baseline_server'] = True
        else:
            post_data['role'] = 'remote'
            post_data['baseline_server'] = False
        create_data = dict(
            cluster_id=post_data['cluster_id'],
            server_id=server_id,
            cluster_type=TestServerEnums.RUN_ENV_CHOICES[0][0],
            role=post_data['role'],
            baseline_server=post_data['baseline_server'],
            kernel_install=post_data['kernel_install'],
            var_name=post_data['var_name']
        )
        cluster_server = TestClusterServer.objects.filter(cluster_id=post_data['cluster_id'], server_id=server_id)
        if cluster_server:
            return False, '机器已添加'
        cluster_server = TestClusterServer.objects.create(**create_data)
        with transaction.atomic():
            operation_li = list()
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_cluster_aligroup_server',
                'pid': cluster_server.id,
                'operation_type': 'create',
                'table': TestClusterServer._meta.db_table
            }
            operation_li.append(log_data)
            operation(operation_li)
        TestServer.objects.filter(id=test_server.first().id).update(
            spec_use=1,
            private_ip=post_data.get('private_ip', '')
        )
        return True, cluster_server

    @staticmethod
    def check_cloud_server(post_data):
        # 同一集群下，变量名不能相同
        if TestClusterServer.objects.filter(cluster_id=post_data['cluster_id'],
                                            var_name=post_data['var_name']).exists():
            return False, '变量名已存在'

        server_id_list = TestClusterServer.objects.filter(cluster_id=post_data['cluster_id']
                                                          ).values_list('server_id', flat=True)
        if server_id_list:
            cloud_server = CloudServer.objects.filter(id=server_id_list[0])
            if cloud_server.exists():
                if cloud_server.first().region != post_data.get('region') or \
                        cloud_server.first().zone != post_data.get('zone'):
                    return False, '同一集群下，region和zone必须保持一致'
        return True, ''

    def create_cloud_server(self, post_data, user_id):
        success, msg = self.check_cloud_server(post_data)
        if not success:
            return False, msg
        test_server = CloudServer.objects.filter(instance_id=post_data.get('instance_id')).first()
        if test_server is None:
            cloud_server_service = CloudServerService()
            success, test_server = cloud_server_service.create(post_data, user_id)
            if not success:
                return False, test_server
            test_server.in_pool = False
            test_server.save()
        else:
            test_server.spec_use = 1
            test_server.save()
        server_id = test_server.id
        # 集群下添加第一个机器时，角色为local
        if not TestClusterServer.objects.filter(cluster_id=post_data['cluster_id']).exists():
            post_data['role'] = 'local'
            post_data['baseline_server'] = True
        else:
            post_data['role'] = 'remote'
            post_data['baseline_server'] = False
        create_data = dict(
            cluster_id=post_data['cluster_id'],
            server_id=server_id,
            cluster_type=TestServerEnums.RUN_ENV_CHOICES[1][0],
            role=post_data['role'],
            baseline_server=post_data['baseline_server'],
            kernel_install=post_data['kernel_install'],
            var_name=post_data['var_name']
        )
        cluster_server = TestClusterServer.objects.filter(cluster_id=post_data['cluster_id'], server_id=server_id)
        if cluster_server:
            return False, '机器已添加'
        cluster_server = TestClusterServer.objects.create(**create_data)
        with transaction.atomic():
            operation_li = list()
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_cluster_aliyun_server',
                'pid': cluster_server.id,
                'operation_type': 'create',
                'table': TestClusterServer._meta.db_table
            }
            operation_li.append(log_data)
            operation(operation_li)
        CloudServer.objects.filter(id=test_server.id).update(spec_use=1)
        return True, cluster_server

    @staticmethod
    def update_test_server(data, pk, user_id):
        cluster_server = TestClusterServer.objects.filter(id=pk)
        if cluster_server.first() is None:
            return False, None
        # 同一集群下，变量名不能相同
        tmp_server = TestClusterServer.objects.filter(cluster_id=cluster_server.first().cluster_id,
                                                      var_name=data.get('var_name')).first()
        if tmp_server is not None and tmp_server.id != pk:
            return False, '变量名在集群: {} 中已存在'.format(TestCluster.objects.get(
                id=cluster_server.first().cluster_id).name)
        update_data = dict(
            baseline_server=0 if data.get('baseline_server') in [False, 'false'] else 1,
            kernel_install=0 if data.get('kernel_install') in [False, 'false'] else 1,
            var_name=data.get('var_name')
        )
        if data.get('role'):
            update_data['role'] = data.get('role')
        with transaction.atomic():
            operation_li = list()
            values_li = list()
            for key in update_data:
                values_li.append((key, getattr(cluster_server.first(), key), update_data[key]))
            # 修改角色为local时, 是否基线机器为 True时,其他机器同步修改
            cluster_servers = TestClusterServer.objects.filter(cluster_id=cluster_server.first().cluster_id)
            if data.get('role') == 'local':
                cluster_servers.update(role='remote')
            if data.get('baseline_server'):
                cluster_servers.update(baseline_server=False)
            cluster_server.update(**update_data)
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_cluster_aligroup_server',
                'pid': pk,
                'operation_type': 'update',
                'table': TestClusterServer._meta.db_table,
                'values_li': values_li
            }
            operation_li.append(log_data)
            operation(operation_li)
        test_server = TestServer.objects.filter(id=cluster_server.first().server_id)
        if test_server:
            test_server.update(private_ip=data.get('private_ip'), channel_type=data.get('channel_type'))
            server_state = data.get('state')
            if server_state in ['Reserved', 'Available', 'Unusable']:
                test_server.update(state=server_state)
        return True, cluster_server.first()

    @staticmethod
    def update_cloud_server(data, pk, user_id):
        cluster_server = TestClusterServer.objects.filter(id=pk)
        if cluster_server.first() is None:
            return False, '机器不存在'
        # 同一集群下，变量名不能相同
        tmp_server = TestClusterServer.objects.filter(cluster_id=cluster_server.first().cluster_id,
                                                      var_name=data.get('var_name')).first()
        if tmp_server is not None and tmp_server.id != pk:
            return False, '变量名在集群: {} 中已存在'.format(TestCluster.objects.get(
                id=cluster_server.first().cluster_id).name)
        allow_update_fields = ['role', 'baseline_server', 'kernel_install', 'var_name']
        update_data = dict()
        for field in allow_update_fields:
            if data.get(field) or data.get(field) == 0:
                update_data[field] = data.get(field)
        with transaction.atomic():
            operation_li = list()
            values_li = list()
            for key in update_data:
                values_li.append((key, getattr(cluster_server.first(), key), update_data[key]))
            # 修改角色为local时, 是否基线机器为 True时,其他机器同步修改
            cluster_servers = TestClusterServer.objects.filter(cluster_id=cluster_server.first().cluster_id)
            if data.get('role') == 'local':
                cluster_servers.update(role='remote')
            if data.get('baseline_server'):
                cluster_servers.update(baseline_server=False)
            cluster_server.update(**update_data)
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_cluster_aliyun_server',
                'pid': pk,
                'operation_type': 'update',
                'table': TestClusterServer._meta.db_table,
                'values_li': values_li
            }
            operation_li.append(log_data)
            operation(operation_li)
        CloudServerService.update(data, cluster_server.first().server_id, user_id)
        return True, cluster_server.first()

    def delete(self, data, pk, user_id):
        cluster_server = TestClusterServer.objects.filter(id=pk)
        if cluster_server:
            server = cluster_server.first()
            if server.cluster_type == TestServerEnums.RUN_ENV_CHOICES[0][0]:
                test_server = TestServer.objects.filter(id=server.server_id)
                # 2021/1/6 删除内网集群机器，同步删除内网单机机器(从单机池加入不删除，非单机池加入删除机器)
                test_server_obj = test_server.first()
                if test_server_obj is not None and not test_server_obj.in_pool:
                    if test_server_obj.state == 'Occupied':
                        return False, '机器被占用'
                    # 通过集群加入的虚拟机，父主机也删除
                    if test_server_obj.parent_server_id is not None:
                        TestServer.objects.filter(id=test_server_obj.parent_server_id).delete()
                    test_server.delete()
                else:
                    # 单机池机器仅修改占用状态
                    test_server.update(spec_use=0)
            else:
                test_server = CloudServer.objects.filter(id=server.server_id)
                test_server_obj = test_server.first()
                if test_server_obj is not None and not test_server_obj.in_pool:
                    if test_server_obj.state == 'Occupied':
                        return False, '机器被占用'
                    test_server.delete()
                else:
                    test_server.update(spec_use=0)
            with transaction.atomic():
                operation_li = list()
                log_data = {
                    'creator': user_id,
                    'operation_object': 'machine_cluster_aligroup_server'
                    if cluster_server.first().cluster_type == TestServerEnums.RUN_ENV_CHOICES[0][0]
                    else 'machine_cluster_aliyun_server',
                    'pid': pk,
                    'operation_type': 'delete',
                    'table': TestClusterServer._meta.db_table
                }
                operation_li.append(log_data)
                cluster_server.delete()
                if server.role == 'local':
                    group_cluster_server = TestClusterServer.objects.filter(cluster_id=server.cluster_id).first()
                    if group_cluster_server:
                        group_cluster_server.role = 'local'
                        group_cluster_server.save()
                operation(operation_li)
        return True, '删除成功'

    @staticmethod
    def check_var_name(post_data):
        # 同一集群下，变量名不能相同
        cluster_server_id = post_data.get('cluster_server_id')
        cluster_server = TestClusterServer.objects.filter(cluster_id=post_data.get('cluster_id'),
                                                          var_name=post_data.get('var_name')).first()
        if cluster_server is not None and cluster_server_id is not None and cluster_server_id != cluster_server.id:
            return False, '变量名已存在'
        return True, '变量名校验通过'


class ServerTagService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        storted_fun = lambda x: (0 if not x.create_user else 1, -x.id)
        if data.get('name'):
            q &= Q(name__icontains=data.get('name'))
        if data.get('description'):
            q &= Q(description__icontains=data.get('description'))
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        if data.get('run_mode') and data.get('run_environment'):
            server_tag_id_list = ServerTagRelation.objects.filter(run_environment=data.get('run_environment'),
                                                                  object_type=data.get('run_mode')
                                                                  ).values_list('server_tag_id', flat=True)
            q &= Q(id__in=set(server_tag_id_list))
        if data.get('tag_id_list'):
            tag_id_list = str(data.get('tag_id_list')).split(',')
            # 排序优先级：集群当前的标签 > 系统预设标签 > id
            storted_fun = lambda x: (0 if str(x.id) in tag_id_list else 1, 0 if not x.create_user else 1, -x.id)
        return sorted(queryset.filter(q), key=storted_fun)

    @staticmethod
    def create(data, user_id):
        form_fields = ['name', 'tag_color', 'create_user', 'update_user', 'description', 'ws_id']
        create_data = dict()
        for field in form_fields:
            create_data.update({field: data.get(field)})
        create_data.update({'create_user': user_id})
        create_data.update({'update_user': user_id})
        tag = ServerTag.objects.filter(name=data.get('name'), ws_id=data.get('ws_id')).first()
        if tag:
            return False, tag
        else:
            server_tag = ServerTag.objects.create(**create_data)
            with transaction.atomic():
                log_data = {
                    'creator': user_id,
                    'operation_object': 'machine_server_tag',
                    'pid': server_tag.id,
                    'operation_type': 'create',
                    'table': ServerTag._meta.db_table
                }
                operation([log_data])
            return True, server_tag

    @staticmethod
    def update(data, pk, user_id):
        allow_modify_fields = ['name', 'tag_color', 'description']
        server_tag = ServerTag.objects.filter(id=pk)
        if server_tag.first() is None:
            return False, 'not existed'
        if data.get('name') != server_tag.first().name:
            server_tag_old = ServerTag.objects.filter(name=data.get('name'), ws_id=server_tag.first().ws_id).first()
            if server_tag_old:
                return False, 'name existed'
        update_data = dict()
        update_data.update({'update_user': user_id})
        for field in allow_modify_fields:
            update_data.update({field: data.get(field)})

        with transaction.atomic():
            values_li = list()
            for key in update_data:
                values_li.append((key, getattr(server_tag.first(), key), update_data[key]))
            server_tag.update(**update_data)
            operation_li = list()
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_server_tag',
                'pid': pk,
                'operation_type': 'update',
                'table': ServerTag._meta.db_table,
                'values_li': values_li
            }
            operation_li.append(log_data)
            operation(operation_li)
        return True, server_tag.first()

    def delete(self, data, pk, user_id):
        with transaction.atomic():
            operation_li = list()
            ServerTag.objects.filter(id=pk).delete()
            log_data = {
                'creator': user_id,
                'operation_object': 'machine_server_tag',
                'pid': pk,
                'operation_type': 'delete',
                'table': ServerTag._meta.db_table
            }
            operation_li.append(log_data)
            operation(operation_li)


class ServerTagRelationService(CommonService):

    @staticmethod
    def add_tag_relation(tags, test_server_id, server_type, run_environment):
        tag_list = []
        for tag_id in tags:
            tag_list.append(
                ServerTagRelation(
                    run_environment=run_environment,
                    object_type=server_type,
                    object_id=test_server_id,
                    server_tag_id=tag_id
                )
            )
        ServerTagRelation.objects.filter(object_type=server_type, object_id=test_server_id).delete()
        ServerTagRelation.objects.bulk_create(tag_list)

    @staticmethod
    def update_tag_log(run_environment, object_type, object_id, new_tags, values_li):
        origin_tags = ServerTagRelation.objects.filter(run_environment=run_environment,
                                                       object_type=object_type,
                                                       object_id=object_id
                                                       ).values_list('server_tag_id', flat=True)
        if set(origin_tags) != set(new_tags):
            origin_tags = ServerTag.objects.filter(id__in=origin_tags).values_list('name', flat=True)
            new_tag = ServerTag.objects.filter(id__in=new_tags).values_list('name', flat=True)
            values_li.append(('tag', ', '.join(sorted(origin_tags)), ', '.join(sorted(new_tag))))

    @staticmethod
    def add_base_server_tag(server, ws_id):
        arch = server.get('arch')
        sm_name = server.get('sm_name')
        extend_tags = list()
        if arch:
            arch_tag = ServerTag.objects.filter(name=arch, ws_id=ws_id).first()
            if arch_tag is None:
                arch_tag = ServerTag.objects.create(name=arch, ws_id=ws_id, description='arch标签')
            extend_tags.append(arch_tag.id)

        if sm_name:
            sm_name_tag = ServerTag.objects.filter(name=sm_name, ws_id=ws_id).first()
            if sm_name_tag is None:
                sm_name_tag = ServerTag.objects.create(name=sm_name, ws_id=ws_id, description='机型标签')
            extend_tags.append(sm_name_tag.id)
        return extend_tags


class ToneAgentService(CommonService):

    def toneagent_deploy(self, post_data):
        """
         {
            "instance_id": "xxx",
            "arch": "x86_64",
            "version": "aliyun_x86_64_1.0.1",
            "mode": "active"
         }
        """
        server = CloudServer.objects.get(instance_id=post_data.get('instance_id'))
        return deploy_agent_by_ecs_assistant(
            cloud_server=server,
            arch=post_data.get('arch'),
            version=post_data.get('version'),
            mode=post_data.get('mode'),
        )

    def toneagent_version_list(self, version):
        list_url = '{}/v1/agent/version/manage?arch={}&page_num=1&page_size=100'.format(TONEAGENT_DOMAIN, version)
        try:
            result = requests.get(list_url).json()
        except Exception as e:
            error_logger.error('request to toneagent version list api failed! detail: {}'.format(str(e)))
            return False, 'request to toneagent version list api failed!'
        return True, result['data']


class ServerSnapshotService(CommonService):
    @staticmethod
    def filter(request):
        data = request.GET
        q = Q()
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        test_server_list = TestServerSnapshot.objects.exclude(ip='').filter(q).values_list('ip', flat=True).distinct()
        cloud_server_list = CloudServerSnapshot.objects.exclude(private_ip='').filter(q). \
            values_list('private_ip', flat=True).distinct()
        test_server_sn_list = TestServerSnapshot.objects.exclude(sn='').filter(q & Q(ip='') & Q(sn__isnull=False)). \
            values_list('sn', flat=True).distinct()
        cloud_server_sn_list = CloudServerSnapshot.objects.exclude(sn=''). \
            filter(q & Q(pub_ip='') & Q(sn__isnull=False)).values_list('sn', flat=True).distinct()
        return list(test_server_list) + list(cloud_server_list) + list(test_server_sn_list) + list(cloud_server_sn_list)


class SyncServerStateService(CommonService):
    @staticmethod
    def sync_state(data):
        provider = data.get('server_provider')
        server_id = data.get('server_id')
        try:
            if provider == TestServerEnums.RUN_ENV_CHOICES[1][0]:
                server = CloudServer.objects.filter(id=server_id).first()
                ip = server.private_ip
            else:
                server = TestServer.objects.filter(id=server_id).first()
                ip = server.ip
            tsn = server.tsn
            _, channel_state, _ = TestServerService().get_channel_state(
                {
                    'ip': ip,
                    'tsn': tsn
                }
            )
            if channel_state:
                if server.state == TestServerState.BROKEN:
                    if server.history_state == TestServerState.RESERVED:
                        server.state = server.history_state
                    else:
                        server.state = TestServerState.AVAILABLE
                server.real_state = TestServerState.AVAILABLE
            else:
                server.state = TestServerState.BROKEN
                server.real_state = TestServerState.BROKEN
            server.save()
            return True
        except Exception as e:
            error_logger.error(f'sync server state error: {e}')
            return False


def release_cloud_server(cloud_server):
    cloud_ak = CloudAk.objects.filter(id=cloud_server.ak_id, query_scope='all').first()
    if cloud_ak.provider == TestServerEnums.CLOUD_SERVER_PROVIDER_CHOICES[0][0]:
        driver = EcsDriver(
            cloud_ak.access_id, cloud_ak.access_key, cloud_server.region,
            cloud_server.zone, resource_group_id=cloud_ak.resource_group_id
        )
    else:
        driver = EciDriver(
            cloud_ak.access_id, cloud_ak.access_key,
            cloud_server.region, cloud_server.zone
        )
    success, msg = driver.destroy_instance(cloud_server.instance_id)
    return success, msg


class AgentTaskInfoService(CommonService):
    def get_agent_task_info(self, data):
        try:
            request = QueryTaskRequest(
                settings.TONEAGENT_ACCESS_KEY,
                settings.TONEAGENT_SECRET_KEY
            )
            request.set_tid(data.get('tid'))
            request.set_query_detail(True)
            res = request.send_request()
            task_info = res.get('data')
            if task_info.get('env'):
                new_env_info = self._parse_env_info(task_info.get('env'))
                task_info['env'] = new_env_info
            new_script = self._parse_script(task_info.get('script'))
            task_info['script'] = new_script
            return task_info
        except Exception as e:
            error_logger.error(f'get agent task info failed:{e}')
            return dict()

    @staticmethod
    def _parse_env_info(env_info):
        env_info_dict = pack_env_infos(env_info)
        new_info_data = []
        for k, v in env_info_dict.items():
            new_info_data.append(f'{k}={v}')
        return '\n'.join(new_info_data)

    @staticmethod
    def _parse_script(script):
        new_script = ''
        sensitive_words = ['export', 'access_id', 'access_key']
        script = base64.b64decode(script).decode()
        for line in script.split('\n'):
            for sensitive_word in sensitive_words:
                if sensitive_word in line:
                    continue
            new_script += f'{line}\n'
        return new_script


def auto_release_server():
    waiting_release_servers = ReleaseServerRecord.objects.filter(is_release=False)
    for waiting_release_server in waiting_release_servers:
        if waiting_release_server.estimated_release_at < datetime.now():
            cloud_server = CloudServer.objects.filter(id=waiting_release_server.server_id)
            if cloud_server.exists():
                success, msg = release_cloud_server(cloud_server.first())
                scheduler_logger.info(f'auto release server result: {success} | {msg}')
            else:
                scheduler_logger.info(f'cloud server({waiting_release_server.server_id}) not exists')
            waiting_release_server.is_release = True
            waiting_release_server.release_at = datetime.now()
            waiting_release_server.save()
            cloud_server.delete()