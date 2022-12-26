from datetime import datetime
from django.db import models
from django_extensions.db.fields import json

from tone.models import BaseModel
from django.forms.models import model_to_dict


class Baseline(BaseModel):
    SERVER_PROVIDER_CHOICES = (
        ('aligroup', '集团内'),
        ('aliyun', '阿里云'),
    )

    TEST_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
    )

    name = models.CharField(max_length=100, db_index=True, help_text='基线名称')
    version = models.CharField(max_length=64, help_text='产品版本')
    description = models.TextField(null=True, blank=True, help_text='基线描述')
    test_type = models.CharField(max_length=64, choices=TEST_TYPE_CHOICES, db_index=True, help_text='测试类型')
    server_provider = models.CharField(max_length=64, choices=SERVER_PROVIDER_CHOICES,
                                       default='aligroup', db_index=True, help_text='机器类型')
    ws_id = models.CharField(null=True, blank=True, max_length=64, db_index=True, help_text='所属Workspace')
    creator = models.IntegerField(help_text='创建者', null=True)
    update_user = models.IntegerField(help_text='修改者', null=True)

    class Meta:
        db_table = 'baseline'

    def to_dict(self):
        job_dict = model_to_dict(self)
        job_dict['gmt_modified'] = datetime.strftime(self.gmt_modified, "%Y-%m-%d %H:%M:%S")
        job_dict['gmt_created'] = datetime.strftime(self.gmt_created, "%Y-%m-%d %H:%M:%S")
        return job_dict


class FuncBaselineDetail(BaseModel):
    baseline_id = models.IntegerField(help_text='基线Id', null=True, blank=True)
    test_job_id = models.IntegerField(help_text='关联JOB ID')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE ID')
    test_case_id = models.IntegerField(db_index=True, help_text='关联CASE ID')
    sub_case_name = models.CharField(max_length=128, help_text='SUB CASE')
    impact_result = models.BooleanField(help_text='是否影响基线')
    bug = models.CharField(max_length=255, null=True, blank=True, help_text='Aone记录')
    description = models.TextField(null=True, blank=True, help_text='问题描述')
    source_job_id = models.IntegerField(null=True, blank=True, help_text='来源job')
    note = models.CharField(max_length=255, null=True, blank=True, help_text='NOTE')
    creator = models.IntegerField(help_text='创建者', null=True)
    update_user = models.IntegerField(help_text='修改者', null=True)

    class Meta:
        db_table = 'func_baseline_detail'


class PerfBaselineDetail(BaseModel):
    RUN_MODE_CHOICES = (
        ('standalone', '单机'),
        ('cluster', '多机')
    )

    baseline_id = models.IntegerField(help_text='基线Id', null=True, blank=True)
    test_job_id = models.IntegerField(help_text='关联JOB ID')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE ID')
    test_case_id = models.IntegerField(db_index=True, help_text='关联CASE ID')
    server_ip = models.CharField(blank=True, help_text='机器IP', max_length=128, null=True)
    server_sn = models.CharField(blank=True, help_text='关联机器SN', max_length=128, null=True)
    # 集团内
    server_sm_name = models.CharField(max_length=128, null=True, blank=True, help_text='机型')
    # 云上
    server_instance_type = models.CharField(max_length=128, null=True, blank=True, help_text='规格')
    server_image = models.CharField(blank=True, default='', max_length=100, help_text='镜像')
    server_bandwidth = models.IntegerField(null=True, blank=True, help_text='带宽')
    run_mode = models.CharField(max_length=64, choices=RUN_MODE_CHOICES, default='standalone', help_text='测试类型')
    source_job_id = models.IntegerField(null=True, blank=True, help_text='来源job')
    metric = models.CharField(max_length=128, help_text='指标')
    test_value = models.CharField(max_length=64, help_text='测试值')
    unit = models.CharField(max_length=64, default='')
    cv_value = models.CharField(max_length=64, help_text='精确值高')
    max_value = models.CharField(max_length=64, help_text='最大值')
    min_value = models.CharField(max_length=64, help_text='最小值')
    value_list = json.JSONField(default=list(), help_text='多次测试值')
    note = models.CharField(max_length=255, null=True, blank=True, help_text='NOTE')
    creator = models.IntegerField(help_text='创建者', null=True)
    update_user = models.IntegerField(help_text='修改者', null=True)

    class Meta:
        db_table = 'perf_baseline_detail'
