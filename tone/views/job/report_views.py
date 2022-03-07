# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author:
"""
import json

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views import View
from rest_framework.response import Response
from django.utils.decorators import method_decorator

from tone import settings
from tone.core.common.constant import EnvType
from tone.core.common.views import CommonAPIView
from tone.models import PlanInstance, TestPlan
from tone.models.report.test_report import ReportTemplate, Report, ReportObjectRelation
from tone.serializers.job.report_serializers import ReportTemplateSerializer, ReportTemplateDetailSerializer, \
    ReportSerializer, ReportDetailSerializer
from tone.services.report.report_services import ReportTemplateService, ReportService, ReportDetailService
from tone.core.common.expection_handler.error_catch import views_catch_error


class ReportTemplateListView(CommonAPIView):
    """报告模板管理"""
    serializer_class = ReportTemplateSerializer
    queryset = ReportTemplate.objects.all()
    service_class = ReportTemplateService
    order_by = ()

    def get(self, request):
        """获取报告模板列表信息"""
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, many=True, page=True)
        return Response(response_data)

    def post(self, request):
        """新增报告模板"""
        success, instance = self.service.create_report_template(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False, page=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class ReportTemplateDetailView(CommonAPIView):
    """报告模板详情管理"""
    serializer_class = ReportTemplateDetailSerializer
    queryset = ReportTemplate.objects.all()
    service_class = ReportTemplateService

    def get(self, request):
        """查询报告模板详情"""
        queryset = self.get_queryset().filter(id=request.GET.get('id')).first()
        response_data = self.get_response_data(queryset, many=False, page=False)
        return Response(response_data)

    def put(self, request):
        """修改报告模板"""
        success, instance = self.service.update_report_template(request.data, operator=request.user.id)
        if success:
            return Response(self.get_response_data(instance, many=False, page=False))
        else:
            if instance:
                return Response(self.get_response_code(code=201, msg=instance))
            else:
                return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))

    def delete(self, request):
        """删除报告模板"""
        success, instance = self.service.delete_report_template(request.data, operator=request.user.id)
        if success:
            return Response(self.get_response_code())
        else:
            if instance:
                return Response(self.get_response_code(code=201, msg=instance))
            else:
                return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))


class ReportTemplateCopyView(CommonAPIView):
    """拷贝报告模板"""
    serializer_class = ReportTemplateSerializer
    queryset = ReportTemplate.objects.all()
    service_class = ReportTemplateService

    def post(self, request):
        success, instance = self.service.copy_report_template(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False, page=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class ReportView(CommonAPIView):
    serializer_class = ReportSerializer
    queryset = Report.objects.all()
    service_class = ReportService
    permission_classes = []

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询测试报告列表
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建测试报告
        """
        self.service.create(request.data, operator=request.user.id)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        编辑测试报告
        """
        self.service.update(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除测试报告
        """
        self.service.delete(request.data, operator=request.user)
        return Response(self.get_response_code())


class ReportDetailView(CommonAPIView):
    serializer_class = ReportDetailSerializer
    queryset = Report.objects.all()
    service_class = ReportDetailService
    permission_classes = []

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询测试报告详情
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)


class ReportDailyView(View):
    def get(self, request, plan_name):
        plan = TestPlan.objects.filter(name=plan_name).first()
        if not plan:
            return HttpResponse('无该计划')
        last_plan_instance = PlanInstance.objects.filter(plan_id=plan.id).last()
        if not last_plan_instance:
            return HttpResponse('该计划暂无实例')
        report_relation_obj = ReportObjectRelation.objects.filter(
            object_type='plan_instance',
            object_id=last_plan_instance.id
        ).first()
        if not report_relation_obj:
            return HttpResponse('该计划暂无报告')
        report = Report.objects.filter(id=report_relation_obj.report_id).first()
        url = f'{EnvType.cur_domain()}/ws/{report.ws_id}/test_report/{report.id}'
        return redirect(url)
