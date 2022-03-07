from rest_framework import serializers

from tone.core.common.msg_notice import get_user_info
from tone.core.common.redis_cache import redis_cache
from tone.core.common.serializers import CommonSerializer
from tone.models import HelpDoc, User, SiteConfig, SitePushConfig, Workspace, Project, Comment, TestJob, BaseConfig


class HelpDocSerializer(CommonSerializer):
    creator = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()
    brief_content = serializers.SerializerMethodField()

    class Meta:
        model = HelpDoc
        exclude = ['is_deleted', 'content']

    @staticmethod
    def get_brief_content(obj):
        if obj.doc_type == 'notice':
            return obj.content[:31]

    @staticmethod
    def get_creator(obj):
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


class HelpDocDetailSerializer(HelpDocSerializer):

    class Meta:
        model = HelpDoc
        exclude = ['is_deleted']


class TestFarmSerializer(CommonSerializer):
    push_config_list = serializers.SerializerMethodField()
    last_sync_time = serializers.SerializerMethodField()

    class Meta:
        model = SiteConfig
        exclude = ['is_deleted']

    @staticmethod
    def get_push_config_list(obj):
        id_list = Workspace.objects.all().values_list('id')
        push_config_queryset = \
            SitePushConfig.objects.filter(site_id=obj.id, ws_id__in=id_list
                                          ) | SitePushConfig.objects.filter(
                site_id=obj.id, ws_id__isnull=True) | SitePushConfig.objects.filter(
                site_id=obj.id, ws_id='')
        return SitePushConfigSerializer(push_config_queryset, many=True).data

    @staticmethod
    def get_last_sync_time(_):
        last_sync_portal = BaseConfig.objects.filter(config_type='sys', config_key='LAST_SYNC_TEST_FARM_TIME').first()
        if last_sync_portal:
            return last_sync_portal.config_value.split('.')[0]
        return '2020-01-01 00:00:00'


class TestFarmJobSerializer(CommonSerializer):
    class Meta:
        model = TestJob
        fields = ['id', 'name', 'sync_time']


class SitePushConfigSerializer(CommonSerializer):
    ws_name = serializers.SerializerMethodField()
    show_name = serializers.SerializerMethodField()
    project_list = serializers.SerializerMethodField()
    job_info = serializers.SerializerMethodField()
    sync_start_time = serializers.SerializerMethodField()

    class Meta:
        model = SitePushConfig
        exclude = ['is_deleted']

    @staticmethod
    def get_sync_start_time(obj):
        return None if not obj.sync_start_time else obj.sync_start_time.split('.')[0]

    @staticmethod
    def get_job_info(obj):
        if obj.ws_id and obj.project_id and obj.job_name_rule:
            job_obj = TestJob.objects.filter(
                ws_id=obj.ws_id, project_id=obj.project_id, sync_time__isnull=False, query_scope='all'
            ).order_by('-sync_time').first()
            if job_obj:
                return {
                    'job_id': job_obj.id,
                    'job_name': job_obj.name,
                    'last_time': job_obj.end_time,
                }
        return None

    @staticmethod
    def get_ws_name(obj):
        if obj.ws_id:
            return Workspace.objects.get(id=obj.ws_id).name

    @staticmethod
    def get_show_name(obj):
        if obj.ws_id:
            return Workspace.objects.get(id=obj.ws_id).show_name

    @staticmethod
    def get_project_id_list(obj):
        return obj.project_id.split(',')

    @staticmethod
    def get_project_list(obj):
        if obj.project_id:
            project_id_list = obj.project_id.split(',')
            return Project.objects.filter(ws_id=obj.ws_id, id__in=project_id_list).values('id', 'name')


class WorkspaceListSerializer(CommonSerializer):

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'show_name']


class ProjectListSerializer(CommonSerializer):

    class Meta:
        model = Project
        fields = ['id', 'name']


class CommentSerializer(CommonSerializer):
    user_info = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        exclude = ['is_deleted']

    @staticmethod
    def get_user_info(obj):
        return get_user_info(obj.creator)
