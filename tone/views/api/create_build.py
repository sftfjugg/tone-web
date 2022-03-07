# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import json

from tone.models import BuildJob, Workspace, Project
from tone.core.utils.helper import CommResp
from tone.core.common.expection_handler.error_catch import api_catch_error
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.verify_token import token_required


@token_required
@api_catch_error
def create_build_info(request):
    resp = CommResp()
    if request.method != 'POST':
        raise ValueError(ErrorCode.SUPPORT_POST)
    operator = request.user
    data = json.loads(request.body)
    ws_name = data.get('workspace')
    assert ws_name, ValueError('workspace must required')
    ws_queryset = Workspace.objects.filter(name=ws_name)
    if not ws_queryset.exists():
        raise ValueError('ws not exists')
    ws_id = ws_queryset.first().id
    project = Project.objects.get(ws_id=ws_id, name=data.get('project')) if \
        Project.objects.filter(ws_id=ws_id, name=data.get('project')).exists() else Project.objects.get(name='default')
    name = data.get('name')
    build_from = data.get('build_from')
    product_id = project.product_id
    project_id = project.id
    arch = data.get('arch')
    build_env = data.get('build_env')
    build_config = data.get('build_config')
    build_log = data.get('build_log')
    build_file = data.get('build_file')
    build_url = data.get('build_url')
    git_repo = data.get('git_repo')
    git_branch = data.get('git_branch')
    git_commit = data.get('git_commit')
    git_url = data.get('git_url')
    commit_msg = data.get('commit_msg')
    committer = operator.username
    compiler = data.get('compiler')
    description = data.get('description')
    assert build_from, ValueError('build_from must required')
    assert arch, ValueError('arch must required')
    assert git_branch, ValueError('git_branch must required')
    assert git_commit, ValueError('git_commit must required')
    assert commit_msg, ValueError('commit_msg must required')
    assert name, ValueError('name must required')
    build_job = BuildJob.objects.create(
        name=name,
        build_from=build_from,
        product_id=product_id,
        project_id=project_id,
        arch=arch,
        build_env=build_env,
        build_config=build_config,
        build_log=build_log,
        build_file=build_file,
        build_url=build_url,
        git_repo=git_repo,
        git_branch=git_branch,
        git_commit=git_commit,
        git_url=git_url,
        commit_msg=commit_msg,
        committer=committer,
        compiler=compiler,
        description=description,
    )
    resp.data = {'build_job_id': build_job.id}
    return resp.json_resp()
