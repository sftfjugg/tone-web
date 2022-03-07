# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models import JobTag
from tone.models.sys.auth_models import User


class JobTagSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()
    source_tag = serializers.CharField(source='get_source_tag_display')

    class Meta:
        model = JobTag
        fields = ['id', 'name', 'creator_name', 'description', 'creator', 'source_tag',
                  'tag_color', 'gmt_created', 'gmt_modified', 'update_user']

    @staticmethod
    def get_creator_name(obj):
        creator_name = '系统预设'
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
