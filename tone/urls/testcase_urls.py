from django.urls import path

from tone.views.sys import testcase_views

urlpatterns = [

    path('test_case/', testcase_views.TestCaseView.as_view(), name='test_case'),
    path('test_case/detail/<int:pk>/', testcase_views.TestCaseDetailView.as_view(), name='test_case_detail'),
    path('test_case/batch/', testcase_views.TestCaseBatchView.as_view(), name='test_case_batch'),
    path('test_suite/', testcase_views.TestSuiteView.as_view(), name='test_suite'),
    path('test_suite/detail/<int:pk>/', testcase_views.TestSuiteDetailView.as_view(), name='test_suite_detail'),
    path('test_suite/batch/', testcase_views.TestSuiteBatchView.as_view(), name='test_suite_batch'),
    path('test_suite/sync/<int:pk>/', testcase_views.TestSuiteSyncView.as_view(), name='test_suite_sync'),
    path('test_suite/exist/', testcase_views.TestSuiteExistView.as_view(),
         name='test_suite_exist'),
    path('test_metric/', testcase_views.TestMetricView.as_view(), name='test_metric'),
    path('test_metric/<int:pk>/', testcase_views.TestMetricDetailView.as_view(), name='test_metric_detail'),
    path('workspace/case/', testcase_views.WorkspaceCaseView.as_view(), name='workspace_case'),
    path('workspace/has_record/', testcase_views.WorkspaceCaseHasRecordView.as_view(), name='workspace_has_record'),
    path('workspace/case/batch/add/', testcase_views.WorkspaceCaseBatchAddView.as_view(), name='workspace_batch_add'),
    path('workspace/case/batch/del/', testcase_views.WorkspaceCaseBatchDelView.as_view(), name='workspace_batch_del'),
    path('test_domain/', testcase_views.TestDomainView.as_view(), name='test_domain'),
    path('test_metric_list/', testcase_views.TestMetricListView.as_view(), name='test_metric_list'),
    path('workspace/suite/', testcase_views.WorkspaceSuiteView.as_view(), name='workspace_suite'),
    path('test_suite/retrieve/', testcase_views.TestSuiteRetrieveView.as_view(), name='test_suite_retrieve'),
    path('retrieve/quantity/', testcase_views.RetrieveQuantityView.as_view(), name='retrieve_quantity'),
    path('sync_case_to_cache/', testcase_views.SyncCaseToCache.as_view(), name='sync_case_to_cache'),
    path('manual_sync/', testcase_views.ManualSyncCase.as_view(), name='manual_sync'),
    path('last_sync/', testcase_views.LastSyncCase.as_view(), name='last_sync'),
    path('sys_case/confirm/', testcase_views.SysCaseDelView.as_view(), name='sys_case_del'),
    path('ws_case/confirm/', testcase_views.WsCaseDelView.as_view(), name='ws_case_del'),
    path('test_business/', testcase_views.TestBusinessView.as_view(), name='test_business'),
    path('test_business/detail/<int:pk>/', testcase_views.TestBusinessDetailView.as_view(),
         name='test_business_detail'),
    path('business/brief/', testcase_views.BusinessBriefView.as_view(), name='business_brief'),
    path('workspace/business/brief/', testcase_views.WorkspaceBusinessBriefView.as_view(),
         name='workspace_business_brief'),
]
