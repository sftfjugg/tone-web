# flake8: noqa
import json
import logging
import re

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

from tone.core.common.permission_config_info import SYS_PERMISSION_CONFIG, WS_PERMISSION_CONFIG, VALID_URL_LIST, \
    RE_PERMISSION_CONFIG
from tone.core.utils.config_parser import get_config_from_db
from tone.models import RoleMember, WorkspaceMember, Role, Workspace, User


logger = logging.getLogger('permission_manage')


def check_operator_permission(operator_id, check_obj):
    """非系统管理员super_admin, sys_admin ws_member 只能操作自己"""
    sys_role_id = RoleMember.objects.get(user_id=operator_id).role_id
    sys_role = Role.objects.get(id=sys_role_id).title
    if sys_role not in ['super_admin', 'sys_admin']:
        operator_role_id = WorkspaceMember.objects.get(ws_id=check_obj.ws_id, user_id=operator_id).role_id
        operator_role = Role.objects.get(id=operator_role_id).title
        allow_list = ['ws_owner', 'ws_admin', 'ws_test_admin']
        if operator_role not in allow_list and operator_id != check_obj.creator:
            return False
    return True


class ValidPermission(MiddlewareMixin):
    """权限校验"""
    @staticmethod
    def check_white_list(current_path):
        """校验白名单"""
        if 'admin/' in current_path:
            return True
        config_white_list = [tmp_url.strip() for tmp_url in
                             get_config_from_db('WHITE_LIST', '').replace('，', ',').split(',') if tmp_url.strip()]
        white_list = list(set(config_white_list) | set(VALID_URL_LIST))
        for valid_url in white_list:
            ret = re.match(valid_url, current_path)
            if ret:
                return True
        return False

    @staticmethod
    def check_sys_permission(current_path, current_method, current_role_name, ws_id):
        """校验系统级权限"""
        # 管理员拥有一切权限
        if current_role_name == 'sys_admin':
            return 'success'
        # 当前访问路由需要进行权限校验
        if current_path in SYS_PERMISSION_CONFIG:
            url_permission = SYS_PERMISSION_CONFIG[current_path]
            # 验证请求方式
            if current_method in url_permission:
                method_permission = url_permission[current_method]
                if current_role_name in method_permission:
                    return 'success'
                elif "ws_permission" not in method_permission:
                    return 'fail'
                elif not ws_id and "ws_permission" in method_permission:
                    return 'fail'
        return 'success'

    @staticmethod
    def ws_white_handle(workspace_member, current_path, current_role_name, user_id, ws_id):
        """ws下路径白名单"""
        if workspace_member is None:
            # 是否是申请加入私有请求
            if current_path in ['/api/sys/project/list/', '/api/sys/workspace/member/apply/',
                                '/api/auth/personal_center/', '/api/sys/workspace/history/']:
                return 'success'
            # 系统管理员直接进入私密ws, 默认角色ws_member
            elif current_role_name == 'sys_admin':
                WorkspaceMember.objects.get_or_create(user_id=user_id, ws_id=ws_id,
                                                      role_id=Role.objects.get(title='ws_member').id)
                return 'success'
            else:
                return 'fail'
        return 'pass'

    @staticmethod
    def check_ws_url_permission(current_path, current_method, ws_role_name):
        """ws路由权限校验"""
        if current_path in WS_PERMISSION_CONFIG:
            url_permission = WS_PERMISSION_CONFIG[current_path]
            # 验证请求方式
            if current_method in url_permission:
                method_permission = url_permission.get(current_method)
                if ws_role_name in method_permission:
                    return 'success'
                else:
                    return 'fail'
        return 'pass'

    @staticmethod
    def check_re_permission(current_path, current_method, ws_role_name):
        """正则表达式路由校验"""
        for re_url in RE_PERMISSION_CONFIG:
            ret = re.match(re_url, current_path)
            if ret:
                re_method_permission = RE_PERMISSION_CONFIG.get(re_url)
                # 验证请求方式
                if current_method in re_method_permission:
                    method_permission = re_method_permission[current_method]
                    if ws_role_name in method_permission:
                        return True
                    else:
                        return False
        return True

    def check_ws_permission(self, current_path, current_role_name, user_id, ws_id, current_method):
        """ws级别权限校验"""
        workspace_member = WorkspaceMember.objects.filter(user_id=user_id, ws_id=ws_id).first()
        res_check = self.ws_white_handle(workspace_member, current_path, current_role_name, user_id, ws_id)
        if res_check == 'success':
            return True
        ws_role_name = ''
        if workspace_member is not None:
            ws_role = Role.objects.get(id=workspace_member.role_id)
            ws_role_name = ws_role.title
        else:
            # 私密ws,非成员无权限
            request_ws = Workspace.objects.filter(id=ws_id).first()
            if request_ws is None:
                return False
            else:
                if not request_ws.is_public:
                    return False
        if ws_role_name == 'ws_owner':
            return True
        ws_url_res = self.check_ws_url_permission(current_path, current_method, ws_role_name)
        if ws_url_res == 'success':
            return True
        elif ws_url_res == 'fail':
            return False
        # 处理正则格式的路由
        if not self.check_re_permission(current_path, current_method, ws_role_name):
            return False
        return True

    @staticmethod
    def parse_request_ws_id(request):
        # 获取请求参数
        try:
            body = None
            body_unicode = request.body.decode('utf-8')
            try:
                if body_unicode:
                    body = json.loads(body_unicode)
            except Exception as e:
                logger.warning(str(e))
                body = request.POST
            if isinstance(body, dict) and body:
                ws_id = body.get('ws_id', '') or str(body.get('id', '') if len(str(body.get('id', ''))) == 8 else '') or \
                        str(body.get('workspace', '') if len(str(body.get('workspace', ''))) == 8 else '')
            else:
                ws_id = request.GET.get('ws_id', '')
            return ws_id
        except Exception as e:
            logger.error(f'parse_request_ws_id error!path:{request.path_info}, error:{e}')

    def process_request(self, request):
        """权限校验中间件"""
        current_path = request.path_info  # 当前访问路径
        # 检查是否属于白名单
        if self.check_white_list(current_path):
            return None
        ws_id = self.parse_request_ws_id(request)

        # from tone.services.auth.auth_services import OpenCoralUCenter
        # ucenter_service = OpenCoralUCenter()
        # success, user_info = ucenter_service.get_authorized_user(request.COOKIES.get('_oc_ut'))
        # current_user = ucenter_service.get_user_obj   _by_user_info(success, user_info, request)

        response_401 = JsonResponse(status=401, data={'code': 401, 'msg': '没有权限，请联系统管理员'})
        current_method = request.method
        if request.user is None or request.user.id is None:
            # 游客
            if request.method == 'DELETE':
                return response_401
            if ws_id:
                request_ws = Workspace.objects.filter(id=ws_id).first()
                if request_ws is None:
                    return response_401
                if not request_ws.is_public:
                    return response_401
                # 游客公开权限校验
                if not self.check_ws_permission(current_path, None, None, ws_id, current_method):
                    return response_401
            else:
                sys_result = self.check_sys_permission(current_path, current_method, 'user', None)
                if sys_result == 'fail':
                    return response_401
        else:
            role_member = RoleMember.objects.filter(user_id=request.user.id).first()
            current_role_name = 'user'
            if role_member is not None:
                current_role = Role.objects.filter(id=role_member.role_id).first()
                current_role_name = 'user' if current_role is None else current_role.title
            if current_role_name == 'sys_admin':
                return None
            if ws_id:
                # 成员ws权限校验
                if not self.check_ws_permission(
                        current_path, current_role_name, request.user.id, ws_id, current_method):
                    return response_401
            else:
                # 成员系统权限校验
                if current_role_name != 'sys_admin':
                    sys_result = self.check_sys_permission(current_path, current_method, current_role_name, None)
                    if sys_result == 'fail':
                        return response_401
        return None
