from tone.models import TestMetric, TestCase
from tone.services.sys.testcase_services import WorkspaceRetrieveService, WorkspaceCaseRelation, TestMetricService, \
    TestCaseService
from tone.core.utils.helper import CommResp
from tone.core.common.verify_token import token_required
from tone.core.common.expection_handler.error_catch import api_catch_error
from datetime import datetime


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


@api_catch_error
@token_required
def get_suite_increase(request):
    resp = CommResp()
    last_sync_time = request.GET['last_sync_time']
    queryset = TestCase.objects.filter(gmt_modified__gt=datetime.strptime(last_sync_time, '%Y-%m-%d %H:%M:%S')).\
        extra(select={'suite_name': 'test_suite.name',
                      'suite_id': 'test_suite.id',
                      'test_type': 'test_suite.test_type'},
              tables=['test_suite'],
              where=['test_case.test_suite_id = test_suite.id'])
    suite_data_list = [{'case_id': case_info.id, 'case_name': case_info.name, 'suite_id': case_info.suite_id,
                        'suite_name': case_info.suite_name, 'test_type': case_info.test_type}
                       for case_info in queryset]
    queryset_deleted = TestCase.objects. \
        filter(gmt_modified__gt=datetime.strptime(last_sync_time, '%Y-%m-%d %H:%M:%S'), query_scope='deleted'). \
        values_list('id', flat=True)
    resp.data = {'increase': suite_data_list, 'deleted': list(queryset_deleted)}
    return resp.json_resp()
