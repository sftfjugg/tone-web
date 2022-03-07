from rest_framework.exceptions import APIException

from tone.core.common.exceptions import exception_code


class BaseAPIException(APIException):
    def __init__(self, code=None, msg=None):
        self.code = code
        self.msg = msg
        super().__init__()


class NoMorePageException(BaseAPIException):
    def __init__(self, code=exception_code.SUCCESS_200['code'], msg=exception_code.SUCCESS_200['msg']):
        super().__init__(code, msg)


class FieldRequiredException(BaseAPIException):
    def __init__(self, code=exception_code.FIELD_REQUIRED_202['code'], msg=exception_code.FIELD_REQUIRED_202['msg']):
        super().__init__(code, msg)


class DataExistsException(BaseAPIException):
    def __init__(self, code=exception_code.DATA_EXISTS_203['code'], msg=exception_code.DATA_EXISTS_203['msg']):
        super().__init__(code, msg)


class StarAgentException(BaseAPIException):
    def __init__(self, code=exception_code.STARAGENT_ERROR_511['code'], msg=exception_code.STARAGENT_ERROR_511['msg']):
        super().__init__(code, msg)


class ToneAgentException(BaseAPIException):
    def __init__(self, code=exception_code.TONEAGENT_ERROR_512['code'], msg=exception_code.TONEAGENT_ERROR_512['msg']):
        super().__init__(code, msg)


class AliYunException(BaseAPIException):
    def __init__(self, code=exception_code.ALIYUN_ERROR_513['code'], msg=exception_code.ALIYUN_ERROR_513['code']):
        super().__init__(code, msg)
