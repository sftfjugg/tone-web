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
from tone.models import JobTag, json
from tone.serializers.job.tag_serializers import JobTagSerializer
from tone.services.job.tag_services import JobTagService, JobTagRelationService
from tone.core.common.expection_handler.error_catch import views_catch_error


class JobTagView(CommonAPIView):
    serializer_class = JobTagSerializer
    queryset = JobTag.objects.all()
    service_class = JobTagService
    permission_classes = []
    order_by = ['-gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询JobTag
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建JobTag
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改JobTag
        """
        success = self.service.update(request.data, operator=request.user)
        if success:
            return Response(self.get_response_code())
        else:
            return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除JobTag
        """
        success = self.service.delete(request.data, operator=request.user)
        if success:
            return Response(self.get_response_code())
        else:
            return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))


class JobTagRelationView(CommonAPIView):
    queryset = JobTag.objects.all()
    service_class = JobTagRelationService
    permission_classes = []

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        关联JobTag
        """
        success = self.service.create(request.data, operator=request.user)
        if success:
            return Response(self.get_response_code())
        else:
            return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))
