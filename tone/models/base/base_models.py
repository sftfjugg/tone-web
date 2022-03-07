from django.db import models

from tone.core.common.objects import ToneModelObjects


class BaseModel(models.Model):
    objects = ToneModelObjects()

    gmt_created = models.DateTimeField('create_at', auto_now_add=True, help_text='创建时间')
    gmt_modified = models.DateTimeField('modify_at', auto_now=True, help_text='修改时间')
    is_deleted = models.BooleanField(default=False, db_index=True, help_text='是否被删除')

    class Meta:
        abstract = True
