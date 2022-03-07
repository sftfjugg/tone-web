from django.db import models
from tone.models.base.base_models import BaseModel


class OfflineUpload(BaseModel):
    TEST_TYPE_CHOICES = (
        ('functional', '功能测试'),
        ('performance', '性能测试'),
        ('business', '业务测试'),
        ('stability', '稳定性测试')
    )
    UPLOAD_STATE_CHOICES = (
        ('file', '文件上传中'),
        ('running', '文件解析中'),
        ('success', '成功'),
        ('fail', '失败')
    )
    file_name = models.CharField(max_length=128, help_text='文件名称')
    file_link = models.CharField(max_length=256, help_text='文件下载地址')
    project_id = models.IntegerField(help_text='project_id')
    baseline_id = models.IntegerField(help_text='baseline_id')
    test_job_id = models.IntegerField(help_text='test_job_id')
    test_type = models.CharField(max_length=64, choices=TEST_TYPE_CHOICES, default='functional', db_index=True,
                                 help_text='测试类型')
    ws_id = models.CharField(max_length=64, help_text='workspace id')
    uploader = models.IntegerField(help_text='上传者')
    state = models.CharField(max_length=64, choices=UPLOAD_STATE_CHOICES, default='success',
                             db_index=True, help_text='任务状态')
    state_desc = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'offline_upload'
