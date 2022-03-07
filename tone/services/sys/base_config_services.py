# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from django.db.models import Q
from django.db import transaction

from tone.models import BaseConfig, BaseConfigHistory
from tone.core.common.services import CommonService
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import BaseConfigException


class BaseConfigService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(config_type=data.get('config_type')) if data.get('config_type') else q
        q &= Q(enable=data.get('enable')) if data.get('enable') else q
        q &= Q(creator=data.get('creator')) if data.get('creator') else q
        q &= Q(update_user=data.get('update_user')) if data.get('update_user') else q
        q &= Q(config_key__icontains=data.get('config_key')) if data.get('config_key') else q
        q &= Q(config_value__icontains=data.get('config_value')) if data.get('config_value') else q
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        return queryset.filter(q)

    def update(self, data, operator):
        config_id = data.get('config_id')
        assert config_id, BaseConfigException(ErrorCode.CONFIG_ID_NEED)
        self.check_id(config_id)
        obj = BaseConfig.objects.get(id=config_id)
        with transaction.atomic():
            self.save_history(obj, operator.id)
            for key, value in data.items():
                if key == 'config_key':
                    if value != obj.config_key:
                        self.check_config_key(value)
                if hasattr(obj, key):
                    setattr(obj, key, value)
                else:
                    pass
            obj.update_user = operator.id
            obj.save()

    def create(self, data, operator):
        config_key = data.get('config_key')
        creator = operator.id
        description = data.get('description')
        config_type = data.get('config_type')
        config_value = data.get('config_value')
        bind_stage = data.get('bind_stage')
        enable = data.get('enable', True)
        assert config_key, BaseConfigException(ErrorCode.CONFIG_KEY_NEED)
        assert config_type, BaseConfigException(ErrorCode.CONFIG_TYPE_NEED)
        self.check_config_key(config_key)
        BaseConfig.objects.create(config_key=config_key, description=description, creator=creator,
                                  config_type=config_type, config_value=config_value, bind_stage=bind_stage,
                                  enable=enable)

    def delete(self, data):
        config_id = data.get('config_id')
        assert config_id, BaseConfigException(ErrorCode.CONFIG_ID_NEED)
        self.check_id(config_id)
        with transaction.atomic():
            BaseConfigHistory.objects.filter(config_key=BaseConfig.objects.get(id=config_id).config_key).delete()
            BaseConfig.objects.filter(id=config_id).delete()

    @staticmethod
    def check_config_key(config_key):
        key_list = [config_key]
        if config_key.startswith('TONE_'):
            key_list.append(config_key.split('TONE_', 1)[1])
        else:
            key_list.append('TONE_' + config_key)
        obj = BaseConfig.objects.filter(config_key__in=key_list)
        if obj.exists():
            raise BaseConfigException(ErrorCode.CONFIG_DUPLICATION)

    @staticmethod
    def check_id(config_id):
        obj = BaseConfig.objects.filter(id=config_id)
        if not obj.exists():
            raise BaseConfigException(ErrorCode.CONFIG_NONEXISTENT)

    @staticmethod
    def save_history(obj, update_user):
        count = BaseConfigHistory.objects.filter(config_key=obj.config_key).count() + 1
        BaseConfigHistory.objects.create(config_key=obj.config_key, config_value=obj.config_value,
                                         description=obj.description, update_user=update_user,
                                         source_gmt_created=obj.gmt_modified, bind_stage=obj.bind_stage,
                                         change_id=count, commit=obj.commit)


class BaseConfigHistoryService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(config_type=data.get('config_type')) if data.get('config_type') else q
        q &= Q(update_user=data.get('update_user')) if data.get('update_user') else q
        q &= Q(config_key=data.get('config_key')) if data.get('config_key') else q
        q &= Q(commit=data.get('commit')) if data.get('commit') else q
        q &= Q(change_id=data.get('change_id')) if data.get('change_id') else q
        q &= Q(id=data.get('history_id')) if data.get('history_id') else q
        q &= Q(change_id__gt=1)
        return queryset.filter(q)
