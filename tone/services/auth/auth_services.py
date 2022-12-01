import uuid


from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q

from initial.workspace.initialize import WorkspaceDataInitialize
from tone.core.common.msg_notice import InSiteMsgHandle
from tone.core.common.permission_config_info import SYS_ROLE_MAP
from tone.core.common.redis_cache import redis_cache
from tone.core.common.services import CommonService
from tone.core.utils.short_uuid import short_uuid
from tone.models import WorkspaceMember, User, RoleMember, Role, ApproveInfo, Workspace, \
    InSiteWorkProcessUserMsg, InSiteWorkProcessMsg, InSiteSimpleMsg, WorkspaceAccessHistory
from tone.serializers.auth.auth_serializers import UserSerializer, LoginUserInfoSerializer
from tone.services.sys.interface_token_services import InterfaceTokenService


class ProfileSchema(object):
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.username = kwargs.get('username')
        self.first_name = kwargs.get('first_name')
        self.last_name = kwargs.get('last_name')
        self.email = kwargs.get('email')
        self.role_list = kwargs.get('role_list')
        self.ws_list = kwargs.get('ws_list')
        self.avatar = kwargs.get('avatar')
        self.gmt_created = kwargs.get('gmt_created')
        self.emp_id = kwargs.get('emp_id')


class AuthService(CommonService):

    def user_login(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login(request, user)
            user_info = self.get_login_user_info(request)
            return True, user_info
        return False, '用户名或密码错误'

    def user_register(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        password_repeat = request.data.get('password_repeat')
        if User.objects.filter(username=username).exists():
            return False, '用户名已存在'
        if password != password_repeat:
            return False, '两次输入的密码不一致'

        user = User.objects.create_user(
            username=username,
            password=password,
            last_name=username,
            emp_id=short_uuid(),
            token=str(uuid.uuid4()).replace('-', '')
        )

        RoleMember.objects.create(user_id=user.id, role_id=Role.objects.get(title='user').id)
        login(request, user)
        user_info = self.get_login_user_info(request)
        return True, user_info

    def reset_password(self, user_id):
        new_random_password = User.objects.make_random_password()
        sign_password = make_password(new_random_password)
        User.objects.filter(id=user_id).update(password=sign_password)
        return new_random_password

    def change_password(self, request):
        user_id = request.data.get('user_id', request.user.id)
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        new_password_repeat = request.data.get('new_password_repeat')

        user = authenticate(
            username=User.objects.get(id=user_id).username,
            password=old_password
        )
        if not user:
            return False, '旧密码输入错误'

        if new_password != new_password_repeat:
            return False, '两次输入的新密码不一致'

        if authenticate(
            username=User.objects.get(id=user_id).username,
            password=new_password
        ):
            return False, '新密码不能与旧密码一致'

        sign_password = make_password(new_password)
        User.objects.filter(id=user_id).update(password=sign_password)
        login(request, User.objects.filter(id=user_id).first())

        user_info = self.get_login_user_info(request)
        return True, user_info

    def get_login_user_info(self, request):
        if request.user.is_authenticated:
            user_info = LoginUserInfoSerializer(request.user, many=False).data
        else:
            user_info = LoginUserInfoSerializer(None, many=False).data
        # 返回用户角色相关信息
        user_info.update(UserInfoService().get_user_info(
            request.GET,
            operator=request.user.id if request.user else None
        ))
        # 返回公共ws信息，方便前端跳转
        common_ws = Workspace.objects.filter(is_common=True).first()
        if not common_ws:
            WorkspaceDataInitialize().initialize_common_ws()
        return {
            'user_info': user_info,
            'redirect_info': {
                'common_ws_id': common_ws.id
            },
        }


class UserService(CommonService):
    @staticmethod
    def filter(queryset, data, cur_user_id):
        ws_id = data.get('ws_id')
        role_id = data.get('role_id')
        q = Q()
        if ws_id:
            ws_q = Q(ws_id=ws_id)
            user_id_list = WorkspaceMember.objects.filter(ws_q).values_list('user_id', flat=True)
            q &= Q(id__in=user_id_list)
        if role_id:
            role_member = RoleMember.objects.filter(role_id=role_id)
            user_id_list = role_member.values_list('user_id', flat=True)
            q &= Q(id__in=user_id_list)
        return queryset.filter(q)

    @staticmethod
    def set_role(data, operator):
        user_id = data.get('user_id')
        role_id = data.get('role_id')
        if user_id == operator:
            return False, '不能更改本人的角色'
        # 修改用户角色信息, 权限逐级递减, 低级别不能修改高级别
        user_role_member = RoleMember.objects.filter(user_id=operator).first()
        role = Role.objects.filter(id=user_role_member.role_id).first()
        # 被修改人当前角色
        role_member = RoleMember.objects.filter(user_id=user_id)
        user_role = Role.objects.filter(id=role_member.first().role_id).first()
        if role.id >= user_role.id and role.title != 'sys_admin':
            return False, '当前权限不足'
        if role_id:
            if role_member.first() is None:
                RoleMember.objects.create(user_id=user_id, role_id=role_id)
            else:
                if operator:
                    # 当前角色可以设置的角色
                    if Role.objects.filter(title__in=SYS_ROLE_MAP.get(role.title), id=role_id).exists():
                        role_member.update(role_id=role_id)
                        # 被设置系统角色, 发送消息到被操作人
            user_role = Role.objects.filter(id=role_member.first().role_id).first()
            InSiteMsgHandle().by_update_sys_role(operator, user_id, user_role.title)
        return True, '修改成功'

    @classmethod
    def put_users_to_redis(cls, users=None):
        if not users:
            users = User.objects.all()
        data = {}
        for user in users:
            data[user.id] = UserSerializer(user, many=False).data
        redis_cache.set('USER_DATA', data)

    @classmethod
    def get_users_from_redis(cls):
        return dict()

    @classmethod
    def get_user(cls, user_id, users_cache=None):
        return User.objects.filter(id=user_id).first()

    def query_user_from_db(self, source_data, params, cur_user):
        user_list = []
        flag = False
        for item in source_data['data']:
            if item['id'] == cur_user.id:
                flag = True
                continue
            user_list.append(item)
        source_data['data'] = user_list
        if flag and cur_user.id and params.get('page', '1') == '1':
            user_list.insert(0, UserSerializer(cur_user, many=False).data)
        if params.get('role_id'):
            return source_data
        return source_data


class RoleService(CommonService):
    @staticmethod
    def filter(queryset, data, operator):
        # 根据角色返回可设置的角色列表
        sys_role_map = {
            'super_admin': ['super_admin', 'sys_admin', 'sys_test_admin', 'user'],
            'sys_admin': ['sys_admin', 'sys_test_admin', 'user'],
            'sys_test_admin': ['sys_test_admin'],
            'user': ['user']
        }
        ws_role_map = {
            'ws_owner': ['ws_admin', 'ws_test_admin', 'ws_member'],
            'ws_admin': ['ws_test_admin', 'ws_member'],
            'ws_test_admin': ['ws_test_admin'],
            'ws_member': ['ws_member'],
            # 'ws_tourist': ['ws_tourist'],
        }
        q = Q()
        ws_id = data.get('ws_id', '')
        title = data.get('title', '')
        role_type = data.get('role_type', '')
        is_filter = data.get('is_filter', '1')
        role_member = RoleMember.objects.filter(user_id=operator).first()
        sys_role = Role.objects.filter(id=role_member.role_id).first()
        # 根据用户角色返回不同的角色下拉列表
        if operator and str(is_filter) == '1':
            if role_type == 'system':
                q &= Q(title__in=sys_role_map.get(sys_role.title))
            elif ws_id:
                workspace_member = WorkspaceMember.objects.filter(user_id=operator, ws_id=ws_id).first()
                if sys_role.title not in ['super_admin', 'sys_admin']:
                    role = Role.objects.filter(id=workspace_member.role_id).first()
                    q &= Q(title__in=ws_role_map.get(role.title))
                else:
                    q &= Q(title__in=['ws_admin', 'ws_test_admin', 'ws_member'])
        if ws_id:
            role_type = 'workspace'
        if title:
            q &= Q(title=title)
        if role_type:
            q &= Q(role_type=role_type)
        return queryset.filter(q)


class UserInfoService(CommonService):
    @staticmethod
    def get_user_info(data, operator):
        ws_is_exist = None
        ws_is_public = None
        ws_id = data.get('ws_id', '')
        if ws_id:
            # 根据ws_id 查询workspace不存在
            workspace_obj = Workspace.objects.filter(id=ws_id).first()
            if workspace_obj is None:
                ws_is_exist = False
            else:
                ws_is_exist = True
                ws_is_public = workspace_obj.is_public
        default_user_info = {
            'user_id': None,
            'role_title': 'sys_tourist',
            'sys_role_title': 'sys_tourist',
            'sys_role_id': None,
            'emp_id': None,
            'ws_role_title': 'ws_tourist',
            'ws_role_id': None,
            'ws_is_exist': ws_is_exist,
            'ws_is_public': ws_is_public,
        }
        if not operator:
            return default_user_info

        role_member = RoleMember.objects.filter(user_id=operator).first()
        emp_id = User.objects.filter(id=operator).first().emp_id
        if ws_id:
            # 查询ws级角色信息
            ws_role_title = None
            ws_role_id = None
            work_member = WorkspaceMember.objects.filter(ws_id=ws_id, user_id=operator).first()
            sys_role = Role.objects.filter(id=role_member.role_id).first()
            if work_member is not None:
                role = Role.objects.filter(id=work_member.role_id).first()
                if role is not None:
                    ws_role_title = role.title
                    ws_role_id = role.id
            return {
                'user_id': operator,
                'role_title': ws_role_title,
                'ws_role_title': 'ws_tourist' if ws_is_public and not ws_role_title else ws_role_title,
                'ws_role_id': ws_role_id,
                'sys_role_title': sys_role.title,
                'sys_role_id': sys_role.id,
                'ws_is_exist': ws_is_exist,
                'ws_is_public': ws_is_public,
                'emp_id': emp_id,
            }
        else:
            # 系统级角色信息
            if role_member is not None:
                role = Role.objects.filter(id=role_member.role_id).first()
                if role is not None:
                    return {
                        'user_id': operator,
                        'role_title': role.title,
                        'sys_role_title': role.title,
                        'sys_role_id': role.id,
                        'emp_id': emp_id,
                    }
        return default_user_info

    @staticmethod
    def get_first_entry(user_id, ws_id):
        if WorkspaceAccessHistory.objects.filter(user_id=user_id, ws_id=ws_id).exists():
            return True
        return False


class PersonalHomeService(CommonService):
    @staticmethod
    def get_personal_info(data, operator):
        # 获取用户信息
        user = User.objects.filter(id=operator.id).first()
        return user

    @staticmethod
    def workspace_info(operator):
        user = User.objects.filter(id=operator.id).first()
        return user

    @staticmethod
    def approve_info(operator):
        ws_id_list = Workspace.objects.all().values_list('id', flat=True)
        approve_list = ApproveInfo.objects.filter(object_type='workspace',
                                                  object_id__in=ws_id_list,
                                                  proposer=operator.id)
        return approve_list


class UserTokenService(CommonService):
    @staticmethod
    def get_user_token(operator):
        token = User.objects.filter(username=operator.username).first().token
        if token is None:
            InterfaceTokenService().create(operator=operator)
        return User.objects.filter(username=operator.username).first().token

    @staticmethod
    def update_user_token(operator):
        InterfaceTokenService().create(operator=operator)
        return User.objects.filter(username=operator.username).first().token


class ReApplyService(CommonService):
    @staticmethod
    def re_apply(data):
        # 拒绝审批后, 再次申请
        with transaction.atomic():
            # 获取原申请记录
            approve_info = ApproveInfo.objects.filter(id=data.get('id')).first()
            # 区分加入 或者 新建ws ,create复制原来WS
            origin_ws_obj = Workspace.objects.get(id=approve_info.object_id)
            if approve_info.action == 'create':
                origin_ws_obj.id = short_uuid()
                # 修改被拒绝创建的WS名称
                if origin_ws_obj and '[refused at' in origin_ws_obj.show_name:
                    origin_ws_obj.show_name = origin_ws_obj.show_name.split('[refused at')[0]
                    origin_ws_obj.name = origin_ws_obj.name.split('[refused at')[0]
                origin_ws_obj.save()

            # 复制新申请记录
            approve_info.id = None
            approve_info.reason = data.get('reason')
            approve_info.status = 'waiting'
            approve_info.approver = None
            approve_info.refuse_reason = None
            approve_info.object_id = origin_ws_obj.id
            approve_info.save()


class FilterWsAdminService(CommonService):
    @staticmethod
    def get_ws_admin(queryset, data):
        q = Q()
        ws_info = {}
        ws_id = data.get('ws_id', '')
        if ws_id:
            q &= Q(ws_id=ws_id)
            ws_obj = Workspace.objects.get(id=ws_id)
            ws_info = {
                'name': ws_obj.name,
                'show_name': ws_obj.show_name,
            }
        role_id_list = Role.objects.filter(title__in=['ws_owner', 'ws_test_admin']).values_list('id', flat=True)
        q &= Q(role_id__in=role_id_list)
        return queryset.filter(q), ws_info


class MsgNotifyService(CommonService):
    @staticmethod
    def get_msg_state(operator):
        """查询消息通知状态"""
        # 任务通知全部已读 红点提示
        task_msg_state = False
        task_msg_total_num = len(InSiteSimpleMsg.objects.filter(receiver=operator))
        task_msg_unread_num = len(InSiteSimpleMsg.objects.filter(receiver=operator, is_read=False))
        if task_msg_unread_num:
            task_msg_state = True
        # 审批通知未处理数量
        apply_msg_id_list = InSiteWorkProcessUserMsg.objects.filter(user_id=operator, i_am_handle=False
                                                                    ).values_list('msg_id', flat=True)
        apply_msg_num = len(InSiteWorkProcessMsg.objects.filter(id__in=apply_msg_id_list))
        apply_msg_id_list = InSiteWorkProcessUserMsg.objects.filter(user_id=operator).values_list('msg_id', flat=True)
        apply_msg_total_num = len(InSiteWorkProcessMsg.objects.filter(id__in=apply_msg_id_list))
        return {
            'task_msg_state': task_msg_state,
            'apply_msg_unread_num': apply_msg_num,
            'task_msg_total_num': task_msg_total_num,
            'task_msg_unread_num': task_msg_unread_num,
            'apply_msg_total_num': apply_msg_total_num,
        }

    @staticmethod
    def get_task_msg(data, operator):
        """查询任务通知"""
        is_read = data.get('is_read')
        if is_read != '0':
            return InSiteSimpleMsg.objects.filter(receiver=operator)
        else:
            return InSiteSimpleMsg.objects.filter(receiver=operator, is_read=False)

    @staticmethod
    def update_task_msg(data):
        """更新单条任务消息已读"""
        task_msg_id = data.get('msg_id')
        InSiteSimpleMsg.objects.filter(id=task_msg_id).update(is_read=True)

    @staticmethod
    def update_all_task_msg(operator):
        """更新全部任务消息已读"""
        InSiteSimpleMsg.objects.filter(receiver=operator, is_read=False).update(is_read=True)

    @staticmethod
    def get_apply_msg(data, operator):
        """查询审批通知"""
        is_read = data.get('is_read', '')
        if is_read != '0':
            apply_msg_id_list = InSiteWorkProcessUserMsg.objects.filter(user_id=operator).values_list('msg_id',
                                                                                                      flat=True)
        else:
            apply_msg_id_list = InSiteWorkProcessUserMsg.objects.filter(
                user_id=operator, i_am_handle=False).values_list('msg_id', flat=True)
        return InSiteWorkProcessMsg.objects.filter(id__in=apply_msg_id_list)

    @staticmethod
    def update_apply_msg(data, operator):
        """更新单条审批消息已读"""
        apply_msg_id = data.get('msg_id')
        InSiteWorkProcessUserMsg.objects.filter(user_id=operator, msg_id=apply_msg_id).update(i_am_handle=True)

    @staticmethod
    def update_all_apply_msg(operator):
        """更新全部审批消息已读"""
        InSiteWorkProcessUserMsg.objects.filter(user_id=operator, i_am_handle=False).update(i_am_handle=True)
