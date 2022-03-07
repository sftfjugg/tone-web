# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from functools import wraps
import traceback

from django.conf import settings
from rest_framework.response import Response

from tone.core.utils.helper import CommResp
from tone.core.common.log_manager import get_logger


def views_catch_error(func):
    """
    视图类异常捕获
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            logger = get_logger()
            try:
                err_code = eval(str(err))
                code = err_code[0]
                msg = err_code[1]
            except SyntaxError:
                error_detail = traceback.format_exc()
                code = 500
                if settings.DEBUG:
                    msg = error_detail
                else:
                    msg = '系统有误，请联系开发人员'
            logger.error("error: {}".format(msg))
            return Response({'code': code, 'msg': msg})

    return wrapper


def api_catch_error(func):
    """
    视图类异常捕获
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            resp = CommResp()
            logger = get_logger()
            try:
                err_code = eval(str(err))
                code = err_code[0]
                msg = err_code[1]
            except SyntaxError:
                msg = str(err)
                code = 500
            resp.result = False
            if settings.ENV_TYPE == 'prod':
                resp.msg = '系统错误，请联系开发'
            else:
                resp.msg = msg
            resp.code = code
            logger.error("error: {}".format(traceback.print_exc()))
            return resp.json_resp()

    return wrapper
