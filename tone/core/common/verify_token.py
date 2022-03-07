# _*_ coding:utf-8 _*_
"""
Module Description: 用户认证类
Date:
Author: Yfh
"""
import time
import json
import base64

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

from tone.models import User
from tone.core.common.expection_handler.error_code import ErrorCode


def token_required(func):
    @csrf_exempt
    def wrapper(request, *args, **kwargs):
        signature = None
        username = None
        if request.method == 'GET':
            signature = request.GET.get('signature')
            username = request.GET['username']
        elif request.method == 'POST':
            signature = request.POST.get('signature')
            username = request.POST.get('username')
        if not signature:
            data = json.loads(request.body)
            signature = data.get('signature')
            username = data.get('username')
        assert signature, ValueError(ErrorCode.TOKEN_NEED)
        return func(request, *args, **kwargs) if check_token(signature, username, request) else HttpResponse(
            json.dumps({'success': False, 'msg': 'Token invalid', 'code': 500}))

    return wrapper


def check_token(signature, user, request, expired_time=300):
    token = base64.b64decode(signature).decode('utf-8').split('|')
    if len(token) != 3:
        raise ValueError(ErrorCode.TOKEN_FORMAT_ERROR)
    username = token[0]
    _token = token[1]
    timestamp = float(token[2])
    if not User.objects.filter(username=username, token=_token).exists() or username != user:
        raise ValueError(ErrorCode.USERNAME_NOT_REGISTER)
    if time.time() - timestamp > expired_time:
        raise ValueError(ErrorCode.TOKEN_OVERDUE)
    request.user = User.objects.get(username=user)
    return True
