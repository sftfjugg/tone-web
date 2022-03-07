from django.shortcuts import render


# @login_required
from tone import settings


def index(request):
    static_url = settings.STATIC_URL.strip('/') if settings.ENV_TYPE == 'local' else 'static'
    return render(request, 'index.html', context={'static_url': static_url})
