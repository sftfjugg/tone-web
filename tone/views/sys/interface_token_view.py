# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework.response import Response
from django.utils.decorators import method_decorator

from tone.services.sys.interface_token_services import InterfaceTokenService
from tone.core.common.views import CommonAPIView
from tone.core.common.expection_handler.error_catch import views_catch_error


class InterfaceTokenView(CommonAPIView):
    service_class = InterfaceTokenService
    permission_classes = []
    order_by = ['-gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        创建Token
        """
        self.service.create(operator=request.user)
        return Response(self.get_response_code())
