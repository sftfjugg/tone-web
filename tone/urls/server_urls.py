from django.urls import path

from tone.views.sys import server_views

urlpatterns = [

    path('server_tag/', server_views.ServerTagView.as_view(), name='server_tag'),
    path('server_tag/detail/<int:pk>/', server_views.ServerTagDetailView.as_view(), name='server_tag_detail'),
    path('test_server/', server_views.TestServerView.as_view(), name='test_server'),
    path('specify_test_server/', server_views.SpecifyTestServerView.as_view(), name='specify_test_server'),
    path('test_server/detail/<int:pk>/', server_views.TestServerDetailView.as_view(), name='test_server_detail'),
    path('test_server/deploy/', server_views.TestServerDeployView.as_view(), name='test_server_deploy'),
    path('test_server/update/', server_views.TestServerUpdateView.as_view(), name='test_server_update'),
    path('test_server/update/batch/', server_views.TestServerBatchUpdateView.as_view(),
         name='test_server_batch_update'),
    path('test_server/check/', server_views.TestServerCheckView.as_view(), name='test_server_check'),
    path('test_server/channel/check/', server_views.TestServerChannelCheckView.as_view(), name='channel_server_check'),
    path('test_server/channel/state/', server_views.TestServerChannelStateView.as_view(), name='channel_server_state'),
    path('test_server/group/', server_views.TestServerGroupView.as_view(), name='test_server_group'),
    path('cloud_server/', server_views.CloudServerView.as_view(), name='cloud_server'),
    path('cloud_server/detail/<int:pk>/', server_views.CloudServerDetailView.as_view(), name='cloud_server_detail'),
    path('cloud_server/image/', server_views.CloudServerImageView.as_view(), name='test_server_image'),
    path('cloud_server/instance_type/', server_views.CloudServerInstanceTypeView.as_view(),
         name='test_server_instance'),
    path('cloud_server/aliyun/', server_views.CloudServerInstanceView.as_view(), name='test_server_aliyun'),
    path('cloud_server/region/', server_views.CloudServerRegionView.as_view(), name='test_server_region'),
    path('cloud_server/zone/', server_views.CloudServerZoneView.as_view(), name='test_server_zone'),
    path('cloud_server/disk/categories/', server_views.CloudServerDiskCategoriesView.as_view(),
         name='test_server_disk'),
    path('test_cluster/', server_views.TestClusterView.as_view(), name='test_cluster'),
    path('test_cluster/detail/<int:pk>/', server_views.TestClusterDetailView.as_view(), name='test_cluster_detail'),
    path('test_cluster/cloud_type/<int:pk>/', server_views.TestClusterCloudTypeView.as_view(),
         name='test_cluster_cloud_type'),
    path('test_cluster/test_server/', server_views.TestClusterTestServerView.as_view(),
         name='test_cluster_test_server'),
    path('test_cluster/cloud_server/', server_views.TestClusterCloudServerView.as_view(),
         name='test_cluster_cloud_server'),
    path('test_cluster/test_server/detail/<int:pk>/', server_views.TestClusterTestServerDetailView.as_view(),
         name='cluster_test_server_detail'),
    path('test_cluster/cloud_server/detail/<int:pk>/', server_views.TestClusterCloudServerDetailView.as_view(),
         name='cluster_cloud_server_detail'),
    path('cloud_ak/', server_views.CloudAkView.as_view(), name='cloud_ak'),
    path('cloud_image/', server_views.CloudImageView.as_view(), name='cloud_image'),
    path('check/var_name/', server_views.CheckVarNameView.as_view(), name='check_var_name'),
    path('check/cloud_name/', server_views.CloudServerCheckView.as_view(), name='check_cloud_name'),
    path('toneagent_version/', server_views.ToneAgentVersion.as_view(), name='toneagent_version'),
    path('toneagent_deploy/', server_views.ToneAgentDeploy.as_view(), name='toneagent_deploy'),
    path('del_confirm/', server_views.ServerDelConfirmView.as_view(), name='server_del_confirm'),
    path('sync_vm/', server_views.SyncVmView.as_view(), name='sync_vm_server'),
    path('server_snapshot/', server_views.ServerSnapshotView.as_view(), name='server_snapshot'),

    path('sync_state/', server_views.SyncServerStateView.as_view(), name='sync_state'),
    path('agent_task_info/', server_views.AgentTaskInfoView.as_view(), name='agent_task_info'),
]
