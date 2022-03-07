import base64
import datetime
import hashlib
import hmac
import uuid
from urllib.parse import urlencode, quote_plus

import requests


class AliyunAuth(object):

    def __init__(self, access_id, access_key, config, url='http://eci.aliyuncs.com/', version="2018-08-08"):
        assert config['Action'], "Value error"

        self.config = config
        self.url = url
        self.access_id = access_id
        self.access_key = access_key
        self.__data = dict({
            "AccessKeyId": self.access_id,
            "SignatureMethod": 'HMAC-SHA1',
            "SignatureVersion": "1.0",
            "SignatureNonce": str(uuid.uuid1()),
            "Timestamp": datetime.datetime.utcnow().isoformat(),
            "Version": version,
            "Format": "JSON",
        }, **config)

    @property
    def data(self):
        return self.__data

    @data.setter
    def data(self, value):
        if self.__data:
            raise AssertionError("not allow opeartion")
        self.__data = value

    @staticmethod
    def percent_encode(encodeStr):
        if isinstance(encodeStr, bytes):
            encodeStr = encodeStr.decode('utf-8')
        res = quote_plus(encodeStr.encode('utf-8'), '')
        res = res.replace('+', '%20').replace('*', '%2A').replace('%7E', '~')
        return res

    def auth(self):
        base = sorted(self.data.items(), key=lambda data: data[0])
        canstring = ''
        for k, v in base:
            canstring += '&' + self.percent_encode(k) + '=' + self.percent_encode(v)
        self.access_key += "&"
        data = 'GET&%2F&' + self.percent_encode(canstring[1:])
        self._salt(data)
        return self.data

    def _salt(self, data):
        result = data.encode(encoding='utf-8')
        uri = hmac.new(self.access_key.encode("utf-8"), result, hashlib.sha1).digest()
        key = base64.b64encode(uri).strip()
        self.data['Signature'] = key
        return self.data


class AliyunAPIRequest():
    def __init__(self, access_id, access_key, url='http://eci.aliyuncs.com/', version="2018-08-08"):
        self.url = url
        self.version = version
        self.access_id = access_id
        self.access_key = access_key

    def get(self, action, config=None):
        param_config = {
            "Action": action
        }
        if config and isinstance(config, dict):
            param_config.update(config)
        auth = AliyunAuth(self.access_id, self.access_key, config=param_config, url=self.url, version=self.version)
        token = auth.auth()
        params = urlencode(token)
        req = requests.get('%s?%s' % (self.url, params))
        res = req.content
        return res
