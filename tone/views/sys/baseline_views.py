from django.utils.decorators import method_decorator

from tone.core.common.expection_handler.error_catch import views_catch_error
from tone.core.common.views import CommonAPIView
from tone.models import Baseline, FuncBaselineDetail, PerfBaselineDetail
from rest_framework.response import Response

from tone.schemas.sys.baseline_schemas import BaselineSchema, FuncBaselineDetailSchema, PerfBaselineDetailSchema, \
    SearchSuiteSchema, PerfBaselineBatchAddSchema, PerfBaselineAddOneSchema, ContrastBaselineSchema
from tone.serializers.sys.baseline_serializers import BaselineSerializer, \
    FuncBaselineDetailSerializer, PerfBaselineDetialSerializer
from tone.services.sys.baseline_services import BaselineService, \
    FuncBaselineService, PerfBaselineService, SuiteSearchServer, ContrastBaselineService


class AllBaselineView(CommonAPIView):
    """所有基线"""
    serializer_class = BaselineSerializer
    queryset = Baseline.objects.all()
    service_class = BaselineService
    schema_class = BaselineSchema
    version = None  # 产品版本
    test_type = None  # 测试类型
    server_provider = None  # 机器类型

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取所有基线分类:
        基线分类：      server_provider——    test_type
        集团-功能：     aligroup——        functional
        集团-性能：     aligroup  ——     performance
        云上-功能：     aliyun    ——      functional
        云上-性能：     aliyun  ——       performance
        test_type 和 name 和 ws_id 和 server_provider 联合唯一基线标识
        参数：id、name、version用于筛选
        """
        baseline_list = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(baseline_list, many=True, page=True)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """新增基线分类"""
        success, instance = self.service.create(request.data, operator=request.user)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
            return Response(response_data)

    @method_decorator(views_catch_error)
    def put(self, request):
        """编辑基线分类"""
        success, instance = self.service.update(request.data, operator=request.user)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
            return Response(response_data)

    @method_decorator(views_catch_error)
    def delete(self, request):
        """删除基线分类以及删除其管理的TestSuite/TestConf/Metric相关记录：根据名称和测试类型"""
        self.service.delete(request.data)
        return Response(self.get_response_code())


class FuncBaselineView(CommonAPIView):
    """功能基线详情"""
    serializer_class = FuncBaselineDetailSerializer
    queryset = FuncBaselineDetail.objects.all()
    service_class = FuncBaselineService
    schema_class = FuncBaselineDetailSchema

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取功能基线详情
        1.suite展开：传参：基线id
        2.conf展开：传参：基线id + test_suite_id
        3.fail case展开：传参：基线id + test_suite_id + test_case_id
        """
        success, instance = self.service.get(self.get_queryset(), request.GET)
        if success:
            response_data = self.get_response_data(instance, many=True)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=200, msg='suite name or case name expand')
            response_data['data'] = instance
            return Response(response_data)

    @method_decorator(views_catch_error)
    def put(self, request):
        """编辑fail_case信息"""
        success, instance = self.service.update(request.data)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
            return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """job结果执行加入基线详情"""
        success, instance = self.service.create(request.data)
        if success:
            response_data = self.get_response_data(instance, many=True)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
            return Response(response_data)

    @method_decorator(views_catch_error)
    def delete(self, request):
        """删除Failcase"""
        self.service.delete(request.data)
        return Response(self.get_response_code())


class PerfBaselineView(CommonAPIView):
    """性能基线详情"""
    service_class = PerfBaselineService
    serializer_class = PerfBaselineDetialSerializer
    schema_class = PerfBaselineDetailSchema
    queryset = PerfBaselineDetail.objects.all()
    server_provider = None

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取性能基线详情信息：集团（aligroup）和云上（aliyun）机器展开有差异
        性能基线分为集团和云上

        """
        success, instance = self.service.get(self.get_queryset(), request.GET)
        if success:
            response_data = self.get_response_data(instance, many=True)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=200, msg='suite name or case name expand')
            response_data['data'] = instance
            return Response(response_data)

    @method_decorator(views_catch_error)
    def delete(self, request):
        """删除性能基线详情，即删除一条metric"""
        self.service.delete(request.data)
        return Response(self.get_response_code())


class SearchSuiteView(CommonAPIView):
    """搜索suite"""
    service_class = SuiteSearchServer
    serializer_class = FuncBaselineDetailSerializer
    schema_class = SearchSuiteSchema
    queryset = None

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        根据search_suite名称搜索suite名称分类
        test_type：区分 功能/性能
        baseline_id: 过滤suite_id，获取suite名称分类列表
        响应如：
            "data":[
                {
                    "test_suite_name": "libhugetlbfs",
                    "test_suite_id": 58
                },
                {
                    "test_suite_name": "ltp",
                    "test_suite_id": 54
                }
            ]
        """
        success, instance = self.service.search_suite(request.GET)
        if success:
            self.serializer_class = success
            response_data = self.get_response_data(instance, many=True)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=200, msg='success search suite name')
            response_data['data'] = instance
            return Response(response_data)


class PerfBaselineAddOneView(CommonAPIView):
    service_class = PerfBaselineService
    serializer_class = PerfBaselineDetialSerializer
    schema_class = PerfBaselineAddOneSchema

    def post(self, request):
        """通过 Testconf 加入性能基线详情"""
        success, instance = self.service.add_one_perf(request.data)
        if success:
            response_data = self.get_response_data(instance, many=True)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class PerfBaselineBatchAddView(CommonAPIView):
    """性能批量加入基线"""
    service_class = PerfBaselineService
    serializer_class = PerfBaselineDetialSerializer
    schema_class = PerfBaselineBatchAddSchema

    def post(self, request):
        """性能批量加入基线
        集团
        • 新增性能基线，包含属性：
        1）产品版本，基线描述，TestSuite/Testconf/Metric；
        2）机器信息：SN，IP，机型，Runmode，来源Job。3）Metric基线值。所有属性值在加入基线时系统自动获取。
        云上
        新增性能基线，包含属性：
        1）产品版本，基线描述，TestSuite/Testconf/Metric；
        2）机器信息：SN，IP，规格，Image，Bandwidth，Runmode，来源Job。3）Metric基线值。所有属性值在加入基线时系统自动获取。
        性能基线可以在 1.TestSuite 2.Testconf 任何层级添加， 3.通过批量操作添加
        """
        success, instance = self.service.add_perf(request.data)
        if success:
            response_data = self.get_response_data(instance, many=True)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class ContrastBaselineView(CommonAPIView):
    """性能对比基线"""
    service_class = ContrastBaselineService
    schema_class = ContrastBaselineSchema

    def post(self, request):
        """
        1. suite级对比基线
        2. conf级对比基线 传参：1.baseline_id 2.job_id 3.suite_id 4.case_id
        """
        success, instance = self.service.contrast_perf(request.data)
        if success:
            response_data = self.get_response_code(code=200, msg=instance)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)
