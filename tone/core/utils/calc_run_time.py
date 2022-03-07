# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import time
from functools import wraps
import logging

logger = logging.getLogger('acl')


def calc_run_time(decorator):
    def inner(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            res = func(*args, **kwargs)
            end_time = time.time()
            use_time = end_time - start_time
            logger.error(f"{decorator}: run time: {use_time}")
            return res

        return wrapper

    return inner
