"""tone URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os

from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path


from tone.views.sys import main_views

urlpatterns = [
    # include
    path('api/sys/', include('tone.urls.sys_urls'), name='sys'),
    path('api/auth/', include('tone.urls.auth_urls'), name='auth'),
    path('api/case/', include('tone.urls.testcase_urls'), name='case'),
    path('api/server/', include('tone.urls.server_urls'), name='server'),
    path('api/job/', include('tone.urls.job_urls'), name='job'),
    path('api/baseline/', include('tone.urls.baseline_urls'), name='baseline'),
    path('api/portal/', include('tone.urls.portal_urls'), name='portal'),
    path('api/plan/', include('tone.urls.plan_urls'), name='plan'),
    path('api/report/', include('tone.urls.report_urls'), name='report'),
    # api
    path('api/', include('tone.urls.api_urls'), name='sys'),
    # admin
    path('admin/', include('tone.urls.admin_urls'), name='admin'),

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


urlpatterns.append(re_path(r'', main_views.index))
