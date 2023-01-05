# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework.response import Response
from django.utils.decorators import method_decorator

from tone.core.common.views import CommonAPIView
from tone.services.job.result_compare_services import CompareEnvInfoService, CompareListService, \
    CompareSuiteInfoService, CompareChartService, CompareFormService, CompareConfInfoService, CompareDuplicateService
from tone.serializers.job.report_serializers import CompareFormSerializer
from tone.models import CompareForm
from tone.core.common.expection_handler.error_catch import views_catch_error
from tone.core.utils.calc_run_time import calc_run_time


class CompareSuiteInfoView(CommonAPIView):
    permission_classes = []
    service_class = CompareSuiteInfoService

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        获取suite信息
        """
        data = self.service.filter(request.data)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class CompareConfInfoView(CommonAPIView):
    permission_classes = []
    service_class = CompareConfInfoService

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        获取suite信息
        """
        data = self.service.filter(request.data)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class CompareEnvInfoView(CommonAPIView):
    permission_classes = []
    service_class = CompareEnvInfoService

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        对比环境信息
        """
        data = self.service.filter(request.data)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class CompareListView(CommonAPIView):
    permission_classes = []
    service_class = CompareListService

    @method_decorator(views_catch_error)
    @method_decorator(calc_run_time(decorator='compare_list'))
    def post(self, request):
        """
        性能对比列表
        """
        if request.data.get('async_request'):
            data = self.service.get_suite_compare_data_v1(request.data)
        else:
            data = self.service.filter(request.data)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class CompareChartView(CommonAPIView):
    permission_classes = []
    service_class = CompareChartService

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        性能对比图表
        """
        data = self.service.filter(request.data)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)


class CompareFormView(CommonAPIView):
    permission_classes = []
    service_class = CompareFormService
    serializer_class = CompareFormSerializer
    queryset = CompareForm.objects.all()
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取WorkSpace下TestTemplate
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_only_for_data(queryset)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        性能对比图表
        """
        data, hash_key = self.service.create(request.data, operator=request.user)
        response_data = self.get_response_code()
        response_data['data'] = data
        response_data['hash_key'] = hash_key
        return Response(response_data)


class CompareDuplicateView(CommonAPIView):
    permission_classes = []
    service_class = CompareDuplicateService

    @method_decorator(views_catch_error)
    def post(self, request):
        data = self.service.get(request.data)
        response_data = self.get_response_code()
        response_data['data'] = data
        return Response(response_data)
