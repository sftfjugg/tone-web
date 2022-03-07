import logging
import time
import datetime
import json
from datetime import timedelta
import base64
import requests
import urllib.request
from tone.core.common.log_manager import get_logger
from tone.core.common.services import CommonService
from tone.models import TestSuite, TestCase, TestDomain, TestMetric, TestJob, Project, Repo, ProjectBranchRelation, \
    RepoBranch, Baseline, PerfResult, FuncResult, SiteConfig, BuildJob, TestServerSnapshot, DomainRelation, \
    TestJobCase, ResultFile, CloudServerSnapshot, FuncBaselineDetail, PerfBaselineDetail, TestJobSuite
from tone.settings import APP_DOMAIN


logger = logging.getLogger('sync_test_farm')


class SyncPortalService(CommonService):

    def __init__(self):
        self.BIZ_NAME = 'tone'
        self.TEST_FARM_URL = 'http://127.0.0.1:5000'
        self.TEST_FARM_TOKEN = '5511657c86764b4aa33d0bb970f9cb4c'
        self.IS_MASTER = True
        site_config = SiteConfig.objects.first()
        if site_config:
            self.BIZ_NAME = site_config.business_system_name
            self.TEST_FARM_URL = site_config.site_url
            self.TEST_FARM_TOKEN = site_config.site_token
            self.IS_MASTER = site_config.is_major
        self.CASE_META_API = '/api/pub/update_case_meta_data'
        self.SYNC_JOB_API = '/api/pub/job/add'
        self.SYNC_JOB_STATUS_API = '/api/pub/job/update'
        self.SYNC_PERF_API = '/api/pub/import/perf_result'
        self.SYNC_FUNC_API = '/api/pub/import/func_result'
        self.SYNC_BASELINE_API = '/api/pub/sync/baseline'
        self.SYNC_BASELINE_DEL_API = '/api/pub/sync/baseline/del'
        self.STATUS_SW = {'pending': 0, 'running': 1, 'success': 2, 'fail': 3, 'stop': 4, 'skip': 5}

    def get_sign(self):
        timestamp = str(time.time())
        sign_items = [self.BIZ_NAME, self.TEST_FARM_TOKEN, timestamp]
        return base64.b64encode('|'.join(sign_items).encode('utf-8'))

    def sync_case_meta(self, is_all):  # noqa: C901
        if not self.IS_MASTER:
            return 403, 'not master station'
        before_week = datetime.datetime.now() - timedelta(days=7)
        test_suite_list = TestSuite.objects.filter(gmt_modified__gte=before_week, certificated=True)
        if is_all == '1':
            test_suite_list = TestSuite.objects.filter(certificated=True)
        suite_obj_list = list()
        for test_suite in test_suite_list:
            case_obj_list = list()
            test_case_list = TestCase.objects.filter(test_suite_id=test_suite.id, certificated=True)
            for test_case in test_case_list:
                metric_obj_list = list()
                test_metric_list = TestMetric.objects.filter(object_type='case', object_id=test_case.id)
                for test_metric in test_metric_list:
                    metric_obj = dict(
                        name=test_metric.name,
                        cv_threshold=test_metric.cv_threshold,
                        cmp_threshold=test_metric.cmp_threshold,
                        direction=test_metric.direction,
                        unit=test_metric.unit
                    )
                    metric_obj_list.append(metric_obj)
                domain_name_list = self.get_domain_name('case', test_case.id)
                case_obj = dict(
                    name=test_case.name,
                    repeat=test_case.repeat,
                    timeout=test_case.timeout,
                    domain=domain_name_list,
                    metrics=metric_obj_list
                )
                case_obj_list.append(case_obj)
            metric_obj_list = list()
            test_metric_list = TestMetric.objects.filter(object_type='suite', object_id=test_suite.id)
            for test_metric in test_metric_list:
                metric_obj = dict(
                    name=test_metric.name,
                    cv_threshold=test_metric.cv_threshold,
                    cmp_threshold=test_metric.cmp_threshold,
                    direction=test_metric.direction,
                    unit=test_metric.unit
                )
                metric_obj_list.append(metric_obj)
            domain_name_list = self.get_domain_name('suite', test_suite.id)
            suite_obj = dict(
                name=test_suite.name,
                domain=domain_name_list,
                run_mode=0 if test_suite.run_mode == 'standalone' else 1,
                test_type=0 if test_suite.test_type == 'functional' else 1,
                test_cases=case_obj_list,
                metrics=metric_obj_list
            )
            suite_obj_list.append(suite_obj)
        req_param = dict(
            signature=self.get_sign(),
            biz_name=self.BIZ_NAME,
            data=suite_obj_list
        )
        try:
            res = requests.post(url=self.TEST_FARM_URL + self.CASE_META_API, json=req_param, verify=False)
            if res.ok:
                return json.loads(res.text)['code'], json.loads(res.text)['msg']
        except Exception as error:
            logger.error(f'推送suite异常：{error}, req_param:{req_param}')
            return 201, str(error)

    def get_domain_name(self, object_type, object_id):
        domain_list = list()
        domain_relation_list = DomainRelation.objects.filter(object_type=object_type, object_id=object_id)
        if domain_relation_list:
            for domain_relation in domain_relation_list:
                test_domain = TestDomain.objects.filter(id=domain_relation.domain_id).first()
                if test_domain:
                    domain_list.append(test_domain.name)
        return domain_list

    def sync_job(self, test_job_id):
        test_job = TestJob.objects.filter(id=test_job_id).first()
        if not test_job:
            return 201, 'test job not existed.'
        _, _, baseline_id = self.sync_baseline(test_job.baseline_id)
        project = Project.objects.filter(id=test_job.project_id).first()
        project_name = ''
        if project:
            project_name = project.name
        build = dict()
        build_job = BuildJob.objects.filter(id=test_job.build_job_id).first()
        if build_job:
            build_state = {'pending': 3, 'running': 0, 'success': 1, 'fail': 2}
            build = dict(
                name=build_job.name,
                state=build_state.get(build_job.state, 0),
                arch=build_job.arch,
                build_config=build_job.build_config,
                build_log=build_job.build_log,
                build_file=build_job.build_file,
                build_env=build_job.build_env,
                git_branch=build_job.git_branch,
                git_commit=build_job.git_commit,
                git_url=build_job.git_repo,
                commit_msg=build_job.commit_msg,
                committer=build_job.committer,
                compiler=build_job.compiler,
                description=build_job.description
            )
        distro = ''
        test_server_snapshot = TestServerSnapshot.objects.filter(job_id=test_job_id).first()
        if test_server_snapshot:
            distro = test_server_snapshot.distro
        # 获取job结果url
        tone_job_link = '{}/ws/{}/test_result/{}'.format(APP_DOMAIN, test_job.ws_id, test_job_id)
        data = dict(
            job_name=test_job.name,
            state=self.STATUS_SW.get(test_job.state, 0),
            project=project_name,
            release=test_job.product_version,
            test_type=0 if test_job.test_type == 'functional' else 1,
            baseline_name=self.get_baseline_name(test_job.baseline_id),
            baseline_id=baseline_id,
            tone_job_id=test_job_id,
            tone_job_link=tone_job_link,
            kernel_info=test_job.kernel_info,
            rpm_info=test_job.rpm_info,
            cleanup_info=test_job.cleanup_info,
            script_info=test_job.script_info,
            env_info=test_job.env_info,
            kernel_version=test_job.kernel_version,
            need_reboot=test_job.need_reboot,
            distro=distro,
            build=build,
            start_date=test_job.start_time.strftime('%Y-%m-%d %H:%M:%S')
        )
        req_param = dict(
            signature=self.get_sign(),
            biz_name=self.BIZ_NAME,
            data=data
        )
        try:
            res = requests.post(url=self.TEST_FARM_URL + self.SYNC_JOB_API, json=req_param, verify=False)
            if res.ok:
                return json.loads(res.text)['code'], json.loads(res.text)['msg']
            else:
                return 201, res.content
        except Exception as error:
            logger.error(f'推送job异常：{error}, req_param:{req_param}')
            return 201, str(error)

    def get_server_info(self, test_job_id, test_suite_id, test_case_id):
        test_server_name = ''
        ip = ''
        sn = ''
        case_state = ''
        test_job_case = TestJobCase.objects.\
            filter(job_id=test_job_id, test_suite_id=test_suite_id, test_case_id=test_case_id).first()
        if test_job_case:
            case_state = self.STATUS_SW.get(test_job_case.state, 0)
            test_server = TestServerSnapshot.objects.filter(id=test_job_case.server_snapshot_id).first()
            if test_server:
                if test_server.name:
                    test_server_name = test_server.name
                else:
                    test_server_name = test_server.sn
                ip = test_server.ip
                sn = test_server.sn
        return test_server_name, ip, sn, case_state

    def get_git_info(self, project_id):
        git = dict()
        project_repo = ProjectBranchRelation.objects.filter(project_id=project_id).first()
        if project_repo:
            repo = Repo.objects.filter(id=project_repo.repo_id).first()
            branch_name = ''
            branch = RepoBranch.objects.filter(id=project_repo.branch_id).first()
            if branch:
                branch_name = branch.name
            if repo:
                git = dict(
                    name=repo.name,
                    git_branch=branch_name,
                    git_commit=repo.git_url,
                    git_url=repo.git_url,
                    commit_msg=''
                )
        return git

    def get_baseline_name(self, baseline_id):
        baseline_name = ''
        if baseline_id:
            baseline = Baseline.objects.filter(id=baseline_id).first()
            if baseline:
                baseline_name = baseline.name
        return baseline_name

    def sync_job_status(self, test_job_id, state, end_date=''):
        test_job = TestJob.objects.filter(id=test_job_id).first()
        if not test_job:
            return 201, 'test job not existed.'
        if test_job.end_time:
            end_date = test_job.end_time.strftime('%Y-%m-%d %H:%M:%S')
        distro = ''
        server_provider = test_job.server_provider
        snapshot_model = TestServerSnapshot if server_provider == 'aligroup' else CloudServerSnapshot
        distro_list = snapshot_model.objects.filter(job_id=test_job_id).values_list('distro', flat=True)
        distro_list = [tmp_distro.strip() for tmp_distro in distro_list
                       if tmp_distro is not None and tmp_distro.strip()]
        if distro_list:
            distro = distro_list[0]
        data = dict(
            job_name=test_job.name,
            tone_job_id=test_job_id,
            state=state,
            distro=distro,
            product_version=test_job.product_version,
            kernel_version=test_job.show_kernel_version,
            end_date=end_date
        )
        req_param = dict(
            signature=self.get_sign(),
            biz_name=self.BIZ_NAME,
            data=data
        )
        try:
            res = requests.post(url=self.TEST_FARM_URL + self.SYNC_JOB_STATUS_API, json=req_param, verify=False)
            if res.ok:
                return json.loads(res.text)['code'], json.loads(res.text)['msg']
            else:
                return 201, res.content
        except Exception as error:
            logger.error(f'推送job status异常：{error}, req_param:{req_param}')
            return 201, str(error)

    def sync_perf_result(self, test_job_id):  # noqa: C901
        test_job = TestJob.objects.filter(id=test_job_id).first()
        if not test_job:
            return 201, 'test job not existed.'
        test_suite_id_list = PerfResult.objects.\
            filter(test_job_id=test_job_id).values_list('test_suite_id', flat=True).distinct()
        test_suite_list = list()
        for test_suite_id in test_suite_id_list:
            test_suite = TestSuite.objects.filter(id=test_suite_id).first()
            if not test_suite:
                return 201, 'test_suite not existed'
            test_job_suite = TestJobSuite.objects.filter(job_id=test_job_id, test_suite_id=test_suite_id).first()
            if not test_job_suite:
                return 201, 'test_job_suite error.'
            test_case_id_list = PerfResult.objects.filter(test_job_id=test_job_id, test_suite_id=test_suite_id).\
                values_list('test_case_id', flat=True).distinct()
            test_case_list = list()
            for test_case_id in test_case_id_list:
                test_case = TestCase.objects.filter(id=test_case_id).first()
                if not test_case:
                    return 201, 'test_case not existed'
                perf_result_list = PerfResult.objects.\
                    filter(test_job_id=test_job_id, test_suite_id=test_suite_id, test_case_id=test_case_id)
                metric_list = list()
                for perf_result in perf_result_list:
                    metric_obj = dict(
                        metric=perf_result.metric,
                        test_value=perf_result.test_value,
                        cv_value=perf_result.cv_value,
                        unit=perf_result.unit,
                        value_list=perf_result.value_list,
                        baseline_value=perf_result.baseline_value if perf_result.baseline_value else 0,
                        baseline_cv_value=perf_result.baseline_cv_value if perf_result.baseline_cv_value else 0,
                        track_result=perf_result.track_result,
                        compare_result=perf_result.compare_result,
                        match_baseline=perf_result.match_baseline,
                        start_date=perf_result.gmt_created.strftime('%Y-%m-%d %H:%M:%S'),
                        end_date=perf_result.gmt_modified.strftime('%Y-%m-%d %H:%M:%S')
                    )
                    metric_list.append(metric_obj)
                test_server_name, ip, sn, case_state = self.get_server_info(test_job_id, test_suite_id, test_case_id)
                case_obj = dict(
                    case_name=test_case.name,
                    state=case_state,
                    test_server_name=test_server_name,
                    ip=ip,
                    sn=sn,
                    metrics=metric_list
                )
                test_case_list.append(case_obj)
            suite_obj = dict(
                suite_name=test_suite.name,
                state=self.STATUS_SW.get(test_job_suite.state, 0),
                cases=test_case_list
            )
            test_suite_list.append(suite_obj)
        data = dict(
            job_name=test_job.name,
            tone_job_id=test_job_id,
            suites=test_suite_list
        )
        req_param = dict(
            signature=self.get_sign(),
            biz_name=self.BIZ_NAME,
            data=data
        )
        try:
            res = requests.post(url=self.TEST_FARM_URL + self.SYNC_PERF_API, json=req_param, verify=False)
            if res.ok:
                return json.loads(res.text)['code'], json.loads(res.text)['msg']
            else:
                return 201, res.content
        except Exception as error:
            logger.error(f'推送perf result异常：{error}, req_param:{req_param}')
            return 201, str(error)

    def sync_func_result(self, test_job_id):  # noqa: C901
        test_job = TestJob.objects.filter(id=test_job_id).first()
        if not test_job:
            return 201, 'test job not existed.'
        test_suite_id_list = FuncResult.objects.\
            filter(test_job_id=test_job_id).values_list('test_suite_id', flat=True).distinct()
        test_suite_list = list()
        for test_suite_id in test_suite_id_list:
            test_suite = TestSuite.objects.filter(id=test_suite_id).first()
            if not test_suite:
                return 201, 'test_suite not existed'
            test_job_suite = TestJobSuite.objects.filter(job_id=test_job_id, test_suite_id=test_suite_id).first()
            if not test_job_suite:
                return 201, 'test_job_suite error.'
            test_case_id_list = FuncResult.objects.filter(test_job_id=test_job_id, test_suite_id=test_suite_id). \
                values_list('test_case_id', flat=True).distinct()
            test_case_list = list()
            for test_case_id in test_case_id_list:
                test_case = TestCase.objects.filter(id=test_case_id).first()
                if not test_case:
                    return 201, 'test_case not existed'
                func_result_list = FuncResult.objects. \
                    filter(test_job_id=test_job_id, test_suite_id=test_suite_id, test_case_id=test_case_id)
                sub_case_list = list()
                for func_result in func_result_list:
                    sub_case_obj = dict(
                        sub_case_name=func_result.sub_case_name,
                        case_result=func_result.sub_case_result,
                        match_baseline=func_result.match_baseline,
                        bug=func_result.bug,
                        note=func_result.note,
                        description=func_result.description,
                        start_date=func_result.gmt_created.strftime('%Y-%m-%d %H:%M:%S'),
                        end_date=func_result.gmt_modified.strftime('%Y-%m-%d %H:%M:%S')
                    )
                    sub_case_list.append(sub_case_obj)
                cpu_model, os_version, conf_arch, package_list = \
                    self.parse_result_file(test_case_id, test_job_id, test_suite_id)
                test_server_name, ip, sn, case_state = self.get_server_info(test_job_id, test_suite_id, test_case_id)
                case_obj = dict(
                    case_name=test_case.name,
                    state=case_state,
                    test_server_name=test_server_name,
                    ip=ip,
                    sn=sn,
                    cpu_model=cpu_model,
                    os_version=os_version,
                    arch=conf_arch,
                    sub_case_results=sub_case_list,
                    packages=package_list
                )
                test_case_list.append(case_obj)
            suite_obj = dict(
                suite_name=test_suite.name,
                state=self.STATUS_SW.get(test_job_suite.state, 0),
                cases=test_case_list
            )
            test_suite_list.append(suite_obj)
        data = dict(
            job_name=test_job.name,
            tone_job_id=test_job_id,
            suites=test_suite_list
        )
        req_param = dict(
            signature=self.get_sign(),
            biz_name=self.BIZ_NAME,
            data=data
        )
        try:
            res = requests.post(url=self.TEST_FARM_URL + self.SYNC_FUNC_API, json=req_param, verify=False)
            if res.ok:
                return json.loads(res.text)['code'], json.loads(res.text)['msg']
            else:
                return 201, res.content
        except Exception as error:
            logger.error(f'推送func result异常：{error}, req_param:{req_param}')
            return 201, str(error)

    def parse_result_file(self, test_case_id, test_job_id, test_suite_id):
        package_list = list()
        cpu_model, os_version, conf_arch = '', '', ''
        func_result_file = ResultFile.objects. \
            filter(test_job_id=test_job_id, test_suite_id=test_suite_id, test_case_id=test_case_id,
                   result_file='statistic.json').all()
        for file in func_result_file:
            try:
                file_url = file.result_path + file.result_file
                response = urllib.request.urlopen(file_url)
                file_content = json.loads(response.read())
                if 'testinfo' in file_content:
                    if 'cpu_model' in file_content['testinfo']:
                        cpu_model = file_content['testinfo']['cpu_model']
                    if 'os_version' in file_content['testinfo']:
                        os_version = file_content['testinfo']['os_version']
                if 'hostname' in file_content['testinfo']:
                    conf_arch = file_content['testinfo']['hostname'][4]
                if 'packages' in file_content['testinfo']:
                    for package in file_content['testinfo']['packages']:
                        package_obj = dict()
                        package_obj['arch'] = package['arch']
                        package_obj['name'] = package['name']
                        package_obj['repo'] = package['repo']
                        package_obj['version'] = package['version']
                        package_list.append(package_obj)
            except Exception as err:
                logger = get_logger()
                logger.error('parse statistic.json failed , err is {}'.format(err.args))
                continue
        return cpu_model, os_version, conf_arch, package_list

    def sync_baseline(self, baseline_id):
        baseline = Baseline.objects.filter(id=baseline_id).first()
        if not baseline:
            return 201, 'baseline not existed.', 0
        test_suite_list = list()
        if baseline.test_type == 'functional':
            test_suite_list = self.sync_func_baseline_detail(baseline_id)
        else:
            test_suite_list = self.sync_perf_baseline_detail(baseline_id)
        data = dict(
            name=baseline.name,
            test_type=0 if baseline.test_type == 'functional' else 1,
            server_provider=baseline.server_provider,
            version=baseline.version,
            desc=baseline.description,
            tone_job_id=0,
            suites=test_suite_list
        )
        req_param = dict(
            signature=self.get_sign(),
            biz_name=self.BIZ_NAME,
            data=data
        )
        try:
            res = requests.post(url=self.TEST_FARM_URL + self.SYNC_BASELINE_API, json=req_param, verify=False)
            if res.ok:
                return json.loads(res.text)['code'], json.loads(res.text)['msg'], json.loads(res.text)['data']
            else:
                return 201, res.content, 0
        except Exception as error:
            logger.error(f'推送baseline异常：{error}, req_param:{req_param}')
            return 201, str(error), 0

    def sync_func_baseline_detail(self, baseline_id):
        test_suite_list = list()
        test_suite_id_list = FuncBaselineDetail.objects. \
            filter(baseline_id=baseline_id).values_list('test_suite_id', flat=True).distinct()
        for test_suite_id in test_suite_id_list:
            test_suite = TestSuite.objects.filter(id=test_suite_id).first()
            if not test_suite:
                break
            test_case_id_list = FuncBaselineDetail.objects.\
                filter(baseline_id=baseline_id, test_suite_id=test_suite_id). \
                values_list('test_case_id', flat=True).distinct()
            test_case_list = list()
            for test_case_id in test_case_id_list:
                test_case = TestCase.objects.filter(id=test_case_id).first()
                if not test_case:
                    break
                func_result_list = FuncBaselineDetail.objects. \
                    filter(baseline_id=baseline_id, test_suite_id=test_suite_id, test_case_id=test_case_id)
                sub_case_list = list()
                for func_result in func_result_list:
                    sub_case_obj = dict(
                        sub_case_name=func_result.sub_case_name,
                        bug=func_result.bug,
                        impact_result=func_result.impact_result,
                        note=func_result.description
                    )
                    sub_case_list.append(sub_case_obj)
                case_obj = dict(
                    test_case_name=test_case.name,
                    sub_cases=sub_case_list,
                )
                test_case_list.append(case_obj)
            suite_obj = dict(
                test_suite_name=test_suite.name,
                cases=test_case_list
            )
            test_suite_list.append(suite_obj)
        return test_suite_list

    def sync_perf_baseline_detail(self, baseline_id):
        test_suite_list = list()
        test_suite_id_list = PerfBaselineDetail.objects. \
            filter(baseline_id=baseline_id).values_list('test_suite_id', flat=True).distinct()
        for test_suite_id in test_suite_id_list:
            test_suite = TestSuite.objects.filter(id=test_suite_id).first()
            if not test_suite:
                break
            test_case_id_list = PerfBaselineDetail.objects. \
                filter(baseline_id=baseline_id, test_suite_id=test_suite_id). \
                values_list('test_case_id', flat=True).distinct()
            test_case_list = list()
            for test_case_id in test_case_id_list:
                test_case = TestCase.objects.filter(id=test_case_id).first()
                if not test_case:
                    break
                perf_result_list = PerfBaselineDetail.objects. \
                    filter(baseline_id=baseline_id, test_suite_id=test_suite_id, test_case_id=test_case_id)
                metric_list = list()
                for perf_result in perf_result_list:
                    metric_obj = dict(
                        metric=perf_result.metric,
                        value=perf_result.test_value,
                        cv_value=perf_result.cv_value,
                        unit=perf_result.unit,
                        value_list=perf_result.value_list,
                        max_value=perf_result.max_value,
                        min_value=perf_result.min_value,
                        note=perf_result.note
                    )
                    metric_list.append(metric_obj)
                case_obj = dict(
                    test_case_name=test_case.name,
                    metrics=metric_list
                )
                test_case_list.append(case_obj)
            suite_obj = dict(
                test_suite_name=test_suite.name,
                cases=test_case_list
            )
            test_suite_list.append(suite_obj)
        return test_suite_list

    def sync_baseline_del(self, baseline_id):
        baseline = Baseline.objects.filter(id=baseline_id).first()
        if not baseline:
            return 201, 'baseline not existed.', 0
        data = dict(
            name=baseline.name,
            version=baseline.version
        )
        req_param = dict(
            signature=self.get_sign(),
            biz_name=self.BIZ_NAME,
            data=data
        )
        try:
            res = requests.post(url=self.TEST_FARM_URL + self.SYNC_BASELINE_DEL_API, json=req_param, verify=False)
            if res.ok:
                return json.loads(res.text)['code'], json.loads(res.text)['msg'], json.loads(res.text)['data']
            else:
                return 201, res.content, 0
        except Exception as error:
            logger.error(f'推送baseline异常：{error}, req_param:{req_param}')
            return 201, str(error), 0
