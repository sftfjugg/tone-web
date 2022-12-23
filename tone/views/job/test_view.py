# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import urllib.parse as urlparse

from rest_framework.response import Response
from django.utils.decorators import method_decorator

from tone import settings
from tone.core.common.exceptions import exception_code
from tone.core.common.views import CommonAPIView, BaseView
from tone.core.utils.tone_thread import ToneThread
from tone.models import TestJob, TestJobCase, FuncResult, ResultFile, PerfResult, \
    JobCollection, TestJobSuite, MonitorInfo
from tone.serializers.job.test_serializers import JobTestSerializer, JobTestSummarySerializer, \
    JobTestConfigSerializer, JobTestResultSerializer, JobTestConfResultSerializer, \
    JobTestCaseResultSerializer, JobTestCaseVersionSerializer, JobTestCaseFileSerializer, \
    JobTestCasePerResultSerializer, JobTestPrepareSerializer, JobTestProcessSuiteSerializer, \
    JobTestProcessCaseSerializer, JobTestProcessMonitorSerializer, JobTestMachineFaultSerializer, \
    CloudJobTestMachineFaultSerializer
from tone.services.job.test_services import JobTestService, JobTestConfigService, JobTestSummaryService, \
    JobTestResultService, JobTestConfResultService, JobTestCaseResultService, \
    JobTestCaseVersionService, JobTestCaseFileService, EditorNoteService, JobCollectionService, UpdateStateService, \
    JobTestPrepareService, JobTestProcessSuiteService, JobTestProcessCaseService, JobTestCasePerResultService, \
    JobTestProcessMonitorJobService, DataConversionService, MachineFaultService
from tone.core.common.constant import JOB_MONITOR_ITEM
from tone.core.common.expection_handler.custom_error import JobTestException
from tone.core.common.expection_handler.error_catch import views_catch_error
from tone.core.common.expection_handler.error_code import ErrorCode


class JobTestView(CommonAPIView):
    serializer_class = JobTestSerializer
    queryset = TestJob.objects.all()
    service_class = JobTestService
    permission_classes = []
    order_by = ['-id']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取WorkSpace下JobTest
        """
        request_data = request.GET
        if request_data.get('query_count'):
            response_data = self.get_response_code()
            queryset = self.service.filter(self.get_queryset(), request_data, operator=request.user)
            update_data = self.service.query_display_count(request_data, queryset, operator=request.user.id)
            response_data.update(update_data)
        else:
            response_data = self.get_response_code()
            instance, total = self.service.db_filter_job(request_data, operator=request.user.id)
            response_data['data'] = instance
            response_data['total'] = total
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建JobTest
        """
        try:
            self.service.create(request.data, operator=request.user)
        except JobTestException:
            return Response(self.get_response_code(code=ErrorCode.GLOBAL_VARIABLES_ERROR[0],
                                                   msg=ErrorCode.GLOBAL_VARIABLES_ERROR[1]))
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改JobTest
        """
        self.service.update(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除JobTest
        """
        success, instance = self.service.delete(request.data, operator=request.user.id)
        return Response(self.get_response_code(code=200 if success else 201, msg=instance))

    @staticmethod
    def count(queryset, operator, response_data, ws_id):
        """
        统计job相关数据
        """
        ws_job = TestJob.objects.filter(ws_id=ws_id).count()
        all_job = queryset.count()
        pending_job = queryset.filter(state__in=['pending', 'pending_q']).count()
        running_job = queryset.filter(state='running').count()
        success_job = queryset.filter(state='success').count()
        fail_job = queryset.filter(state='fail').count()
        my_job = TestJob.objects.filter(creator=operator.id, ws_id=ws_id).count()
        collection_jobs = JobCollection.objects.filter(user_id=operator.id)
        collection_job = 0
        for collection in collection_jobs:
            if TestJob.objects.filter(id=collection.job_id, ws_id=ws_id).exists():
                collection_job += 1
        response_data.update({
            'ws_job': ws_job,
            'all_job': all_job,
            'pending_job': pending_job,
            'running_job': running_job,
            'success_job': success_job,
            'fail_job': fail_job,
            'my_job': my_job,
            'collection_job': collection_job,
        })
        for i in response_data['data']:
            if JobCollection.objects.filter(job_id=i['id'], user_id=operator.id).exists():
                i['collection'] = True


class JobTestConfigView(CommonAPIView):
    serializer_class = JobTestConfigSerializer
    queryset = TestJob.objects.all()
    service_class = JobTestConfigService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobTestConfig
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)


class JobTestSummaryView(CommonAPIView):
    serializer_class = JobTestSummarySerializer
    queryset = TestJob.objects.all()
    service_class = JobTestSummaryService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobTestSummary
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        for i in response_data['data']:
            i['collection'] = True if JobCollection.objects.filter(job_id=i['id'],
                                                                   user_id=request.user.id).exists() else False

        return Response(response_data)


class JobTestBuildView(CommonAPIView):
    service_class = JobTestPrepareService

    @method_decorator(views_catch_error)
    def get(self, request):
        code, instance = self.service.get_build_kernel(request.GET)
        response_data = self.get_response_code(code=code)
        response_data['data'] = instance
        return Response(response_data)


class JobTestPrepareView(CommonAPIView):
    serializer_class = JobTestPrepareSerializer
    queryset = TestJob.objects.all()
    service_class = JobTestPrepareService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobTestProcess准备阶段数据
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=False)
        return Response(response_data)


class JobPrepareView(CommonAPIView):
    service_class = JobTestPrepareService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobTestProcess准备阶段数据，2022-12-15新增优化，用于替换JobTestPrepareView
        """
        job_id = request.GET.get('job_id')
        test_job = TestJob.objects.filter(id=job_id).first()
        response_data = self.get_response_only_for_data(self.service.get_test_prepare(test_job))
        return Response(response_data)


class JobTestProcessSuiteView(CommonAPIView):
    serializer_class = JobTestProcessSuiteSerializer
    queryset = TestJobSuite.objects.all()
    service_class = JobTestProcessSuiteService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobTestProcess准备阶段数据
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=False)
        return Response(response_data)


class JobTestProcessCaseView(CommonAPIView):
    serializer_class = JobTestProcessCaseSerializer
    queryset = TestJobCase.objects.all()
    service_class = JobTestProcessCaseService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobTestProcess准备阶段数据
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)


class JobTestResultView(CommonAPIView):
    serializer_class = JobTestResultSerializer
    queryset = TestJob.objects.all()
    service_class = JobTestResultService
    permission_classes = []
    order_by = ['-id']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobTestResult
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response = self.service.filter_search(self.get_response_data(queryset, page=False), request.GET)
        response_data = self.get_response_only_for_data(response)
        return Response(response_data)


class JobTestConfResultView(CommonAPIView):
    serializer_class = JobTestConfResultSerializer
    queryset = TestJobCase.objects.all()
    service_class = JobTestConfResultService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobTestResult
        """
        self.test_job_obj = self.service.get_test_job_obj(request.GET)
        self.test_type = self.test_job_obj.test_type
        self.suite_result = self.service.get_perfresult(request.GET, self.test_type)
        querysets = self.service.filter(self.get_queryset(), request.GET)
        datas = self.get_test_job_case_data(querysets)
        response = self.service.filter_search(datas, request.GET)
        response_data = self.get_response_only_for_data(response)
        return Response(response_data)

    def get_test_job_case_data(self, querysets):
        thread_tasks = []
        test_job_case_list = []
        for query in querysets:
            test_job_case = TestJobCase.objects.filter(id=query.id)
            thread_tasks.append(
                ToneThread(self.get_serializer_data, (test_job_case, True, False))
            )
            thread_tasks[-1].start()
        for thread_task in thread_tasks:
            thread_task.join()
            case_item_data = thread_task.get_result()
            test_job_case_list.append(case_item_data)
        datas = [case.get('data')[0] for case in test_job_case_list if case.get('data')]
        return datas


class JobTestCaseResultView(CommonAPIView):
    serializer_class = JobTestCaseResultSerializer
    queryset = FuncResult.objects.all()
    service_class = JobTestCaseResultService
    permission_classes = []
    order_by = []

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobCaseResult
        """
        queryset = self.service.filter(self.get_queryset(), request)
        response_data = self.get_response_data(queryset)
        return Response(response_data)


class JobTestCasePerResultView(CommonAPIView):
    serializer_class = JobTestCasePerResultSerializer
    queryset = PerfResult.objects.all()
    service_class = JobTestCasePerResultService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobCaseResult
        """
        querysets = self.service.filter(self.get_queryset(), request.GET)
        datas = self.get_per_result_data(querysets)
        response_data = self.get_response_only_for_data(datas)
        return Response(response_data)

    def get_per_result_data(self, querysets):
        thread_tasks = []
        per_result_list = []
        for query in querysets:
            per_result = PerfResult.objects.filter(id=query.id)
            thread_tasks.append(
                ToneThread(self.get_serializer_data, (per_result, True, False))
            )
            thread_tasks[-1].start()
        for thread_task in thread_tasks:
            thread_task.join()
            per_result_data = thread_task.get_result()
            per_result_list.append(per_result_data)
        datas = [case.get('data')[0] for case in per_result_list if case.get('data')]
        return datas


class JobTestCaseVersionView(CommonAPIView):
    serializer_class = JobTestCaseVersionSerializer
    queryset = TestJob.objects.all()
    service_class = JobTestCaseVersionService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobVaseVersionResult
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)


class JobTestCaseFileView(CommonAPIView):
    serializer_class = JobTestCaseFileSerializer
    queryset = ResultFile.objects.all()
    service_class = JobTestCaseFileService
    permission_classes = []
    order_by = []

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobCaseVersionResult
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=False)
        data = dict()
        result = []
        path_map = dict()
        for file in response_data['data']:
            path_map[str(file['id'])] = [file['result_path'], file['result_file']]
            self.calc_result(data, file['dp_result_file'])
        self.calc_data(data, result, path_map)
        response_data['data'] = result
        return Response(response_data)

    def calc_result(self, data, file):
        count = file.count('/')
        values = file.split('/')
        if count > 0:
            if values[0] in data:
                self.calc_result(data[values[0]], '/'.join(values[1:]))
            else:
                data[values[0]] = {}
                self.calc_result(data[values[0]], '/'.join(values[1:]))
        else:
            data[values[0]] = {}

    def calc_data(self, data, result, path_map):
        for key, value in data.items():
            if value:
                item = {"name": key, "items": []}
                self.calc_data(value, item["items"], path_map)
                result.append(item)
            else:
                key_value = key.split('$')
                result.append({
                    "name": key_value[0],
                    "items": [],
                    "path": self.get_sign_url(path_map.get(key_value[1]))
                })

    @staticmethod
    def get_sign_url(path):
        _path = urlparse.urlparse(path[0]).path
        file_path = urlparse.urljoin(_path, path[1])
        return file_path


class EditorNoteView(CommonAPIView):
    permission_classes = []
    service_class = EditorNoteService

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        编辑备注
        """
        self.service.editor_note(request.data)
        return Response(self.get_response_code())


class JobCollectionView(CommonAPIView):
    permission_classes = []
    service_class = JobCollectionService

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建JobTest
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除JobTest
        """
        self.service.delete(request.data, operator=request.user)
        return Response(self.get_response_code())


class EditorStateView(CommonAPIView):
    permission_classes = []
    service_class = UpdateStateService

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建CodeBranch
        """
        self.service.update_state(request.data, request.user.id)
        return Response(self.get_response_code())


class JobMonitorItemView(CommonAPIView):

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        job监控项列表
        """
        data = JOB_MONITOR_ITEM
        response_data = self.get_response_only_for_data(data)
        return Response(response_data)


class JobTestProcessMonitorJobView(CommonAPIView):
    serializer_class = JobTestProcessMonitorSerializer
    queryset = MonitorInfo.objects.all()
    service_class = JobTestProcessMonitorJobService

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取JobTestProcess监控数据
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        job_model = TestJob.objects.filter(id=request.GET.get('job_id')).first()
        if not job_model:
            raise JobTestException(ErrorCode.TEST_JOB_NONEXISTENT)
        data = self.service.get_monitor_info_serializer(queryset, job_model, self.serializer_class)
        response_data = self.get_response_only_for_data(data)
        return Response(response_data)


class YamlDataVerify(BaseView):
    service_class = DataConversionService

    def post(self, request):
        """
        校验yaml文本的合法性
        """
        if not request.data.get('yaml_data'):
            return Response(self.get_response_code(code=201, msg='yaml文本为空'))
        try:
            self.service.yaml_conv_to_json(
                request.data.get('yaml_data'),
                request.data.get('workspace'),
            )
            return Response(self.get_response_code())
        except Exception as e:
            return Response(self.get_response_code(code=201, msg=str(e)))


class DataConversion(BaseView):
    service_class = DataConversionService

    def post(self, request):
        try:
            if request.data.get('type', 'json2yaml') == 'json2yaml':
                conversion_data = self.service.json_conv_to_yaml(
                    request.data.get('json_data')
                )
            else:
                conversion_data = self.service.yaml_conv_to_json(
                    request.data.get('yaml_data'),
                    request.data.get('workspace')
                )
            response_data = self.get_response_code()
            response_data['data'] = conversion_data
            return Response(response_data)
        except Exception as e:
            response_data = self.get_response_code(code=201, msg=str(e))
            return Response(response_data)


class MachineFaultView(CommonAPIView):
    service_class = MachineFaultService

    def get(self, request):
        try:
            server_provider = ''
            job_id = request.GET.get('job_id')
            test_job = TestJob.objects.filter(id=job_id).first()
            if test_job:
                server_provider = test_job.server_provider
            queryset = self.service.get_machine_fault(request.GET)
            if server_provider == 'aligroup':
                self.serializer_class = JobTestMachineFaultSerializer
                response_data = self.get_response_data(queryset)
                return Response(response_data)
            else:
                self.serializer_class = CloudJobTestMachineFaultSerializer
                response_data = self.get_response_data(queryset)
                return Response(response_data)
        except Exception:
            response_data = self.get_response_code(code=exception_code.MACHINE_INFO_ERROR_514['code'],
                                                   msg=exception_code.MACHINE_INFO_ERROR_514['msg'])
            response_data['data'] = []
            return Response(response_data)
