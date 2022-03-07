from tone.core.common.views import BaseView
from rest_framework.response import Response
from tone.services.portal.sync_portal_services import SyncPortalService


class SyncPortalSuiteView(BaseView):
    service_class = SyncPortalService

    def get(self, request):
        code, msg = self.service.sync_case_meta(request.GET['is_all'])
        response_data = self.get_response_code()
        response_data['code'] = code
        response_data['msg'] = msg
        return Response(response_data)


class SyncPortalJobView(BaseView):
    service_class = SyncPortalService

    def get(self, request):
        code, msg = self.service.sync_job(request.GET['test_job_id'])
        response_data = self.get_response_code()
        response_data['code'] = code
        response_data['msg'] = msg
        return Response(response_data)


class SyncPortalJobStatusView(BaseView):
    service_class = SyncPortalService

    def get(self, request):
        code, msg = self.service.sync_job_status(request.GET['test_job_id'], request.GET['state'])
        response_data = self.get_response_code()
        response_data['code'] = code
        response_data['msg'] = msg
        return Response(response_data)


class SyncPortalPerfView(BaseView):
    service_class = SyncPortalService

    def get(self, request):
        code, msg = self.service.sync_perf_result(request.GET['test_job_id'])
        response_data = self.get_response_code()
        response_data['code'] = code
        response_data['msg'] = msg
        return Response(response_data)


class SyncPortalFuncView(BaseView):
    service_class = SyncPortalService

    def get(self, request):
        code, msg = self.service.sync_func_result(request.GET['test_job_id'])
        response_data = self.get_response_code()
        response_data['code'] = code
        response_data['msg'] = msg
        return Response(response_data)