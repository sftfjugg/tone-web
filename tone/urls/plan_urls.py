# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author:
"""
from django.urls import path

from tone.views.job import plan_views

urlpatterns = [
    # 计划管理
    # 1.计划配置列表
    path('list/', plan_views.PlanListView.as_view(), name='plan_list'),
    # 2.计划详情
    path('detail/', plan_views.PlanDetailView.as_view(), name='plan_detail'),
    # 3.Copy计划
    path('copy/', plan_views.PlanCopyView.as_view(), name='plan_copy'),
    # 4.运行计划
    path('run/', plan_views.PlanRunView.as_view(), name='plan_run'),
    # 计划结果
    path('view/', plan_views.PlanViewView.as_view(), name='plan_view'),
    path('result/', plan_views.PlanResultView.as_view(), name='plan_result'),
    path('result/detail/', plan_views.PlanResultDetailView.as_view(), name='plan_result_detail'),
    # 对比计划
    path('constraint/', plan_views.PlanConstraintView.as_view(), name='plan_constraint'),
    path('check/cron_expression/', plan_views.CheckCronExpressionView.as_view(), name='check_cron_expression'),
    path('manual_create/', plan_views.ManualCreateView.as_view(), name='manual_create_report'),
]
