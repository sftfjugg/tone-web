# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework import serializers
from tone.models import User, json
from tone.models.sys.log_model import OperationLogs
from tone.core.common.serializers import CommonSerializer
from tone.core.common.operation_module.machine_management import OPERATION_OBJECT


class OperationsLosSerializer(CommonSerializer):
    operation_object = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()
    old_values = serializers.SerializerMethodField()
    new_values = serializers.SerializerMethodField()

    class Meta:
        model = OperationLogs
        fields = ['id', 'operation_type', 'operation_object', 'db_table', 'db_pid', 'old_values',
                  'new_values', 'operation_sn', 'creator', 'gmt_created']

    @staticmethod
    def get_operation_object(obj):
        return OPERATION_OBJECT.get(obj.operation_object)

    @staticmethod
    def get_old_values(obj):
        if obj.old_values.get('owner') is not None:
            owner_id = obj.old_values.get('owner')
            owner_obj = User.objects.filter(id=owner_id).first()
            if owner_obj:
                creator_name = owner_obj.first_name if owner_obj.first_name else owner_obj.last_name
                obj.old_values.update({'owner': '{}-{}'.format(creator_name, owner_obj.emp_id)})
        return str(obj.old_values)

    @staticmethod
    def get_new_values(obj):
        if obj.new_values.get('owner') is not None:
            owner_id = obj.new_values.get('owner')
            owner_obj = User.objects.filter(id=owner_id).first()
            if owner_obj:
                creator_name = owner_obj.first_name if owner_obj.first_name else owner_obj.last_name
                obj.new_values.update({'owner': '{}-{}'.format(creator_name, owner_obj.emp_id)})
        return str(obj.new_values)

    @staticmethod
    def get_creator(obj):
        creator = 'system'
        creator_obj = User.objects.filter(id=obj.creator).first()
        if creator_obj:
            creator = creator_obj.first_name if creator_obj.first_name else creator_obj.last_name
        return creator
