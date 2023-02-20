from tone.settings import cp


TONE_STORAGE_DOMAIN = cp.get('tone_storage_domain')
TONE_STORAGE_HOST = cp.get('tone_storage_host')
TONE_STORAGE_PROXY_PORT = cp.get('tone_storage_proxy_port')
TONE_STORAGE_SFTP_PORT = cp.getint('tone_storage_sftp_port')
TONE_STORAGE_BUCKET = cp.get('tone_storage_bucket')
TONE_STORAGE_USER = cp.get('tone_storage_user')
TONE_STORAGE_PASSWORD = cp.get('tone_storage_password')
TONE_OUTSIDE_DOMAIN = cp.get('tone_outside_domain')
