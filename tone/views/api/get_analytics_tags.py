# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from django.db import connection

from tone.core.utils.helper import CommResp
from tone.core.common.expection_handler.error_catch import api_catch_error
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.constant import FILTER_JOB_TAG_SQL
from tone.models import JobTagRelation, JobTag


@api_catch_error
def get_analytics_tags(request):
    resp = CommResp()
    data = request.GET
    project_id = data.get('project_id', None)
    assert project_id, ValueError(ErrorCode.PROJECT_ID_NEED)
    with connection.cursor() as cursor:
        cursor.execute(FILTER_JOB_TAG_SQL.format(project_id=project_id))
        rows = cursor.fetchall()
        test_jobs = [row[0] for row in rows]
    tags = list(set([job_tag.tag_id for job_tag in JobTagRelation.objects.filter(job_id__in=test_jobs)]))
    resp.data = [{'tag_name': tag.name, 'tag_id': tag.id} for tag in JobTag.objects.filter(id__in=tags) if
                 tag.name != 'analytics' and tag.source_tag != 'system_tag']
    return resp.json_resp()
