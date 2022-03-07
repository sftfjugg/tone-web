# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import random
import string

from tone.models import User
from tone.core.common.services import CommonService
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import TokenException


class InterfaceTokenService(CommonService):

    @staticmethod
    def create(operator):
        username = operator.username
        token = ''.join(random.sample(string.ascii_letters + string.digits, 32))
        assert username, TokenException(ErrorCode.PERMISSION_ERROR)
        if not User.objects.filter(username=username).exists():
            raise TokenException(ErrorCode.USERNAME_NOT_REGISTER)
        User.objects.filter(username=username).update(token=token)
