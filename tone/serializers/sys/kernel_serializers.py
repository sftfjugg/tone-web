# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models import KernelInfo
from tone.models.sys.auth_models import User


class KernelSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()

    class Meta:
        model = KernelInfo
        fields = ['id', 'creator_name', 'description', 'version', 'kernel_link', 'devel_link', 'headers_link',
                  'release', 'enable', 'gmt_created', 'gmt_modified', 'update_user']

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
