# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import logging

from tone import settings
from tone.core.utils.helper import CommResp

logger = logging.getLogger()


def get_path(request):
    resp = CommResp()
    path = request.GET.get('path')
    resp.data = f"http://{settings.TONE_STORAGE_DOMAIN}:{settings.TONE_STORAGE_PROXY_PORT}{path}"
    return resp.json_resp()
