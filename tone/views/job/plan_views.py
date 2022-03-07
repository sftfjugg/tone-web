# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author:
"""
from django.http import HttpResponse
from rest_framework.response import Response

from tone.core.common.views import CommonAPIView
from tone.models import TestPlan, json, PlanInstance, TestJob
from tone.schemas.job.plan_schemas import PlanListSchema, PlanDetailSchema, PlanCopySchema, PlanResultDetailSchema, \
    PlanRunSchema, PlanResultSchema, PlanViewSchema
from tone.serializers.job.plan_serializers import TestPlanSerializer, TestPlanDetailSerializer, PlanResultSerializer, \
    PlanViewSerializer, PlanResultDetailSerializer
from tone.serializers.job.test_serializers import JobTestSerializer
from tone.services.plan.plan_services import PlanService, PlanResultService


class PlanListView(CommonAPIView):
    """计划列表管理"""
    serializer_class = TestPlanSerializer
    queryset = TestPlan.objects.all()
    service_class = PlanService
    schema_class = PlanListSchema

    def get(self, request):
        """获取计划列表信息"""
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, many=True, page=True)
        return Response(response_data)

    def post(self, request):
        """新增计划"""
        success, instance = self.service.create_plan(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False, page=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class PlanDetailView(CommonAPIView):
    """计划详情管理"""
    serializer_class = TestPlanDetailSerializer
    queryset = TestPlan.objects.all()
    service_class = PlanService
    schema_class = PlanDetailSchema

    def get(self, request):
        """查询计划详情"""
        queryset = self.get_queryset().filter(id=request.GET.get('id')).first()
        response_data = self.get_response_data(queryset, many=False, page=False)
        return Response(response_data)

    def put(self, request):
        """修改计划"""
        success, instance = self.service.update_plan(request.data, operator=request.user.id)
        if success:
            return Response(self.get_response_code())
        else:
            if instance:
                return Response(self.get_response_code(code=201, msg=instance))
            else:
                return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))

    def delete(self, request):
        """删除计划"""
        success = self.service.delete_plan(request.data, operator=request.user.id)
        if success:
            return Response(self.get_response_code())
        else:
            return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))


class PlanCopyView(CommonAPIView):
    """拷贝计划"""
    serializer_class = TestPlanSerializer
    queryset = TestPlan.objects.all()
    service_class = PlanService
    schema_class = PlanCopySchema

    def post(self, request):
        success, instance = self.service.copy_plan(request.data, operator=request.user.id)
        response_data = self.get_response_data(instance, many=False, page=False)
        return Response(response_data)


class PlanRunView(CommonAPIView):
    """运行计划"""
    serializer_class = PlanResultSerializer
    queryset = TestPlan.objects.all()
    service_class = PlanService
    schema_class = PlanRunSchema

    def post(self, request):
        """手动运行计划"""
        success, instance = self.service.run_plan(request.data, operator=request.user.id)
        if success:
            response_data = self.get_response_data(instance, many=False, page=False)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class PlanViewView(CommonAPIView):
    """计划视图"""
    serializer_class = PlanViewSerializer
    queryset = TestPlan.objects.all()
    service_class = PlanService
    schema_class = PlanViewSchema

    def get(self, request):
        is_many, queryset = self.service.filter_plan_view(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, many=is_many, page=is_many)
        return Response(response_data)


class PlanResultView(CommonAPIView):
    """计划结果"""
    serializer_class = PlanResultSerializer
    queryset = PlanInstance.objects.all()
    service_class = PlanResultService
    schema_class = PlanResultSchema

    def get(self, request):
        """获取计划实例列表信息"""
        queryset = self.service.get_plan_result(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, many=True, page=True)
        return Response(response_data)

    def delete(self, request):
        """删除计划实例"""
        success = self.service.delete_plan_instance(request.data, operator=request.user.id)
        if success:
            return Response(self.get_response_code())
        else:
            return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))


class PlanResultDetailView(CommonAPIView):
    serializer_class = PlanResultDetailSerializer
    queryset = PlanInstance.objects.all()
    service_class = PlanResultService
    schema_class = PlanResultDetailSchema

    def get(self, request):
        """获取计划实例结果详情信息"""
        queryset = self.service.get_plan_detail_result(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, many=False, page=False)
        return Response(response_data)

    def post(self, request):
        """修改计划实例基础配置备注信息"""
        success = self.service.modify_note(request.data, operator=request.user.id)
        if success:
            return Response(self.get_response_code())
        else:
            return HttpResponse(status=401, content=json.dumps({'code': 401, 'msg': '没有权限，请联系统管理员'}))


class PlanConstraintView(CommonAPIView):
    serializer_class = JobTestSerializer
    queryset = TestJob.objects.all()
    service_class = PlanService

    def get(self, request):
        """对比计划中添加计划job"""
        queryset = self.service.get_constraint_job(self.get_queryset(), request.GET)
        return Response(self.get_response_data(queryset, page=False, many=True))


class CheckCronExpressionView(CommonAPIView):
    service_class = PlanService

    def post(self, request):
        success, instance = self.service.check_cron_express(request.data)
        if success:
            response_data = self.get_response_code(code=200, msg='校验通过')
            response_data['data'] = instance
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class ManualCreateView(CommonAPIView):
    service_class = PlanService

    def get(self, request):
        success, instance = self.service.manual_create_report(request.GET)
        if success:
            response_data = self.get_response_code(code=200, msg='自动生成成功')
            response_data['data'] = instance
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)
