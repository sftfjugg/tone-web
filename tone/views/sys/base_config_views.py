# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework.response import Response
from django.utils.decorators import method_decorator

from tone.core.common.views import CommonAPIView
from tone.serializers.sys.base_config_serializers import BaseConfigSerializer, BaseConfigHistorySerializer
from tone.models import BaseConfig, BaseConfigHistory
from tone.services.sys.base_config_services import BaseConfigService, BaseConfigHistoryService
from tone.core.common.expection_handler.error_catch import views_catch_error
from tone.core.common.constant import BIND_STAGE


class BaseConfigView(CommonAPIView):
    serializer_class = BaseConfigSerializer
    queryset = BaseConfig.objects.all()
    service_class = BaseConfigService
    permission_classes = []
    order_by = ['-gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询BaseConfig
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        response_data['bind_stage'] = BIND_STAGE
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建BaseConfig
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改BaseConfig
        """
        self.service.update(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除BaseConfig
        """
        self.service.delete(request.data)
        return Response(self.get_response_code())


class BaseConfigHistoryView(CommonAPIView):
    serializer_class = BaseConfigHistorySerializer
    queryset = BaseConfigHistory.objects.all()
    service_class = BaseConfigHistoryService
    permission_classes = []
    order_by = ['-gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询BaseConfig
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)
