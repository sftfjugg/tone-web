# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from tone.core.utils.helper import CommResp
from tone.core.common.expection_handler.error_catch import api_catch_error
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.models import TestJob


@api_catch_error
def get_product_version(request):
    resp = CommResp()
    data = request.GET
    product_id = data.get('product_id', None)
    if product_id:
        product_version = TestJob.objects.filter(product_id=product_id).values('product_version').distinct()
    else:
        product_version = TestJob.objects.all().values('product_version').distinct()
    resp.data = sorted(
        list(set([job['product_version'].rstrip() for job in product_version if job['product_version']])))
    return resp.json_resp()
