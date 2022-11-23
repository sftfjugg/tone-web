from django_extensions.db.fields import json

from tone.models import BaseModel, models, TestServerEnums

TEST_OBJ_CHOICES = (
    ('kernel', '内核'),
    ('rpm', 'RPM包')
)

BLOCKING_STATEGY_CHOICES = (
    (1, '忽略前序计划，直接同时执行'),
    (2, '中止前序运行中计划,再执行'),
    (3, '有前序运行中的计划，忽略本次执行')
)

STATE_CHOICES = (
    ('pending', '队列中'),
    ('running', '运行中'),
    ('success', '已完成'),
    ('fail', '失败'),
    ('stop', '终止'),
)

STAGE_TYPE_CHOICES = (
    ('test_stage', '测试阶段'),
    ('prepare_env', '环境阶段')
)

JOB_STATE_CHOICES = (
    ('pending', '队列中'),
    ('running', '运行中'),
    ('success', '成功'),
    ('fail', '失败'),
    ('stop', '终止'),
    ('skip', '跳过'),
)


class TestPlan(BaseModel):
    name = models.CharField(max_length=128, db_index=True, help_text='计划名称')
    project_id = models.IntegerField(null=True)
    baseline_info = json.JSONField(default=dict(), help_text='基线信息')
    test_obj = models.CharField(max_length=32, choices=TEST_OBJ_CHOICES, default='kernel', help_text='被测对象')
    kernel_version = models.CharField(max_length=64, help_text='内核版本', null=True, blank=True)
    kernel_info = json.JSONField(default=dict(), help_text='内核信息')
    rpm_info = json.JSONField(default=dict(), help_text='RPM信息')
    script_info = json.JSONField(default=list(), help_text='脚本信息')
    build_pkg_info = json.JSONField(default=dict(), help_text='build内核信息')
    env_info = json.JSONField(default=dict(), help_text='环境信息')
    notice_info = json.JSONField(default=dict(), help_text='通知信息')
    cron_schedule = models.BooleanField(default=False, help_text='是否周期触发')
    cron_info = models.CharField(max_length=128, null=True, blank=True, help_text='定时信息')
    blocking_strategy = models.IntegerField(choices=BLOCKING_STATEGY_CHOICES, null=True, blank=True,
                                            help_text='阻塞策略')
    description = models.CharField(max_length=256, null=True, blank=True, help_text='描述信息')
    build_job_id = models.IntegerField(null=True, help_text='build job id')
    ws_id = models.CharField(max_length=8)
    enable = models.BooleanField(default=True, help_text='是否可用')
    creator = models.IntegerField(help_text='创建者')
    update_user = models.IntegerField(help_text='修改者', null=True)
    last_time = models.DateTimeField(null=True, help_text='最后一次运行时间')
    next_time = models.DateTimeField(null=True, help_text='下次运行时间')
    auto_report = models.BooleanField(default=False, null=True, blank=True, help_text='自动生成报告')
    report_name = models.CharField(max_length=128, null=True, blank=True, help_text='报告名称')
    report_tmpl_id = models.IntegerField(null=True, blank=True, help_text='关联模板')
    report_description = models.CharField(max_length=512, null=True, blank=True, help_text='报告描述')
    group_method = models.CharField(max_length=16, null=True, blank=True, help_text='分组方式')
    base_group = models.IntegerField(help_text='基准组', null=True)
    stage_id = models.IntegerField(help_text='基准阶段', null=True)

    class Meta:
        db_table = 'test_plan'


class PlanStageRelation(BaseModel):
    plan_id = models.IntegerField()
    stage_name = models.CharField(max_length=128, help_text='阶段名称')
    stage_index = models.IntegerField(help_text='阶段顺序')
    stage_type = models.CharField(max_length=32, choices=STAGE_TYPE_CHOICES, help_text='阶段类型')
    impact_next = models.BooleanField(default=False, help_text='是否影响后续步骤')

    class Meta:
        db_table = 'plan_stage_relation'


class PlanStageTestRelation(BaseModel):
    plan_id = models.IntegerField()
    run_index = models.IntegerField(help_text='触发顺序')
    stage_id = models.IntegerField()
    tmpl_id = models.IntegerField()

    class Meta:
        db_table = 'plan_stage_test_relation'


class PlanStagePrepareRelation(BaseModel):
    plan_id = models.IntegerField()
    run_index = models.IntegerField()
    stage_id = models.IntegerField()
    prepare_info = json.JSONField(default=dict(), help_text='脚本信息、监控信息等配置')

    class Meta:
        db_table = 'plan_stage_prepare_relation'


class PlanInstance(BaseModel):
    RUN_MODE_CHOICES = (
        ('auto', '自动触发'),
        ('manual', '手动触发'),
    )
    plan_id = models.IntegerField()
    run_mode = models.CharField(max_length=32, choices=RUN_MODE_CHOICES, default='auto')
    state = models.CharField(max_length=32, choices=STATE_CHOICES, default='pending')
    statistics = models.CharField(max_length=32, null=True, blank=True, help_text='统计信息')
    name = models.CharField(max_length=128, db_index=True, help_text='计划名称')
    baseline_info = json.JSONField(default=dict(), help_text='基线信息')
    test_obj = models.CharField(max_length=32, choices=TEST_OBJ_CHOICES, default='kernel', help_text='被测对象')
    kernel_version = models.CharField(max_length=64, help_text='内核版本', null=True, blank=True)
    kernel_info = json.JSONField(default=dict(), help_text='内核信息')
    rpm_info = json.JSONField(default=dict(), help_text='RPM信息')
    script_info = json.JSONField(default=list(), help_text='脚本信息')
    build_pkg_info = json.JSONField(default=dict(), help_text='build内核信息')
    build_job_id = models.IntegerField(null=True, help_text='build job id')
    env_info = json.JSONField(default=dict(), help_text='环境信息')
    notice_info = json.JSONField(default=dict(), help_text='通知信息')
    ws_id = models.CharField(max_length=8)
    project_id = models.IntegerField(null=True)
    creator = models.IntegerField(null=True, blank=True, help_text='创建者')
    start_time = models.DateTimeField(null=True, help_text='开始时间')
    end_time = models.DateTimeField(null=True, help_text='结束时间')
    note = models.CharField(max_length=255, null=True, blank=True, help_text='备注')
    state_desc = models.TextField(null=True, blank=True)
    auto_report = models.BooleanField(default=False, null=True, blank=True, help_text='自动生成报告')
    report_is_saved = models.BooleanField(default=False, help_text='是否已保存报告')
    report_name = models.CharField(max_length=128, null=True, blank=True, help_text='报告名称')
    report_tmpl_id = models.IntegerField(null=True, blank=True, help_text='关联模板')
    report_description = models.CharField(max_length=512, null=True, blank=True, help_text='报告描述')
    group_method = models.CharField(max_length=16, null=True, blank=True, help_text='分组方式')
    base_group = models.IntegerField(help_text='基准组', null=True)
    stage_id = models.IntegerField(help_text='基准阶段', null=True)

    class Meta:
        db_table = 'plan_instance'


class PlanInstanceStageRelation(BaseModel):
    plan_instance_id = models.IntegerField()
    stage_name = models.CharField(max_length=128, help_text='阶段名称')
    stage_index = models.IntegerField(help_text='阶段顺序')
    stage_type = models.CharField(max_length=32, choices=STAGE_TYPE_CHOICES, help_text='阶段类型')
    impact_next = models.BooleanField(default=False, help_text='是否影响后续步骤')

    class Meta:
        db_table = 'plan_instance_stage_relation'


class PlanInstanceTestRelation(BaseModel):
    TEST_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
        ('business', '业务测试'),
        ('stability', '稳定性测试')
    )

    plan_instance_id = models.IntegerField()
    run_index = models.IntegerField(help_text='触发顺序')
    instance_stage_id = models.IntegerField()
    test_type = models.CharField(max_length=64, choices=TEST_TYPE_CHOICES, db_index=True, default='functional',
                                 help_text='测试类型')
    tmpl_id = models.IntegerField()
    job_id = models.IntegerField(null=True, blank=True, help_text='关联的job id')
    state = models.CharField(max_length=64, choices=JOB_STATE_CHOICES, default='pending',
                             db_index=True, help_text='任务状态')
    state_desc = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'plan_instance_test_relation'


class PlanInstancePrepareRelation(BaseModel):
    plan_instance_id = models.IntegerField()
    run_index = models.IntegerField()
    instance_stage_id = models.IntegerField()
    extend_info = json.JSONField(default=dict(), help_text='脚本信息、监控信息等扩展配置')
    channel_type = models.CharField(max_length=64, default='otheragent', null=True, blank=True,
                                    choices=TestServerEnums.SERVER_CHANNEL_TYPE_CHOICES, help_text='通道类型')
    ip = models.CharField(max_length=64, help_text='IP', null=True, blank=True)
    sn = models.CharField(max_length=64, help_text='SN', null=True, blank=True)
    script_info = models.TextField(null=True, blank=True, help_text='脚本信息')
    tid = models.CharField(max_length=64, null=True, blank=True, help_text='TICKET ID')
    state = models.CharField(max_length=32, choices=STATE_CHOICES, default='pending')
    result = models.TextField(null=True, blank=True, help_text='脚本结果')
    state_desc = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'plan_instance_prepare_relation'
