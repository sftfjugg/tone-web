from django.db import models
from django_extensions.db.fields import json

from tone.models import BaseModel
from django_extensions.db.fields.json import JSONField


class InSiteWorkProcessMsg(BaseModel):
    """站内通知 —— 集中式的处理消息"""
    subject = models.CharField(max_length=255, help_text='主题')
    content = JSONField(default=dict(), null=True, blank=True, help_text='通知内容')
    process_id = models.IntegerField(null=True, help_text='关联审批id')
    is_handle = models.BooleanField(default=False, db_index=True, help_text='是否被处理')

    class Meta:
        db_table = 'insite_workprocess_mesg'


class InSiteWorkProcessUserMsg(BaseModel):
    """集中式"""
    user_id = models.IntegerField(db_index=True, help_text='关联用户id')
    msg_id = models.IntegerField(help_text='关联集中式处理信息id')
    i_am_handle = models.BooleanField(default=False, help_text='是否本人处理')

    class Meta:
        db_table = 'insite_workprocess_user_mesg'


class InSiteSimpleMsg(BaseModel):
    """站内通知 —— 普通消息通知"""
    MSG_TYPE_CHOICE = (
        ('job_complete', '任务完成'),
        ('plan_complete', '计划完成'),
        ('machine_broken', '机器故障'),
        ('announcement', '系统公告'),
    )
    subject = models.CharField(max_length=255, help_text='主题')
    content = JSONField(default=dict(), null=True, blank=True, help_text='通知内容')
    msg_type = models.CharField(max_length=64, choices=MSG_TYPE_CHOICE, help_text='消息类型')
    msg_object_id = models.IntegerField(help_text='关联对象id')
    receiver = models.IntegerField(db_index=True, help_text='关联接收人id')
    is_read = models.BooleanField(default=False, db_index=True, help_text='已读')

    class Meta:
        db_table = 'insite_simple_mesg'


class OutSiteMsg(BaseModel):
    """站外通知"""
    SEND_TYPE_CHOICE = (
        ('markdown', 'markdown'),
        ('html', 'html'),
        ('link', 'link'),
    )
    SEND_BY_CHOICE = (
        ('ding_talk', '钉钉'),
        ('mail', '邮箱'),
    )
    subject = models.CharField(max_length=255, help_text='主题')
    content = models.TextField(blank=True, null=True, help_text='通知内容')
    send_to = models.TextField(default='', help_text='接收对象信息')
    cc_to = models.TextField(default='', help_text='抄送人邮箱')
    bcc_to = models.CharField(max_length=255, default='', help_text='邮件group')
    send_by = models.CharField(max_length=64, choices=SEND_BY_CHOICE, help_text='发送方式')
    send_type = models.CharField(max_length=64, choices=SEND_TYPE_CHOICE, help_text='发送类型')
    msg_link = models.CharField(max_length=256, default='', help_text='消息链接')
    msg_pic = models.CharField(max_length=256, default='', help_text='消息图片')
    extend_info = json.JSONField(default=dict(), help_text='扩展信息')
    is_send = models.BooleanField(default=False, db_index=True, help_text='已发送')

    class Meta:
        db_table = 'outsite_mesg'

