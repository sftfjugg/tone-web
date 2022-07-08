from datetime import datetime

from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models import Workspace, WorkspaceMember, ApproveInfo, User, Role, RoleMember
from tone.serializers.auth.auth_serializers import UserBriefSerializer, get_user_avatar
from tone.services.sys.workspace_services import WorkspaceService


def _get_users_cache_from_request(request):
    return request.users_cache if hasattr(request, 'users_cache') else None


class WorkspaceIndexListSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'logo', 'show_name', 'owner_name', 'is_public', 'is_member',
                  'theme_color', 'creator', 'is_common', 'description', 'is_show']

    def get_owner_name(self, obj):
        user_list = self.context['request'].user_list
        for user in user_list:
            if user.id == obj.owner:
                return '{}({})'.format(user.last_name, user.first_name) if user.first_name else user.last_name

    def get_is_member(self, obj):
        cur_user_id = self.context['request'].user.id
        member_list = self.context['request'].member_list
        for member in member_list:
            if member.ws_id == obj.id and member.user_id == cur_user_id:
                return True
        return False

    @staticmethod
    def get_logo(obj):
        return WorkspaceService.get_ws_logo(obj.logo)


class WorkspaceSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    owner_avatar = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'logo', 'show_name', 'owner_name', 'owner_avatar', 'description', 'is_public', 'member_count',
                  'theme_color', 'creator', 'is_common', 'is_show']

    def get_owner_name(self, obj):
        user_list = self.context['request'].user_list
        for user in user_list:
            if user.id == obj.owner:
                return '{}({})'.format(user.last_name, user.first_name) if user.first_name else user.last_name

    def get_owner_avatar(self, obj):
        return get_user_avatar(obj.owner)

    def get_member_count(self, obj):
        member_list = self.context['request'].member_list
        member_count = 0
        for member in member_list:
            if member.ws_id == obj.id:
                member_count += 1
        return member_count

    @staticmethod
    def get_logo(obj):
        return WorkspaceService.get_ws_logo(obj.logo)


class WorkspaceSelectSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    owner_avatar = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'logo', 'show_name', 'owner_name', 'owner_avatar', 'description', 'is_public', 'member_count',
                  'theme_color', 'creator', 'is_common', 'is_show']

    def get_owner_name(self, obj):
        user_list = self.context['request'].user_list
        for user in user_list:
            if user.id == obj.owner:
                return '{}({})'.format(user.last_name, user.first_name) if user.first_name else user.last_name

    def get_owner_avatar(self, obj):
        return get_user_avatar(obj.owner)

    def get_member_count(self, obj):
        member_list = self.context['request'].member_list
        member_count = 0
        for member in member_list:
            if member.ws_id == obj.id:
                member_count += 1
        return member_count

    @staticmethod
    def get_logo(obj):
        return WorkspaceService.get_ws_logo(obj.logo)


class WorkspaceDetailSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    creator_avatar = serializers.SerializerMethodField()
    proposer_name = serializers.SerializerMethodField()
    proposer_dep = serializers.SerializerMethodField()
    proposer_date = serializers.SerializerMethodField()
    apply_reason = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    owner_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        exclude = ['is_deleted']

    def get_owner_name(self, obj):
        user_list = self.context['request'].user_list
        for user in user_list:
            if user.id == obj.owner:
                return '{}({})'.format(user.last_name, user.first_name) if user.first_name else user.last_name

    def get_creator_name(self, obj):
        user_list = self.context['request'].user_list
        for user in user_list:
            if user.id == obj.creator:
                return '{}({})'.format(user.last_name, user.first_name) if user.first_name else user.last_name

    def get_creator_avatar(self, obj):
        return get_user_avatar(obj.creator)

    def get_member_count(self, obj):
        member_list = self.context['request'].member_list
        member_count = 0
        for member in member_list:
            if member.ws_id == obj.id:
                member_count += 1
        return member_count

    @staticmethod
    def get_apply_reason(obj):
        approve_obj = ApproveInfo.objects.filter(object_type='workspace', object_id=obj.id).first()
        if not approve_obj:
            return
        return approve_obj.reason

    def get_proposer_name(self, obj):
        approve_obj = ApproveInfo.objects.filter(object_type='workspace', object_id=obj.id).first()
        if not approve_obj:
            return
        proposer = User.objects.filter(id=approve_obj.proposer).first()
        if not proposer:
            return
        return '{}({})'.format(proposer.last_name, proposer.first_name) if proposer.first_name else proposer.last_name

    @staticmethod
    def get_proposer_dep(obj):
        approve_obj = ApproveInfo.objects.filter(object_type='workspace', object_id=obj.id).first()
        if not approve_obj:
            return
        proposer = User.objects.filter(id=approve_obj.proposer).first()
        if not proposer:
            return
        return proposer.dep_desc

    @staticmethod
    def get_proposer_date(obj):
        approve_obj = ApproveInfo.objects.filter(object_type='workspace', object_id=obj.id).first()
        if not approve_obj:
            return datetime.strftime(obj.gmt_created, '%Y-%m-%d')
        return datetime.strftime(approve_obj.gmt_created, '%Y-%m-%d')

    def get_is_member(self, obj):
        cur_user_id = self.context['request'].user.id
        member_list = self.context['request'].member_list
        for member in member_list:
            if member.ws_id == obj.id and member.user_id == cur_user_id:
                return True
        return False

    @staticmethod
    def get_logo(obj):
        return WorkspaceService.get_ws_logo(obj.logo)

    def get_owner_avatar(self, obj):
        user_list = self.context['request'].user_list
        for user in user_list:
            if user.id == obj.owner:
                return user.avatar


class WorkspaceMenuHistorySerializer(CommonSerializer):
    logo = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'show_name', 'logo', 'theme_color', 'is_common']

    @staticmethod
    def get_logo(obj):
        return WorkspaceService.get_ws_logo(obj.logo)


class WorkspaceBriefSerializer(CommonSerializer):
    logo = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'show_name', 'description', 'logo', 'owner_name',
                  'theme_color', 'is_public', 'creator', 'is_common']

    @staticmethod
    def get_logo(obj):
        return WorkspaceService.get_ws_logo(obj.logo)

    def get_owner_name(self, obj):
        user_list = self.context['request'].user_list
        for user in user_list:
            if user.id == obj.owner:
                return '{}({})'.format(user.last_name, user.first_name) if user.first_name else user.last_name


class WorkspaceMemberSerializer(CommonSerializer):
    user_info = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    join_date = serializers.SerializerMethodField()

    class Meta:
        model = WorkspaceMember
        fields = ['user_info', 'is_owner', 'join_date']

    def get_user_info(self, obj):
        is_self = False   # 是否本人
        is_admin = False    # 是否系统级管理员
        can_update = False    # 是否可修改角色
        user_obj = User.objects.filter(id=obj.user_id).first()
        user_info = UserBriefSerializer(user_obj, many=False).data
        view_request = self.context.get('request', '')
        if view_request and view_request.user is not None and obj.user_id == view_request.user.id:
            is_self = True
        sys_role_id = RoleMember.objects.get(user_id=obj.user_id).role_id
        sys_role = Role.objects.get(id=sys_role_id).title
        if sys_role in ['super_admin', 'sys_admin']:
            is_admin = True
        workspace_member = WorkspaceMember.objects.filter(ws_id=obj.ws_id, user_id=obj.user_id).first()
        # 兼容role_id不存在
        if not workspace_member.role_id:
            workspace_member.role_id = Role.objects.get(title='ws_member').id
            workspace_member.save()
        if workspace_member is None:
            workspace_member = WorkspaceMember.objects.get_or_create(ws_id=obj.ws_id, user_id=obj.user_id,
                                                                     role_id=Role.objects.get(title='ws_member').id)
        user_role = Role.objects.filter(id=workspace_member.role_id).first()
        if view_request and view_request.user is not None:
            operate_user = view_request.user.id
            operate_sys_role_id = RoleMember.objects.get(user_id=operate_user).role_id
            operate_sys_role = Role.objects.get(id=operate_sys_role_id).title
            operate_member = WorkspaceMember.objects.filter(ws_id=obj.ws_id, user_id=operate_user).first()
            if operate_member is not None:
                operate_role = Role.objects.filter(id=operate_member.role_id).first()
                if (operate_sys_role in {'super_admin', 'sys_admin'} or operate_role.id < user_role.id) and \
                        user_role.title != 'ws_owner':
                    can_update = True
        user_info['role_list'] = [{'id': user_role.id, 'name': user_role.title}]
        user_info['is_self'] = is_self
        user_info['is_admin'] = is_admin
        user_info['can_update'] = can_update
        return user_info

    @staticmethod
    def get_is_owner(obj):
        workspace = Workspace.objects.filter(id=obj.ws_id).first()
        return obj.user_id == workspace.owner

    @staticmethod
    def get_join_date(obj):
        return datetime.strftime(obj.gmt_created, '%Y-%m-%d')


class WorkspaceMemberApproveInfoSerializer(CommonSerializer):
    proposer_name = serializers.SerializerMethodField()
    proposer_avatar = serializers.SerializerMethodField()
    proposer_email = serializers.SerializerMethodField()

    class Meta:
        model = ApproveInfo
        fields = ['id', 'gmt_created', 'proposer_name', 'proposer_avatar', 'proposer_email', 'reason']

    @staticmethod
    def get_proposer_name(obj):
        user_obj = User.objects.filter(id=obj.proposer).first()
        if not user_obj:
            return
        return user_obj.last_name or user_obj.first_name

    @staticmethod
    def get_proposer_avatar(obj):
        return get_user_avatar(obj.proposer)

    @staticmethod
    def get_proposer_email(obj):
        user_obj = User.objects.filter(id=obj.proposer).first()
        if not user_obj:
            return
        return user_obj.email


class WorkspaceApproveDetailSerializer(CommonSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    proposer_name = serializers.SerializerMethodField()
    proposer_avatar = serializers.SerializerMethodField()
    proposer_dep = serializers.SerializerMethodField()
    approver_name = serializers.SerializerMethodField()
    ws_logo = serializers.SerializerMethodField()
    theme_color = serializers.SerializerMethodField()
    is_public = serializers.SerializerMethodField()

    class Meta:
        model = ApproveInfo
        exclude = ['is_deleted', 'relation_data']

    @staticmethod
    def get_title(obj):
        if obj.object_type == 'workspace':
            ws = Workspace.objects.filter(id=obj.object_id, query_scope='all').first()
            return ws.show_name

    @staticmethod
    def get_description(obj):
        if obj.object_type == 'workspace':
            obj = Workspace.objects.filter(id=obj.object_id, query_scope='all').first()
            return obj.description

    @staticmethod
    def get_proposer_name(obj):
        user_obj = User.objects.filter(id=obj.proposer).first()
        if not user_obj:
            return
        return user_obj.last_name or user_obj.first_name

    @staticmethod
    def get_proposer_avatar(obj):
        return get_user_avatar(obj.proposer)

    @staticmethod
    def get_proposer_dep(obj):
        user_obj = User.objects.filter(id=obj.proposer).first()
        if not user_obj:
            return
        return user_obj.dep_desc

    @staticmethod
    def get_approver_name(obj):
        user_obj = User.objects.filter(id=obj.approver).first()
        if not user_obj:
            return
        return user_obj.last_name or user_obj.first_name

    @staticmethod
    def get_is_public(obj):
        if obj.object_type == 'workspace':
            obj = Workspace.objects.filter(id=obj.object_id, query_scope='all').first()
            return obj.is_public

    @staticmethod
    def get_ws_logo(obj):
        if obj.object_type == 'workspace':
            obj = Workspace.objects.filter(id=obj.object_id, query_scope='all').first()
            return WorkspaceService.get_ws_logo(obj.logo)

    @staticmethod
    def get_theme_color(obj):
        if obj.object_type == 'workspace':
            obj = Workspace.objects.filter(id=obj.object_id, query_scope='all').first()
            return obj.theme_color


class WorkspaceApproveInfoSerializer(CommonSerializer):
    title = serializers.SerializerMethodField()
    proposer_name = serializers.SerializerMethodField()
    proposer_avatar = serializers.SerializerMethodField()

    class Meta:
        model = ApproveInfo
        exclude = ['is_deleted', 'relation_data']

    @staticmethod
    def get_title(obj):
        if obj.object_type == 'workspace':
            ws = Workspace.objects.filter(id=obj.object_id, query_scope='all').first()
            ws_show_name = ws.show_name.split('[')[0]
            return ws_show_name

    @staticmethod
    def get_proposer_name(obj):
        user_obj = User.objects.filter(id=obj.proposer).first()
        if not user_obj:
            return
        return user_obj.last_name or user_obj.first_name

    @staticmethod
    def get_proposer_avatar(obj):
        return get_user_avatar(obj.proposer)
