from rest_framework.response import Response

from tone.core.common.views import CommonAPIView
from tone.models import HelpDoc, SiteConfig, Workspace, Project, Comment, SitePushConfig
from tone.schemas.sys.server_schemas import HelpDocSchema, TestFarmSchema
from tone.serializers.sys.help_doc_serializers import HelpDocSerializer, HelpDocDetailSerializer, TestFarmSerializer, \
    WorkspaceListSerializer, ProjectListSerializer, CommentSerializer, TestFarmJobSerializer, SitePushConfigSerializer
from tone.services.sys.help_doc_services import HelpDocService, TestFarmService, CommentService, WorkspaceConfigService


class HelpDocView(CommonAPIView):
    serializer_class = HelpDocSerializer
    queryset = HelpDoc.objects.all()
    service_class = HelpDocService
    schema_class = HelpDocSchema
    order_by = ['order_id']

    def get(self, request):
        """获取文档列表"""
        if request.GET.get('id'):
            self.serializer_class = HelpDocDetailSerializer
        response_data = self.get_response_data(self.service.filter(self.get_queryset(), request.GET), page=False)
        return Response(response_data)

    def post(self, request):
        """
        新增文档
        参数：1. title 标题
        2.content 文档信息
        3.tags
        4.active
        """
        success, instance = self.service.create(request.data, operator=request.user)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
            return Response(response_data)

    def put(self, request):
        """修改文档信息"""
        success, instance = self.service.update(request.data, operator=request.user)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def delete(self, request):
        """删除文档"""
        queryset = self.service.delete(request.data)
        response_data = self.get_response_data(queryset, many=False, page=False)
        return Response(response_data)


class TestFarmView(CommonAPIView):
    serializer_class = TestFarmSerializer
    queryset = SiteConfig.objects.all()
    service_class = TestFarmService
    schema_class = TestFarmSchema

    def get(self, _):
        """获取 Testfarm 配置信息"""
        response_data = self.get_response_data(self.service.filter(), many=False)
        return Response(response_data)

    def post(self, request):
        """修改站点配置"""
        success, instance = self.service.update(request.data)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class PushConfigView(CommonAPIView):
    serializer_class = SitePushConfigSerializer
    queryset = SitePushConfig.objects.all()
    service_class = TestFarmService

    def post(self, request):
        """新增推送配置"""
        success, instance = self.service.create_push_config(request.data)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def put(self, request):
        """修改推送配置"""
        success, instance = self.service.update_push_config(request.data)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def delete(self, request):
        """删除推送配置"""
        code, instance = self.service.delete_push_config(request.data)
        response_data = self.get_response_code(code=code, msg=instance)
        return Response(response_data)


class PushJobView(CommonAPIView):
    serializer_class = TestFarmJobSerializer
    service_class = TestFarmService
    order_by = []

    def get(self, request):
        """获取推送配置下符合条件的job列表"""
        success, instance, page_num = self.service.filter_job_list(request.GET)
        if success:
            if page_num:
                response_data = self.get_response_code()
                response_data['data'] = instance
                response_data['page_num'] = page_num
            else:
                response_data = self.get_response_data(instance, many=True, page=True)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def post(self, request):
        """推送指定job"""
        code, instance = self.service.push_spe_job(request.data)
        response_data = self.get_response_code(code=code, msg=instance)
        return Response(response_data)


class WorkspaceConfigView(CommonAPIView):
    service_class = WorkspaceConfigService

    def get(self, request):
        response_data = self.get_response_code()
        response_data['data'] = self.service.get_ws_config(request.GET)
        return Response(response_data)

    def put(self, request):
        code, instance = self.service.update_ws_config(request.data)
        response_data = self.get_response_code(code=code, msg=instance)
        return Response(response_data)


class PortalTestView(CommonAPIView):
    service_class = TestFarmService

    def get(self, _):
        """master配置：测试同步portal流程是否走通"""
        success, instance = self.service.manual_sync_job()
        if success:
            response_data = self.get_response_code(msg=instance)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class WorkspaceListView(CommonAPIView):
    serializer_class = WorkspaceListSerializer
    queryset = Workspace.objects.all()
    order_by = ['-gmt_created']

    def get(self, _):
        """获取 Workspace 下拉"""
        response_data = self.get_response_data(self.get_queryset(), page=False)
        return Response(response_data)


class ProjectListView(CommonAPIView):
    serializer_class = ProjectListSerializer
    queryset = Project.objects.all()
    order_by = ['-gmt_created']

    def get(self, request):
        """获取 Workspace下 project 下拉"""
        response_data = self.get_response_data(self.get_queryset().filter(ws_id=request.GET.get('ws_id')), page=False)
        return Response(response_data)


class CommentView(CommonAPIView):
    serializer_class = CommentSerializer
    queryset = Comment.objects.all()
    service_class = CommentService

    def get(self, request):
        response_data = self.get_response_data(self.service.filter_comment(self.get_queryset(), request.GET), page=True)
        return Response(response_data)

    def post(self, request):
        success, instance = self.service.create_comment(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(201, msg=instance)
        return Response(response_data)

    def put(self, request):
        success, instance = self.service.update_comment(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance)
        else:
            response_data = self.get_response_code(201, msg=instance)
        return Response(response_data)

    def delete(self, request):
        success, instance = self.service.delete_comment(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_code(msg=instance)
        else:
            response_data = self.get_response_code(201, msg=instance)
        return Response(response_data)
