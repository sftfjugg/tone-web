from rest_framework.response import Response

from tone.core.common.views import CommonAPIView
from tone.models import TestJob
from tone.serializers.job.test_serializers import JobTestSerializer
from tone.services.sys.dashboard_services import DashboardService
from tone.services.sys.workspace_services import DashboardListService


class LiveDataView(CommonAPIView):
    service_class = DashboardService

    def get(self, request):
        response = self.get_response_code()
        response['data'] = self.service.get_live_data(request.GET)
        return Response(response)


class SysDataView(CommonAPIView):
    service_class = DashboardService

    def get(self, request):
        response = self.get_response_code()
        response['data'] = self.service.get_sys_data_v2(request.GET)
        return Response(response)


class ChartDataView(CommonAPIView):
    service_class = DashboardService

    def get(self, request):
        success, instance = self.service.get_chart_data(request.GET)
        if success:
            response = self.get_response_code()
            response['data'] = instance
        else:
            response = self.get_response_code(code=201, msg=instance)
        return Response(response)


class WorkspaceDataView(CommonAPIView):
    service_class = DashboardService

    def get(self, request):
        response = self.get_response_code()
        response['data'] = self.service.get_ws_data(request.GET)
        return Response(response)


class ProjectJobView(CommonAPIView):
    service_class = DashboardService
    serializer_class = JobTestSerializer
    queryset = TestJob.objects.all()
    permission_classes = []
    order_by = ['-gmt_created']

    def get(self, request):
        success, instance = self.service.get_project_job(self.get_queryset(), request.GET)
        if success:
            response_data = self.get_response_data(instance)
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class ProjectDataView(CommonAPIView):
    service_class = DashboardService

    def get(self, request):
        response = self.get_response_code()
        response['data'] = self.service.get_project_data(request.GET)
        return Response(response)


class WorkspaceChartView(CommonAPIView):
    service_class = DashboardService

    def get(self, request):
        success, instance = self.service.get_ws_chart_data(request.GET)
        if success:
            response_data = self.get_response_code()
            response_data['data'] = instance
        else:
            response_data = self.get_response_code(code=201, msg=instance)
        return Response(response_data)


class WorkspaceListDataView(CommonAPIView):
    service_class = DashboardListService
    serializer_class = JobTestSerializer

    def get(self, request):
        response = self.get_response_code()
        response['data'] = self.service.get_ws_data_list(request.GET)
        return Response(response)
