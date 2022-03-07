from django.urls import path

from tone.views.sys import workspace_views, log_views, kernel_views, product_views, base_config_views, \
    interface_token_view, help_doc_views, dashboard_views

urlpatterns = [
    # ws
    path('workspace/', workspace_views.WorkspaceView.as_view(), name='workspace'),
    path('workspace/list/', workspace_views.WorkspaceListView.as_view(), name='workspace_list'),
    path('workspace/all/list/', workspace_views.AllWorkspaceView.as_view(), name='workspace_all_list'),
    path('workspace/list_select/', workspace_views.WorkspaceListSelectView.as_view(), name='workspace_list'),
    path('workspace/history/', workspace_views.WorkspaceHistoryView.as_view(), name='workspace_history'),
    path('workspace/detail/<str:id>/', workspace_views.WorkspaceDetailView.as_view(), name='workspace_detail'),
    path('workspace/member/', workspace_views.WorkspaceMemberView.as_view(), name='workspace_member'),
    path('workspace/member/apply/', workspace_views.WorkspaceMemberApplyView.as_view(), name='workspace_member_apply'),

    path('workspace/quantity/', workspace_views.WorkspaceQuantityView.as_view(), name='workspace_quantity'),
    path('workspace/member/quantity/', workspace_views.MemberQuantityView.as_view(), name='workspace_member_quantity'),

    path('approve/', workspace_views.ApproveView.as_view(), name='approve'),
    path('approve/detail/<int:pk>/', workspace_views.ApproveDetailView.as_view(), name='approve_detail'),
    path('approve/quantity/', workspace_views.ApproveQuantityView.as_view(), name='approve_quantity'),

    path('upload/', workspace_views.UploadView.as_view(), name='upload'),
    path('operation/log/', log_views.OperationLogsView.as_view(), name='log'),

    # kernel
    path('kernel/', kernel_views.KernelView.as_view(), name='kernel_info'),
    path('config/', base_config_views.BaseConfigView.as_view(), name='base_config'),
    path('config/history/', base_config_views.BaseConfigHistoryView.as_view(), name='base_config_history'),
    path('product/', product_views.ProductView.as_view(), name='product_views'),
    path('project/', product_views.ProjectView.as_view(), name='project_views'),
    path('product/drag/', product_views.ProductDragView.as_view(), name='product_drag_views'),
    path('project/drag/', product_views.ProjectDragView.as_view(), name='project_drag_views'),
    path('repository/', product_views.RepositoryView.as_view(), name='repository'),
    path('branch/', product_views.CodeBranchView.as_view(), name='branch'),
    path('branch/relation/', product_views.ProjectBranchView.as_view(), name='branch_relation'),
    path('check/gitlab/', product_views.CheckGitLabView.as_view(), name='gitlab'),
    path('sync_kernel/', kernel_views.SyncKernelView.as_view(), name='sync_kernel'),

    # token
    path('token/', interface_token_view.InterfaceTokenView.as_view(), name='token'),
    path('help_doc/', help_doc_views.HelpDocView.as_view(), name='help_doc'),
    path('test_farm/', help_doc_views.TestFarmView.as_view(), name='test_farm'),
    path('push_config/', help_doc_views.PushConfigView.as_view(), name='push_config'),
    path('portal_test/', help_doc_views.PortalTestView.as_view(), name='portal_test'),
    path('project/list/', help_doc_views.ProjectListView.as_view(), name='project_list'),
    path('comment/', help_doc_views.CommentView.as_view(), name='comment'),
    path('push_job/', help_doc_views.PushJobView.as_view(), name='push_job'),
    path('ws_config/', help_doc_views.WorkspaceConfigView.as_view(), name='workspace_config'),
    path('live_data/', dashboard_views.LiveDataView.as_view(), name='live_data'),
    path('sys_data/', dashboard_views.SysDataView.as_view(), name='sys_data'),
    path('chart_data/', dashboard_views.ChartDataView.as_view(), name='chart_data'),
    path('ws_data/', dashboard_views.WorkspaceDataView.as_view(), name='workspace_data'),
    path('ws_project_job/', dashboard_views.ProjectJobView.as_view(), name='product_job'),
    path('ws_project_data/', dashboard_views.ProjectDataView.as_view(), name='product_data'),
    path('ws_chart/', dashboard_views.WorkspaceChartView.as_view(), name='workspace_chart'),
    path('workspace/check/', workspace_views.WorkspaceCheckView.as_view(), name='workspace_check'),
    path('ws_data_list/', dashboard_views.WorkspaceListDataView.as_view(), name='workspace_data_list'),
]
