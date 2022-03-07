# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models.job.job_models import JobType, JobTypeItem, JobTypeItemRelation
from tone.models.sys.auth_models import User


class JobTypeSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    has_baseline = serializers.SerializerMethodField()

    class Meta:
        model = JobType
        fields = ['id', 'name', 'is_default', 'enable', 'test_type', 'server_type', 'has_baseline',
                  'description', 'creator_name', 'ws_id', 'gmt_created', 'priority', 'is_first', 'business_type']

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        if obj.creator == 0:
            return '系统预设'
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_has_baseline(obj):
        job_type_item = JobTypeItem.objects.filter(name='baseline').first()
        if job_type_item:
            job_item_relation = JobTypeItemRelation.objects.filter(job_type_id=obj.id, item_id=job_type_item.id).first()
            if job_item_relation:
                return 1
        return 0


class JobTypeItemSerializer(CommonSerializer):
    class Meta:
        model = JobTypeItem
        fields = ['id', 'name', 'show_name', 'description', 'config_index']


class JobTypeItemRelationSerializer(CommonSerializer):
    name = serializers.SerializerMethodField()
    show_name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    config_index = serializers.SerializerMethodField()
    alias = serializers.SerializerMethodField()

    class Meta:
        model = JobTypeItemRelation
        fields = ['name', 'show_name', 'description', 'config_index', 'alias']

    @staticmethod
    def get_name(obj):
        item = JobTypeItem.objects.get(id=obj.item_id)
        return item.name

    @staticmethod
    def get_show_name(obj):
        return obj.item_show_name

    @staticmethod
    def get_alias(obj):
        return obj.item_alias

    @staticmethod
    def get_description(obj):
        item = JobTypeItem.objects.get(id=obj.item_id)
        return item.description

    @staticmethod
    def get_config_index(obj):
        item = JobTypeItem.objects.get(id=obj.item_id)
        return item.config_index
