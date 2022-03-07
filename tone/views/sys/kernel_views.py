# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework.response import Response
from django.utils.decorators import method_decorator

from tone.core.common.views import CommonAPIView
from tone.schemas.sys.kernel_schemas import KernelSyncSchema
from tone.serializers.sys.kernel_serializers import KernelSerializer
from tone.models import KernelInfo
from tone.services.sys.kernel_services import KernelInfoService
from tone.core.common.expection_handler.error_catch import views_catch_error


class KernelView(CommonAPIView):
    serializer_class = KernelSerializer
    queryset = KernelInfo.objects.all()
    service_class = KernelInfoService
    permission_classes = []
    order_by = ['-gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询KernelInfo
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建KernelInfo
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改KernelInfo
        """
        self.service.update(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除KernelInfo
        """
        self.service.delete(request.data, operator=request.user)
        return Response(self.get_response_code())


class SyncKernelView(CommonAPIView):
    serializer_class = KernelSerializer
    service_class = KernelInfoService
    schema_class = KernelSyncSchema

    def post(self, request):
        """
        内核配置同步: version_list, 必传参数, 内核版本名称的列表（兼容批量同步）
        响应：
        {
        "data": "",
        "code": 200,
        "msg": "同步成功"
        }
        """
        success, instance = self.service.sync_kernel(request.data, operator=request.user)
        response_data = self.get_response_code(msg=instance)
        if success:
            response_data['code'] = 200
        else:
            response_data['code'] = 201
        return Response(response_data)
