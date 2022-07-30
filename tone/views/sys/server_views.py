import re
from rest_framework.response import Response

from tone.core.common.info_map import add_link_msg
from tone.core.common.views import CommonAPIView, BaseView
from tone.models import TestServer, CloudServer, ServerTag, TestCluster, TestClusterServer, CloudAk, CloudImage
from tone.serializers.sys.server_serializers import TestServerSerializer, CloudServerSerializer, ServerTagSerializer, \
    TestClusterSerializer, TestClusterServerSerializer, CloudAkSerializer, CloudImageSerializer, \
    SpecifyTestServerSerializer
from tone.serializers.sys.testcase_serializers import SysTemplateSerializer
from tone.services.sys.server_services import TestServerService, CloudServerService, ServerTagService, \
    TestClusterService, TestClusterServerService, CloudAkService, CloudImageService, ToneAgentService
from tone.schemas.sys.server_schemas import ServerTagSchema, ServerTagDetailSchema, \
    TestServerCheckSchema, TestServerSchema, \
    TestServerDetailSchema, TestClusterSchema, TestClusterDetailSchema, TestClusterTestServerSchema, \
    TestClusterTestServerDetailSchema, TestClusterCloudServerDetailSchema, TestServerDeploySchema, \
    TestServerUpdateSchema, CloudServerSchema, \
    CloudServerDetailSchema, TestServerBatchUpdateSchema, CloudAkSchema, CloudServerImageSchema, \
    CloudServerInstanceSchema, CloudServerInstanceTypeSchema, CloudServerRegionSchema, CloudServerZoneSchema, \
    CloudServerDiskCategoriesSchema, TestClusterCloudServerSchema, TestServerChannelCheckSchema, CloudImageSchema, \
    TestServerChannelStateSchema


class TestServerView(CommonAPIView):
    serializer_class = TestServerSerializer
    queryset = TestServer.objects.all()
    service_class = TestServerService
    schema_class = TestServerSchema
    permission_classes = []

    def get(self, request):
        """
        集团单机列表查询
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        添加集团单机
        """
        success, instance = self.service.add_group_server(request.data)
        if success:
            response_data = self.get_response_data(None, many=False)
            response_data['msg'] = instance
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            link_msg = add_link_msg(instance)
            if link_msg:
                response_data['link_msg'] = link_msg
            return Response(response_data)


class SpecifyTestServerView(CommonAPIView):
    serializer_class = SpecifyTestServerSerializer
    queryset = TestServer.objects.all()
    service_class = TestServerService

    def get(self, request):
        """
        指定机器：集团单机列表查询
        """
        queryset = self.service.filter_specify_machine(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True if not request.GET.get('paging') else False)
        return Response(response_data)


class TestServerDetailView(CommonAPIView):
    serializer_class = TestServerSerializer
    service_class = TestServerService
    schema_class = TestServerDetailSchema
    queryset = TestServer.objects.all()

    def get(self, request, pk):
        """
        集团单机详情查询接口
        """
        instance = self.queryset.filter(id=pk).first()
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)

    def put(self, request, pk):
        """
        集团单机编辑接口
        """
        success, msg = self.service.update(request.data, pk, request.user.id)
        if success:
            response_data = self.get_response_data(None, many=False)
            response_data['msg'] = msg
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = msg
            return Response(response_data)

    def delete(self, request, pk):
        """
        集团单机删除接口
        """
        success, msg = self.service.delete(request.data, pk, request.user.id)
        response_data = self.get_response_code()
        if success != 200:
            response_data['code'] = 201
            response_data['msg'] = msg
        return Response(response_data)


class TestServerCheckView(CommonAPIView):
    serializer_class = TestServerSerializer
    service_class = TestServerService
    schema_class = TestServerCheckSchema

    def get(self, ips):
        """
        ip/sn检测接口
        """
        success, errors, msg = self.service.test_server_check(self.request.GET.getlist('ips'),
                                                              self.request.GET.get('channel_type'),
                                                              server_id=self.request.GET.get('server_id'),
                                                              ws_id=self.request.GET.get('ws_id'))
        response_data = self.get_response_data(None, many=False)
        response_data['data'] = {
            'success': success,
            'errors': errors
        }
        response_data['code'] = 200
        response_data['msg'] = msg
        return Response(response_data)


class TestServerChannelStateView(CommonAPIView):
    serializer_class = TestServerSerializer
    service_class = TestServerService
    schema_class = TestServerChannelStateSchema

    def get(self, ips):
        """
        channel_type查询机器状态
        """
        success, ret, error = self.service.get_channel_state(self.request.GET)
        response_data = self.get_response_data(None, many=False)
        response_data['data'] = ret
        response_data['code'] = success
        if success != 200:
            response_data['msg'] = error
        return Response(response_data)


class TestServerChannelCheckView(CommonAPIView):
    serializer_class = TestServerSerializer
    service_class = TestServerService
    schema_class = TestServerChannelCheckSchema

    def get(self, request):
        """
        ip/sn检测接口
        """
        success, msg = self.service.server_channel_check(request.GET)
        response_data = self.get_response_code(code=success, msg=msg)
        return Response(response_data)


class TestServerUpdateView(CommonAPIView):
    serializer_class = TestServerSerializer
    service_class = TestServerService
    schema_class = TestServerUpdateSchema

    def get(self, pk):
        """
        同步更新单机信息
        """
        success, msg = self.service.update_server(self.request.GET.get('pk'))
        response_data = self.get_response_data(None, many=False)
        if success:
            response_data['code'] = 200
            response_data['msg'] = msg
            return Response(response_data)
        else:
            response_data['code'] = 201
            response_data['msg'] = msg
            return Response(response_data)


class TestServerBatchUpdateView(CommonAPIView):
    serializer_class = TestServerSerializer
    service_class = TestServerService
    schema_class = TestServerBatchUpdateSchema

    def get(self, request):
        """
        批量同步更新单机信息
        """
        error_list = []
        for pk in request.GET.getlist('pks'):
            success, msg = self.service.update_server(pk)
            if not success:
                error_list.append(pk)
        response_data = self.get_response_data(None, many=False)
        if len(error_list) == 0:
            response_data['code'] = 200
            response_data['msg'] = 'success'
            return Response(response_data)
        else:
            response_data['code'] = 201
            response_data['data'] = error_list
            response_data['msg'] = '部分更新失败'
            return Response(response_data)

    def post(self, request):
        """
        批量修改备注、标签、owner
        """
        code, msg = self.service.batch_update_server(request.data, operator=request.user.id)
        response_data = self.get_response_code(code=code, msg=msg)
        return Response(response_data)


class TestServerDeployView(CommonAPIView):
    serializer_class = TestServerSerializer
    service_class = TestServerService
    schema_class = TestServerDeploySchema

    def post(self, request):
        """
        部署机器
        """
        success, instance = self.service.deploy(request.data)
        if success:
            response_data = self.get_response_data(None, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)


class TestServerGroupView(BaseView):
    queryset = TestServer.objects.all()
    service_class = TestServerService
    permission_classes = []

    def get(self, request):
        """
        集团单机app_group列表查询
        """
        data = self.service.get_app_group(request.GET)
        if not data:
            response_data = self.get_response_code(msg='error')
        else:
            response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class CloudServerView(CommonAPIView):
    serializer_class = CloudServerSerializer
    queryset = CloudServer.objects.all()
    service_class = CloudServerService
    schema_class = CloudServerSchema
    permission_classes = []

    def get(self, request):
        """
        云上单机列表查询
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        is_page = False if request.GET.get('no_page', False) else True
        response_data = self.get_response_data(queryset, page=is_page)
        return Response(response_data)

    def post(self, request):
        """
        添加云上单机
        """
        success, instance = self.service.create(request.data, request.user.id)
        if success:
            response_data = self.get_response_data(None, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)


class CloudServerDetailView(CommonAPIView):
    serializer_class = CloudServerSerializer
    service_class = CloudServerService
    queryset = CloudServer.objects.all()
    schema_class = CloudServerDetailSchema

    def get(self, request, pk):
        """
        云上单机详情查询接口
        """
        instance = self.queryset.filter(id=pk).first()
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)

    def put(self, request, pk):
        """
        云上单机编辑接口
        """
        success, instance = self.service.update(request.data, pk, request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)

    def delete(self, request, pk):
        """
        云上单机删除接口
        """
        success, msg = self.service.delete(request.data, pk, request.user.id)
        if success:
            response_data = self.get_response_code()
        else:
            response_data = self.get_response_code(code=201, msg=msg)
        return Response(response_data)


class CloudServerCheckView(CommonAPIView):
    service_class = CloudServerService

    def get(self, request):
        """
        云上机器名称校验
        """
        success, instance = self.service.check_instance(request.GET)
        response_data = self.get_response_code(code=200 if success else 201, msg=instance)
        return Response(response_data)


class CloudServerImageView(BaseView):
    queryset = CloudServer.objects.all()
    service_class = CloudServerService
    schema_class = CloudServerImageSchema
    permission_classes = []

    def get(self, request):
        """
        查询镜像列表
        """
        data = self.service.get_image_list(request.GET)
        if not data:
            response_data = self.get_response_code(code=201, msg='查询镜像列表为空')
        else:
            response_data = self.get_response_code()
            response_data['data'] = data
        return Response(response_data)


class CloudServerInstanceTypeView(BaseView):
    queryset = CloudServer.objects.all()
    service_class = CloudServerService
    schema_class = CloudServerInstanceTypeSchema
    permission_classes = []

    def get(self, request):
        """
        查询规格列表
        """
        data = self.service.get_instance_type(request.GET)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class CloudServerInstanceView(BaseView):
    queryset = CloudServer.objects.all()
    service_class = CloudServerService
    schema_class = CloudServerInstanceSchema
    permission_classes = []

    def get(self, request):
        """
        查询服务器实例列表
        """
        data = self.service.get_aliyun_server(request.GET)

        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class CloudServerRegionView(BaseView):
    queryset = CloudServer.objects.all()
    service_class = CloudServerService
    schema_class = CloudServerRegionSchema
    permission_classes = []

    def get(self, request):
        """
        查询region列表
        """
        success, instance = self.service.get_region_list(request.GET)
        if success:
            response_data = self.get_response_code()
            response_data['data'] = instance
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class CloudServerZoneView(BaseView):
    queryset = CloudServer.objects.all()
    service_class = CloudServerService
    schema_class = CloudServerZoneSchema
    permission_classes = []

    def get(self, request):
        """
        查询zone列表
        """
        data = self.service.get_zone_list(request.GET)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class CloudServerDiskCategoriesView(BaseView):
    queryset = CloudServer.objects.all()
    service_class = CloudServerService
    schema_class = CloudServerDiskCategoriesSchema
    permission_classes = []

    def get(self, request):
        """
        查询磁盘规格列表
        """
        data = self.service.get_disk_categories(request.GET)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class CloudAkView(CommonAPIView):
    queryset = CloudAk.objects.all()
    serializer_class = CloudAkSerializer
    service_class = CloudAkService
    schema_class = CloudAkSchema
    permission_classes = []
    order_by = ('-id',)

    def get(self, request):
        """
        查询ak列表
        """
        order_by, queryset = self.service.filter(self.get_queryset(), request.GET)
        if order_by:
            self.order_by = order_by
        if queryset:
            response_data = self.get_response_data(queryset)
        else:
            response_data = self.get_response_code(code=201, msg='云上测试配置：无可用AK')
        return Response(response_data)

    def post(self, request):
        """
        新增AK: workspace下 同provider下，name 三者联合唯一，
        provider枚举 {'aliyun_ecs': '阿里云ECS','aliyun_eci': '阿里云ECI'}
        access_id, access_key必填，description非必填
        """
        success, instance = self.service.create(request.data, operator=request.user)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def put(self, request):
        """
        修改指定id的cloud ak信息：name, provider, access_id, access_key, description
        """
        success, instance = self.service.update(request.data, operator=request.user)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def delete(self, request):
        """
        删除指定id列表的cloud ak，如 id:[1, 2,...]
        """
        self.service.delete(request.data)
        response_data = self.get_response_code()
        return Response(response_data)


class CloudImageView(CommonAPIView):
    queryset = CloudImage.objects.all()
    serializer_class = CloudImageSerializer
    service_class = CloudImageService
    schema_class = CloudImageSchema
    permission_classes = []
    order_by = ('-id',)

    def get(self, request):
        """
        查询image配置列表
        """
        order_by, queryset = self.service.filter(self.get_queryset(), request.GET)
        if order_by:
            self.order_by = order_by
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        新增image配置: 必填项: ak_id, provider, region,
        public_type, usage_type, login_user, image_id, image_name,
        image_version, platform
        """
        success, instance = self.service.create(request.data, operator=request.user)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def put(self, request):
        """
        修改指定id的cloud image配置信息：ak_id, provider, region, image_id, image_name, image_version, platform
        """
        success, instance = self.service.update(request.data, operator=request.user)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def delete(self, request):
        """
        删除指定id列表的cloud image配置，如 id:[1, 2,...]
        """
        self.service.delete(request.data)
        response_data = self.get_response_code()
        return Response(response_data)


class ServerTagView(CommonAPIView):
    serializer_class = ServerTagSerializer
    service_class = ServerTagService
    queryset = ServerTag.objects.all()
    schema_class = ServerTagSchema
    filter_fields = []
    order_by = ()

    def get(self, request):
        """
        机器标签列表查询
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        添加机器标签
        """
        if not re.search('^[a-zA-Z0-9_.-]+$', request.data.get('name')):
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = "标签名不合法."
            return Response(response_data)
        elif not request.user.id:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = "用户未登录."
            return Response(response_data)
        else:
            existed, instance = self.service.create(request.data, request.user.id)
            if existed:
                response_data = self.get_response_data(instance, many=False)
                return Response(response_data)
            else:
                response_data = self.get_response_data(instance, many=False)
                response_data['code'] = 201
                response_data['msg'] = "标签名已存在."
                return Response(response_data)


class ServerTagDetailView(CommonAPIView):
    serializer_class = ServerTagSerializer
    service_class = ServerTagService
    queryset = ServerTag.objects.all()
    schema_class = ServerTagDetailSchema

    def get(self, request, pk):
        """
        查询tag详情
        """
        instance = self.queryset.filter(id=pk).first()
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)

    def put(self, request, pk):
        """
        编辑tag
        """
        existed, instance = self.service.update(request.data, pk, request.user.id)
        if existed:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)

    def delete(self, request, pk):
        """
        删除指定tag
        """
        self.service.delete(request.data, pk, request.user.id)
        response_data = self.get_response_code()
        return Response(response_data)


class TestClusterView(CommonAPIView):
    serializer_class = TestClusterSerializer
    service_class = TestClusterService
    queryset = TestCluster.objects.all()
    schema_class = TestClusterSchema

    def get(self, request):
        """
        集群列表查询
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        新建集群
        """
        success, instance = self.service.create(request.data, request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:

            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)


class TestClusterDetailView(CommonAPIView):
    serializer_class = TestClusterSerializer
    service_class = TestClusterService
    queryset = TestCluster.objects.all()
    schema_class = TestClusterDetailSchema

    def get(self, request, pk):
        """
        查询集群详情
        """
        instance = self.queryset.filter(id=pk).first()
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)

    def put(self, request, pk):
        """
        编辑集群
        """
        success, instance = self.service.update(request.data, pk, request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)

    def delete(self, request, pk):
        """
        删除指定集群
        """
        self.service.delete(request.data, pk, request.user.id)
        response_data = self.get_response_code()
        return Response(response_data)


class TestClusterCloudTypeView(BaseView):
    serializer_class = TestClusterSerializer
    service_class = TestClusterService
    queryset = TestCluster.objects.all()

    def get(self, request, pk):
        """
        查询集群云上单机状态
        返回参数：0、无单机；1、选择已有；2、立即购买
        """
        data = self.service.get_cloud_type(pk)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class TestClusterTestServerView(CommonAPIView):
    serializer_class = TestClusterServerSerializer
    service_class = TestClusterServerService
    queryset = TestClusterServer.objects.all()
    schema_class = TestClusterTestServerSchema

    def get(self, request):
        """
        集群下机器列表查询
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        集群下添加机器
        """
        success, instance = self.service.create_test_server(request.data, request.user.id)
        if success:
            response_data = self.get_response_data(None, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)


class TestClusterCloudServerView(CommonAPIView):
    serializer_class = TestClusterServerSerializer
    service_class = TestClusterServerService
    queryset = TestClusterServer.objects.all()
    schema_class = TestClusterCloudServerSchema

    def get(self, request):
        """
        集群下机器列表查询
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        集群下添加机器
        """
        success, instance = self.service.create_cloud_server(request.data, request.user.id)
        if success:
            response_data = self.get_response_data(None, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)


class TestClusterTestServerDetailView(CommonAPIView):
    serializer_class = TestClusterServerSerializer
    service_class = TestClusterServerService
    queryset = TestCluster.objects.all()
    schema_class = TestClusterTestServerDetailSchema

    def put(self, request, pk):
        """
        集群下更新机器
        """
        success, instance = self.service.update_test_server(request.data, pk, request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)

    def delete(self, request, pk):
        """
        删除集群下机器
        """
        success, instance = self.service.delete(request.data, pk, request.user.id)
        if success:
            response_data = self.get_response_code(msg=instance)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class TestClusterCloudServerDetailView(CommonAPIView):
    serializer_class = TestClusterServerSerializer
    service_class = TestClusterServerService
    queryset = TestCluster.objects.all()
    schema_class = TestClusterCloudServerDetailSchema

    def put(self, request, pk):
        """
        集群下更新机器
        """
        success, instance = self.service.update_cloud_server(request.data, pk, request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
            return Response(response_data)

    def delete(self, request, pk):
        """
        删除集群下机器
        """
        self.service.delete(request.data, pk, request.user.id)
        response_data = self.get_response_code()
        return Response(response_data)


class CheckVarNameView(CommonAPIView):
    """校验变量名"""
    service_class = TestClusterServerService

    def post(self, request):
        success, instance = self.service.check_var_name(request.data)
        if success:
            response_data = self.get_response_code(code=200)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class ToneAgentDeploy(CommonAPIView):
    service_class = ToneAgentService

    def post(self, request):
        success, result = self.service.toneagent_deploy(request.data)
        if success:
            response_data = self.get_response_code()
        else:
            response_data = self.get_response_code(code=3001, msg=result)
        response_data['data'] = result
        return Response(response_data)


class ToneAgentVersion(CommonAPIView):
    service_class = ToneAgentService

    def get(self, request):
        success, result = self.service.toneagent_version_list(request.GET.get('version'))
        if success:
            response_data = self.get_response_code()
        else:
            response_data = self.get_response_code(msg=result)
            result = list()
        response_data['data'] = result
        return Response(response_data)


class ServerDelConfirmView(CommonAPIView):
    serializer_class = SysTemplateSerializer
    service_class = TestServerService

    def get(self, request):
        return Response(self.get_response_data(self.service.del_server_confirm(request.GET), many=True, page=True))


class SyncVmView(CommonAPIView):
    serializer_class = TestServerSerializer
    service_class = TestServerService

    def get(self, request):
        code, instance = self.service.get_vm_server(request.GET)
        response_data = self.get_response_code(code=code)
        if code == 200:
            response_data['data'] = instance
        else:
            response_data['msg'] = instance
        return Response(response_data)

    def post(self, request):
        success, instance = self.service.add_vm_server(request.data, request.user.id)
        if success:
            response_data = self.get_response_code(code=200, msg=instance)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)
