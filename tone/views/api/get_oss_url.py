# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import logging
from django.http import HttpResponse
import requests

from tone import settings
from tone.core.utils.helper import CommResp

logger = logging.getLogger()


def get_path(request):
    resp = CommResp()
    path = request.GET.get('path')
    download = request.GET.get('download')
    ftp_url = f"http://{settings.TONE_STORAGE_DOMAIN}:{settings.TONE_STORAGE_PROXY_PORT}{path}"
    if download == '1':
        resp = requests.get(ftp_url)
        tmp_file = path.split('/')
        file_name = tmp_file[len(tmp_file) - 1]
        response = HttpResponse(content_type="application/octet-stream")
        response["Content-Disposition"] = 'attachment; filename={0}'.format(file_name)
        response["Access-Control-Expose-Headers"] = "Content-Disposition"
        response["Access-Control-Allow-Origin"] = "*"
        response["Server"] = "*"
        response.write(resp.content)
        return response
    else:
        resp.data = ftp_url
    return resp.json_resp()
