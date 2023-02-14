from datetime import datetime

from django.db import models
from django_extensions.db.fields import json
from django.forms.models import model_to_dict
from tone.models.sys.workspace_models import Project, Product
from tone.models.sys.auth_models import User
from tone.models.report.test_report import Report, ReportObjectRelation
from tone.models.sys.server_models import TestServerSnapshot, CloudServerSnapshot

from tone.models.base.base_models import BaseModel


class TestJob(BaseModel):
    JOB_STATE_CHOICES = (
        ('pending', '队列中'),
        ('running', '运行中'),
        ('success', '成功'),
        ('fail', '失败'),
        ('stop', '终止'),
        ('skip', '跳过'),
    )

    SERVER_PROVIDER_CHOICES = (
        ('aligroup', '集团内'),
        ('aliyun', '阿里云'),
    )

    JOB_CREATED_FROM_CHOICES = (
        ('web', '页面创建'),
        ('api', 'API创建'),
        ('schedule', '定时创建'),
        ('offline', '离线上传'),
    )

    TEST_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
        ('business', '业务测试'),
        ('stability', '稳定性测试')
    )

    name = models.CharField(max_length=100, db_index=True, help_text='任务名称')
    state = models.CharField(max_length=64, choices=JOB_STATE_CHOICES, default='pending',
                             db_index=True, help_text='任务状态')
    job_type_id = models.IntegerField(help_text='job类型')
    project_id = models.IntegerField(help_text='project', db_index=True, null=True, blank=True)
    product_id = models.IntegerField(help_text='product', null=True, blank=True)
    product_version = models.TextField(help_text='product_version', null=True, blank=True)
    baseline_id = models.IntegerField(help_text='基线', null=True, blank=True)
    baseline_job_id = models.IntegerField(help_text='基线Job', null=True, blank=True)
    test_type = models.CharField(max_length=64, choices=TEST_TYPE_CHOICES, default='functional', db_index=True,
                                 help_text='测试类型')
    iclone_info = json.JSONField(default=dict(), null=True, blank=True, help_text='重装信息')
    build_pkg_info = json.JSONField(default=dict(), null=True, blank=True, help_text='build内核信息')
    kernel_info = json.JSONField(default=dict(), null=True, blank=True, help_text='内核信息')
    need_reboot = models.BooleanField(help_text='是否需要重启', default=False)
    rpm_info = json.JSONField(default=list(), null=True, blank=True, help_text='RPM信息')
    script_info = json.JSONField(default=list(), help_text='脚本信息')
    monitor_info = json.JSONField(default=list(), help_text='监控信息')
    cleanup_info = models.TextField(null=True, blank=True, help_text='清理脚本')
    notice_info = json.JSONField(default=dict(), help_text='通知信息')
    console = models.BooleanField(default=False, help_text='console')
    kernel_version = models.CharField(max_length=128, null=True, blank=True, help_text='内核版本')
    show_kernel_version = models.CharField(max_length=128, null=True, blank=True, help_text='显示内核版本')
    env_info = json.JSONField(default=dict(), help_text='变量信息')
    creator = models.IntegerField(help_text='创建者')
    tmpl_id = models.IntegerField(null=True, blank=True, help_text='关联模板')
    plan_id = models.IntegerField(null=True, blank=True, help_text='关联计划')
    report_name = models.CharField(max_length=256, null=True, blank=True, help_text='模板名字')
    callback_api = models.CharField(max_length=256, null=True, blank=True, help_text='回调接口')
    report_template_id = models.IntegerField(null=True, blank=True, help_text='关联报告模板')
    report_is_saved = models.BooleanField(default=False, help_text='是否已保存报告')
    source_job_id = models.IntegerField(null=True, blank=True, help_text='来源任务')
    server_provider = models.CharField(max_length=64, choices=SERVER_PROVIDER_CHOICES,
                                       default='aligroup', db_index=True, help_text='机器类型')
    created_from = models.CharField(max_length=64, choices=JOB_CREATED_FROM_CHOICES,
                                    default='web', db_index=True, help_text='创建类型')
    ws_id = models.CharField(max_length=64, help_text='workspace id')
    note = models.TextField(null=True, blank=True, help_text='NOTE')
    test_result = models.CharField(max_length=64, null=True, blank=True, help_text='结果统计')
    state_desc = models.TextField(null=True, blank=True)
    build_job_id = models.IntegerField(null=True, help_text='build job id')
    start_time = models.DateTimeField(null=True, help_text='开始时间')
    end_time = models.DateTimeField(null=True, help_text='结束时间')
    sync_time = models.DateTimeField(null=True, db_index=True, help_text='同步时间')

    def to_dict(self):
        job_dict = model_to_dict(self)
        job_dict['gmt_modified'] = datetime.strftime(self.gmt_modified, "%Y-%m-%d %H:%M:%S")
        job_dict['gmt_created'] = datetime.strftime(self.gmt_created, "%Y-%m-%d %H:%M:%S")
        return job_dict

    @property
    def project_name(self):
        project_name = None
        if self.project_id and Project.objects.filter(id=self.project_id).exists():
            project_name = Project.objects.get(id=self.project_id).name
        return project_name

    @property
    def creator_name(self):
        creator_name = None
        creator = User.objects.filter(id=self.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @property
    def report_li(self):
        report_li = []
        report_id_list = ReportObjectRelation.objects.filter(object_type='job',
                                                             object_id=self.id).values_list('report_id')
        if report_id_list:
            report_queryset = Report.objects.filter(id__in=report_id_list)
            report_li = [{
                'id': report.id,
                'name': report.name,
                'creator': report.creator,
                'creator_name': self.creator_name,
                'gmt_created': datetime.strftime(report.gmt_created, "%Y-%m-%d %H:%M:%S"),
            } for report in report_queryset]
        return report_li

    @property
    def product_name(self):
        return Product.objects.get(id=self.product_id).name

    @property
    def server(self):
        server = None
        if self.server_provider == 'aligroup':
            if TestServerSnapshot.objects.filter(job_id=self.id).count() == 1:
                server = TestServerSnapshot.objects.get(job_id=self.id).ip
        else:
            if CloudServerSnapshot.objects.filter(job_id=self.id).count() == 1:
                server = CloudServerSnapshot.objects.get(job_id=self.id).private_ip
        return server

    @property
    def collection(self):
        return False

    class Meta:
        db_table = 'test_job'


class TestJobCase(BaseModel):
    JOB_TEST_CASE_CHOICES = (
        ('pending', '初始化'),
        ('running', '运行中'),
        ('success', '成功'),
        ('fail', '失败'),
        ('skip', '跳过'),
        ('stop', '终止')
    )

    RUN_MODE_CHOICES = (
        ('standalone', '单机'),
        ('cluster', '多机')
    )
    SERVER_PROVIDER = (
        ('aligroup', '集团内部'),
        ('aliyun', '阿里云')
    )
    job_id = models.IntegerField(help_text='关联JOB ID', db_index=True)
    state = models.CharField(max_length=64, db_index=True, default='pending',
                             choices=JOB_TEST_CASE_CHOICES, help_text='状态')
    test_case_id = models.IntegerField(db_index=True, help_text='关联CASE ID')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE ID')
    run_mode = models.CharField(max_length=64, choices=RUN_MODE_CHOICES, default='standalone', help_text='测试类型')
    server_provider = models.CharField(max_length=64, choices=SERVER_PROVIDER, default='aligroup')
    repeat = models.IntegerField(default=1, help_text='重复次数')
    server_object_id = models.IntegerField(null=True, blank=True, help_text='机器id')
    server_tag_id = models.CharField(null=True, blank=True, max_length=256, help_text='机器标签id字符串')
    env_info = json.JSONField(default=dict(), help_text='变量信息')
    need_reboot = models.BooleanField(help_text='是否需要重启', default=False)
    setup_info = models.TextField(null=True, blank=True, help_text='初始脚本')
    cleanup_info = models.TextField(null=True, blank=True, help_text='清理脚本')
    console = models.BooleanField(default=False, help_text='console')
    monitor_info = json.JSONField(default=list(), help_text='监控信息')
    priority = models.IntegerField(default=10, help_text='优先级')
    note = models.CharField(max_length=255, null=True, blank=True, help_text='NOTE')
    analysis_note = models.CharField(max_length=255, null=True, blank=True, help_text='NOTE')
    server_snapshot_id = models.IntegerField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, help_text='结束时间')
    end_time = models.DateTimeField(null=True, help_text='结束时间')

    class Meta:
        db_table = 'test_job_case'


class TestJobSuite(BaseModel):
    JOB_TEST_CASE_CHOICES = (
        ('pending', '初始化'),
        ('running', '运行中'),
        ('success', '成功'),
        ('fail', '失败'),
        ('skip', '跳过'),
        ('stop', '终止')
    )

    RUN_MODE_CHOICES = (
        ('standalone', '单机'),
        ('cluster', '多机')
    )
    SERVER_PROVIDER = (
        ('aligroup', '集团内部'),
        ('aliyun', '阿里云')
    )
    job_id = models.IntegerField(help_text='关联JOB ID')
    state = models.CharField(max_length=64, db_index=True, default='pending',
                             choices=JOB_TEST_CASE_CHOICES, help_text='状态')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE ID')
    need_reboot = models.BooleanField(help_text='是否需要重启', default=False)
    setup_info = models.TextField(null=True, blank=True, help_text='初始脚本')
    cleanup_info = models.TextField(null=True, blank=True, help_text='清理脚本')
    console = models.BooleanField(default=False, help_text='console')
    monitor_info = json.JSONField(default=list(), help_text='监控信息')
    priority = models.IntegerField(default=10, help_text='优先级')
    note = models.CharField(max_length=255, null=True, blank=True, help_text='NOTE')
    start_time = models.DateTimeField(null=True, help_text='结束时间')
    end_time = models.DateTimeField(null=True, help_text='结束时间')

    class Meta:
        db_table = 'test_job_suite'


class TestTemplate(BaseModel):
    SERVER_PROVIDER_CHOICES = (
        ('aligroup', '集团内部'),
        ('aliyun', '阿里云')
    )

    name = models.CharField(max_length=128, db_index=True, help_text='模板名称')
    schedule_info = json.JSONField(default=dict(), help_text='定时配置')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    job_name = models.CharField(max_length=256, db_index=True, null=True, blank=True, help_text='Job名称')
    job_type_id = models.IntegerField(null=True, blank=True, help_text='job类型')
    project_id = models.IntegerField(null=True, blank=True, help_text='project')
    product_id = models.IntegerField(null=True, blank=True, help_text='product')
    baseline_id = models.IntegerField(help_text='基线', null=True, blank=True)
    baseline_job_id = models.IntegerField(help_text='基线Job', null=True, blank=True)
    iclone_info = json.JSONField(default=dict(), null=True, blank=True, help_text='重装信息')
    kernel_info = json.JSONField(default=dict(), null=True, blank=True, help_text='内核信息')
    build_pkg_info = json.JSONField(default=dict(), null=True, blank=True, help_text='build内核信息')
    need_reboot = models.BooleanField(help_text='是否需要重启', default=False)
    rpm_info = json.JSONField(default=list(), null=True, blank=True, help_text='RPM信息')
    script_info = json.JSONField(default=list(), help_text='脚本信息')
    monitor_info = json.JSONField(default=list(), help_text='监控信息')
    cleanup_info = models.TextField(null=True, blank=True, help_text='清理脚本')
    notice_info = json.JSONField(default=dict(), help_text='通知信息')
    console = models.BooleanField(default=False, help_text='console')
    kernel_version = models.CharField(max_length=128, null=True, blank=True, help_text='内核版本')
    callback_api = models.CharField(max_length=256, null=True, blank=True, help_text='回调接口')
    report_name = models.CharField(max_length=256, null=True, blank=True, help_text='模板名字')
    report_template_id = models.IntegerField(null=True, blank=True, help_text='关联报告模板')
    env_info = json.JSONField(default=dict(), help_text='变量信息')
    enable = models.BooleanField(default=True, help_text='使用状态')
    server_provider = models.CharField(max_length=64, choices=SERVER_PROVIDER_CHOICES, default='aligroup')

    creator = models.IntegerField(help_text='创建者')
    update_user = models.IntegerField(help_text='修改者', null=True)
    ws_id = models.CharField(null=True, blank=True, max_length=8, db_index=True, help_text='所属Workspace')

    class Meta:
        db_table = 'test_tmpl'


class TestTmplCase(BaseModel):
    RUN_MODE_CHOICES = (
        ('standalone', '单机'),
        ('cluster', '多机')
    )
    SERVER_PROVIDER = (
        ('aligroup', '集团内部'),
        ('aliyun', '阿里云')
    )

    tmpl_id = models.IntegerField(help_text='关联模板ID')
    test_case_id = models.IntegerField(db_index=True, help_text='关联CASE ID')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE ID')
    run_mode = models.CharField(max_length=64, choices=RUN_MODE_CHOICES, default='standalone', help_text='测试类型')
    server_provider = models.CharField(max_length=64, choices=SERVER_PROVIDER, default='aligroup')
    repeat = models.IntegerField(default=1, help_text='重复次数')
    custom_ip = models.CharField(max_length=64, null=True, blank=True, help_text='自定义机器IP')
    custom_sn = models.CharField(max_length=64, null=True, blank=True, help_text='自定义机器SN')
    custom_channel = models.CharField(max_length=64, null=True, blank=True,
                                      default='tone-agent', help_text='agent类型')
    server_object_id = models.IntegerField(null=True, blank=True, help_text='机器id')
    server_tag_id = models.CharField(null=True, blank=True, max_length=256, help_text='机器标签id字符串')
    env_info = json.JSONField(default=dict(), help_text='变量信息')
    need_reboot = models.BooleanField(help_text='是否需要重启', default=False)
    setup_info = models.TextField(null=True, blank=True, help_text='初始脚本')
    cleanup_info = models.TextField(null=True, blank=True, help_text='清理脚本')
    console = models.BooleanField(default=False, help_text='console')
    monitor_info = json.JSONField(default=list(), help_text='监控信息')
    priority = models.IntegerField(default=10, help_text='优先级')
    server_snapshot_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = 'test_tmpl_case'


class TestTmplSuite(BaseModel):
    JOB_TEST_CASE_CHOICES = (
        ('pending', '初始化'),
        ('running', '运行中'),
        ('success', '成功'),
        ('fail', '失败')
    )

    RUN_MODE_CHOICES = (
        ('standalone', '单机'),
        ('cluster', '多机')
    )
    SERVER_PROVIDER = (
        ('aligroup', '集团内部'),
        ('aliyun', '阿里云')
    )
    tmpl_id = models.IntegerField(help_text='关联JOB ID')
    test_suite_id = models.IntegerField(db_index=True, help_text='关联SUITE ID')
    need_reboot = models.BooleanField(help_text='是否需要重启', default=False)
    setup_info = models.TextField(null=True, blank=True, help_text='初始脚本')
    cleanup_info = models.TextField(null=True, blank=True, help_text='清理脚本')
    console = models.BooleanField(default=False, help_text='console')
    monitor_info = json.JSONField(default=list(), help_text='监控信息')
    priority = models.IntegerField(default=10, help_text='优先级')

    class Meta:
        db_table = 'test_tmpl_suite'


class TestStep(BaseModel):
    STEP_STATE_CHOICES = (
        ('running', '运行中'),
        ('skip', '已跳过'),
        ('stop', '已停止'),
        ('success', '成功'),
        ('fail', '失败')
    )

    STEP_STAGE_CHOICES = (
        ('initcloud', '机器初始化'),
        ('待补充..', '...')
    )

    job_id = models.IntegerField(db_index=True, help_text='所属JOB')
    tid = models.CharField(max_length=1000, help_text='TICKET ID')
    state = models.CharField(max_length=64, choices=STEP_STATE_CHOICES, db_index=True, help_text='状态')
    stage = models.CharField(max_length=64, choices=STEP_STAGE_CHOICES, db_index=True, help_text='步骤')
    job_case_id = models.IntegerField(db_index=True, help_text='关联CASE')
    job_suite_id = models.IntegerField(db_index=True, default=0, help_text='关联SUITE')
    dag_step_id = models.IntegerField(db_index=True, help_text='关联dag步骤id')
    server = models.CharField(max_length=64, null=True, blank=True, help_text='server info')
    cluster_id = models.IntegerField(db_index=True, default=0, help_text='关联集群id')
    result = models.TextField(null=True, blank=True, help_text='结果')
    log_file = models.CharField(max_length=512, null=True, blank=True, help_text='日志文件')

    class Meta:
        db_table = 'test_step'


class JobType(BaseModel):
    SERVER_TYPE_CHOICES = (
        ('aligroup', '集团内'),
        ('aliyun', '阿里云'),
    )

    TEST_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
        ('business', '业务测试'),
        ('stability', '稳定性测试')
    )
    BUSINESS_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
        ('business', '接入测试'),
    )
    name = models.CharField(max_length=64, db_index=True, help_text='JobType名称')
    enable = models.BooleanField(default=True, help_text='JobType使用状态')
    is_default = models.BooleanField(default=False, help_text='是否是系统默认')
    test_type = models.CharField(max_length=64, choices=TEST_TYPE_CHOICES, db_index=True, help_text='测试类型')
    business_type = models.CharField(max_length=64, null=True,
                                     choices=BUSINESS_TYPE_CHOICES, help_text='业务测试类型')
    server_type = models.CharField(max_length=64, choices=SERVER_TYPE_CHOICES, db_index=True, help_text='机器类型')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    creator = models.IntegerField(help_text='创建者')
    ws_id = models.CharField(max_length=64, db_index=True, help_text='Workspace ID')
    priority = models.IntegerField(default=1)
    is_first = models.BooleanField(default=False, help_text='是否作为默认显示')

    class Meta:
        unique_together = ('name', 'ws_id',)
        db_table = 'job_type'


class JobTypeItem(BaseModel):
    name = models.CharField(max_length=64, db_index=True, help_text='名称')
    show_name = models.CharField(max_length=64, db_index=True, help_text='显示名称')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    config_index = models.IntegerField(help_text='配置类型')

    class Meta:
        unique_together = ('show_name', 'config_index',)
        db_table = 'job_type_item'


class JobTypeItemRelation(BaseModel):
    job_type_id = models.IntegerField(help_text='job类型id')
    item_id = models.IntegerField(help_text='job表单配置元素id')
    item_show_name = models.CharField(max_length=64, db_index=True, help_text='Item显示名称')
    item_alias = models.CharField(max_length=64, blank=True, db_index=True, help_text='Item别名')

    class Meta:
        db_table = 'job_item_relation'


class JobCollection(BaseModel):
    job_id = models.IntegerField(help_text='job id')
    user_id = models.IntegerField(help_text='user id')

    class Meta:
        db_table = 'job_collection'


class BuildJob(BaseModel):
    BUILD_STATE_CHOICES = (
        ('pending', '队列中'),
        ('running', '运行中'),
        ('success', '成功'),
        ('fail', '失败'),
    )

    BUILD_FROM_CHOICES = (
        ('cbp', 'CBP'),
        ('jenkins', 'JENKINS'),
        ('manual', '手动'),
    )
    name = models.CharField(max_length=64, help_text='the build job name')
    state = models.CharField(max_length=64, choices=BUILD_STATE_CHOICES, default='pending', help_text='state')
    build_from = models.CharField(max_length=64, choices=BUILD_FROM_CHOICES, default='manual', help_text='build from')
    product_id = models.IntegerField(null=True, help_text='ProductModel.id')
    project_id = models.IntegerField(null=True, help_text='ProjectModel.id')
    arch = models.CharField(max_length=64, help_text='arch')
    build_env = models.CharField(max_length=256, null=True, help_text='json info about build environment')
    build_config = models.CharField(max_length=256, null=True, help_text='build configure')
    build_machine = models.CharField(max_length=256, null=True, help_text='build machine')
    build_log = models.CharField(max_length=512, null=True, help_text='build log')
    build_file = models.CharField(max_length=256, null=True, help_text='build file')
    build_url = models.CharField(max_length=256, null=True, help_text='build url')
    git_repo = models.CharField(max_length=256, null=True, help_text='git repo')
    git_branch = models.CharField(max_length=256, help_text='git_branch')
    git_commit = models.CharField(max_length=256, help_text='git_commit')
    git_url = models.CharField(max_length=256, help_text='git_url')
    builder_branch = models.CharField(max_length=256, help_text='build_branch')
    commit_msg = models.CharField(max_length=32, help_text='commit_msg')
    committer = models.CharField(max_length=32, null=True, help_text='committer')
    compiler = models.CharField(max_length=256, null=True, help_text='compiler')
    description = models.CharField(max_length=512, null=True, help_text='the job description')
    cbp_id = models.IntegerField(null=True, help_text='os-goldmine cbp id')
    tid = models.CharField(max_length=64, null=True, help_text='tid')
    build_msg = models.TextField(null=True, help_text='build msg')
    rpm_list = json.JSONField(default=list(), help_text='rpm list')
    creator = models.IntegerField(null=True, help_text='creator id')

    class Meta:
        db_table = 'build_job'


class MonitorInfo(BaseModel):
    OBJECT_TYPE_CHOICES = (
        ('job', 'JOB'),
        ('case', 'CASE'),
    )
    state = models.BooleanField(default=False, help_text='监控是否成功')
    monitor_link = models.CharField(max_length=256, null=True, help_text='monitor link')
    is_open = models.BooleanField(default=True, help_text='监控是否开启')
    monitor_level = models.CharField(max_length=64, choices=OBJECT_TYPE_CHOICES, default='job', help_text='level')
    monitor_objs = json.JSONField(default=list(), null=True, blank=True, help_text='monitor objs')
    object_id = models.IntegerField(null=True, help_text='Job id or JobCase id')
    server = models.CharField(max_length=32, null=True, help_text='sn or ip')
    remark = models.TextField(blank=True, default='', help_text='备注')

    class Meta:
        db_table = 'monitor_info'


class JobMonitorItem(BaseModel):
    """ job监控项表 """

    name = models.CharField('名称', unique=True, help_text='监控项名称', max_length=64, null=False, blank=False)

    class Meta:
        managed = True
        db_table = 'job_monitor_item'
        verbose_name = verbose_name_plural = 'job监控项表'


class JobDownloadRecord(BaseModel):
    DOWNLOAD_STATE_CHOICES = (
        ('running', '文件打包中'),
        ('success', '成功'),
        ('fail', '失败')
    )
    job_id = models.IntegerField(help_text='job id', db_index=True)
    state = models.CharField(max_length=64, choices=DOWNLOAD_STATE_CHOICES, default='running', help_text='state')
    job_url = models.CharField(max_length=256, null=True, help_text='job下载链接')

    class Meta:
        db_table = 'job_download_record'

    def to_dict(self):
        job_dict = model_to_dict(self)
        job_dict['gmt_modified'] = datetime.strftime(self.gmt_modified, "%Y-%m-%d %H:%M:%S")
        job_dict['gmt_created'] = datetime.strftime(self.gmt_created, "%Y-%m-%d %H:%M:%S")
        return job_dict
