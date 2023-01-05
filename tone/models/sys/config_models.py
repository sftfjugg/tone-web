from django.db import models
from django_extensions.db.fields import json

from tone.models import BaseModel


class BaseConfig(BaseModel):
    config_type = models.CharField(max_length=64, help_text='配置类型')
    config_key = models.CharField(max_length=64, db_index=True, help_text='配置KEY')
    config_value = models.TextField(max_length=64, null=True, blank=True, help_text='配置VALUE')
    description = models.CharField(max_length=128, null=True, blank=True, help_text='描述')
    bind_stage = models.CharField(max_length=128, null=True, blank=True, help_text='绑定步骤')
    enable = models.BooleanField(default=True, help_text='启用状态')
    creator = models.IntegerField(help_text='创建者', null=True)
    update_user = models.IntegerField(help_text='修改者', null=True)
    commit = models.TextField(max_length=64, null=True, blank=True, help_text='提交日志')
    ws_id = models.CharField(max_length=16, null=True, blank=True, help_text='ws id')

    class Meta:
        unique_together = ('config_key', 'ws_id',)
        db_table = 'base_config'


class BaseConfigHistory(BaseModel):
    config_key = models.CharField(max_length=64, db_index=True, help_text='配置KEY')
    config_value = models.TextField(max_length=64, null=True, blank=True, help_text='配置VALUE')
    description = models.CharField(max_length=128, null=True, blank=True, help_text='描述')
    update_user = models.IntegerField(help_text='修改者', null=True)
    bind_stage = models.CharField(max_length=128, null=True, blank=True, help_text='绑定步骤')
    change_id = models.IntegerField(default=0)
    commit = models.TextField(max_length=64, null=True, blank=True, help_text='提交日志')
    source_gmt_created = models.DateTimeField('create_at', null=True, help_text='创建时间')

    class Meta:
        db_table = 'base_config_history'


class AccessToken(BaseModel):
    access_id = models.CharField(max_length=64, help_text='ACCESS ID')
    access_key = models.CharField(max_length=64, help_text='ACCESS KEY')
    source = models.CharField(max_length=128, null=True, blank=True, help_text='来源')
    description = models.CharField(max_length=64, null=True, blank=True, help_text='描述')

    class Meta:
        db_table = 'access_token'


class JobTag(BaseModel):
    SOURCE_TAG_CHOICE = (
        ('system_tag', '系统标签'),
        ('custom_tag', '自定义标签'),
    )

    name = models.CharField(max_length=128, db_index=True, help_text='标签名称')
    source_tag = models.CharField(max_length=32, choices=SOURCE_TAG_CHOICE, default='custom_tag', help_text='标签来源')
    description = models.CharField(max_length=512, null=True, blank=True, help_text='描述')
    tag_color = models.CharField(max_length=128, default='', help_text='颜色')
    creator = models.IntegerField(help_text='创建者', null=True)
    update_user = models.IntegerField(help_text='修改者', null=True)
    ws_id = models.CharField(max_length=64, help_text='workspace id')

    class Meta:
        db_table = 'job_tag'


class JobTagRelation(BaseModel):
    tag_id = models.IntegerField(db_index=True, help_text='关联Tag')
    job_id = models.IntegerField(db_index=True, help_text='关联对象ID')

    class Meta:
        db_table = 'job_tag_relation'


class TemplateTagRelation(BaseModel):
    template_id = models.IntegerField(db_index=True, help_text='关联template')
    tag_id = models.IntegerField(db_index=True, help_text='关联Tag')

    class Meta:
        db_table = 'template_tag_relation'


class KernelInfo(BaseModel):
    version = models.CharField(max_length=128, unique=True, db_index=True)
    kernel_link = models.CharField(null=True, max_length=128)
    devel_link = models.CharField(null=True, max_length=128)
    headers_link = models.CharField(null=True, max_length=128)
    release = models.BooleanField(default=True)
    enable = models.BooleanField(default=True)
    creator = models.IntegerField()
    update_user = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=512, null=True, blank=True)
    kernel_packages = json.JSONField(default=dict(), help_text='扩展包')

    class Meta:
        db_table = 'kernel_info'


class HelpDoc(BaseModel):
    title = models.CharField(max_length=100, unique=True, help_text='标题')
    order_id = models.IntegerField(help_text='显示顺序id', null=True)
    creator = models.IntegerField(db_index=True, help_text='创建人ID', null=True)
    update_user = models.IntegerField(db_index=True, help_text='修改人ID', null=True)
    content = models.TextField(null=True, blank=True, help_text='文档详情')
    tags = models.CharField(max_length=200, null=True, blank=True, help_text='标签')
    active = models.BooleanField(default=True, help_text='是否展示')
    doc_type = models.CharField(max_length=64, default='help_doc', help_text='文档类型')

    class Meta:
        db_table = 'help_doc'


class SiteConfig(BaseModel):
    is_major = models.BooleanField(default=True, help_text='是否主站点')
    site_url = models.CharField(max_length=200, help_text='Testfarm地址')
    site_token = models.CharField(max_length=200, help_text='Testfarm Token')
    business_system_name = models.CharField(max_length=200, default='', help_text='业务系统名称')

    class Meta:
        db_table = 'site_config'


class SitePushConfig(BaseModel):
    site_id = models.IntegerField(help_text='关联站点配置')
    ws_id = models.CharField(max_length=64, null=True, blank=True, help_text='workspace id')
    project_id = models.CharField(max_length=64, null=True, blank=True, help_text='关联project id字符串')
    job_name_rule = models.CharField(max_length=200, null=True, blank=True, help_text='Job名称规则')
    sync_start_time = models.CharField(max_length=64, null=True, blank=True, help_text='同步起始时间')

    class Meta:
        db_table = 'site_push_config'


class Comment(BaseModel):
    OBJECT_TYPE_CHOICES = (
        ('report', 'report'),
        ('help_doc', 'help_doc')
    )
    object_type = models.CharField(max_length=64, choices=OBJECT_TYPE_CHOICES, default='report', help_text='关联类型')
    object_id = models.IntegerField(db_index=True, help_text='关联id')
    content = models.TextField(blank=True, null=True, help_text='评论内容')
    creator = models.IntegerField(help_text='评论人')

    class Meta:
        db_table = 'comment'
