from rest_framework.response import Response

from tone.core.common.views import CommonAPIView, BaseView
from tone.models import TestCase, TestSuite, TestMetric, WorkspaceCaseRelation, TestDomain, TestBusiness
from tone.schemas.sys.testcase_schemas import TestCaseSchema, TestCaseDetailSchema, TestCaseBatchSchema, \
    TestSuiteSchema, TestSuiteDetailSchema, TestMetricSchema, TestMetricDetailSchema, WorkspaceCaseSchema, \
    WorkspaceCaseBatchSchema, DomainSchema, TestSuiteExistSchema, SuiteRetrieveSchema
from tone.serializers.sys.testcase_serializers import TestCaseSerializer, TestSuiteSerializer, TestMetricSerializer, \
    WorkspaceCaseRelationSerializer, TestSuiteCaseSerializer, TestSuiteWsCaseSerializer, TestDomainSerializer, \
    BriefSuiteSerializer, TestRetrieveCaseSerializer, TestRetrieveSuiteSerializer, RetrieveCaseSerializer, \
    SysTemplateSerializer, SysJobSerializer, TestBusinessSerializer, BusinessSuiteSerializer
from tone.services.sys.testcase_services import TestCaseService, TestSuiteService, TestMetricService, \
    WorkspaceCaseService, TestDomainService, SyncCaseToCacheService, WorkspaceRetrieveService, ManualSyncService, \
    TestBusinessService


class TestCaseView(CommonAPIView):
    serializer_class = TestCaseSerializer
    queryset = TestCase.objects.all()
    service_class = TestCaseService
    schema_class = TestCaseSchema
    permission_classes = []

    def get(self, request):
        """
        case列表查询
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        添加case
        """
        success, instance = self.service.create(request.data)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
            return Response(response_data)


class TestCaseDetailView(CommonAPIView):
    serializer_class = TestCaseSerializer
    service_class = TestCaseService
    schema_class = TestCaseDetailSchema
    queryset = TestCase.objects.all()

    def get(self, request, pk):
        """
        case详情
        """
        if request.GET.get('retrieve'):
            self.serializer_class = RetrieveCaseSerializer
        instance = self.queryset.filter(id=pk).first()
        if instance is not None:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=404, msg='case not exists')
        return Response(response_data)

    def put(self, request, pk):
        """
        编辑指定的case
        """
        success, instance = self.service.update(request.data, pk)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)

    def delete(self, _, pk):
        """
        删除指定case
        """
        self.service.delete(pk)
        response_data = self.get_response_code()
        return Response(response_data)


class TestCaseBatchView(CommonAPIView):
    serializer_class = TestCaseSerializer
    service_class = TestCaseService
    schema_class = TestCaseBatchSchema
    queryset = TestCase.objects.all()

    def put(self, request):
        """
        批量修改case的领域，超时时间和执行次数
        """
        self.service.update_batch(request.data, operator=1)
        response_data = self.get_response_code()
        return Response(response_data)

    def delete(self, request):
        """
        批量删除case
        """
        self.service.remove_case(request.data, operator=1)
        return Response(self.get_response_code())


class TestSuiteBatchView(CommonAPIView):
    service_class = TestSuiteService

    def put(self, request):
        self.service.update_batch(request.data)
        response_data = self.get_response_code()
        return Response(response_data)

    def delete(self, request):
        self.service.remove_suite(request.data)
        return Response(self.get_response_code())


class TestSuiteView(CommonAPIView):
    serializer_class = TestSuiteSerializer
    queryset = TestSuite.objects.all()
    service_class = TestSuiteService
    schema_class = TestSuiteSchema
    order_by = ['-gmt_created']

    def get(self, request):
        """
        suite列表查询
        """
        page_many = True
        if request.GET.get('scope') == 'case':
            self.serializer_class = TestSuiteCaseSerializer
        elif request.GET.get('scope') == 'brief_case':
            self.serializer_class = BriefSuiteSerializer
            page_many = False
        if request.GET.get('order'):
            self.order_by = request.GET.get('order').split(',')
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=page_many)
        return Response(response_data)

    def post(self, request):
        """
        添加suite
        """
        success, instance = self.service.create(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class BusinessBriefView(CommonAPIView):
    service_class = TestSuiteService

    def get(self, request):
        instance = self.service.filter_business(request.GET)
        response_data = self.get_response_code()
        response_data['data'] = instance
        return Response(response_data)


class WorkspaceBusinessBriefView(CommonAPIView):
    serializer_class = BusinessSuiteSerializer
    service_class = TestSuiteService

    def get(self, request):
        instance = self.service.filter_ws_business(request, request.GET)
        if request.GET.get('scope') == 'brief':
            response_data = self.get_response_code()
            response_data['data'] = instance
        else:
            response_data = self.get_response_data(instance, many=True, page=True)
        return Response(response_data)


class TestSuiteDetailView(CommonAPIView):
    serializer_class = TestSuiteSerializer
    service_class = TestSuiteService
    schema_class = TestSuiteDetailSchema
    queryset = TestSuite.objects.all()

    def get(self, _, pk):
        """
        查询suite详情
        """
        instance = self.queryset.filter(id=pk).first()
        if instance is not None:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=404, msg='suite not exists')
        return Response(response_data)

    def put(self, request, pk):
        """
        编辑suite
        """
        success, instance = self.service.update(request.data, pk)
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
        删除指定suite
        """
        success, instance = self.service.delete(pk, request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_code(code=200, msg=instance)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class TestSuiteSyncView(CommonAPIView):
    serializer_class = TestSuiteSerializer
    service_class = TestSuiteService
    queryset = TestSuite.objects.all()

    def get(self, _, pk):
        """
        suite同步功能
        """
        self.code, self.msg = self.service.sync_case(pk)
        response_data = self.get_response_data(None, many=False)
        return Response(response_data)


class TestSuiteExistView(CommonAPIView):
    serializer_class = TestSuiteSerializer
    service_class = TestSuiteService
    schema_class = TestSuiteExistSchema
    queryset = TestSuite.objects.all()

    def get(self, request):
        """
        suite验证是否存在
        """
        code, msg = self.service.exist(request.GET)
        response_data = self.get_response_code(code=code, msg=msg)
        return Response(response_data)


class TestMetricView(CommonAPIView):
    serializer_class = TestMetricSerializer
    queryset = TestMetric.objects.all()
    service_class = TestMetricService
    schema_class = TestMetricSchema
    permission_classes = []

    def get(self, request):
        """
        查询指标列表
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        给suite或者case添加指标
        """
        success, instance = self.service.create(request.data)
        if success:
            response_data = self.get_response_data(None, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_data(None, many=False)
            response_data['code'] = 201
            response_data['msg'] = instance
            return Response(response_data)


class TestMetricListView(BaseView):
    queryset = TestMetric.objects.all()
    service_class = TestMetricService
    permission_classes = []

    def get(self, request):
        """
        查询metric列表
        """
        data = self.service.get_metric_list(request.GET)
        if not data:
            response_data = self.get_response_code(msg='error')
        else:
            response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class TestMetricDetailView(CommonAPIView):
    serializer_class = TestMetricSerializer
    service_class = TestMetricService
    queryset = TestMetric.objects.all()
    schema_class = TestMetricDetailSchema

    def get(self, _, pk):
        """
        根据id查询指标详情
        """
        instance = self.queryset.filter(id=pk).first()
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)

    def put(self, request, pk):
        """
        根据id修改指标信息
        """
        success, instance = self.service.update(request.data, pk)
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
        删除指定id的指标
        """
        self.service.delete(request.data, pk)
        response_data = self.get_response_code()
        return Response(response_data)

    def post(self, request):
        self.service.batch_delete(request.data)
        response_data = self.get_response_code()
        return Response(response_data)


class WorkspaceCaseView(CommonAPIView):
    serializer_class = WorkspaceCaseRelationSerializer
    queryset = WorkspaceCaseRelation.objects.all()
    service_class = WorkspaceCaseService
    schema_class = WorkspaceCaseSchema
    permission_classes = []

    def get(self, request):
        """
        workspace下获取case列表
        """
        page = True
        if request.GET.get('order'):
            self.order_by = request.GET.get('order').split(',')
        if request.GET.get('object_type') and request.GET.get('object_id'):
            self.serializer_class = TestMetricSerializer
        elif request.GET.get('suite_id'):
            self.serializer_class = TestCaseSerializer
        elif request.GET.get('scope') == 'brief_case':
            self.serializer_class = BriefSuiteSerializer
            page = False
        else:
            if request.GET.get('scope') == 'all' or int(request.GET.get('page_size', 10)) >= 100:
                data = TestCaseService().get_ws_all_cases(self.get_queryset(), request)
                response_data = self.get_response_code()
                response_data['data'] = data
                return Response(response_data)
            else:
                self.serializer_class = TestSuiteWsCaseSerializer
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=page)
        return Response(response_data)

    def post(self, request):
        """
        workspace下添加case
        """
        instance = self.service.create(request.data)
        response_data = self.get_response_data(instance, many=False)
        return Response(response_data)


class WorkspaceCaseHasRecordView(CommonAPIView):
    serializer_class = WorkspaceCaseRelationSerializer
    queryset = WorkspaceCaseRelation.objects.all()
    service_class = WorkspaceCaseService
    schema_class = WorkspaceCaseSchema
    permission_classes = []

    def get(self, request):
        """
        ws下是否有suite列表查询
        """
        ws_count = self.service.has_suite(self.get_queryset(), request.GET)
        if ws_count > 0:
            self.msg = True
        else:
            self.msg = False
        self.code = 200
        response_data = self.get_response_data(None, many=False)
        return Response(response_data)


class WorkspaceCaseBatchAddView(CommonAPIView):
    serializer_class = WorkspaceCaseRelationSerializer
    queryset = WorkspaceCaseRelation.objects.all()
    service_class = WorkspaceCaseService
    schema_class = WorkspaceCaseBatchSchema

    def post(self, request):
        """
        workspace下（批量）添加case
        """
        instance = self.service.add_case(request.data, operator=1)
        response_data = self.get_response_data(instance, many=True)
        return Response(response_data)


class WorkspaceCaseBatchDelView(CommonAPIView):
    serializer_class = WorkspaceCaseRelationSerializer
    queryset = WorkspaceCaseRelation.objects.all()
    service_class = WorkspaceCaseService
    schema_class = WorkspaceCaseBatchSchema

    def delete(self, request):
        """
        workspace下（批量）删除case
        """
        self.service.remove_case(request.data, operator=1)
        return Response(self.get_response_code())


class TestDomainView(CommonAPIView):
    serializer_class = TestDomainSerializer
    queryset = TestDomain.objects.all()
    order_by = ('-id',)
    service_class = TestDomainService
    schema_class = DomainSchema
    permission_classes = []

    def get(self, request):
        """
        查询domain列表
        """
        order_by, queryset = self.service.filter(self.get_queryset(), request.GET)
        if order_by:
            self.order_by = order_by
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        """
        新增domain: name唯一，description非必填
        """
        success, instance = self.service.create(request.data, operator=request.user)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def put(self, request):
        """
        修改指定id的domain信息：name 必传（name与其他不重复）, description
        """
        success, instance = self.service.update(request.data, operator=request.user)
        if success:
            response_data = self.get_response_data(instance, many=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)

    def delete(self, request):
        """
        删除指定id列表的domain（兼容批量删除） 如 id: [1, 2,...]
        """
        success, instance = self.service.delete(request.data)
        if success:
            response_data = self.get_response_code()
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class WorkspaceSuiteView(CommonAPIView):
    serializer_class = WorkspaceCaseRelationSerializer
    queryset = WorkspaceCaseRelation.objects.all()
    service_class = WorkspaceCaseService
    schema_class = WorkspaceCaseSchema


class SyncCaseToCache(CommonAPIView):
    serializer_class = TestCaseSerializer
    service_class = SyncCaseToCacheService

    def get(self, request):
        success, testcases = self.service.sync_case_to_cache(request.GET.get('scope', 'suite'))
        if success:
            response_data = self.get_response_code()
            response_data['data'] = testcases
        else:
            response_data = self.get_response_code(code=500, msg='同步失败')
        return Response(response_data)


class TestSuiteRetrieveView(CommonAPIView):
    serializer_class = TestRetrieveSuiteSerializer
    queryset = WorkspaceCaseRelation.objects.all()
    service_class = WorkspaceRetrieveService
    schema_class = SuiteRetrieveSchema

    def get(self, request):
        """
        Tone 平台下test suite 检索：信息获取
        1. 性能测试 、功能测试 数量获取 传参：total_num
        2. 获取 suite name 信息列表  传参：test_type + ws_id
        3. suite下conf展开： case name 列表获取（conf 展开） 传参：ws_id + suite_id
        4. conf同级：case name 列表获取（conf 展开） 排除自身 传参： ws_id + suite_id + case_id
        """
        msg = 'conf total number' if request.GET.get('total_num') else ''
        if request.GET.get('suite_id'):
            self.serializer_class = TestRetrieveCaseSerializer
        serialize_flag, queryset = self.service.filter(self.get_queryset(), request.GET)
        if serialize_flag:
            response_data = self.get_response_data(queryset)
        else:
            response_data = self.get_response_code(code=200, msg=msg)
            response_data['data'] = queryset
        return Response(response_data)

    def post(self, request):
        """
        Test Suite 搜索功能, 传参 search_key： 输入框搜索内容
        1. search_key为空，返回历史搜索记录，
        2. 输入后，实时显示检索记录： 历史 + suite + conf  传参： （1）search_key （2）result: 搜索结果标识
        3. 检索确定后显示搜索列表： 全部 + suite + conf + domain 传参： （1）search_key
        """
        serialize_flag, instance = self.service.search(request.data, self)
        if serialize_flag:
            response_data = self.get_response_data(instance, many=True)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class RetrieveQuantityView(CommonAPIView):
    """获取搜索结果页数量"""
    serializer_class = TestRetrieveSuiteSerializer
    queryset = WorkspaceCaseRelation.objects.all()
    service_class = WorkspaceRetrieveService
    schema_class = SuiteRetrieveSchema

    def get(self, request):
        """获取搜索结果页数量"""
        instance = self.service.get_quantity(request.GET)
        response_data = self.get_response_code(code=200, msg='get the quantity of display page')
        response_data['data'] = instance
        return Response(response_data)


class ManualSyncCase(CommonAPIView):
    """手动触发同步suite以及case"""
    service_class = ManualSyncService

    def get(self, request):
        """手动同步suite"""
        success, instance = self.service.manual_sync(request.GET)
        if success:
            response_data = self.get_response_code(msg=instance)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class LastSyncCase(CommonAPIView):
    """最后一次同步Suite时间"""
    service_class = ManualSyncService

    def get(self, _):
        instance = self.service.get_last_datetime()
        response_data = self.get_response_code(code=200, msg='获取最近同步时间成功')
        response_data['data'] = instance
        return Response(response_data)


class SysCaseDelView(CommonAPIView):
    serializer_class = SysTemplateSerializer
    service_class = TestSuiteService

    def get(self, request):
        instance, flag = self.service.sys_case_confirm(request, request.GET)
        if flag == 'job':
            self.serializer_class = SysJobSerializer
        if flag == 'pass':
            response = self.get_response_code(code=instance)
        else:
            response = self.get_response_data(instance, many=True, page=True)
        response['flag'] = flag
        return Response(response)


class WsCaseDelView(CommonAPIView):
    serializer_class = SysTemplateSerializer
    service_class = TestSuiteService

    def post(self, request):
        instance, flag = self.service.ws_case_confirm(request, request.data)
        if flag == 'pass':
            response = self.get_response_code(code=instance)
        else:
            if flag == 'job':
                self.serializer_class = SysJobSerializer
            response = self.get_response_data(instance, many=True, page=True)
        response['flag'] = flag
        return Response(response)


class TestBusinessView(CommonAPIView):
    serializer_class = TestBusinessSerializer
    queryset = TestBusiness.objects.all()
    service_class = TestBusinessService

    def get(self, request):
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    def post(self, request):
        success, instance = self.service.create(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
            return Response(response_data)


class TestBusinessDetailView(CommonAPIView):
    serializer_class = TestBusinessSerializer
    service_class = TestBusinessService

    def get(self, _, pk):
        self.serializer_class = TestSuiteSerializer
        response_data = self.get_response_data(self.service.filter_suite(pk), many=True)
        return Response(response_data)

    def put(self, request, pk):
        success, instance = self.service.update(request.data, pk, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False)
            return Response(response_data)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
            return Response(response_data)

    def delete(self, _, pk):
        self.service.delete(pk)
        response_data = self.get_response_code()
        return Response(response_data)
