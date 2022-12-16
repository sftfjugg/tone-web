from django.urls import path

from tone.views.api.views import TestAPIView
from tone.views.api import create_job, query_job, rerun_config, create_build, get_oss_url, get_product_version, \
    get_analytics_tags, append_item, get_suite_info, add_server
from tone.views.sys import admin_views

urlpatterns = [
    path('migrate/', admin_views.migrate),
    path('init_data/', admin_views.init_data),
    path('create_superuser/', admin_views.create_superuser),

]
