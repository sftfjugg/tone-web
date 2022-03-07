from django.db import models
from django_extensions.db.fields import json

from tone.models.base.base_models import BaseModel


class FuncResult(BaseModel):
    test_job_id = models.IntegerField(db_index=True, help_text='关联JOB')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE')
    test_case_id = models.IntegerField(db_index=True, help_text='关联CASE')
    sub_case_name = models.CharField(max_length=128, db_index=True, help_text='SUB CASE')
    sub_case_result = models.IntegerField(help_text='SUB CASE结果')
    match_baseline = models.BooleanField(help_text='是否匹配基线')
    bug = models.CharField(max_length=255, null=True, blank=True, help_text='Aone记录')
    description = models.TextField(null=True, blank=True, help_text='基线问题描述')
    note = models.CharField(max_length=255, null=True, blank=True, help_text='结果备注')
    dag_step_id = models.IntegerField(db_index=True, help_text='关联DAG步骤id')

    class Meta:
        db_table = 'func_result'


class PerfResult(BaseModel):
    test_job_id = models.IntegerField(db_index=True, help_text='关联JOB')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE')
    test_case_id = models.IntegerField(db_index=True, help_text='关联CASE')
    metric = models.CharField(max_length=128, db_index=True, help_text='指标')
    test_value = models.CharField(max_length=64, help_text='测试值')
    cv_value = models.CharField(max_length=64, help_text='cv值')
    unit = models.CharField(max_length=64, default='')
    max_value = models.CharField(max_length=64, help_text='最大值')
    min_value = models.CharField(max_length=64, help_text='最小值')
    value_list = json.JSONField(default=list(), help_text='多次测试值')
    repeat = models.IntegerField(help_text='重复次数')
    baseline_value = models.CharField(max_length=64, null=True, blank=True, help_text='基线值')
    baseline_cv_value = models.CharField(max_length=64, null=True, blank=True, help_text='基线cv值')
    compare_result = models.CharField(max_length=64, null=True, blank=True, help_text='对比结果')
    track_result = models.CharField(max_length=64, null=True, blank=True, help_text='跟踪结果')
    match_baseline = models.BooleanField(help_text='是否匹配基线', null=True, blank=True, )
    compare_baseline = models.IntegerField(default=0, help_text='baseline id')
    dag_step_id = models.IntegerField(db_index=True)
    note = models.CharField(max_length=255, null=True, blank=True, help_text='NOTE')

    class Meta:
        db_table = 'perf_result'


class ResultFile(BaseModel):
    test_job_id = models.IntegerField(db_index=True, help_text='关联JOB')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE')
    test_case_id = models.IntegerField(db_index=True, help_text='关联CASE')
    result_path = models.CharField(max_length=512, help_text='结果路径')
    result_file = models.CharField(max_length=512, help_text='结果文件')
    archive_file_id = models.IntegerField(help_text='ARCHIVE ID')

    class Meta:
        db_table = 'result_file'


class ArchiveFile(BaseModel):
    ws_name = models.CharField(max_length=64, db_index=True, help_text='Workspace Name')
    project_name = models.CharField(max_length=64, db_index=True, help_text='Project Name')
    test_plan_id = models.IntegerField(db_index=True, null=True, blank=True, help_text='关联Plan')
    test_job_id = models.IntegerField(db_index=True, help_text='关联JOB')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE')
    test_case_id = models.IntegerField(db_index=True, help_text='关联CASE')
    arch = models.CharField(max_length=64, db_index=True, help_text='ARCH')
    kernel = models.CharField(max_length=64, db_index=True, help_text='内核')
    sn = models.CharField(max_length=64, db_index=True, help_text='SN')
    archive_link = models.CharField(max_length=512, help_text='LINK')
    test_date = models.DateField(auto_now_add=True, help_text='测试日期')

    class Meta:
        db_table = 'archive_file'


class CompareForm(BaseModel):
    req_form = json.JSONField(default=dict(), help_text='请求表单')
    hash_key = models.CharField(max_length=64, db_index=True, help_text='表单数据hash后的值')

    class Meta:
        db_table = 'compare_form'


class BusinessResult(BaseModel):
    test_job_id = models.IntegerField(db_index=True, help_text='关联JOB')
    test_business_id = models.IntegerField(db_index=True, help_text='关联BUSINESS')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE')
    test_case_id = models.IntegerField(db_index=True, help_text='关联CASE')
    link = models.CharField(max_length=255, null=True, blank=True, help_text='ci_project')
    ci_system = models.CharField(max_length=255, null=True, blank=True, help_text='ci_system')
    ci_result = models.CharField(max_length=512, null=True, blank=True, help_text='ci_result')
    ci_detail = models.TextField(null=True, blank=True, help_text='结果详情')
    note = models.CharField(max_length=255, null=True, blank=True, help_text='备注')
    dag_step_id = models.IntegerField(help_text='关联DAG步骤id')

    class Meta:
        db_table = 'business_result'
