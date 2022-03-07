from datetime import timedelta
import logging

from django.db.models import Q

from tone.celery import app
from tone.models import BaseConfig, SiteConfig, SitePushConfig, TestJob, datetime
from tone.services.portal.sync_portal_services import SyncPortalService
from tone.core.handle.report_handle import ReportHandle

logger = logging.getLogger('sync_test_farm')


def sync_portal_task():  # noqa: C901
    last_sync_portal = BaseConfig.objects.filter(config_type='sys', config_key='LAST_SYNC_TEST_FARM_TIME').first()
    sync_portal_flag = BaseConfig.objects.filter(config_type='sys', config_key='SYNC_TEST_FARM_FLAG').first()
    if sync_portal_flag is None:
        # 第一次执行， 同步suite ,is_all="1"
        BaseConfig.objects.create(config_type='sys', config_key='SYNC_TEST_FARM_FLAG',
                                  config_value='1', description='1：全量同步, 0：同步近三天')
        sync_flag = '1'
    else:
        sync_flag = '1' if sync_portal_flag.config_value == '1' else '0'
    if last_sync_portal is None:
        # 第一次执行， 同步suite ,is_all="1"
        BaseConfig.objects.create(config_type='sys', config_key='LAST_SYNC_TEST_FARM_TIME', config_value=datetime.now())
        is_all = '1'
    else:
        is_all = '1' if last_sync_portal.config_value == '1' else '0'
    logger.info(f'定时推送任务开始执行: sync_portal_flag：{sync_portal_flag}, is_all:{is_all}')
    # 同步suite到portal
    code, msg = sync_suite_portal(sync_flag)
    logger.info(f'推送suite data，code:{code}, msg:{msg}')
    # 查询站点信息, 获取Job列表
    site_config = SiteConfig.objects.all().first()
    site_push_config_list = SitePushConfig.objects.filter(site_id=site_config.id)
    # 默认推送起始时间为：最后一次同步时间退3天
    last_sync_time = BaseConfig.objects.filter(config_type='sys', config_key='LAST_SYNC_TEST_FARM_TIME'
                                               ).first().config_value
    last_sync_datetime = datetime.strptime(last_sync_time.split('.')[0], '%Y-%m-%d %H:%M:%S')
    default_sync_start_time = last_sync_datetime - timedelta(days=3)
    for site_push_obj in site_push_config_list:
        tmp_ws_id = site_push_obj.ws_id
        tmp_project_id = site_push_obj.project_id
        if not tmp_ws_id or not tmp_project_id:
            continue
        if not site_push_obj.sync_start_time:
            tmp_sync_start_time = default_sync_start_time
        else:
            tmp_sync_start_time = datetime.strptime(str(site_push_obj.sync_start_time).split('.')[0],
                                                    '%Y-%m-%d %H:%M:%S')
        logger.info(f'配置：{tmp_ws_id}-{tmp_project_id},推送起始时间：{tmp_sync_start_time}')
        tmp_job_name_rule = site_push_obj.job_name_rule
        q = Q()
        try:
            q &= Q(ws_id=tmp_ws_id,
                   project_id=tmp_project_id,
                   start_time__isnull=False,
                   sync_time__isnull=True,
                   name__iregex=tmp_job_name_rule)
            if is_all == '0':
                q &= Q(gmt_created__gte=tmp_sync_start_time)
            tmp_job_id_list = list(TestJob.objects.filter(q).values_list('id', flat=True))
        except Exception as error_msg:
            logger.error(error_msg)
            continue

        job_id_list = list(set(tmp_job_id_list))
        if job_id_list:
            logger.info(f'配置：{tmp_ws_id}-{tmp_project_id},推送job列表:{job_id_list}')
            [sync_job_data.delay(tmp_job_id) for tmp_job_id in job_id_list[::-1]]
            tmp_min_job_id = sorted(job_id_list)[0]
            site_push_obj.sync_start_time = TestJob.objects.get(id=tmp_min_job_id).gmt_created
            site_push_obj.save()
            logger.info(f'配置：{tmp_ws_id}-{tmp_project_id}'
                        f'更新最小job id:{tmp_min_job_id} 的创建时间{site_push_obj.sync_start_time}')
        else:
            # 起始时间大于当前时间不更新
            if not site_push_obj.sync_start_time or str(site_push_obj.sync_start_time) < str(datetime.now()):
                site_push_obj.sync_start_time = datetime.now()
                site_push_obj.save()
            logger.info(f'配置：{tmp_ws_id}-{tmp_project_id}, 当前 job 推送完毕，更新当前时间')
    BaseConfig.objects.filter(config_type='sys', config_key='LAST_SYNC_TEST_FARM_TIME'
                              ).update(config_value=datetime.now())
    return code, msg


def sync_suite_portal(is_all):
    """同步suite到portal"""
    return SyncPortalService().sync_case_meta(is_all)


def check_master_config_job(job_id):
    site_config = SiteConfig.objects.all().first()
    site_push_config_list = SitePushConfig.objects.filter(site_id=site_config.id)
    for site_push_obj in site_push_config_list:
        tmp_ws_id = site_push_obj.ws_id
        tmp_project_id = site_push_obj.project_id
        if not tmp_ws_id or not tmp_project_id:
            continue
        try:
            tmp_job_name_rule = site_push_obj.job_name_rule
            q = Q()
            q &= Q(ws_id=tmp_ws_id,
                   project_id=tmp_project_id,
                   start_time__isnull=False,
                   name__iregex=tmp_job_name_rule)
            if site_push_obj.sync_start_time:
                tmp_sync_start_time = datetime.strptime(str(site_push_obj.sync_start_time).split('.')[0],
                                                        '%Y-%m-%d %H:%M:%S')
                q &= Q(gmt_created__gte=tmp_sync_start_time)
            if job_id in list(TestJob.objects.filter(q).values_list('id', flat=True)):
                return True, 'sync_job_id_list_{}_{}'.format(tmp_ws_id, tmp_project_id)
        except Exception:
            continue
    return False, None


@app.task
def sync_job_data(job_id, check_master=False):
    """同步Job数据到portal"""
    check_master_res, tmp_sync_job_cache = check_master_config_job(job_id)
    if check_master and not check_master_res:
        return
    code, msg = SyncPortalService().sync_job(job_id)
    logger.info(f'推送job，code:{code}, msg:{msg}')
    state_map = {'pending': 0, 'running': 1, 'success': 2, 'fail': 3, 'stop': 4, 'skip': 5}
    job_obj = TestJob.objects.get(id=job_id)
    job_state = job_obj.state
    state = state_map.get(job_state)
    code, msg = SyncPortalService().sync_job_status(job_id, state)
    logger.info(f'推送job status，code:{code}, msg:{msg}')
    sync_job_state_portal(job_id)
    if job_state in ['success', 'fail', 'stop', 'skip']:
        if job_obj.test_type == 'functional':
            code, msg = SyncPortalService().sync_func_result(job_id)
            logger.info(f'推送func data，code:{code}, msg:{msg}')
        else:
            code, msg = SyncPortalService().sync_perf_result(job_id)
            logger.info(f'推送perf data，code:{code}, msg:{msg}')
        job_obj.sync_time = datetime.now()
        job_obj.save()


@app.task
def sync_job_portal(job_id):
    """同步Job到portal"""
    return SyncPortalService().sync_job(job_id)


@app.task
def sync_job_state_portal(job_id):
    """同步job状态到portal"""
    state_map = {'pending': 0, 'running': 1, 'success': 2, 'fail': 3, 'stop': 4, 'skip': 5}
    state = state_map.get(TestJob.objects.get(id=job_id).state)
    return SyncPortalService().sync_job_status(job_id, state)


@app.task
def sync_func_result_portal(test_job_id):
    """同步功能结果到portal"""
    return SyncPortalService().sync_func_result(test_job_id)


@app.task
def sync_perf_result_portal(test_job_id):
    """同步性能结果到portal"""
    return SyncPortalService().sync_perf_result(test_job_id)


@app.task
def save_report(test_job_id):
    """保存报告"""
    ReportHandle(test_job_id).save_report()


@app.task
def sync_baseline(baseline_id):
    """修改基线"""
    return SyncPortalService().sync_baseline(baseline_id)


@app.task
def sync_baseline_del(baseline_id):
    """删除基线"""
    return SyncPortalService().sync_baseline_del(baseline_id)
