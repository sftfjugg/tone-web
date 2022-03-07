import os

from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from tone.models import User
from tone.settings import ENV_TYPE


class DisableCSRFCheck(MiddlewareMixin):
    def process_request(self, request):
        setattr(request, '_dont_enforce_csrf_checks', True)


class APITestMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if settings.ENV_TYPE == 'local' and os.environ.get('API_TEST_ENV') == 'true':
            url = request.get_full_path()
            if url.split('?')[0] in ['/', '/tests/', '/sendBucSSOToken.do']:
                return
            if not request.user or not request.user.is_authenticated:
                user = User.objects.first()
                if not user:
                    user = User.objects.create_user('tone_test')
                request.user = user


# todo
class LocalTest(MiddlewareMixin):
    def process_request(self, request):
        if ENV_TYPE == 'local':
            url = request.get_full_path()
            if url == '/':
                return
            user = User.objects.filter(id=2).first()
            request.user = user
