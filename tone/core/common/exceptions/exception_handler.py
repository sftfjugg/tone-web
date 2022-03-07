import logging
import os
import traceback

from django.db import IntegrityError
from rest_framework import status
from rest_framework.response import Response

from tone.core.common.exceptions import exception_code
from tone.core.common.exceptions.exception_class import BaseAPIException


def common_exception_handler(exc, context):
    if isinstance(exc, BaseAPIException):
        error_code = exc.code
        error_msg = exc.msg
    elif isinstance(exc, IntegrityError):
        error_code, error_msg = _catch_integrity_error(exc)
    else:
        error_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if os.environ.get('API_TEST_ENV') == 'true':
            error_msg = str(exc)
            traceback.print_exc()
        else:
            error_msg = exception_code.SERVER_ERROR_500['msg']

    if _need_raise_exc(error_code):
        raise exc
    return Response(dict(code=error_code, msg=error_msg), status=error_code)


def _need_raise_exc(error_code):
    if status.is_server_error(error_code) and os.environ.get('API_TEST_ENV') != 'true':
        return True
    return False


def _catch_integrity_error(exc):
    """
    # ('UNIQUE constraint failed: workspace.show_name')
    # (1062, "Duplicate entry 'eleme' for key 'workspace_name_cff03e24_uniq'")
    """
    try:
        if len(exc.args) == 1:
            error_info_list = exc.args[0].split(".")
            model_name = error_info_list[0].split(':')[-1]
            field_name = error_info_list[1]
            error_code = exception_code.DATA_EXISTS_203['code']
            error_msg = '{} {} 已经存在'.format(model_name, field_name)
        else:
            if 'cannot be null' in exc.args[1]:
                error_code = exception_code.FIELD_REQUIRED_202['code']
                error_msg = exception_code.FIELD_REQUIRED_202['msg']
            else:
                error_code = exception_code.DATA_EXISTS_203['code']
                error_info_list = exc.args[1].split("'")
                input_msg = error_info_list[1]
                field_info_list = error_info_list[3].split('_')
                model_name = field_info_list[0]
                field_info_list = field_info_list[1:-2]
                field_name = '_'.join(field_info_list)
                error_msg = '{} {} "{}" 已经存在'.format(model_name, field_name, input_msg)
    except Exception as e:
        error_code = exception_code.PARAM_ERROR_204['code']
        error_msg = exception_code.PARAM_ERROR_204['msg']
        logging.error(str(e))
    return error_code, error_msg
