from rest_framework.response import Response

from tone.core.common.views import CommonAPIView


class TestAPIView(CommonAPIView):
    def get(self, request):
        return Response(self.get_response_code())
