from tone.core.utils.config_parser import cp

AUTH_USER_MODEL = 'tone.User'

ALI_SSO_SERVER = cp.get('ali_sso_server')
LOGIN_URL = cp.get('login_url')
LOGOUT_URL = cp.get('logout_url')
ACL_URL = cp.get('acl_url')
ACL_SERVER = cp.get('acl_server')
ACL_CONFIG = cp.get('acl_config')
ACL_VERSION = cp.get('acl_version')
ACL_ACCESS_KEY = cp.get('acl_access_key')
ACL_SECRET_KEY = cp.get('acl_secret_key')

ENV_MODE = cp.get('env_mode')
SSO_HOST = cp.get('sso_host')
UCENTER_SERVER_ADDR = cp.get('ucenter_server_addr')
UCENTER_SERVER_KEY = cp.get('ucenter_server_key')
UCENTER_AUTH_SIGN_KEY = cp.get('ucenter_auth_sign_key')
UCENTER_LOGIN_URL = cp.get('ucenter_login_url')
UCENTER_LOGOUT_URL = cp.get('ucenter_logout_url')
UCENTER_REGISTER_URL = cp.get('ucenter_register_url')
DOMAIN = cp.get('domain')
