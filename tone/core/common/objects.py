import time
import datetime

from django.db import transaction
from django.db.models import QuerySet, fields
from django.db.models.manager import BaseManager


class ToneQuerySet(QuerySet):
    def delete(self, really_delete=False):
        """
        重写objects.filter.delete()方法
        1.逻辑删除id为1的job:
            JobModel.objects.filter(id=1).delete()
        2.真删除id为2的job
            JobModel.objects.filter(id=2).delete(really_delete=True) 真删除id为2的job
        :return:
        """
        if not really_delete:
            with transaction.atomic():
                self._modify_unique_fields_value()
                return self.update(is_deleted=True)
        return super(ToneQuerySet, self).delete()

    def update(self, **kwargs):
        if not kwargs.get('not_update_time', None):
            kwargs['gmt_modified'] = datetime.datetime.now()
        else:
            del kwargs['not_update_time']
        return super(ToneQuerySet, self).update(**kwargs)

    def _modify_unique_fields_value(self):
        """
        检查该model中的unique字段或者unique_together字段，删除同时更改他们的value值
        """
        if not self.exists():
            return
        model_fields = self.model._meta.fields
        unique_together_fields_list = self.model._meta.unique_together \
            if hasattr(self.model._meta, 'unique_together') else set()
        update_data = dict()
        for model_field in model_fields:
            if model_field.primary_key:
                continue
            is_unique_field = False
            if model_field.unique:
                is_unique_field = True
            else:
                for unique_together_fields in unique_together_fields_list:
                    if model_field.attname in unique_together_fields:
                        is_unique_field = True
                        break
            if is_unique_field:
                if isinstance(model_field, fields.IntegerField):
                    update_value = getattr(self.first(), model_field.attname) + int(time.time())
                else:
                    old_value = getattr(self.first(), model_field.attname)
                    old_value = '' if old_value is None else old_value
                    update_value = '{}_{}'.format(old_value, str(time.time()))
                update_data[model_field.attname] = update_value
        if update_data:
            self.update(**update_data)


class ToneModelObjects(BaseManager.from_queryset(ToneQuerySet)):
    def filter(self, *args, **kwargs):
        """
        重写objects.filter方法，方便查询is_deleted为True的数据
        1.查询没有被删除的job数据:
            JobModel.objects.filter(name='xxx')
        2.查询被删除的job数据
            JobModel.objects.filter(name='xxx', query_scope='deleted')
        3.查询全部job数据
            JobModel.objects.filter(name='xxx', query_scope='all')
        """
        if not kwargs.get('query_scope'):
            kwargs['is_deleted'] = False
        else:
            if kwargs.get('query_scope') == 'deleted':
                kwargs["is_deleted"] = True
            kwargs.pop('query_scope')
        return super(ToneModelObjects, self).filter(*args, **kwargs)

    def all(self, query_scope=None):
        if query_scope:
            return self.filter(query_scope=query_scope)
        else:
            return self.filter()

    def last(self, query_scope=None):
        if query_scope:
            return self.last()
        else:
            return self.filter().last()

    def get(self, *args, **kwargs):
        if not kwargs.get('query_scope'):
            kwargs['is_deleted'] = False
        else:
            if kwargs.get('query_scope') == 'deleted':
                kwargs["is_deleted"] = True
            kwargs.pop('query_scope')
        return super(ToneModelObjects, self).get(*args, **kwargs)

    def get_value(self, *args, **kwargs):
        """
        一般用于查询条件唯一的场景，如id等
        """
        queryset = super(ToneModelObjects, self).filter(*args, **kwargs)
        return super(ToneModelObjects, self).get(*args, **kwargs) if queryset.exists() else None

    def get_unique_value(self, *args, **kwargs):
        pass
