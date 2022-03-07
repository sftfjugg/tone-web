from rest_framework import serializers
from tone.core.common.serializers import CommonSerializer
from tone.models import Baseline, FuncBaselineDetail, PerfBaselineDetail, TestSuite, TestCase, TestJob, User


class BaselineSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    update_user_name = serializers.SerializerMethodField()

    class Meta:
        model = Baseline
        fields = ["id", "name", "version", "description", "test_type", "server_provider", "ws_id", 'creator',
                  'update_user', 'creator_name', 'update_user_name', 'gmt_created']

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_update_user_name(obj):
        update_user = None
        creator = User.objects.filter(id=obj.update_user).first()
        if creator:
            update_user = creator.first_name if creator.first_name else creator.last_name
        return update_user


class FuncBaselineDetailSerializer(CommonSerializer):
    test_suite_name = serializers.SerializerMethodField()
    test_case_name = serializers.SerializerMethodField()
    sub_case_id = serializers.SerializerMethodField()
    job_name = serializers.SerializerMethodField()

    class Meta:
        model = FuncBaselineDetail
        exclude = ['is_deleted']

    @staticmethod
    def get_test_suite_name(obj):
        """获取suite name"""
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite is None:
            return None
        return test_suite.name

    @staticmethod
    def get_test_case_name(obj):
        """获取case_name"""
        test_case = TestCase.objects.filter(id=obj.test_case_id).first()
        if test_case is None:
            return None
        return test_case.name

    @staticmethod
    def get_sub_case_id(obj):
        """获取case_name"""
        test_case = TestCase.objects.filter(name=obj.sub_case_name).first()
        if test_case is None:
            return None
        return test_case.id

    @staticmethod
    def get_job_name(obj):
        """获取case_name"""
        test_job = TestJob.objects.filter(id=obj.source_job_id).first()
        if test_job is None:
            return None
        return test_job.name


class PerfBaselineDetialSerializer(CommonSerializer):
    test_suite_name = serializers.SerializerMethodField()
    test_case_name = serializers.SerializerMethodField()
    job_name = serializers.SerializerMethodField()

    class Meta:
        model = PerfBaselineDetail
        exclude = ['is_deleted']

    @staticmethod
    def get_test_suite_name(obj):
        """获取suite name"""
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite is None:
            return None
        return test_suite.name

    @staticmethod
    def get_test_case_name(obj):
        """获取case_name"""
        test_case = TestCase.objects.filter(id=obj.test_case_id).first()
        if test_case is None:
            return None
        return test_case.name

    @staticmethod
    def get_job_name(obj):
        """获取case_name"""
        test_job = TestJob.objects.filter(id=obj.source_job_id).first()
        if test_job is None:
            return None
        return test_job.name
