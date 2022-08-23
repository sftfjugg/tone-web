# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import json
import uuid

from django.db import transaction
from django.http import JsonResponse

from tone.core.common.toneagent import add_server_to_toneagent
from tone.models import TestJob, TestJobCase, TestJobSuite, JobTagRelation, Project, JobTag, Baseline, TestTemplate, \
    JobType, TestSuite, TestCase, TestServer, CloudServer, TestCluster, ServerTag, Workspace, KernelInfo
from tone.core.utils.helper import CommResp
from tone.core.handle.job_handle import JobDataHandle
from tone.core.common.verify_token import token_required
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.error_catch import api_catch_error
from tone.serializers.job.test_serializers import JobTestSerializer, JobSerializerForAPI


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
