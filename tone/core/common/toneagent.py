import hmac
import logging
import time
import json
import ssl
import base64
import hashlib
import urllib
import urllib.request as urllib2

import requests

from django.conf import settings

from tone.core.cloud.aliyun.ecs_assistant import EcsAssistant
from tone.models import CloudAk

logger = logging.getLogger()


class ToneAgentRequest(object):

    def __init__(self, access_key, secret_key):
        self._domain = settings.TONEAGENT_DOMAIN
        self._access_key = access_key
        self._secret_key = secret_key
        self._data = {
            "key": self._access_key,
            # 防止多次请求
            # "nonce": str(uuid.uuid1()),
            # 一定时间内有效
            "timestamp": time.time(),
        }

    def _sign(self):
        sign_str = ""
        for k in sorted(self._data.keys()):
            sign_str += k
            sign_str += str(self._data[k])
        sign = hmac.new(self._secret_key.encode('utf-8'), sign_str.encode('utf-8'), hashlib.sha1).digest()
        base64_sign = base64.b64encode(sign).strip()
        self._data['sign'] = base64_sign.decode()
        return self._data

    def set_proxy(self, domain):
        self._domain = domain

    def request(self, api, data, method='post'):
        self._data.update(data)
        self._sign()
        url = '{domain}/{api}'.format(domain=self._domain, json=data, api=api)
        data = self._data
        try:
            if method == 'get':
                res = requests.get(url, params=data, verify=False)
            else:
                res = requests.post(url, json=data, verify=False)
            return res.json()
        except Exception as e:
            # print(res.text)
            print(e)
            return {'SUCCESS': False, 'ERROR_MSG': 'agent error'}


class SendTaskRequest(ToneAgentRequest):
    def __init__(self, access_key, secret_key):
        self._api = 'api/task'
        self._request_data = dict(
            ip='',
            tsn='',
            script='',
            args='',
            env='',
            sync='false',
            script_type='shell',
            timeout=3600
        )
        super().__init__(access_key=access_key, secret_key=secret_key)

    def set_ip(self, ip):
        self._request_data['ip'] = ip

    def set_tsn(self, tsn):
        self._request_data['tsn'] = tsn

    def set_script(self, script):
        encrypt_script = base64.b64encode(script.encode('utf-8'))
        self._request_data['script'] = encrypt_script.decode()

    def set_script_type(self, script_type):
        self._request_data['script_type'] = script_type

    def set_args(self, args):
        self._request_data['args'] = args

    def set_env(self, env):
        self._request_data['env'] = env

    def set_cwd(self, cwd):
        self._request_data['cwd'] = cwd

    def set_sync(self, sync):
        self._request_data['sync'] = sync

    def set_timeout(self, timeout):
        self._request_data['timeout'] = timeout

    def send_request(self):
        return self.request(self._api, self._request_data)


class RemoveAgentRequest(ToneAgentRequest):
    def __init__(self, access_key, secret_key):
        self._api = 'api/agent/remove'
        self._request_data = dict(
            ip='',
        )
        super().__init__(access_key=access_key, secret_key=secret_key)

    def set_ip(self, ip):
        self._request_data['ip'] = ip

    def set_tsn(self, tsn):
        self._request_data['tsn'] = tsn

    def send_request(self, method='post'):
        return self.request(self._api, self._request_data, method=method)


class AddAgentRequest(ToneAgentRequest):
    def __init__(self, access_key, secret_key):
        self._api = 'api/agent/add'
        self._request_data = dict(
            ip='',
            public_ip='',
            mode='active',
            arch='',
        )
        super().__init__(access_key=access_key, secret_key=secret_key)

    def set_ip(self, ip):
        self._request_data['ip'] = ip

    def set_public_ip(self, public_ip):
        self._request_data['public_ip'] = public_ip

    def set_mode(self, mode):
        self._request_data['mode'] = mode

    def set_arch(self, arch):
        self._request_data['arch'] = arch

    def set_version(self, version):
        self._request_data['version'] = version

    def set_description(self, description):
        self._request_data['description'] = description

    def send_request(self):
        return self.request(self._api, self._request_data)


def tone_agent_info(ip='', tsn=''):
    timestamp = int(time.time())
    data = {
        'key': settings.TONEAGENT_ACCESS_KEY,
        'timestamp': timestamp,
    }
    if ip:
        data.update({'ip': ip})
    else:
        data.update({'tsn': tsn})
    sign_format = ''.join('{0}{{{0}}}'.format(_) for _ in sorted(data.keys()))
    sign_string = sign_format.format(**data)
    sign = hmac.new(settings.TONEAGENT_SECRET_KEY.encode('utf-8'),
                    sign_string.encode('utf-8'),
                    hashlib.sha1).digest()
    base64_sign = base64.b64encode(sign).strip()
    sign = base64_sign.decode()
    data['sign'] = sign
    param_str = urllib.parse.urlencode(data)
    agent_url = '{}/api/agent/info?{}'.format(settings.TONEAGENT_DOMAIN, param_str)
    return agent_url


def server_check(ip):
    agent_url = tone_agent_info(ip=ip)
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
        req = urllib2.Request(agent_url)
        opener = urllib2.build_opener()
        response = opener.open(req, timeout=60)
        result = response.read()
        json_data = json.JSONDecoder().decode(result.decode())
        if not json_data['SUCCESS']:
            return json_data['ERROR_CODE'], None, json_data['ERROR_MSG']
        elif json_data['RESULT']['STATUS'] != 'online':
            return 205, None, 'toneagent service down'
        else:
            return 200, None, json_data
    except urllib2.HTTPError as ex1:
        error_msg = "toneagent:http error ({}:{})\n{}".format(ex1.code, ex1.reason, ex1.fp.read())
        err_code = ex1.code
    except urllib2.URLError as ex2:
        error_msg = "toneagent:url error ({}:{}:{})".format('201', ex2.reason, agent_url)
        err_code = 201
    except Exception as e:
        err_code = 700
        error_msg = str(e)
    return err_code, None, error_msg


def remove_server_from_toneagent(ip_list, tsn_list=None):
    request = RemoveAgentRequest(settings.TONEAGENT_ACCESS_KEY, settings.TONEAGENT_SECRET_KEY)
    request.set_ip(ip_list)
    request.set_tsn(tsn_list)
    res = request.send_request()
    return res


def add_server_to_toneagent(server_ip, pub_ip=None, arch=None, version=None, mode='active'):
    request = AddAgentRequest(settings.TONEAGENT_ACCESS_KEY, settings.TONEAGENT_SECRET_KEY)
    request.set_ip(server_ip)
    request.set_public_ip(pub_ip)
    request.set_arch(arch)
    request.set_version(version)
    request.set_mode(mode)
    request.set_description('created by tone system')
    add_agent_result = request.send_request()
    logger.info(f'add agent request result: {add_agent_result}')
    return add_agent_result


def deploy_agent_by_ecs_assistant(cloud_server, arch, version, mode='active'):
    # 1.请求agent proxy api添加机器、获取tsn
    add_agent_result = add_server_to_toneagent(
        server_ip=cloud_server.private_ip,
        pub_ip=cloud_server.pub_ip,
        arch=arch, version=version, mode=mode
    )
    if not add_agent_result.get("SUCCESS"):
        return False, add_agent_result.get('RESULT') or add_agent_result.get('msg')

    tsn = add_agent_result['RESULT']['TSN']
    rpm_link = add_agent_result['RESULT']['RPM_LINK']

    # 2.调用云助手部署agent
    ak = CloudAk.objects.get(id=cloud_server.ak_id)
    ea = EcsAssistant(
        access_key=ak.access_id,
        secret_key=ak.access_key,
        region=cloud_server.region,
        zone=cloud_server.zone,
        resource_group_id=ak.resource_group_id
    )
    return ea.deploy_agent(cloud_server.instance_id, tsn, rpm_link)
