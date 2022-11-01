import os
import platform

from tone.core.common.constant import EnvType
from tone.settings import base_settings

APP_NAME = os.environ.get('APP_NAME', 'tone')
if base_settings.ENV_TYPE != EnvType.LOCAL:
    LOG_DIR = '/home/%s/logs/custom' % APP_NAME
else:
    if platform.system() == 'Windows':
        LOG_DIR = r'c:\logs\tone\logs'
    else:
        LOG_DIR = os.path.join(os.path.expanduser('~'), 'tone', 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[TONE][%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d %(funcName)s]:%(message)s'
        },
        'verbose': {
            'format': '[SCHEDULE][%(levelname)s][%(asctime)s][%(filename)s:%(lineno)d %(funcName)s]:%(message)s'
        },
        'simple': {
            'format': '[TONE]%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'acl': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '%s/acl.log' % LOG_DIR,
            'maxBytes': 1024 * 1024 * 200,
            'backupCount': 10,
            'formatter': 'standard',
        },
        'database': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '%s/sql.log' % LOG_DIR,
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'schedule': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '{}/schedule.log'.format(LOG_DIR),
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'message': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '{}/message.log'.format(LOG_DIR),
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'test_plan': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '{}/test_plan.log'.format(LOG_DIR),
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'callback': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '{}/callback.log'.format(LOG_DIR),
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'sync_test_farm': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '{}/sync_test_farm.log'.format(LOG_DIR),
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'aliyun': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '{}/aliyun.log'.format(LOG_DIR),
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 2,
            'formatter': 'standard',
        },
        'error': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '{}/error.log'.format(LOG_DIR),
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'all': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '%s/all.log' % LOG_DIR,
            'maxBytes': 1024 * 1024 * 200,
            'backupCount': 10,
            'formatter': 'standard',
        },
    },
    'loggers': {
        'acl': {
            'handlers': ['acl'],
            'level': 'INFO',
            'propagate': True,
        },
        'schedule': {
            'handlers': ['schedule'],
            'level': 'INFO',
            'propagate': False,
        },
        'sync_test_farm': {
            'handlers': ['sync_test_farm'],
            'level': 'INFO',
            'propagate': False,
        },
        'message': {
            'handlers': ['message'],
            'level': 'INFO',
            'propagate': False,
        },
        'test_plan': {
            'handlers': ['test_plan'],
            'level': 'INFO',
            'propagate': False,
        },
        'callback': {
            'handlers': ['callback'],
            'level': 'INFO',
            'propagate': False,
        },
        'aliyun': {
            'handlers': ['aliyun'],
            'level': 'INFO',
            'propagate': False,
        },
        'error': {
            'handlers': ['error'],
            'level': 'INFO',
            'propagate': True,
        },
        '': {
            'handlers': ['all'],
            'level': 'WARNING',
        },
    },
}

