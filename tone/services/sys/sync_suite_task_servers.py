import base64
import hashlib
import hmac
import json
import logging
import time
import urllib
import urllib.request as urllib2

from tone import settings
from tone.celery import app
from tone.core.common import constant
from tone.core.common.toneagent import SendTaskRequest
from tone.core.utils.config_parser import get_config_from_db
from tone.models import BaseConfig, SuiteData, datetime, CaseData


logger = logging.getLogger('schedule')


def sync_suite_task():
    # 更新任务运行状态 running
    BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_STATE').update(config_value='running')
    # 获取suite name 列表
    line_info_list = get_suite_or_case(suite_name='')
    # suite 信息 [[suite_name, test_type], ...]
    suite_data_list = [[line_info[0], line_info[-1]] for line_info in line_info_list]
    if not suite_data_list:
        # 更新任务运行状态
        BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_STATE').update(config_value='waiting')
        return False

    origin_suite_list = SuiteData.objects.all().values_list('name', flat=True)
    suite_name_list = list()
    for suite_data in suite_data_list:
        tmp_suite_name = suite_data[0]
        tmp_test_type = suite_data[1]
        if tmp_test_type not in ['functional', 'stress', 'performance']:
            # 更新任务运行状态
            BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_STATE').update(config_value='waiting')
            return False
        # 将每个suite下的 case信息同步更新到 SuiteData 和 CaseData
        tmp_suite_obj = SuiteData.objects.filter(name=tmp_suite_name).first()
        if tmp_suite_obj is None:
            tmp_suite_obj = SuiteData.objects.create(
                name=tmp_suite_name,
                test_type=tmp_test_type,
                test_framework='tone',
                description=''
            )
        sync_case_event(tmp_suite_name, tmp_suite_obj.id, tmp_suite_obj.description)
        suite_name_list.append(tmp_suite_name)
    # 更新suite
    SuiteData.objects.filter(name__in=list(set(origin_suite_list) - set(suite_name_list))).delete()
    # 同步成功后更新最后一次更新时间
    BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_LAST_TIME').update(config_value=datetime.now())
    # 更新任务运行状态
    BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_STATE').update(config_value='waiting')
    return True


@app.task
def sync_case_event(suite_name, suite_id, desc=''):
    """获取case信息并加入CaseData"""
    # 获取suite的 case 列表
    line_info_list = get_suite_or_case(suite_name)
    if not line_info_list:
        return
    tmp_case_obj_list = list()
    case_name_list = [line_info[-1].split(':')[-1] for line_info in line_info_list[1:]]
    if not case_name_list:
        return
    # 记录原有的case数据
    origin_case_list = CaseData.objects.filter(suite_id=suite_id).values_list('name', flat=True)
    for tmp_case_name in case_name_list:
        tmp_case_obj = CaseData.objects.filter(name=tmp_case_name, suite_id=suite_id).first()
        if tmp_case_obj is None:
            tmp_case_obj_list.append(CaseData(name=tmp_case_name, suite_id=suite_id, description=desc))
    CaseData.objects.bulk_create(tmp_case_obj_list)
    # 删除不存在的case
    CaseData.objects.filter(suite_id=suite_id, name__in=list(set(origin_case_list) - set(case_name_list))).delete()


def get_suite_or_case(suite_name):
    """
    从staragent获取suite 信息  或者 suite下case信息
    :param suite_name:  suite name，为空表示 获取suite信息，不为空表示case信息
    :return: list 信息列表
    """
    test_framework = 'TONE_SYNC'
    server_conf = json.loads(get_config_from_db('SUITE_SYNC_SERVER'))
    server_sn = server_conf['sn']
    clone_flag = '' if suite_name else 'true'
    command = "{}={} {}".format(constant.SCRIPT_FLAG, test_framework, clone_flag)
    # 获取suite name 列表
    args = suite_name
    user = 'root'
    sync = 'true'
    timeout = 3600
    command = "{} {}".format(command, base64.b64encode(bytes('false ' + args, 'utf-8')).decode()) if args else command
    exeurl = "plugin://ostest_exec/ostest_wrapper.sh '{}'".format(command)
    data = {
        'servicetag': server_sn, 'user': user, 'sync': sync,
        'timeout': timeout, 'key': settings.STARAGENT_KEY,
        'exemode': 'nologin', 'exeurl': exeurl,
        'timestamp': int(time.time()),
    }
    sign_format = ''.join('{0}{{{0}}}'.format(_) for _ in sorted(data.keys()))
    sign_string = sign_format.format(**data)
    data['sign'] = hmac.new(settings.STARAGENT_SECRET.encode(),
                            sign_string.encode(),
                            digestmod=hashlib.sha1).hexdigest()
    url = '{}/api/task'.format(settings.STARAGENT_URL)
    try:
        req = urllib2.Request(url, urllib.parse.urlencode(data).encode())
        opener = urllib2.build_opener()
        response = opener.open(req, timeout=600)
        result = response.read()
        json_data = json.JSONDecoder().decode(result.decode())
    except Exception:
        return []

    origin_str = json_data.get('JOBRESULT').strip()
    if not json_data['SUCCESS'] or not origin_str:
        return []

    origin_line_list = origin_str.split('\n')
    line_info_list = [origin_line.strip().split(' ') for origin_line in origin_line_list]
    return line_info_list


def sync_case_info_by_toneagent():
    script = BaseConfig.objects.filter(config_type='script', config_key='TONE_SYNC_CASE')
    if not script.exists():
        logger.warning('sync_case_info_by_toneagent: no sync case script!')
        return False, 'no `TONE_SYNC_CASE` script'
    request = SendTaskRequest(settings.TONEAGENT_ACCESS_KEY, settings.TONEAGENT_SECRET_KEY)
    if not get_config_from_db('SUITE_SYNC_SERVER'):
        logger.warning('sync_case_info_by_toneagent: no sync case server config!')
        return False, 'no `SUITE_SYNC_SERVER` config'
    request.set_ip(json.loads(get_config_from_db('SUITE_SYNC_SERVER')).get('ip'))
    request.set_script(script.first().config_value)
    request.set_script_type('shell')
    request.set_sync('true')
    request.set_timeout(180)
    res = request.send_request()
    if not res['SUCCESS']:
        logger.warning('sync_case_info_by_toneagent: sync case failed: result:{}'.format(res))
        return False, res['ERROR_MSG']
    logger.info('sync_case_info_by_toneagent: sync case success: result:{}'.format(res))
    return True, res['RESULT']['TASK_RESULT']


def parse_toneagent_result(data):
    lines = data.strip().split('\n')
    suite_type_map = {}
    suite_conf_list_map = {}
    tmp_suite_flag = False
    tmp_type_flag = False
    index_line = False
    tmp_conf_list = []
    tmp_suite_name = ''
    for each_line in lines:
        if not each_line:
            continue
        if index_line:
            index_line = False
            continue
        if not tmp_suite_flag and 'suite:' in each_line:
            tmp_suite_name = each_line.split(':')[1].strip()
            tmp_suite_flag = True
            continue
        if not tmp_type_flag and 'type:' in each_line:
            tmp_type = each_line.split(':')[1].strip()
            suite_type_map[tmp_suite_name] = tmp_type
            tmp_type_flag = True
            index_line = True
            continue
        if each_line.startswith('-----'):
            tmp_suite_flag = False
            tmp_type_flag = False
            suite_conf_list_map[tmp_suite_name] = tmp_conf_list
            tmp_conf_list = []
            continue
        tmp_conf = each_line.split()[-1]
        if ':' in tmp_conf:
            tmp_conf_name = tmp_conf.split(':')[-1].strip()
            tmp_conf_list.append(tmp_conf_name)
    else:
        if tmp_conf_list:
            suite_conf_list_map[tmp_suite_name] = tmp_conf_list
    return suite_type_map, suite_conf_list_map


def sync_suite_tone_task():
    BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_STATE').update(config_value='running')
    sync_flag, data = sync_case_info_by_toneagent()
    if not sync_flag:
        logger.warning('sync_suite_tone_task: sync failed, data:{}'.format(data))
        BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_STATE').update(config_value='waiting')
        return False
    suite_type_map, suite_conf_list_map = parse_toneagent_result(data)
    origin_suite_list = SuiteData.objects.all().values_list('name', flat=True)
    for tmp_suite_name, tmp_test_type in suite_type_map.items():
        tmp_suite_obj = SuiteData.objects.filter(name=tmp_suite_name, test_type=tmp_test_type).first()
        if tmp_suite_obj is None:
            tmp_suite_obj = SuiteData.objects.create(
                name=tmp_suite_name,
                test_type=tmp_test_type,
                test_framework='tone',
                description=''
            )
        case_name_list = suite_conf_list_map.get(tmp_suite_name, [])
        suite_id = tmp_suite_obj.id
        if not case_name_list:
            continue
        tmp_case_obj_list = []
        # 记录原有的case数据
        origin_case_list = CaseData.objects.filter(suite_id=suite_id).values_list('name', flat=True)
        for tmp_case_name in case_name_list:
            tmp_case_obj = CaseData.objects.filter(name=tmp_case_name, suite_id=suite_id).first()
            if tmp_case_obj is None:
                tmp_case_obj_list.append(
                    CaseData(
                        name=tmp_case_name,
                        suite_id=suite_id,
                        description=''
                    )
                )
        CaseData.objects.bulk_create(tmp_case_obj_list)
        # 删除不存在的case
        CaseData.objects.filter(suite_id=suite_id, name__in=list(set(origin_case_list) - set(case_name_list))).delete()

    SuiteData.objects.filter(name__in=list(set(origin_suite_list) - set(suite_type_map.keys()))).delete()

    BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_LAST_TIME').update(
        config_value=datetime.now())
    # 更新任务运行状态
    BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_STATE').update(config_value='waiting')
    logger.info('sync_suite_tone_task: sync success')
    return True


def sync_suite_desc_tone_task():
    for tmp_suite_obj in SuiteData.objects.all():
        tmp_suite_name = tmp_suite_obj.name
        command = 'cat /tmp/tone_work_dir/tone/tests/{}/readme.md'.format(tmp_suite_name)
        request = SendTaskRequest(settings.TONEAGENT_ACCESS_KEY, settings.TONEAGENT_SECRET_KEY)
        if not get_config_from_db('SUITE_SYNC_SERVER'):
            logger.warning('sync_suite_desc_tone_task: no sync case server config!')
            return
        request.set_ip(json.loads(get_config_from_db('SUITE_SYNC_SERVER')).get('ip'))
        request.set_script(command)
        request.set_script_type('script')
        request.set_sync('true')
        request.set_timeout(180)
        res = request.send_request()
        if not res['SUCCESS'] or res['RESULT']['TASK_STATUS'] != 'success':
            logger.warning('sync_suite_desc_tone_task: sync case failed: result:{}'.format(res))
            continue
        logger.info('sync_suite_desc_tone_task: sync case success: result:{}'.format(res))
        description = res['RESULT']['TASK_RESULT']

        tmp_suite_obj.description = description
        tmp_suite_obj.save()
        for tmp_case_obj in CaseData.objects.filter(suite_id=tmp_suite_obj.id):
            tmp_case_name = tmp_case_obj.name
            CaseData.objects.filter(name=tmp_case_name, suite_id=tmp_suite_obj.id).update(description=description)
    return True
