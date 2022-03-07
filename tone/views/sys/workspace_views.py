import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response

from tone.core.common.views import CommonAPIView, BaseView
from tone.models import Workspace, WorkspaceMember, ApproveInfo, WorkspaceAccessHistory, json, User
from tone.schemas.sys.workspace_schemas import WorkspaceSchema, WorkspaceHistorySchema, WorkspaceMemberSchema, \
    ApproveSchema, WorkspaceApproveSchema, ApproveQuantitySchema, UploadSchema, MemberQuantitySchema
from tone.serializers.sys.workspace_serializers import WorkspaceSerializer, WorkspaceMemberSerializer, \
    WorkspaceApproveInfoSerializer, WorkspaceBriefSerializer, \
    WorkspaceIndexListSerializer, WorkspaceDetailSerializer, WorkspaceApproveDetailSerializer, \
    WorkspaceMenuHistorySerializer
from tone.services.sys.workspace_services import WorkspaceService, WorkspaceMemberService, ApproveService, \
    WorkspaceHistoryService, ApproveQuantityService, UploadService, MemberQuantityService, WorkspaceListService, \
    AllWorkspaceService, WorkspaceSelectService


class WorkspaceView(CommonAPIView):
    serializer_class = WorkspaceSerializer
    queryset = Workspace.objects.filter(is_approved=True)
    service_class = WorkspaceService
    permission_classes = []
    filter_fields = ['is_public', 'is_approved']
    search_fields = ['name', 'show_name']
    schema_class = WorkspaceSchema
    order_by = ['-gmt_created']

    def get(self, request):
        """
        获取workspace列表接口
        可以根据是否公开、我加入的、我创建的等条件进行过滤
        可以根据关键字进行模糊搜索
        """
        request.user_list = list(User.objects.all())
        request.member_list = list(WorkspaceMember.objects.all())
        if request.GET.get('brief'):
            self.serializer_class = WorkspaceBriefSerializer
        if request.GET.get('call_page') == 'index':
            self.serializer_class = WorkspaceIndexListSerializer
        queryset = self.service.filter(self.get_queryset(), request.GET, operator=request.user.id)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        该接口用来创建workspace
        提交表单之后需要管理员进行审批，请务必写清楚申请理由
        """
        request.user_list = list(User.objects.all())
        request.member_list = list(WorkspaceMember.objects.all())
        success, result = self.service.create(request.data, operator=request.user.id)
        if not success:
            return Response(self.get_response_code(code=status.HTTP_208_ALREADY_REPORTED, msg=result))
        response_data = self.get_response_data(result, many=False)
        return Response(response_data)

    def put(self, request):
        """
        该接口用来修改workspace信息
        只要显示名、描述、logo、是否公开可以修改
        当前owner离职或者转岗后可以转交
        """
        request.user_list = list(User.objects.all())
        request.member_list = list(WorkspaceMember.objects.all())
        success, instance = self.service.update(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def delete(self, request):
        """
        删除workspace接口，需要传reason 请谨慎操作
        """
        self.service.delete(request.data, operator=request.user.id)
        response_data = self.get_response_code()
        return Response(response_data)


class WorkspaceDetailView(CommonAPIView):
    serializer_class = WorkspaceDetailSerializer
    queryset = Workspace.objects.all()

    def get(self, request, id):
        """
        单个workspace详情接口
        """
        request.user_list = list(User.objects.all())
        request.member_list = list(WorkspaceMember.objects.all())
        instance = self.queryset.filter(id=id).first()
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)


class WorkspaceHistoryView(CommonAPIView):
    serializer_class = WorkspaceBriefSerializer
    queryset = WorkspaceAccessHistory.objects.all().order_by('-id')
    service_class = WorkspaceHistoryService
    permission_classes = []
    schema_class = WorkspaceHistorySchema
    filter_fields = ['user_id']
    order_by = None

    def get(self, request):
        """
        该接口用来获取当前（或指定）用户最近访问workspace的记录
        """
        if request.GET.get('call_page') == 'menu':
            self.serializer_class = WorkspaceMenuHistorySerializer
        else:
            request.user_list = list(User.objects.all())
        queryset = self.service.get_distinct_queryset(self.queryset, request.user.id, request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        request.user_list = list(User.objects.all())
        first_entry = self.service.add_entry_history(request.data, operator=request.user.id)
        response_code = self.get_response_code()
        response_code['first_entry'] = first_entry
        return Response(response_code)


class WorkspaceMemberView(CommonAPIView):
    serializer_class = WorkspaceMemberSerializer
    queryset = WorkspaceMember.objects.all()
    service_class = WorkspaceMemberService
    schema_class = WorkspaceMemberSchema
    filter_fields = ['ws_id', 'role_id']

    def get(self, request):
        """
        workspace成员管理
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        添加ws成员
        """
        flag, result = self.service.add_member(request.data, operator=request.user.id)
        if not flag:
            response_data = self.get_response_code(code=201, msg=result)
        else:
            response_data = self.get_response_data(result, many=True)
        return Response(response_data)

    def put(self, request):
        """
        修改成员角色、权限
        """
        success, instance = self.service.modify_member_role(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def delete(self, request):
        """
        （批量）删除ws成员
        """
        success, instance = self.service.remove_member(request.data, operator=request.user.id)
        if success:
            return Response(self.get_response_code(code=200, msg=instance))
        else:
            return Response(self.get_response_code(code=201, msg=instance))


class WorkspaceMemberApplyView(CommonAPIView):
    service_class = WorkspaceMemberService
    schema_class = WorkspaceApproveSchema

    def post(self, request):
        """
        申请加入某个workspace
        """
        flag, msg = self.service.apply_for_join(request.data, operator=request.user)
        if flag:
            response_data = self.get_response_code(msg=msg)
        else:
            response_data = self.get_response_code(code=status.HTTP_500_INTERNAL_SERVER_ERROR, msg=msg)
        return Response(response_data)


class ApproveDetailView(CommonAPIView):
    serializer_class = WorkspaceApproveDetailSerializer
    # 过滤全部审批记录
    queryset = ApproveInfo.objects.all(query_scope='all')

    def get(self, request, pk):
        instance = self.queryset.filter(pk=pk).first()
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)


class ApproveView(CommonAPIView):
    serializer_class = WorkspaceApproveInfoSerializer
    # 显示审批历史记录
    queryset = ApproveInfo.objects.all()
    service_class = ApproveService
    schema_class = ApproveSchema
    order_by = ['-gmt_created']

    def get(self, request):
        """
        1.workspace审批管理列表（包括待审批和已审批）
        2.ws成员加入审批管理列表 action=join & object_type=workspace & object_id=${workspace_id}
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        审批处理 （1.同意 2.拒绝）
        """
        self.service.approve(request.data, operator=request.user.id)
        return Response(self.get_response_code())


class ApproveQuantityView(BaseView):
    schema_class = ApproveQuantitySchema
    service_class = ApproveQuantityService

    def get(self, request):
        """
        审批页面|加入申请页面数量统计

        传参：
        审批页面无需传参数，加入申请页需要传action(值为join)及 ws_id 两个参数
        如：action=join&ws_id=2

        返回：
        backlog_count为待审核数量
        finished_count为审批记录数量
        """
        data = self.service.get_quantity(request.GET)
        if not data:
            response_data = self.get_response_code(msg='缺少ws_id参数')
        else:
            response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class MemberQuantityView(BaseView):
    service_class = MemberQuantityService
    serializer_class = None
    schema_class = MemberQuantitySchema

    def get(self, request):
        data = self.service.get_quantity_result(request.GET)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class UploadView(BaseView):
    schema_class = UploadSchema
    service_class = UploadService

    def post(self, request):
        file = request.FILES.get('file')
        path, link = self.service.upload(request.data, file)
        response_data = self.get_response_code()
        response_data['path'] = path
        response_data['link'] = link
        return Response(response_data)


class WorkspaceQuantityView(BaseView):
    def get(self, request):
        data = {
            'total_count': Workspace.objects.filter(is_approved=True).count(),
            'public_count': Workspace.objects.filter(is_approved=True, is_public=True).count(),
            'un_public_count': Workspace.objects.filter(is_approved=True, is_public=False).count()
        }
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class WorkspaceCheckView(BaseView):
    service_class = WorkspaceService

    def get(self, request):
        code, msg = self.service.check_ws(request.GET)
        return Response(self.get_response_code(code=code, msg=msg))


class WorkspaceListView(CommonAPIView):

    queryset = Workspace.objects.filter(is_approved=True)
    service_class = WorkspaceListService
    serializer_class = WorkspaceIndexListSerializer
    search_fields = ['show_name']
    order_by = None

    def get(self, request):
        request.user_list = list(User.objects.all())
        request.member_list = list(WorkspaceMember.objects.all())
        queryset = self.service.filter(self.get_queryset(), request)
        response_data = self.get_response_data(queryset=queryset)
        return Response(response_data)


class WorkspaceListSelectView(CommonAPIView):
    service_class = WorkspaceSelectService
    serializer_class = WorkspaceIndexListSerializer
    search_fields = ['show_name']
    order_by = None

    def get(self, request):
        request.user_list = list(User.objects.all())
        request.member_list = list(WorkspaceMember.objects.all())
        queryset = self.service.filter()
        response_data = self.get_response_data(queryset=queryset)
        return Response(response_data)

    def put(self, request):
        """
        该接口用来修改workspace信息
        只要显示名、描述、logo、是否公开可以修改
        当前owner离职或者转岗后可以转交
        """
        request.user_list = list(User.objects.all())
        request.member_list = list(WorkspaceMember.objects.all())
        queryset = self.service.update_ws()
        success, instances = self.service.get_distincts_queryset(queryset, data=request.data)
        if success:
            response_data = self.get_response_data(instances)
        else:
            response_data = self.get_response_code(code=201, msg=instances)
        return Response(response_data)


class AllWorkspaceView(CommonAPIView):
    serializer_class = WorkspaceSerializer
    service_class = AllWorkspaceService
    queryset = Workspace.objects.filter(is_approved=True)
    permission_classes = []
    filter_fields = ['is_public', 'is_approved']
    search_fields = ['show_name', 'name']
    schema_class = WorkspaceSchema
    order_by = None

    def get(self, request):
        """
        获取workspace列表接口
        可以根据是否公开、我加入的、我创建的等条件进行过滤
        可以根据关键字进行模糊搜索
        """
        request.user_list = list(User.objects.all())
        request.member_list = list(WorkspaceMember.objects.all())
        if request.GET.get('brief'):
            self.serializer_class = WorkspaceBriefSerializer
        if request.GET.get('call_page') == 'index':
            self.serializer_class = WorkspaceIndexListSerializer
        queryset = self.service.filter(request)
        response_data = self.get_response_data(queryset=queryset)
        return Response(response_data)