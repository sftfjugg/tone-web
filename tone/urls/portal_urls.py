from django.urls import path

from tone.views.portal import sync_portal_views

urlpatterns = [
    path('sync_suite/', sync_portal_views.SyncPortalSuiteView.as_view(), name='sync_suite'),
    path('sync_job/', sync_portal_views.SyncPortalJobView.as_view(), name='sync_job'),
    path('sync_job_status/', sync_portal_views.SyncPortalJobStatusView.as_view(), name='sync_job_status'),
    path('sync_perf_result/', sync_portal_views.SyncPortalPerfView.as_view(), name='sync_perf'),
    path('sync_func_result/', sync_portal_views.SyncPortalFuncView.as_view(), name='sync_func'),
]
