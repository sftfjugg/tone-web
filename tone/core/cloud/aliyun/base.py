from __future__ import print_function

try:
    import httplib
except ImportError:
    import http.client as httplib
import time
import json
import itertools
import mimetypes
from urllib.parse import urlparse


class FileItem(object):
    def __init__(self, filename=None, content=None):
        self.filename = filename
        self.content = content


class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = 'PYTHON_SDK_BOUNDARY'
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, str(value)))
        return

    def add_file(self, field_name, filename, file_handler, mimetype=None):
        """Add a file to be uploaded."""
        body = file_handler.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((field_name, filename, mimetype, body))
        return

    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.
        parts = []
        part_boundary = '--' + self.boundary

        # Add the form fields
        parts.extend([part_boundary, 'Content-Disposition: form-data; name="%s"' % name,
                     'Content-Type: text/plain; charset=UTF-8', '', value]
                     for name, value in self.form_fields
                     )

        # Add the files to upload
        parts.extend(
            [
                part_boundary,
                'Content-Disposition: file; name="%s"; filename="%s"' % (field_name, filename),
                'Content-Type: %s' % content_type,
                'Content-Transfer-Encoding: binary',
                '',
                body
            ]
            for field_name, filename, content_type, body in self.files
        )

        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)


class AliYunOpenApi(object):
    def __init__(self, access_id=None, access_key=None, security_token=None, version='2014-05-26',
                 url='http://ecs.aliyuncs.com/', timeout=30, ali_uid=None, enable_sts_token=False):
        intern_call = False
        self.access_id = access_id
        self.access_key = access_key
        self.ali_uid = ali_uid
        self.timeout = timeout
        self.security_token = security_token
        self.intern_call = intern_call
        self.enable_sts_token = enable_sts_token
        if url.strip().find('http', 0) == 0:
            self.url = url
        else:
            self.url = 'http://%s' % url
        self.version = version
        self.comm_param = dict()
        self.comm_param['Format'] = "json"
        self.comm_param['AccessKeyId'] = access_id
        self.comm_param['SignatureMethod'] = "HMAC-SHA1"
        self.comm_param['Timestamp'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.localtime(time.time() - 8 * 60 * 60))
        self.comm_param['SignatureVersion'] = "1.0"

        self.__domain, self.__port = self.get_domain_and_port()
        self.__httpmethod = 'POST'
        self.__access_key_id = self.access_id
        self.__access_key_secret = self.access_key

    def get_domain_and_port(self):
        parts = urlparse(self.url)
        port = parts.port
        if not port:
            port = 80
        return parts.hostname, port

    def get_request_header(self):
        return {
            'Content-type': 'application/x-www-form-urlencoded',
            'Cache-Control': 'no-cache',
            'Connection': 'Keep-Alive',
        }

    def replace_ak(self, access_key, secret_key):
        self.__access_key_id = access_key
        self.__access_key_secret = secret_key

    def set_app_info(self, app_info):
        self.__access_key_id = app_info.access_key_id
        self.__access_key_secret = app_info.access_key_secret

    def get_api_name(self):
        return ''

    def get_multipart_params(self):
        return list()

    def get_translate_paras(self):
        return dict()

    def get_application_parameters(self):
        app_params = dict()
        for key, value in self.__dict__.items():
            if not key.startswith('__') and key not in self.get_multipart_params() and not key.startswith(
                    '_RestApi__') and value is not None:
                if key.startswith('_'):
                    app_params[key[1:]] = value
                else:
                    app_params[key] = value
        translate_parameter = self.get_translate_paras()
        for key, value in app_params.items():
            if key in translate_parameter:
                app_params[translate_parameter[key]] = app_params[key]
                del app_params[key]
        return app_params


class CommonRequest(object):
    CallerBid = None
    OwnerId = None

    def to_dict(self):
        result = dict()
        for attr, value in vars(self).items():
            if value is not None:
                attr = attr.replace('_', '.')
                result[attr] = value
        return result

    def get_action_name(self):
        raise NotImplementedError('should implement `get_action_name` in request')

    def get_request(self):
        return {'param_str': json.dumps(self, default=lambda obj: obj.__dict__)}


class DescribeInstancesRequest(CommonRequest):
    RegionId = True
    InstanceIds = None

    def get_action_name(self):
        return 'DescribeInstances'


class AttachNetworkInterfaceRequest(CommonRequest):
    RegionId = True
    NetworkInterfaceId = None
    InstanceId = None

    def get_action_name(self):
        return 'AttachNetworkInterface'


class DescribeNetworkInterfacesRequest(CommonRequest):
    RegionId = True
    NetworkInterfaceName = None

    def get_action_name(self):
        return 'DescribeNetworkInterfaces'


class CreateNetworkInterfaceRequest(CommonRequest):
    RegionId = True
    VSwitchId = None
    SecurityGroupId = None
    NetworkInterfaceName = None

    def get_action_name(self):
        return 'CreateNetworkInterface'


class DescribeSecurityGroupRequest(CommonRequest):
    RegionId = True
    VpcId = None
    PageSize = None

    def get_action_name(self):
        return 'DescribeSecurityGroups'


class CreateSecurityGroupRequest(CommonRequest):
    RegionId = True
    SecurityGroupName = None
    Description = None
    VpcId = None

    def get_action_name(self):
        return 'CreateSecurityGroup'


class AuthorizeSecurityGroupRequest(CommonRequest):
    RegionId = True
    SecurityGroupId = None
    Description = None
    IpProtocol = None
    PortRange = None
    SourceCidrIp = None
    NicType = None
    Policy = None
    Priority = None

    def get_action_name(self):
        return 'AuthorizeSecurityGroup'


class BaseDriver(object):
    def get_object_items(self, obj, remove=None):
        if remove:
            return [n for n in dir(obj) if not n.startswith('_') and n not in remove]
        else:
            return [n for n in dir(obj) if not n.startswith('_')]
