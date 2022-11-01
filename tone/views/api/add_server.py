# _*_ coding:utf-8 _*_

import json
import uuid

from django.http import JsonResponse

from tone.core.common.toneagent import add_server_to_toneagent
from tone.models import Workspace, TestServer
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.error_catch import api_catch_error


@api_catch_error
def add_server(request):
    """
    add server api for toneagent client
    """
    if request.method != 'POST':
        raise ValueError(ErrorCode.SUPPORT_POST)
    data = json.loads(request.body)
    ip = data.get('ip')
    tsn = data.get('tsn')
    if TestServer.objects.filter(tsn=tsn).exists():
        return JsonResponse({
            'code': ErrorCode.SERVER_TSN_ALREADY_EXIST[0],
            'msg': ErrorCode.SERVER_TSN_ALREADY_EXIST[1]
        })
    common_ws = Workspace.objects.filter(is_common=True).first()
    test_server = TestServer.objects.create(
        ip=ip,
        tsn=tsn,
        state='Available',
        owner=0,
        ws_id=common_ws.id,
        channel_type='toneagent',
        description='created by toneagent client',
        sn=uuid.uuid4(),
    )
    res = add_server_to_toneagent(ip, server_tsn=tsn)
    if not res.get('SUCCESS'):
        TestServer.objects.filter(id=test_server.id).delete()
        return JsonResponse({
            'code': ErrorCode.ADD_SERVER_TO_TONEAGENT_FAILED[0],
            'msg': ErrorCode.ADD_SERVER_TO_TONEAGENT_FAILED[1]
        })
    return JsonResponse({
        'code': ErrorCode.CODE,
        'msg': ErrorCode.SUCCESS
    })
