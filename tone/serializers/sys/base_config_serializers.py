# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from datetime import datetime

from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models import BaseConfig, BaseConfigHistory
from tone.models.sys.auth_models import User


class BaseConfigSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()

    class Meta:
        model = BaseConfig
        fields = ['id', 'bind_stage', 'config_key', 'config_value', 'creator_name', 'description', 'gmt_created',
                  'gmt_modified', 'update_user', 'enable', 'commit']

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_update_user(obj):
        update_user = None
        creator = User.objects.filter(id=obj.update_user).first()
        if creator:
            update_user = creator.first_name if creator.first_name else creator.last_name
        return update_user


class BaseConfigHistorySerializer(CommonSerializer):
    update_user = serializers.SerializerMethodField()
    source_gmt_created = serializers.SerializerMethodField()

    class Meta:
        model = BaseConfigHistory
        fields = ['id', 'bind_stage', 'config_key', 'config_value', 'description', 'gmt_created', 'update_user',
                  'commit', 'change_id', 'source_gmt_created']

    @staticmethod
    def get_update_user(obj):
        update_user = None
        creator = User.objects.filter(id=obj.update_user).first()
        if creator:
            update_user = creator.first_name if creator.first_name else creator.last_name
        return update_user

    @staticmethod
    def get_source_gmt_created(obj):
        if obj.source_gmt_created:
            return datetime.strftime(obj.source_gmt_created, "%Y-%m-%d %H:%M:%S")
        else:
            return datetime.strftime(obj.gmt_created, "%Y-%m-%d %H:%M:%S")
