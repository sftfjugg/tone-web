# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from django.http import HttpResponse
from rest_framework.response import Response
from django.utils.decorators import method_decorator

from tone.core.common.views import CommonAPIView
from tone.models import TestTemplate, json
from tone.serializers.job.plan_serializers import TestPlanSerializer
from tone.serializers.job.template_serializers import TestTemplateSerializer, TestTemplateDetailSerializer, \
    TemplateItemsSerializer
from tone.services.job.template_services import TestTemplateService, TestTemplateDetailService, \
    TestTemplateItemsService, TestTemplateCopyService
from tone.core.common.expection_handler.error_catch import views_catch_error


class TestTemplateView(CommonAPIView):
    serializer_class = TestTemplateSerializer
    queryset = TestTemplate.objects.all()
    service_class = TestTemplateService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取WorkSpace下TestTemplate
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建TestTemplate
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改TestTemplate
        """
        success = self.service.update(request.data, operator=request.user)
        if success:
            return Response(self.get_response_code())
        else:
            return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除TestTemplate
        """
        success = self.service.delete(request.data, operator=request.user)
        if success:
            return Response(self.get_response_code())
        else:
            return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))


class TestTemplateDetailView(CommonAPIView):
    serializer_class = TestTemplateDetailSerializer
    queryset = TestTemplate.objects.all()
    service_class = TestTemplateDetailService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取WorkSpace下TestTemplate
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)


class TemplateItemsView(CommonAPIView):
    serializer_class = TemplateItemsSerializer
    queryset = TestTemplate.objects.all()
    service_class = TestTemplateItemsService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取WorkSpace下TestTemplate
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)


class TemplateCopyView(CommonAPIView):
    service_class = TestTemplateCopyService
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        Copy Template
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())


class TemplateDelView(CommonAPIView):
    service_class = TestTemplateService
    serializer_class = TestPlanSerializer
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        return Response(self.get_response_data(self.service.del_confirm(request.GET), many=True, page=True))
