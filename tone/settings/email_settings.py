from tone.core.utils.config_parser import cp


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = cp.get('email_host')
EMAIL_HOST_PASSWORD = cp.get('email_password')
EMAIL_HOST_USER = DEFAULT_FROM_EMAIL = cp.get('email_user')
EMAIL_TIMEOUT = 60
EMAIL_PORT = 80

MSG_SWITCH_ON = True if cp.get('msg_switch') in [True, 'true', 1, '1', 'on'] else False
