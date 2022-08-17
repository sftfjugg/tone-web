# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from django.db import models
from django_extensions.db.fields import json

from tone.models.base.base_models import BaseModel


class Report(BaseModel):
    SOURCE_TYPE_CHOICES = (
        ('job', '任务'),
        ('plan', '计划'),
    )
    name = models.CharField(max_length=128, db_index=True, help_text='报告名称')
    product_version = models.CharField(null=True, blank=True, max_length=64, help_text='产品版本')
    project_id = models.IntegerField(null=True, blank=True, help_text='project')
    test_background = models.TextField(null=True, help_text='测试背景')
    test_method = models.TextField(null=True, help_text='测试方法')
    test_conclusion = json.JSONField(default=dict(), help_text='测试结论')
    report_source = models.CharField(max_length=64, choices=SOURCE_TYPE_CHOICES, help_text='报告来源')
    is_automatic = models.BooleanField(default=False, help_text='是否自动生成')
    test_env = json.JSONField(default=dict(), help_text='机器环境信息')
    env_description = models.CharField(max_length=512, null=True, blank=True, help_text='测试环境描述')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    tmpl_id = models.IntegerField(null=True, blank=True, help_text='关联模板')

    creator = models.IntegerField(help_text='创建者')
    ws_id = models.CharField(max_length=64, help_text='workspace id')

    class Meta:
        db_table = 'report'


class ReportItem(BaseModel):
    TEST_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
    )
    name = models.CharField(max_length=128, db_index=True, help_text='测试项名称')
    report_id = models.IntegerField(help_text='关联报告ID')
    test_type = models.CharField(max_length=64, choices=TEST_TYPE_CHOICES, db_index=True, help_text='测试类型')

    class Meta:
        db_table = 'report_item'


class ReportItemSuite(BaseModel):
    SHOW_TYPE_CHOICES = (
        (0, '列表模式'),
        (1, '图表模式type1'),
        (2, '图表模式type2'),
        (3, '图表模式type3'),
    )
    report_item_id = models.IntegerField(help_text='关联测试项ID')
    test_suite_id = models.IntegerField(null=True, blank=True, help_text='suiteID')
    test_suite_name = models.CharField(max_length=256, null=True, blank=True, help_text='suite名字')
    show_type = models.IntegerField(choices=SHOW_TYPE_CHOICES, help_text='显示类型')
    test_suite_description = models.TextField(null=True, help_text='测试工具说明')
    test_env = models.TextField(null=True, help_text='测试环境')
    test_description = models.TextField(null=True, help_text='测试说明')
    test_conclusion = models.TextField(null=True, help_text='测试结论')

    class Meta:
        db_table = 'report_item_suite'


class ReportItemConf(BaseModel):
    report_item_suite_id = models.IntegerField(db_index=True, help_text='关联报告suiteID')
    test_conf_id = models.IntegerField(null=True, blank=True, help_text='confID')
    test_conf_name = models.CharField(max_length=256, null=True, blank=True, help_text='conf名字')
    conf_source = json.JSONField(default=dict(), help_text='conf统计及来源')
    compare_conf_list = json.JSONField(default=list(), help_text='对比conf对应job，用于链接跳转job')

    class Meta:
        db_table = 'report_item_conf'


class ReportItemMetric(BaseModel):
    DIRECTION_CHOICES = (
        ('increase', '上升'),
        ('decline', '下降')
    )
    report_item_conf_id = models.IntegerField(db_index=True, help_text='关联报告confID')
    test_metric = models.CharField(max_length=256, help_text='metric名字')
    test_value = models.CharField(max_length=64, help_text='测试值')
    cv_value = models.CharField(max_length=64, help_text='cv值')
    unit = models.CharField(max_length=64, null=True, blank=True)
    max_value = models.CharField(max_length=64, help_text='最大值')
    min_value = models.CharField(max_length=64, help_text='最小值')
    value_list = json.JSONField(default=list(), help_text='多次测试值')
    direction = models.CharField(max_length=64, choices=DIRECTION_CHOICES, null=True, help_text='期望方向')
    compare_data = json.JSONField(default=list(), help_text='metric对比数据')

    class Meta:
        db_table = 'report_item_metric'


class ReportItemSubCase(BaseModel):
    report_item_conf_id = models.IntegerField(db_index=True, help_text='关联报告confID')
    sub_case_name = models.CharField(max_length=256, help_text='sub_case名字')
    result = models.CharField(null=True, max_length=64, help_text='sub_case结果')
    compare_data = json.JSONField(default=list(), help_text='sub_case对比数据')

    class Meta:
        db_table = 'report_item_sub_case'


class ReportObjectRelation(BaseModel):
    OBJECT_TYPE_CHOICES = (
        ('job', '任务'),
        ('plan', '计划'),
    )
    object_type = models.CharField(max_length=64, choices=OBJECT_TYPE_CHOICES, help_text='关联对象')
    object_id = models.IntegerField(help_text='关联对象ID')
    report_id = models.IntegerField(help_text='关联报告ID')

    class Meta:
        db_table = 'report_object_relation'


class ReportTemplate(BaseModel):
    name = models.CharField(max_length=128, db_index=True, help_text='模板名称')
    is_default = models.BooleanField(default=False, help_text='是否是系统默认')
    need_test_background = models.BooleanField(default=False, help_text='是否需要测试背景')
    background_desc = models.CharField(max_length=128, null=True, blank=True, help_text='测试背景描述')
    need_test_method = models.BooleanField(default=False, help_text='是否需要测试方法')
    test_method_desc = models.CharField(max_length=128, null=True, blank=True, help_text='测试方法描述')
    need_test_summary = models.BooleanField(default=False, help_text='是否需要测试总结')
    test_summary_desc = models.CharField(max_length=128, null=True, blank=True, help_text='测试总结描述')
    need_test_conclusion = models.BooleanField(default=False, help_text='是否需要测试结论')
    test_conclusion_desc = models.CharField(max_length=128, null=True, blank=True, help_text='测试结论描述')
    need_test_env = models.BooleanField(default=False, help_text='是否需要机器环境')
    test_env_desc = models.CharField(max_length=128, null=True, blank=True, help_text='机器环境描述')
    need_env_description = models.BooleanField(default=False, help_text='是否需要测试环境描述')
    env_description_desc = models.CharField(max_length=128, null=True, blank=True, help_text='测试环境描述')
    need_func_data = models.BooleanField(default=False, help_text='是否需要功能测试数据')
    need_perf_data = models.BooleanField(default=False, help_text='是否需要性能能测试数据')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    creator = models.IntegerField(help_text='创建者')
    update_user = models.IntegerField(null=True, help_text='修改者')
    ws_id = models.CharField(null=True, blank=True, max_length=8, db_index=True, help_text='所属Workspace')

    class Meta:
        db_table = 'report_tmpl'


class ReportTmplItem(BaseModel):
    TEST_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
    )
    name = models.CharField(max_length=128, db_index=True, help_text='测试项名称')
    tmpl_id = models.IntegerField(help_text='关联模板ID')
    test_type = models.CharField(max_length=64, choices=TEST_TYPE_CHOICES, db_index=True, help_text='测试类型')

    class Meta:
        db_table = 'report_tmpl_item'


class ReportTmplItemSuite(BaseModel):
    SHOW_TYPE_CHOICES = (
        ('list', '列表模式'),
        ('chart', '图表模式'),
    )
    report_tmpl_item_id = models.IntegerField(help_text='关联测试项ID')
    test_suite_id = models.IntegerField(help_text='关联suiteID')
    test_suite_show_name = models.CharField(max_length=64, null=True, help_text='关联suite显示名')
    test_conf_list = json.JSONField(default=list(), help_text='配置的CONF集')
    show_type = models.CharField(max_length=64, choices=SHOW_TYPE_CHOICES, help_text='显示类型')
    need_test_suite_description = models.BooleanField(default=False, help_text='是否需要测试工具说明')
    need_test_env = models.BooleanField(default=False, help_text='是否需要测试环境')
    test_env_desc = models.CharField(max_length=128, null=True, blank=True, help_text='测试环境描述')
    need_test_description = models.BooleanField(default=False, help_text='是否需要测试说明')
    test_description_desc = models.CharField(max_length=128, null=True, blank=True, help_text='测试说明描述')
    need_test_conclusion = models.BooleanField(default=False, help_text='是否需要测试结论')
    test_conclusion_desc = models.CharField(max_length=128, null=True, blank=True, help_text='测试结论描述')

    class Meta:
        db_table = 'report_tmpl_item_suite'
