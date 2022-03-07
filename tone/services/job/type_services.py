# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from django.db import transaction
from django.db.models import Q

from tone.models import JobType, JobTypeItem, JobTypeItemRelation, TestTemplate
from tone.core.common.services import CommonService
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import JobTypeException


class JobTypeService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(id=data.get('jt_id')) if data.get('jt_id') else q
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        q &= Q(enable=data.get('enable')) if data.get('enable') else q
        return queryset.filter(q).order_by('priority', '-id')

    @staticmethod
    def check_business_type(data):
        business_type = {'functional', 'performance', 'business'}
        if data.get('test_type') == 'business':
            if data.get('business_type') not in business_type:
                raise JobTypeException(ErrorCode.BUSINESS_TYPE_ERROR)

    def update(self, data, operator):
        jt_id = data.get('jt_id')
        assert jt_id, JobTypeException(ErrorCode.TYPE_ID_LACK)
        self.check_permission(operator)
        self.check_id(jt_id)
        obj = JobType.objects.get(id=jt_id)
        for key, value in data.items():
            if key == 'item_dict':
                JobTypeItemRelation.objects.filter(job_type_id=jt_id).delete()
                for item, alias in value.items():
                    item_obj = JobTypeItem.objects.get(id=item)
                    JobTypeItemRelation.objects.create(job_type_id=obj.id, item_id=item,
                                                       item_show_name=item_obj.show_name,
                                                       item_alias='' if not alias else alias)
            elif hasattr(obj, key):
                if key == 'name':
                    if value != obj.name:
                        self.check_name(value, obj.ws_id)
                if key == 'is_first':
                    obj.is_first or self.check_is_first(obj.ws_id)
                if key == 'priority':
                    self.check_priority(value)
                setattr(obj, key, value)
            else:
                pass
        obj.save()
        return {'id': obj.id}

    def create(self, data, operator):
        name = data.get('name')
        is_default = data.get('is_default', False)
        test_type = data.get('test_type')
        server_type = data.get('server_type')
        creator = operator.id
        enable = data.get('enable', True)
        ws_id = data.get('ws_id')
        item_dict = data.get('item_dict', dict())
        description = data.get('description')
        priority = data.get('priority') if data.get('priority') else 50
        is_first = data.get('is_first') if data.get('is_first') else False
        business_type = data.get('business_type')
        assert isinstance(item_dict, dict), JobTypeException(ErrorCode.ITEM_MUST_DIC)
        assert name, JobTypeException(ErrorCode.NAME_NEED)
        assert test_type, JobTypeException(ErrorCode.TEST_TYPE_LACK)
        assert server_type, JobTypeException(ErrorCode.SERVER_TYPE_LACK)
        assert ws_id, JobTypeException(ErrorCode.WS_NEED)
        self.check_permission(operator)
        self.check_item(item_dict)
        self.check_name(name, ws_id)
        with transaction.atomic():
            is_first and self.check_is_first(ws_id)
            obj = JobType(
                name=name,
                is_default=is_default,
                test_type=test_type,
                server_type=server_type,
                creator=creator,
                description=description,
                ws_id=ws_id,
                priority=priority,
                is_first=is_first,
                enable=enable,
                business_type=business_type,
            )
            obj.save()
            for item, alias in item_dict.items():
                item_obj = JobTypeItem.objects.get(id=item)
                JobTypeItemRelation.objects.create(job_type_id=obj.id, item_id=item,
                                                   item_show_name=item_obj.show_name,
                                                   item_alias='' if not alias else alias)
        return {'id': obj.id}

    def delete(self, data, operator):
        jt_id = data.get('jt_id')
        assert jt_id, JobTypeException(ErrorCode.TYPE_ID_LACK)
        self.check_permission(operator)
        self.check_id(jt_id)
        obj = JobType.objects.filter(id=jt_id).first()
        if obj.is_default:
            raise JobTypeException(ErrorCode.SYS_TYPE_ATOMIC)
        else:
            with transaction.atomic():
                JobTypeItemRelation.objects.filter(job_type_id=obj.id).delete()
                TestTemplate.objects.filter(job_type_id=obj.id).delete()
                obj.delete()

    def del_type_confirm(self, data):
        jt_id = data.get('jt_id')
        assert jt_id, JobTypeException(ErrorCode.TYPE_ID_LACK)
        self.check_id(jt_id)
        obj = JobType.objects.filter(id=jt_id).first()
        return TestTemplate.objects.filter(job_type_id=obj.id)

    @staticmethod
    def check_item(item_li):
        for item in item_li.keys():
            item_obj = JobTypeItem.objects.filter(id=item)
            if not item_obj.exists():
                raise JobTypeException(ErrorCode.ITEM_NONEXISTENT)

    @staticmethod
    def check_name(name, ws_id):
        obj = JobType.objects.filter(name=name, ws_id=ws_id)
        if obj.exists():
            raise JobTypeException(ErrorCode.TYPE_DUPLICATION)

    @staticmethod
    def check_is_first(ws_id):
        JobType.objects.filter(is_first=True, ws_id=ws_id).update(is_first=False)

    @staticmethod
    def check_id(jt_id):
        obj = JobType.objects.filter(id=jt_id)
        if not obj.exists():
            raise JobTypeException(ErrorCode.TYPE_NONEXISTENT)

    @staticmethod
    def check_priority(priority):
        if not isinstance(priority, int) or priority > 100 or priority < 0:
            raise JobTypeException(ErrorCode.PRIORITY_FAIL)

    @staticmethod
    def check_permission(operator=None):
        pass


class JobTypeItemService(CommonService):

    @staticmethod
    def filter(queryset, data):
        return queryset


class JobTypeItemRelationService(CommonService):

    @staticmethod
    def filter(queryset, data):
        q = Q()
        if not data.get('jt_id'):
            raise JobTypeException(ErrorCode.TYPE_ID_LACK)
        q &= Q(job_type_id=int(data.get('jt_id')))
        return queryset.filter(q)
