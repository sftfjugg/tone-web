# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""

from tone.core.utils.helper import CommResp
from tone.core.common.expection_handler.error_catch import api_catch_error
from tone.models import JobTypeItem


@api_catch_error
def add_item(request):
    resp = CommResp()
    data = request.GET
    name = data.get('name', None)
    show_name = data.get('show_name', None)
    description = data.get('description', None)
    config_index = data.get('config_index', None)
    JobTypeItem.objects.create(name=name, show_name=show_name, description=description, config_index=config_index)
    resp.result = 'success'
    return resp.json_resp()
