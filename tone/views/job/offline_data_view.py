
from rest_framework.response import Response
from django.utils.decorators import method_decorator

from tone.core.common.views import CommonAPIView, BaseView
from tone.models.job.upload_models import OfflineUpload
from tone.serializers.job.offline_data_serializers import OfflineDataSerializer
from tone.services.job.offline_data_services import OfflineDataUploadService
from tone.schemas.job.offline_data_schemas import OfflineDataUploadSchema
from tone.core.common.expection_handler.error_catch import views_catch_error


class OfflineDataView(CommonAPIView):
    schema_class = OfflineDataUploadSchema
    serializer_class = OfflineDataSerializer
    queryset = OfflineUpload.objects.all()
    service_class = OfflineDataUploadService
    permission_classes = []
    order_by = ['-gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        获取WorkSpace下OfflineDataUpload
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        上传解析offline data
        """
        code, msg = self.service.post(request.POST, request.FILES.get('file'), operator=request.user)
        return Response(self.get_response_code(code=code, msg=msg))

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除offline data
        """
        self.service.delete(request.data.get('pk'))
        return Response(self.get_response_code(code=200, msg='success'))
