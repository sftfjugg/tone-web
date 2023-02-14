import uuid

from django.conf import settings
from django.contrib.auth.backends import RemoteUserBackend
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.contrib.auth import get_user_model, logout as auth_logout, authenticate, login
from urllib.parse import urlparse, parse_qs, urlencode

from rest_framework.response import Response
from rest_framework.views import APIView

from tone.core.common.views import CommonAPIView
from tone.models import User, Role, WorkspaceMember, Workspace, RoleMember, WorkspaceAccessHistory
from tone.schemas.auth.auth_schemas import UserSchema
from tone.serializers.auth.auth_serializers import UserSerializer, RoleSerializer, UserDetailSerializer, \
    PersonalUserSerializer, UserWorkspaceSerializer, UserApproveSerializer, WsAdminSerializer, TaskMsgSerializer, \
    ApplyMsgSerializer, LoginUserInfoSerializer
from tone.services.auth.auth_services import UserService, RoleService, UserInfoService, UserTokenService, \
    PersonalHomeService, ReApplyService, FilterWsAdminService, MsgNotifyService, AuthService
from tone.settings import LOGIN_URL


class LoginView(CommonAPIView):
    service_class = AuthService

    def post(self, request):
        success, result = self.service.user_login(request)
        code = 200 if success else 401
        return JsonResponse({'code': code, 'data': result})


class RegisterView(CommonAPIView):
    service_class = AuthService

    def post(self, request):
        success, result = self.service.user_register(request)
        code = 200 if success else 401
        return JsonResponse({'code': code, 'data': result})


class ResetPasswordView(CommonAPIView):
    service_class = AuthService

    def post(self, request):
        new_password = self.service.reset_password(request.data.get('user_id'))
        return JsonResponse({'code': 200, 'data': new_password})


class ChangePasswordView(CommonAPIView):
    service_class = AuthService

    def post(self, request):
        success, result = self.service.change_password(request)
        code = 200 if success else 401
        return JsonResponse({'code': code, 'data': result})


class PersonalCenterView(CommonAPIView):
    service_class = AuthService

    def get(self, request):
        user_info = self.service.get_login_user_info(request)
        return JsonResponse({'code': 200, 'data': user_info})


class UserView(CommonAPIView):
    serializer_class = UserSerializer
    queryset = User.objects.all().exclude(username='system', is_superuser=True)
    service_class = UserService
    schema_class = UserSchema
    filter_fields = ['is_superuser']
    search_fields = ['first_name', 'last_name']

    def get(self, request):
        queryset = self.service.filter(self.get_queryset(), request.GET, request.user.id)
        source_data = self.get_response_data(queryset)
        response_data = self.service.query_user_from_db(source_data, request.GET, request.user)
        return Response(response_data)

    def post(self, request):
        """
        给用户设置角色
        """
        success, instance = self.service.set_role(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_code(code=200, msg=instance)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class UserDetailView(CommonAPIView):
    serializer_class = UserDetailSerializer
    queryset = User.objects.all().exclude(username='system', is_superuser=True)
    service_class = UserService

    def get(self, request):
        user_id = request.data.get('user_id') or 2
        instance = self.queryset.filter(id=user_id).first()
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)


class RoleView(CommonAPIView):
    serializer_class = RoleSerializer
    queryset = Role.objects.all()
    service_class = RoleService

    def get(self, request):
        """获取角色信息列表"""
        data = self.service.filter(self.get_queryset(), request.GET, operator=request.user.id)
        response_data = self.get_response_data(data)
        response_data['data'] = {
            'list': response_data['data'],
            'num': User.objects.exclude(username='system').count()
        }
        return Response(response_data)


class PersonalHomeView(CommonAPIView):
    """废弃"""
    service_class = PersonalHomeService
    serializer_class = PersonalUserSerializer

    def get(self, request):
        """获取个人中心基本信息，系统角色信息，ws角色信息"""
        instance = self.service.get_personal_info(request.GET, operator=request.user)
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)


class HomeUserView(CommonAPIView):
    service_class = UserInfoService
    serializer_class = PersonalUserSerializer

    def get(self, request):
        """获取个人中心基本信息，系统角色信息，ws角色信息"""
        response_data = self.get_response_data(request.user, many=False)
        user_info = self.service.get_user_info(request.GET, operator=request.user.id)
        response_data['data'].update(user_info)
        if request.GET.get('ws_id'):
            response_data['data'].update(
                {
                    'first_entry': not WorkspaceAccessHistory.objects.filter(
                        ws_id=request.GET.get('ws_id')).exists()
                }
            )
        return Response(response_data)


class LogoutView(View):
    """
    用户登出
    """
    @staticmethod
    def get(request):
        auth_logout(request)
        request.session.flush()
        response = redirect(request.GET.get('callback', '/'))
        return response


class ReLoginView(View):
    @staticmethod
    def get(request):
        back_url = request.GET.get('back_url', '')
        base_login_url = LOGIN_URL.split('?')[0]
        params = urlparse(LOGIN_URL).query
        params_dic = dict([(k, v[0]) for k, v in parse_qs(params).items()])
        params_dic['BACK_URL'] = params_dic['BACK_URL'] + back_url
        params = urlencode(params_dic)
        url = '%s?%s' % (base_login_url, params)
        return HttpResponseRedirect(url)


class PersonalWorkspaceView(CommonAPIView):
    service_class = PersonalHomeService
    serializer_class = UserWorkspaceSerializer

    def get(self, request):
        """获取个人WS信息"""
        instance = self.service.workspace_info(operator=request.user)
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)


class PersonalApproveView(CommonAPIView):
    service_class = PersonalHomeService
    serializer_class = UserApproveSerializer
    order_by = ['-gmt_created']

    def get(self, request):
        """获取个人申请信息"""
        instance = self.service.approve_info(operator=request.user)
        response_data = self.get_response_data(instance, many=True)
        return Response(response_data)


class PersonalTokenView(CommonAPIView):
    service_class = UserTokenService

    def get(self, request):
        """获取用户token信息"""
        data = self.service.get_user_token(operator=request.user)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)

    def put(self, request):
        """更新用户token信息"""
        data = self.service.update_user_token(operator=request.user)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class ReApplyView(CommonAPIView):
    """再次申请"""
    service_class = ReApplyService

    def post(self, request):
        self.service.re_apply(request.data)
        response_data = self.get_response_code()
        return Response(response_data)


class FilterWsAdminView(CommonAPIView):
    """查询404页面，ws信息"""
    service_class = FilterWsAdminService
    queryset = WorkspaceMember.objects.all()
    serializer_class = WsAdminSerializer

    def get(self, request):
        queryset, ws_info = self.service.get_ws_admin(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=False)
        response_data['ws_info'] = ws_info
        return Response(response_data)


class MsgStateView(CommonAPIView):
    service_class = MsgNotifyService
    """查询消息通知状态：任务通知 + 审批通知"""
    def get(self, request):
        data = self.service.get_msg_state(operator=request.user.id)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class TaskMsgView(CommonAPIView):
    """任务通知"""
    service_class = MsgNotifyService
    serializer_class = TaskMsgSerializer

    def get(self, request):
        data = self.service.get_task_msg(request.GET, operator=request.user.id)
        response_data = self.get_response_data(data)
        return Response(response_data)

    def post(self, request):
        """全部已读"""
        data = self.service.update_all_task_msg(operator=request.user.id)
        response_data = self.get_response_data(data)
        return Response(response_data)

    def put(self, request):
        """修改已读状态"""
        data = self.service.update_task_msg(request.data)
        response_data = self.get_response_data(data)
        return Response(response_data)


class ApplyMsgView(CommonAPIView):
    """审批通知"""
    service_class = MsgNotifyService
    serializer_class = ApplyMsgSerializer

    def get(self, request):
        data = self.service.get_apply_msg(request.GET, operator=request.user.id)
        response_data = self.get_response_data(data)
        return Response(response_data)

    def post(self, request):
        """全部已读"""
        data = self.service.update_all_apply_msg(operator=request.user.id)
        response_data = self.get_response_data(data)
        return Response(response_data)

    def put(self, request):
        """修改单条已读状态"""
        data = self.service.update_apply_msg(request.data, operator=request.user.id)
        response_data = self.get_response_data(data)
        return Response(response_data)
