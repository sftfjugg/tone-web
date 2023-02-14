from rest_framework import serializers
from tone.core.common.serializers import CommonSerializer
from tone.models import Baseline, FuncBaselineDetail, PerfBaselineDetail, TestSuite, TestCase, TestJob, User, \
    CloudServerSnapshot, TestServerSnapshot


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
    env_info = serializers.SerializerMethodField()

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

    @staticmethod
    def get_env_info(obj):
        env = dict()
        test_job = TestJob.objects.filter(id=obj.source_job_id).first()
        if test_job is None:
            return env
        if test_job.server_provider == 'aliyun':
            snapshot_obj = CloudServerSnapshot
        else:
            snapshot_obj = TestServerSnapshot
        snapshot_detail = snapshot_obj.objects.filter(job_id=obj.source_job_id)
        if snapshot_detail.exists():
            env = dict({
                'sn': snapshot_detail[0].sn,
                'ip': snapshot_detail[0].private_ip if test_job.server_provider == 'aliyun' else snapshot_detail[0].ip,
                'cpu': snapshot_detail[0].cpu if test_job.server_provider == 'aligroup' else '',
                'memory': snapshot_detail[0].memory_info,
                'disk': snapshot_detail[0].disk,
                'image': snapshot_detail[0].image if test_job.server_provider == 'aliyun' else '',
                'bandwidth': snapshot_detail[0].bandwidth if test_job.server_provider == 'aliyun' else '',
                'distro': snapshot_detail[0].distro,
                'kernel_version': snapshot_detail[0].kernel_version,
                'glibc': snapshot_detail[0].glibc,
                'gcc': snapshot_detail[0].gcc,
            })
        return env
