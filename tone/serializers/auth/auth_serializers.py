from datetime import datetime

from rest_framework import serializers

from tone import settings
from tone.core.common.msg_notice import get_admin_user, get_user_info
from tone.core.common.serializers import CommonSerializer
from tone.models import User, WorkspaceMember, Workspace, RoleMember, Role, ApproveInfo, InSiteSimpleMsg, \
    InSiteWorkProcessMsg, InSiteWorkProcessUserMsg
from tone.services.sys.workspace_services import WorkspaceService


def get_user_avatar(user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return
    return f'{settings.APP_DOMAIN}/static/img/{user.avatar}'


class UserBriefSerializer(CommonSerializer):
    gmt_created = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    avatar_color = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'avatar', 'avatar_color', 'gmt_created']

    @staticmethod
    def get_gmt_created(obj):
        return datetime.strftime(obj.date_joined, '%Y-%m-%d') if obj.date_joined else None

    @staticmethod
    def get_avatar(obj):
        return get_user_avatar(obj.id)

    @staticmethod
    def get_avatar_color(obj):
        return '#5B8FF9'


class UserSerializer(CommonSerializer):
    role_list = serializers.SerializerMethodField()
    ws_list = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    avatar_color = serializers.SerializerMethodField()
    gmt_created = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email',
                  'role_list', 'ws_list', 'avatar', 'avatar_color', 'gmt_created', 'emp_id']

    @staticmethod
    def get_role_list(obj):
        role = None
        role_member = RoleMember.objects.filter(user_id=obj.id).first()
        if role_member is not None:
            role = Role.objects.filter(id=role_member.role_id).first()
        if role is None:
            role = Role.objects.filter(title='user').first()
        return [{'id': role.id, 'name': role.title}]

    @staticmethod
    def get_ws_list(obj):
        ws_list = WorkspaceMember.objects.filter(user_id=obj.id).values_list('ws_id', flat=True)
        return list(Workspace.objects.filter(id__in=ws_list).values_list('show_name', flat=True))

    @staticmethod
    def get_avatar(obj):
        return get_user_avatar(obj.id)

    @staticmethod
    def get_avatar_color(obj):
        return '#5B8FF9'

    @staticmethod
    def get_gmt_created(obj):
        return datetime.strftime(obj.date_joined, '%Y-%m-%d')


class LoginUserInfoSerializer(CommonSerializer):
    ws_list = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    avatar_color = serializers.SerializerMethodField()
    date_joined = serializers.DateTimeField(format='%Y-%m-%d %X')

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email',
                  'ws_list', 'date_joined', 'emp_id', 'token', 'avatar', 'avatar_color']

    @staticmethod
    def get_ws_list(obj):
        ws_list = WorkspaceMember.objects.filter(user_id=obj.id).values_list('ws_id', flat=True)
        return list(Workspace.objects.filter(id__in=ws_list).values_list('show_name', flat=True))

    @staticmethod
    def get_avatar(obj):
        return get_user_avatar(obj.id)

    @staticmethod
    def get_avatar_color(obj):
        return '#5B8FF9'


class UserDetailSerializer(CommonSerializer):
    roles = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    avatar_color = serializers.SerializerMethodField()

    class Meta:
        model = User
        exclude = ['password']

    @staticmethod
    def get_roles(obj):
        return RoleSerializer(obj.groups.all(), many=True).data

    @staticmethod
    def get_avatar(obj):
        return get_user_avatar(obj.id)

    @staticmethod
    def get_avatar_color(obj):
        return '#5B8FF9'


class RoleSerializer(CommonSerializer):
    name = serializers.SerializerMethodField()
    count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = ['id', 'name', 'count', 'description', 'title']

    @staticmethod
    def get_name(obj):
        return obj.title

    @staticmethod
    def get_count(obj):
        return RoleMember.objects.filter(role_id=obj.id).count()


class PersonalWorkspaceSerializer(CommonSerializer):
    member_count = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'logo', 'show_name', 'name', 'description', 'member_count', 'theme_color',
                  'is_public', 'creator']

    @staticmethod
    def get_member_count(obj):
        return WorkspaceMember.objects.filter(ws_id=obj.id).count()

    @staticmethod
    def get_logo(obj):
        return WorkspaceService.get_ws_logo(obj.logo)


class UserWorkspaceSerializer(CommonSerializer):
    workspace_list = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['workspace_list']

    @staticmethod
    def get_workspace_list(obj):
        ws_list = WorkspaceMember.objects.filter(user_id=obj.id).values_list('ws_id', flat=True)
        ws_data_list = PersonalWorkspaceSerializer(Workspace.objects.filter(id__in=ws_list), many=True).data
        ws_role_map = {
            Role.objects.get(title='ws_tester_admin').id: 'ws_tester_admin',
            Role.objects.get(title='ws_tester').id: 'ws_tester',
            Role.objects.get(title='ws_member').id: 'ws_member',
        }
        [ws_data.update({'ws_role': ws_role_map.get(WorkspaceMember.objects.get(user_id=obj.id,
                                                                                ws_id=ws_data.get('id')).role_id)})
         for ws_data in ws_data_list]
        return ws_data_list


class UserApproveSerializer(CommonSerializer):
    ws_info = serializers.SerializerMethodField()
    is_disabled = serializers.SerializerMethodField()
    approve_users = serializers.SerializerMethodField()

    class Meta:
        model = ApproveInfo
        fields = ['id', 'action', 'gmt_created', 'ws_info', 'status', 'reason', 'refuse_reason', 'gmt_modified',
                  'is_disabled', 'approve_users', 'proposer', 'approver']

    @staticmethod
    def get_ws_info(obj):
        ws_obj = Workspace.objects.filter(id=obj.object_id, query_scope='all').first()
        if ws_obj is not None:
            return PersonalWorkspaceSerializer(ws_obj, many=False).data

    def get_is_disabled(self, obj):
        is_disabled = False
        if obj.object_type == 'workspace' and obj.status == 'refused':
            ws_id = obj.object_id
            cur_user_id = self.context['request'].user.id
            if obj.action == 'join':
                # 加入申请, 已经成为ws成员, 申请失效
                if WorkspaceMember.objects.filter(ws_id=ws_id, user_id=cur_user_id).exists():
                    is_disabled = True
            elif obj.action == 'delete':
                # WS已经注销
                if not Workspace.objects.filter(id=ws_id).exists():
                    is_disabled = True
        return is_disabled

    @staticmethod
    def get_approve_users(obj):
        if obj.status == 'waiting':
            admin_user_list = list()
            if obj.action in ['create', 'delete']:
                admin_user_list = get_admin_user(ws_id='', test_admin=False)
            elif obj.action == 'join':
                admin_user_list = get_admin_user(ws_id=obj.object_id, test_admin=False)
            admin_user_list = User.objects.filter(id__in=admin_user_list).values_list('id', flat=True)
            return [get_user_info(user_id) for user_id in admin_user_list]


class PersonalUserSerializer(CommonSerializer):
    sys_role = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'sys_role', 'avatar', 'email']

    @staticmethod
    def get_avatar(obj):
        return get_user_avatar(obj.id)

    @staticmethod
    def get_sys_role(obj):
        role_title = 'user'
        role_member = RoleMember.objects.filter(user_id=obj.id).first()
        if role_member is not None:
            role = Role.objects.filter(id=role_member.role_id).first()
            role_title = role.title
        return role_title

    @staticmethod
    def get_ws_role_list(obj):
        ws_list = WorkspaceMember.objects.filter(user_id=obj.id).values('ws_id', 'role_id')
        # 查询各个ws角色
        ws_role_map = {
            Role.objects.get(title='ws_owner').id: 'ws_owner',
            Role.objects.get(title='ws_tester_admin').id: 'ws_tester_admin',
            Role.objects.get(title='ws_tester').id: 'ws_tester',
            Role.objects.get(title='ws_member').id: 'ws_member',
        }
        [ws.update({'title': ws_role_map.get(ws['role_id'])}) for ws in ws_list]
        return ws_list


class WsAdminSerializer(CommonSerializer):
    avatar = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['name', 'avatar', 'email']

    @staticmethod
    def get_email(obj):
        owner = User.objects.get(id=obj.user_id)
        return owner.email

    @staticmethod
    def get_name(obj):
        owner = User.objects.get(id=obj.user_id)
        return '{}({})'.format(owner.last_name, owner.first_name) if owner.first_name else owner.last_name

    @staticmethod
    def get_avatar(obj):
        return get_user_avatar(obj.user_id)


class TaskMsgSerializer(CommonSerializer):

    class Meta:
        model = InSiteSimpleMsg
        fields = ['id', 'subject', 'content', 'msg_type', 'msg_object_id', 'is_read', 'gmt_created']


class ApplyMsgSerializer(CommonSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = InSiteWorkProcessMsg
        fields = ['id', 'subject', 'content', 'process_id', 'is_handle', 'is_read', 'gmt_created']

    def get_is_read(self, obj):
        cur_user_id = self.context['request'].user.id
        user_msg_obj = InSiteWorkProcessUserMsg.objects.filter(user_id=cur_user_id, msg_id=obj.id).first()
        return False if user_msg_obj is None else user_msg_obj.i_am_handle
