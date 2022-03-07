# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework.response import Response
from django.utils.decorators import method_decorator

from tone.core.common.views import CommonAPIView
from tone.schemas.job.jt_schemas import JobItemSchema, JobTypeSchema
from tone.models import JobType, JobTypeItem, JobTypeItemRelation
from tone.serializers.job.type_serializers import JobTypeSerializer, JobTypeItemSerializer, \
    JobTypeItemRelationSerializer
from tone.serializers.sys.testcase_serializers import SysTemplateSerializer
from tone.services.job.type_services import JobTypeService, JobTypeItemService, JobTypeItemRelationService
from tone.core.common.expection_handler.error_catch import views_catch_error


class JobTypeView(CommonAPIView):
    serializer_class = JobTypeSerializer
    queryset = JobType.objects.all()
    service_class = JobTypeService
    schema_class = JobTypeSchema
    permission_classes = []
    order_by = []

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取WorkSpace下JobType列表接口
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=False)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建JobType
        """
        response_data = self.service.create(request.data, operator=request.user)
        return Response({**self.get_response_code(), **response_data})

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改JobType
        """
        response_data = self.service.update(request.data, operator=request.user)
        return Response({**self.get_response_code(), **response_data})

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除自定义JobType
        """
        self.service.delete(request.data, operator=request.user)
        return Response(self.get_response_code())


class JobTypeItemView(CommonAPIView):
    serializer_class = JobTypeItemSerializer
    queryset = JobTypeItem.objects.all()
    service_class = JobTypeItemService
    schema_class = JobItemSchema
    permission_classes = []
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取原子项
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        res = self.partial(queryset)
        return Response(res)

    def partial(self, queryset):
        res = self.get_response_data(queryset, page=False)
        after_data = {'basic': list(), 'env': list(), 'server': list(), 'more': list()}
        for i in res['data']:
            if i['config_index'] == 1:
                after_data['basic'].append(i)
            elif i['config_index'] == 2:
                after_data['env'].append(i)
            elif i['config_index'] == 3:
                after_data['server'].append(i)
            else:
                after_data['more'].append(i)
        res['data'] = after_data
        return res


class JobTypeItemRelationView(CommonAPIView):
    serializer_class = JobTypeItemRelationSerializer
    queryset = JobTypeItemRelation.objects.all()
    service_class = JobTypeItemRelationService
    permission_classes = []

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取原子项
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=False)
        return Response(response_data)


class JobTypeDelView(CommonAPIView):
    serializer_class = SysTemplateSerializer
    service_class = JobTypeService

    @method_decorator(views_catch_error)
    def get(self, request):
        return Response(self.get_response_data(self.service.del_type_confirm(request.GET), many=True, page=True))
