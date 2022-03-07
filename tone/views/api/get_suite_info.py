from tone.models import TestMetric, TestCase
from tone.services.sys.testcase_services import WorkspaceRetrieveService, WorkspaceCaseRelation, TestMetricService, \
    TestCaseService
from tone.core.utils.helper import CommResp
from tone.core.common.verify_token import token_required
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.error_catch import api_catch_error


@api_catch_error
@token_required
def get_suite_list(request):
    resp = CommResp()
    serialize_flag, queryset = WorkspaceRetrieveService.filter(WorkspaceCaseRelation.objects.all(), request.GET)
    resp.data = queryset
    return resp.json_resp()


@api_catch_error
@token_required
def get_case_list(request):
    resp = CommResp()
    queryset = TestCaseService.filter(TestCase.objects.all(), request.GET)
    case_data_list = [{'id': case_info.id, 'name': case_info.name,
                       'metric_count': TestMetric.objects.filter(object_type='case', object_id=case_info.id).count()}
                      for case_info in queryset]
    resp.data = case_data_list
    return resp.json_resp()


@api_catch_error
@token_required
def get_metric_list(request):
    resp = CommResp()
    queryset = TestMetricService.filter(TestMetric.objects.all(), request.GET)
    metric_data_list = [{'id': metric.id, 'name': metric.name} for metric in queryset]
    resp.data = metric_data_list
    return resp.json_resp()
