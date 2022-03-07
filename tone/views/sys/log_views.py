# _*_ coding:utf-8 _*_
"""
Module Description: 操作日志
Date:
Author: Yfh
"""
from rest_framework.response import Response

from tone.core.common.views import CommonAPIView
from tone.models.sys.log_model import OperationLogs
from tone.services.sys.log_services import OperationLogsService
from tone.serializers.sys.log_serializers import OperationsLosSerializer


class OperationLogsView(CommonAPIView):
    queryset = OperationLogs.objects.all()
    service_class = OperationLogsService
    serializer_class = OperationsLosSerializer

    def get(self, request):
        """
        查询操作日志
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)
