# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import traceback
import logging
from functools import wraps

logger_acl = logging.getLogger('acl')


def catch_error(func):
    """
    异常捕获
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as err:
            traceback.print_exc(err)
            logger_acl.error('error is {}'.format(err))
        return wrapper()
