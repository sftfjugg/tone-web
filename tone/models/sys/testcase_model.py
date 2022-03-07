from django.db import models

from tone.models.base.base_models import BaseModel


class TestSuite(BaseModel):
    TEST_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
        ('business', '业务测试'),
        ('stability', '稳定性测试')
    )

    RUN_MODE_CHOICES = (
        ('standalone', 'standalone'),
        ('cluster', 'cluster')
    )

    TEST_FRAMEWORK_CHOICES = (
        ('aktf', 'aktf'),
        ('tone', 'tone')
    )

    VIEW_TYPE_CHOICES = (
        ('Type1', '所有指标拆分展示(Type1)'),
        ('Type2', '多Conf同指标合并(Type2)'),
        ('Type3', '单Conf多指标合并(Type3)')
    )

    name = models.CharField(max_length=128, db_index=True, help_text='Suite名称')
    test_type = models.CharField(max_length=64, choices=TEST_TYPE_CHOICES, help_text='测试类型')
    run_mode = models.CharField(max_length=64, choices=RUN_MODE_CHOICES, help_text='运行模式')
    doc = models.TextField(null=True, blank=True, help_text='说明文档')
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='描述')
    owner = models.IntegerField(null=True, help_text='Owner')
    is_default = models.BooleanField(default=False, help_text='是否默认')
    test_framework = models.CharField(max_length=64, choices=TEST_FRAMEWORK_CHOICES, default='tone')
    view_type = models.CharField(max_length=64, choices=VIEW_TYPE_CHOICES, help_text='视图类型', default='Type1')
    certificated = models.BooleanField(default=False, help_text='是否认证')

    class Meta:
        db_table = 'test_suite'


class TestCase(BaseModel):

    name = models.CharField(max_length=255, help_text='Case名称')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联suite')
    repeat = models.IntegerField(help_text='重复次数')
    timeout = models.IntegerField(help_text='超时时间')
    doc = models.TextField(null=True, blank=True, help_text='说明文档')
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='描述')
    var = models.TextField(null=True, help_text='变量')
    is_default = models.BooleanField(default=False, help_text='是否默认')
    short_name = models.CharField(max_length=255, null=True, blank=True, help_text='Case简化名')
    alias = models.CharField(max_length=255, null=True, blank=True, help_text='Case别名')
    certificated = models.BooleanField(default=False, help_text='是否认证')

    class Meta:
        db_table = 'test_case'


class TestMetric(BaseModel):
    OBJECT_TYPE_CHOICES = (
        ('suite', 'Test Suite'),
        ('case', 'Test Case')
    )
    DIRECTION_CHOICES = (
        ('increase', '上升'),
        ('decline', "下降")
    )
    name = models.CharField(db_index=True, max_length=255, help_text='指标名')
    object_type = models.CharField(db_index=True, max_length=64, choices=OBJECT_TYPE_CHOICES, help_text='关联对象类型')
    object_id = models.IntegerField(db_index=True, help_text='关联对象ID')
    cv_threshold = models.FloatField(help_text='变异系数阈值')
    cmp_threshold = models.FloatField(help_text='指标跟基线的对比的阈值')
    direction = models.CharField(db_index=True, max_length=64, choices=DIRECTION_CHOICES, help_text='方向')
    unit = models.CharField(max_length=64, default='')

    class Meta:
        db_table = 'test_track_metric'


class WorkspaceCaseRelation(BaseModel):
    TEST_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
        ('business', '业务测试'),
        ('stability', '稳定性测试')
    )

    test_type = models.CharField(max_length=64, choices=TEST_TYPE_CHOICES, help_text='测试类型')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联Suite')
    test_case_id = models.IntegerField(db_index=True, help_text='关联Case')
    ws_id = models.CharField(max_length=8, db_index=True, help_text='关联Workspace')

    class Meta:
        db_table = 'workspace_case_relation'


class TestDomain(BaseModel):

    name = models.CharField(max_length=64, help_text='name')
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='描述')
    creator = models.IntegerField(help_text='创建者', null=True)
    update_user = models.IntegerField(help_text='修改者', null=True)

    class Meta:
        db_table = 'test_domain'


class DomainRelation(BaseModel):
    OBJECT_TYPE_CHOICES = (
        ('suite', 'Test Suite'),
        ('case', 'Test Case')
    )
    object_type = models.CharField(max_length=64, choices=OBJECT_TYPE_CHOICES, help_text='关联对象类型')
    object_id = models.IntegerField(db_index=True, help_text='关联对象ID')
    domain_id = models.IntegerField(db_index=True, help_text='关联领域ID')

    class Meta:
        db_table = 'domain_relation'


class SuiteData(BaseModel):
    TEST_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
        ('business', '业务测试'),
        ('stability', '稳定性测试')
    )

    TEST_FRAMEWORK_CHOICES = (
        ('aktf', 'aktf'),
        ('tone', 'tone')
    )

    name = models.CharField(max_length=128, db_index=True, help_text='Suite名称')
    test_type = models.CharField(max_length=64, choices=TEST_TYPE_CHOICES, help_text='测试类型')
    test_framework = models.CharField(max_length=64, choices=TEST_FRAMEWORK_CHOICES, default='tone')
    description = models.TextField(null=True, blank=True, help_text='描述文档')

    class Meta:
        db_table = 'suite_data'


class CaseData(BaseModel):

    name = models.CharField(max_length=255, help_text='Case名称')
    suite_id = models.IntegerField(db_index=True, help_text='关联suite')
    description = models.TextField(null=True, blank=True, help_text='描述文档')

    class Meta:
        db_table = 'case_data'


class TestBusiness(BaseModel):
    name = models.CharField(max_length=128, db_index=True, help_text='Business名称')
    description = models.CharField(max_length=1024, null=True, blank=True, help_text='描述')
    creator = models.IntegerField(help_text='创建者', null=True)
    update_user = models.IntegerField(help_text='修改者', null=True)

    class Meta:
        db_table = 'test_business'


class BusinessSuiteRelation(BaseModel):
    business_id = models.IntegerField(db_index=True, help_text='关联业务ID')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联对象ID')

    class Meta:
        db_table = 'business_suite_relation'


class AccessCaseConf(BaseModel):
    test_case_id = models.IntegerField(db_index=True, help_text='关联Case')
    ci_type = models.CharField(max_length=100)
    host = models.CharField(max_length=200, null=True)
    user = models.CharField(max_length=100, null=True)
    token = models.CharField(max_length=100, null=True)
    pipeline_id = models.CharField(max_length=100, null=True)
    project_name = models.CharField(max_length=100, null=True)
    params = models.CharField(max_length=2000, null=True, default=None)

    class Meta:
        db_table = 'access_case_conf'
