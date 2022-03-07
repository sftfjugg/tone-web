from tone.core.utils.config_parser import cp

REDIS_CACHE_SWITCH = True

REDIS_HOST = cp.get('redis_host')
REDIS_PORT = cp.getint('redis_port')
# REDIS_USERNAME = cp.get('redis_username')
REDIS_PASSWORD = cp.get('redis_password')
REDIS_CACHE_DB = cp.getint('redis_cache_db')
REDIS_BROKER_DB = cp.getint('celery_broker_db')
REDIS_BACKEND_DB = cp.getint('celery_backend_db')
