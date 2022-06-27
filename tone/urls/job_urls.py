# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from django.urls import path

from tone.views.job import type_view, test_view, tag_view, template_view, result_analysis, result_compare, \
    offline_data_view

urlpatterns = [
    # JobType
    path('type/', type_view.JobTypeView.as_view(), name='job_type'),
    path('items/', type_view.JobTypeItemView.as_view(), name='job_items'),
    path('relation/', type_view.JobTypeItemRelationView.as_view(), name='job_items_relation'),

    path('test/', test_view.JobTestView.as_view(), name='job_test'),
    path('test/summary/', test_view.JobTestSummaryView.as_view(), name='job_test_summary'),
    path('test/result/', test_view.JobTestResultView.as_view(), name='job_test_result'),
    path('test/conf/result/', test_view.JobTestConfResultView.as_view(), name='conf_result'),
    path('test/case/result/', test_view.JobTestCaseResultView.as_view(), name='case_result'),
    path('test/case/performance/result/', test_view.JobTestCasePerResultView.as_view(), name='performance_case_result'),
    path('test/case/version/', test_view.JobTestCaseVersionView.as_view(), name='case_version'),
    path('test/case/file/', test_view.JobTestCaseFileView.as_view(), name='case_file'),
    path('test/config/', test_view.JobTestConfigView.as_view(), name='job_test_config'),
    path('test/process/build/', test_view.JobTestBuildView.as_view(), name='job_test_build_package'),
    path('test/process/prepare/', test_view.JobTestPrepareView.as_view(), name='job_test_process_prepare'),
    path('test/process/suite/', test_view.JobTestProcessSuiteView.as_view(), name='job_test_process_suite'),
    path('test/process/case/', test_view.JobTestProcessCaseView.as_view(), name='job_test_process_case'),
    path('test/process/monitor/job/', test_view.JobTestProcessMonitorJobView.as_view(),
         name='job_test_process_monitor'),
    path('test/editor/note/', test_view.EditorNoteView.as_view(), name='editor_note'),
    path('test/editor/state/', test_view.EditorStateView.as_view(), name='editor_state'),
    path('collection/', test_view.JobCollectionView.as_view(), name='collection job'),
    path('tag/', tag_view.JobTagView.as_view(), name='job_tag'),
    path('tag/relation/', tag_view.JobTagRelationView.as_view(), name='job_tag_relation'),
    path('template/', template_view.TestTemplateView.as_view(), name='template'),
    path('template/detail/', template_view.TestTemplateDetailView.as_view(), name='template_detail'),
    path('template/items/', template_view.TemplateItemsView.as_view(), name='template_items'),
    path('template/copy/', template_view.TemplateCopyView.as_view(), name='template_copy'),
    path('test/job-monitor-item/', test_view.JobMonitorItemView.as_view(), name='job_monitor_item'),
    path('yaml_data_verify/', test_view.YamlDataVerify.as_view(), name='yaml_data_verify'),
    path('data_conversion/', test_view.DataConversion.as_view(), name='data_conversion'),
    path('test_server/machine_fault/', test_view.MachineFaultView.as_view(), name='check_machine_fault'),

    # Analysis
    path('result/perf/analysis/', result_analysis.PerfAnalysisView.as_view(), name='perf_analysis'),
    path('result/func/analysis/', result_analysis.FuncAnalysisView.as_view(), name='func_analysis'),
    path('result/compare/suite/', result_compare.CompareSuiteInfoView.as_view(), name='suite_info'),
    path('result/compare/info/', result_compare.CompareEnvInfoView.as_view(), name='compare_info'),
    path('result/compare/list/', result_compare.CompareListView.as_view(), name='compare_list'),
    path('result/compare/chart/', result_compare.CompareChartView.as_view(), name='compare_chart'),
    path('result/compare/form/', result_compare.CompareFormView.as_view(), name='compare_form'),

    path('type/del/', type_view.JobTypeDelView.as_view(), name='job_type_del'),
    path('template/del/', template_view.TemplateDelView.as_view(), name='template_del'),

    path('test/upload/offline/', offline_data_view.OfflineDataView.as_view(), name='offline_upload'),

]
