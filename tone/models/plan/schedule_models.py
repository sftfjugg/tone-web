from tone.models import BaseModel, models


class ScheduleMap(BaseModel):
    OBJECT_TYPE_CHOICES = (
        ('plan', '测试计划'),
    )

    schedule_job_id = models.CharField(max_length=64, db_index=True)
    object_type = models.CharField(max_length=32, choices=OBJECT_TYPE_CHOICES, default='plan')
    object_id = models.CharField(max_length=64, db_index=True)

    class Meta:
        db_table = 'schedule_map'
