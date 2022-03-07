from __future__ import absolute_import, unicode_literals
import os
from celery import Celery, platforms
from django.conf import settings

from tone.settings import REDIS_PASSWORD, REDIS_HOST, REDIS_PORT, REDIS_BROKER_DB, REDIS_BACKEND_DB

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tone.settings')
# 配置broker, redis作为broker, backend
broker = 'redis://:{}@{}:{}/{}'.format(REDIS_PASSWORD, REDIS_HOST, REDIS_PORT, REDIS_BROKER_DB)
backend = 'redis://:{}@{}:{}/{}'.format(REDIS_PASSWORD, REDIS_HOST, REDIS_PORT, REDIS_BACKEND_DB)
app = Celery('tone', broker=broker, backend=backend)

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

platforms.C_FORCE_ROOT = True
