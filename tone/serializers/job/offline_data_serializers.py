from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models.job.upload_models import OfflineUpload
from tone.models.sys.auth_models import User
from tone.models.sys.workspace_models import Project, Product
from tone.models.sys.baseline_models import Baseline
from tone.settings import APP_DOMAIN


class OfflineDataSerializer(CommonSerializer):
    uploader = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    baseline_name = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    job_link = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()

    class Meta:
        model = OfflineUpload
        fields = ['id', 'file_name', 'file_link', 'project_id', 'baseline_id', 'ws_id', 'job_link', 'uploader',
                  'creator', 'test_type', 'project_name', 'baseline_name', 'product_name',
                  'state', 'state_desc', 'gmt_created']

    @staticmethod
    def get_product_name(obj):
        product_name = None
        project = Project.objects.filter(id=obj.project_id).first()
        if project:
            product = Product.objects.filter(id=project.product_id).first()
            if product:
                product_name = product.name
        return product_name

    @staticmethod
    def get_project_name(obj):
        project_name = None
        project = Project.objects.filter(id=obj.project_id).first()
        if project:
            project_name = project.name
        return project_name

    @staticmethod
    def get_baseline_name(obj):
        baseline_name = None
        baseline = Baseline.objects.filter(id=obj.baseline_id).first()
        if baseline:
            baseline_name = baseline.name
        return baseline_name

    @staticmethod
    def get_uploader(obj):
        uploader_user = None
        creator = User.objects.filter(id=obj.uploader).first()
        if creator:
            uploader_user = creator.first_name if creator.first_name else creator.last_name
        return uploader_user

    @staticmethod
    def get_creator(obj):
        return obj.uploader

    @staticmethod
    def get_job_link(obj):
        return '{}/ws/{}/test_result/{}'.format(APP_DOMAIN, obj.ws_id, obj.test_job_id)
