# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models import TestTemplate, TestTmplCase, TestTmplSuite, TemplateTagRelation, JobTypeItem, \
    JobTypeItemRelation, JobTag
from tone.models.job.job_models import JobType
from tone.models.sys.auth_models import User
from tone.core.common.job_result_helper import get_job_case_server, get_custom_server


class TestTemplateSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    test_type = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()
    job_type = serializers.SerializerMethodField()

    class Meta:
        model = TestTemplate
        fields = ['id', 'name', 'job_name', 'creator_name', 'ws_id', 'gmt_created', 'gmt_modified', 'test_type',
                  'update_user', 'enable', 'description', 'job_type', 'job_type_id', 'creator', 'report_name',
                  'report_template_id', 'server_provider']

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_test_type(obj):
        test_type_map = {
            'functional': '功能测试',
            'performance': '性能测试',
            'business': '业务测试',
            'stability': '稳定性测试',
        }
        if obj.job_type_id and JobType.objects.filter(id=obj.job_type_id).exists():
            job_type = JobType.objects.get(id=obj.job_type_id)
        else:
            return ''
        return test_type_map.get(job_type.test_type)

    @staticmethod
    def get_update_user(obj):
        update_user = None
        creator = User.objects.filter(id=obj.update_user).first()
        if creator:
            update_user = creator.first_name if creator.first_name else creator.last_name
        return update_user

    @staticmethod
    def get_job_type(obj):
        if obj.job_type_id and JobType.objects.filter(id=obj.job_type_id).exists():
            job_type = JobType.objects.get(id=obj.job_type_id)
        else:
            return ''
        return job_type.name


class TestTemplateDetailSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    test_type = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()
    job_type = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    test_config = serializers.SerializerMethodField()
    template_name = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    kernel_info = serializers.JSONField()
    iclone_info = serializers.JSONField()
    rpm_info = serializers.JSONField()
    script_info = serializers.JSONField()
    notice_info = serializers.JSONField()
    env_info = serializers.JSONField()
    monitor_info = serializers.JSONField()
    build_pkg_info = serializers.JSONField()

    class Meta:
        model = TestTemplate
        fields = ['id', 'template_name', 'name', 'creator_name', 'ws_id', 'gmt_created', 'gmt_modified', 'test_type',
                  'build_pkg_info', 'update_user', 'enable', 'description', 'job_type', 'job_type_id', 'project_id',
                  'product_id', 'baseline_id', 'iclone_info', 'kernel_info', 'need_reboot', 'rpm_info', 'script_info',
                  'monitor_info', 'cleanup_info', 'notice_info', 'console', 'kernel_version', 'env_info', 'tags',
                  'test_config', 'report_name', 'report_template_id', 'callback_api', 'baseline_job_id']

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_test_type(obj):
        test_type_map = {
            'functional': '功能测试',
            'performance': '性能测试',
            'business': '业务测试',
            'stability': '稳定性测试',
        }
        if obj.job_type_id:
            job_type = JobType.objects.get(id=obj.job_type_id)
        else:
            return ''
        return test_type_map.get(job_type.test_type)

    @staticmethod
    def get_update_user(obj):
        update_user = None
        creator = User.objects.filter(id=obj.update_user).first()
        if creator:
            update_user = creator.first_name if creator.first_name else creator.last_name
        return update_user

    @staticmethod
    def get_job_type(obj):
        if obj.job_type_id:
            job_type = JobType.objects.get(id=obj.job_type_id)
        else:
            return ''
        return job_type.name

    @staticmethod
    def get_tags(obj):
        tags = [tag.tag_id for tag in TemplateTagRelation.objects.filter(template_id=obj.id)]
        tags = [tag for tag in tags if JobTag.objects.filter(id=tag).exists()]
        return tags

    @staticmethod
    def get_template_name(obj):
        return obj.name

    @staticmethod
    def get_name(obj):
        return obj.job_name

    @staticmethod
    def get_test_config(obj):
        test_config = list()
        template_suites = TestTmplSuite.objects.filter(tmpl_id=obj.id)
        templates_cases = TestTmplCase.objects.filter(tmpl_id=obj.id)
        for template_suite in template_suites:
            obj_dict = {
                'test_suite_id': template_suite.test_suite_id,
                'need_reboot': template_suite.need_reboot,
                'setup_info': template_suite.setup_info,
                'cleanup_info': template_suite.cleanup_info,
                'console': template_suite.console,
                'monitor_info': template_suite.monitor_info,
                'priority': template_suite.priority,
            }
            cases = list()
            for case in templates_cases.filter(test_suite_id=template_suite.test_suite_id):
                ip, is_instance, _, _ = get_job_case_server(case.id, template=True)
                cases.append({
                    'test_case_id': case.test_case_id,
                    'setup_info': case.setup_info,
                    'cleanup_info': case.cleanup_info,
                    'server_object_id': case.server_object_id,
                    'server_tag_id': case.server_tag_id if not case.server_tag_id else [
                        int(tag_id) for tag_id in case.server_tag_id.split(',') if tag_id.isdigit()],
                    'customer_server': get_custom_server(case.id, template=True),
                    'need_reboot': case.need_reboot,
                    'console': case.console,
                    'monitor_info': case.monitor_info,
                    'priority': case.priority,
                    'env_info': case.env_info,
                    'repeat': case.repeat,
                    'ip': ip,
                    'is_instance': is_instance,
                })
            obj_dict['cases'] = cases
            test_config.append(obj_dict)
        return test_config


class TemplateItemsSerializer(CommonSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = TestTemplate
        fields = ['name', 'id', 'items']

    @staticmethod
    def get_items(obj):
        job_type_items = JobTypeItem.objects.all()
        items = [{
            'id': job_type_item.id,
            'name': job_type_item.name,
            'show_name': job_type_item.show_name,
            'description': job_type_item.description,
            'config_index': job_type_item.config_index,
            'alias': '',
        } for job_type_item in job_type_items]
        if obj.job_type_id:
            select_items = JobTypeItemRelation.objects.filter(job_type_id=obj.job_type_id)
            for select_item in select_items:
                for item in items:
                    if item['id'] == select_item.item_id:
                        item['alias'] = select_item.item_alias
        return items
