from django.urls import path

from tone.views.api.views import TestAPIView
from tone.views.api import create_job, query_job, rerun_config, create_build, get_oss_url, get_product_version, \
    get_analytics_tags, append_item, get_suite_info

urlpatterns = [
    path('job', TestAPIView.as_view()),
    path('job/create/', create_job.job_create, name='job_create'),
    path('job/query/', query_job.job_query, name='job_query'),
    path('rerun/config/', rerun_config.config_query, name='config_query'),
    path('create/build/info/', create_build.create_build_info, name='create_build'),
    path('get/oss/url/', get_oss_url.get_path, name='get_oss_url'),
    path('get/product/version/', get_product_version.get_product_version, name='get_product_version'),
    path('get/analytics/tags/', get_analytics_tags.get_analytics_tags, name='get_analytics_tags'),
    path('append/item/', append_item.add_item, name='append_item'),
    path('case/get_suite_list/', get_suite_info.get_suite_list, name='suite_list'),
    path('case/get_case_list/', get_suite_info.get_case_list, name='case_list'),
    path('case/get_metric_list/', get_suite_info.get_metric_list, name='metric_list'),
    path('case/get_suite_all/', get_suite_info.get_metric_list, name='suite_all'),
]
