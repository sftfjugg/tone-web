# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases
import os

from tone.settings import BASE_DIR


from tone.core.utils.config_parser import cp


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': cp.get('db_name'),
        'USER': cp.get('db_user'),
        'PASSWORD': cp.get('db_password'),
        'TIMEOUT': 600,
        'HOST': cp.get('db_host'),
        'PORT': '3306'
    }
}
