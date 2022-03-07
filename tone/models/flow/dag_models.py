from django.db import models
from tone.models.base.base_models import BaseModel


class Dag(BaseModel):
    job_id = models.IntegerField(unique=True, db_index=True)
    graph = models.BinaryField(help_text='dag图')
    is_update = models.BooleanField(default=False, help_text='dag是否需要更新')
    block = models.BooleanField(default=False)

    class Meta:
        db_table = "dag"


class DagStepInstance(BaseModel):
    STEP_STATE_CHOICES = (
        ('pending', '等待中'),
        ('running', '运行中'),
        ('skip', '已跳过'),
        ('stop', '已停止'),
        ('success', '成功'),
        ('fail', '失败')
    )
    STAGE = (
        ('initcloud', '购买云机器、云上测试必须'),
        ('deploy', '部署agent、云上机器必须'),
        ('package', '打包'),
        ('reclone', '重装机、非必须'),
        ('initial', '初始化、非必须'),
        ('script', '执行脚本,分重启前和重启后、非必须'),
        ('install', '安装内核、非必需'),
        ('reboot', '重启、非必须'),
        ('check', '检测机器、非必须'),
        ('prepare', '测试准备、必须'),
        ('test', '测试、必须'),
        ('end', '结束，调度虚拟状态，业务上不会直接体现'),
    )
    dag_id = models.IntegerField()
    step_data = models.TextField(help_text='步骤元数据')
    stage = models.CharField(max_length=64, help_text='阶段')
    state = models.CharField(max_length=64, choices=STEP_STATE_CHOICES, default='pending', help_text='状态')
    remark = models.TextField(help_text='备注')

    class Meta:
        db_table = "dag_step_instance"
