# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import random
import string
from datetime import datetime
import logging

from django.db import transaction

from tone.models import TestJob, ReportTemplate, Report, TestServerSnapshot, CloudServerSnapshot, ReportItemConf, \
    ReportItemSuite, ReportItem, ReportItemMetric, ReportItemSubCase, ReportObjectRelation, ReportTmplItem, \
    ReportTmplItemSuite, TestJobCase, TestJobSuite, TestCase, FuncResult, PerfResult, TestSuite, TestMetric, \
    PerfBaselineDetail, FuncBaselineDetail, Baseline
from tone.core.common.constant import FUNC_CASE_RESULT_TYPE_MAP
from tone.views.api.get_domain_group import get_domain_group


class ReportHandle(object):
    logger = logging.getLogger('message')

    def __init__(self, job_id):
        self.job_id = job_id
        self.job_obj = self.get_job_obj()
        self.report_template_obj = self.get_report_template_obj()

    def get_job_obj(self):
        return TestJob.objects.filter(id=self.job_id).first()

    def get_report_template_obj(self):
        return ReportTemplate.objects.filter(id=self.job_obj.report_template_id).first()

    def get_baseline_name(self):
        baseline_name = ''
        if self.job_obj.baseline_id:
            baseline = Baseline.objects.filter(id=self.job_obj.baseline_id).first()
            if baseline:
                baseline_name = baseline.name
        return baseline_name

    def save_report(self):  # noqa: C901
        logging.info(f'report: job_id {self.job_id}, report_template_id: {self.job_obj.report_template_id}')
        if not self.report_template_obj:
            logging.error(f'report save error: job_id {self.job_id}, report_template_id is null.')
            return
        with transaction.atomic():
            report_name = self.job_obj.report_name if self.job_obj.report_name else \
                ''.join(random.sample(string.ascii_letters + string.digits, 18))
            report = Report.objects.create(name=report_name, product_version=self.job_obj.product_version,
                                           project_id=self.job_obj.project_id, ws_id=self.job_obj.ws_id,
                                           tmpl_id=self.report_template_obj.id, creator=self.job_obj.creator,
                                           is_automatic=1)
            # test_env = self.get_test_env()
            before_name = report.name
            report.test_env = self.get_test_env()
            report.name = before_name.format(date=datetime.strftime(report.gmt_created, "%Y-%m-%d %H:%M:%S"),
                                             job_name=self.job_obj.name, job_id=self.job_id, report_id=report.id,
                                             product_version=report.product_version, report_seq_id=report.id + 1)
            if self.report_template_obj:
                report.test_background = self.report_template_obj.background_desc
                report.test_method = self.report_template_obj.test_method_desc
                report.test_conclusion = self.report_template_obj.test_conclusion_desc
                report.test_env['text'] = self.report_template_obj.test_env_desc
                report.env_description = self.report_template_obj.env_description_desc
            report.save()
            func_all = fail = success = warn = 0
            perf_all = decline = increase = 0
            if self.report_template_obj.is_default:
                conf_list = [job_case.test_case_id for job_case in TestJobCase.objects.filter(job_id=self.job_id)]
                domain_group = get_domain_group(conf_list)
                func_data = domain_group.get('functional')
                perf_data = domain_group.get('performance')
                for item_key, item_value in func_data.items():
                    report_item = ReportItem.objects.create(name=item_key, test_type='functional', report_id=report.id)
                    for suite_key, suite_value in item_value.items():
                        suite_id = int(suite_key)
                        report_item_suite = ReportItemSuite.objects.create(
                            report_item_id=report_item.id, test_suite_id=suite_id, show_type=0,
                            test_suite_name=TestSuite.objects.get_value(id=suite_id).name)
                        for conf_id in suite_value:
                            conf_source = {"is_job": 1, "obj_id": self.job_id}
                            func_results = FuncResult.objects.filter(test_job_id=self.job_id,
                                                                     test_suite_id=suite_id,
                                                                     test_case_id=conf_id)
                            conf_source['all_case'] = func_results.count()
                            conf_source['success_case'] = func_results.filter(sub_case_result=1).count()
                            conf_source['fail_case'] = func_results.filter(sub_case_result=2).count()
                            conf_source['warn_case'] = func_results.filter(sub_case_result=6).count()
                            func_all += conf_source['all_case']
                            success += conf_source['success_case']
                            fail += conf_source['fail_case']
                            warn += conf_source['warn_case']
                            report_item_conf = self.create_report_item(conf_id, conf_source, report_item_suite)
                            for func_result in func_results:
                                self.handle_func_result(func_result, report_item_conf)
                for item_key, item_value in perf_data.items():
                    report_item = ReportItem.objects.create(name=item_key, test_type='performance', report_id=report.id)
                    for suite_key, suite_value in item_value.items():
                        suite_id = int(suite_key)
                        report_item_suite = ReportItemSuite.objects.create(
                            report_item_id=report_item.id, test_suite_id=suite_id, show_type=0,
                            test_suite_name=TestSuite.objects.get_value(id=suite_id).name)
                        for conf_id in suite_value:
                            conf_source = {"is_job": 1, "obj_id": self.job_id}
                            report_item_conf = self.create_report_item(conf_id, conf_source, report_item_suite)
                            perf_results = PerfResult.objects.filter(test_job_id=self.job_id,
                                                                     test_suite_id=suite_id,
                                                                     test_case_id=conf_id)
                            perf_all += perf_results.count()
                            for perf_result in perf_results:
                                decline_tmp, increase_tmp = \
                                    self.handle_perf_result(conf_id, perf_result, report_item_conf)
                                decline += decline_tmp
                                increase += increase_tmp

            else:
                report_tmpl_items = ReportTmplItem.objects.filter(tmpl_id=self.report_template_obj.id)
                for report_tmpl_item in report_tmpl_items:
                    report_item = ReportItem.objects.create(name=report_tmpl_item.name,
                                                            test_type=report_tmpl_item.test_type, report_id=report.id)
                    tmpl_suites = ReportTmplItemSuite.objects.filter(report_tmpl_item_id=report_tmpl_item.id)
                    for tmpl_suite in tmpl_suites:
                        if TestJobSuite.objects.filter(job_id=self.job_id,
                                                       test_suite_id=tmpl_suite.test_suite_id).exists():
                            test_env = self.get_suite_env(tmpl_suite.test_suite_id)
                            if not test_env:
                                test_env = tmpl_suite.test_env_desc
                            tmp_suite = TestSuite.objects.filter(id=tmpl_suite.test_suite_id).first()
                            suite_doc = None
                            if tmp_suite and tmp_suite.doc and tmp_suite.doc.find('Description') > -1 and \
                                    tmp_suite.doc.find('## Homepage') > -1:
                                suite_doc = tmp_suite.doc.split('Description')[1].split('## Homepage')[0]
                            report_item_suite = ReportItemSuite.objects.create(
                                report_item_id=report_item.id, test_suite_id=tmpl_suite.test_suite_id,
                                test_suite_name=tmpl_suite.test_suite_show_name, test_env=test_env,
                                test_description=tmpl_suite.test_description_desc,
                                test_conclusion=tmpl_suite.test_conclusion_desc,
                                test_suite_description=suite_doc,
                                show_type=0 if tmpl_suite.show_type == 'list' else 1)
                            for tmpl_conf in tmpl_suite.test_conf_list:
                                if TestJobCase.objects.filter(job_id=self.job_id,
                                                              test_suite_id=tmpl_suite.test_suite_id,
                                                              test_case_id=tmpl_conf).exists():
                                    conf_source = {"is_job": 1, "obj_id": self.job_id}
                                    if report_tmpl_item.test_type == 'functional':
                                        func_results = FuncResult.objects.filter(test_job_id=self.job_id,
                                                                                 test_suite_id=tmpl_suite.test_suite_id,
                                                                                 test_case_id=tmpl_conf)
                                        conf_source['all_case'] = func_results.count()
                                        conf_source['success_case'] = func_results.filter(sub_case_result=1).count()
                                        conf_source['fail_case'] = func_results.filter(sub_case_result=2).count()
                                        conf_source['warn_case'] = func_results.filter(sub_case_result=6).count()
                                        func_all += conf_source['all_case']
                                        success += conf_source['success_case']
                                        fail += conf_source['fail_case']
                                        warn += conf_source['warn_case']
                                    report_item_conf = self.create_report_item(tmpl_conf, conf_source, report_item_suite
                                                                               )
                                    if report_tmpl_item.test_type == 'functional':
                                        func_results = FuncResult.objects.filter(test_job_id=self.job_id,
                                                                                 test_suite_id=tmpl_suite.test_suite_id,
                                                                                 test_case_id=tmpl_conf)
                                        for func_result in func_results:
                                            self.handle_func_result(func_result, report_item_conf)
                                    else:
                                        perf_results = PerfResult.objects.filter(test_job_id=self.job_id,
                                                                                 test_suite_id=tmpl_suite.test_suite_id,
                                                                                 test_case_id=tmpl_conf)
                                        perf_all += perf_results.count()
                                        for perf_result in perf_results:
                                            decline_tmp, increase_tmp = \
                                                self.handle_perf_result(tmpl_conf, perf_result, report_item_conf)
                                            decline += decline_tmp
                                            increase += increase_tmp
            func_count = {
                'all': func_all,
                'fail': fail,
                'success': success,
                'warn': warn
            }
            perf_count = {
                'all': perf_all,
                'decline': decline,
                'increase': increase
            }
            report.test_conclusion = self.get_test_conclusion(report, perf_count, func_count)
            report.save()
            report_object_relation = ReportObjectRelation.objects. \
                filter(object_type='job', object_id=self.job_id).first()
            if report_object_relation:
                report_object_relation.report_id = report.id
                report_object_relation.save()
            else:
                ReportObjectRelation.objects.create(object_type='job', object_id=self.job_id, report_id=report.id)
            self.job_obj.report_is_saved = True
            self.job_obj.save()

    def get_suite_env(self, test_suite_id):
        test_env = ''
        test_job_case = TestJobCase.objects.filter(job_id=self.job_id, test_suite_id=test_suite_id).first()
        if test_job_case:
            if self.job_obj.server_provider == 'aligroup':
                snapshot = TestServerSnapshot.objects.filter(id=test_job_case.server_object_id).first()
                if snapshot:
                    test_env = snapshot.ip
            else:
                snapshot = CloudServerSnapshot.objects.filter(
                    id=test_job_case.server_object_id).first()
                if snapshot:
                    test_env = snapshot.pub_ip
        return test_env

    def create_report_item(self, conf_id, conf_source, report_item_suite):
        compare_conf_list = list()
        compare_conf_list.append(conf_source)
        if self.job_obj.baseline_id:
            if self.job_obj.test_type == 'functional':
                baseline = FuncBaselineDetail.objects.filter(baseline_id=self.job_obj.baseline_id)
                compare_conf_list.insert(0, dict({
                    "is_job": 0,
                    "obj_id": self.job_obj.baseline_id,
                    "all_case": baseline.count(),
                    "success_case": 0,
                    "fail_case": 0,
                    "warn_case": 0}))
            else:
                compare_conf_list.insert(0, dict({
                    "is_job": 0,
                    "obj_id": self.job_obj.baseline_id}))
            report_item_conf = ReportItemConf.objects.create(
                report_item_suite_id=report_item_suite.id, test_conf_id=conf_id,
                test_conf_name=TestCase.objects.get_value(id=conf_id).name,
                compare_conf_list=compare_conf_list)
        else:
            compare_conf_list.insert(0, dict())
            report_item_conf = ReportItemConf.objects.create(
                report_item_suite_id=report_item_suite.id, test_conf_id=conf_id,
                test_conf_name=TestCase.objects.get_value(id=conf_id).name,
                conf_source=conf_source, compare_conf_list=compare_conf_list)
        return report_item_conf

    def handle_perf_result(self, conf_id, perf_result, report_item_conf):
        metric_obj = TestMetric.objects.filter(name=perf_result.metric, object_type='case', object_id=conf_id).first()
        decline = increase = 0
        compare_data = list()
        compare_obj = dict()
        if self.job_obj.baseline_id:
            perf_baseline = PerfBaselineDetail.objects.filter(baseline_id=perf_result.compare_baseline,
                                                              metric=perf_result.metric).first()
            compare_obj['test_value'] = perf_result.test_value
            compare_obj['cv_value'] = perf_result.cv_value.replace('±', '')
            compare_obj['max_value'] = perf_result.max_value
            compare_obj['min_value'] = perf_result.min_value
            compare_obj['value_list'] = perf_result.value_list
            if perf_baseline:
                compare_obj['compare_value'], compare_obj['compare_result'] = \
                    self.get_compare_result(perf_baseline.test_value, perf_result.test_value, compare_obj['cv_value'],
                                            metric_obj)
                if compare_obj['compare_result'] == 'decline':
                    decline += 1
                if compare_obj['compare_result'] == 'increase':
                    increase += 1
            compare_data.append(compare_obj)
            ReportItemMetric.objects.create(report_item_conf_id=report_item_conf.id,
                                            test_metric=perf_result.metric,
                                            test_value=perf_baseline.test_value if perf_baseline else '0',
                                            cv_value=perf_baseline.cv_value.replace('±', '') if perf_baseline else '0',
                                            unit=perf_baseline.unit if perf_baseline else None,
                                            max_value=perf_baseline.max_value if perf_baseline else '0',
                                            min_value=perf_baseline.min_value if perf_baseline else '0',
                                            value_list=perf_baseline.value_list if perf_baseline else '[]',
                                            direction=metric_obj.direction if metric_obj else 'na',
                                            compare_data=compare_data)
        else:
            compare_data.append(dict())
            ReportItemMetric.objects.create(report_item_conf_id=report_item_conf.id,
                                            test_metric=perf_result.metric,
                                            test_value=perf_result.test_value,
                                            cv_value=perf_result.cv_value.replace('±', ''),
                                            unit=perf_result.unit,
                                            max_value=perf_result.max_value,
                                            min_value=perf_result.min_value,
                                            value_list=perf_result.value_list,
                                            direction=metric_obj.direction if metric_obj else None,
                                            compare_data=compare_data)
        return decline, increase

    def handle_func_result(self, func_result, report_item_conf):
        compare_data = list()
        compare_data.append(FUNC_CASE_RESULT_TYPE_MAP.get(func_result.sub_case_result))
        if self.job_obj.baseline_id:
            func_baseline = FuncBaselineDetail.objects. \
                filter(baseline_id=self.job_obj.baseline_id, sub_case_name=func_result.sub_case_name).first()
            ReportItemSubCase.objects.create(report_item_conf_id=report_item_conf.id,
                                             sub_case_name=func_result.sub_case_name,
                                             result='Fail' if func_baseline else None,
                                             compare_data=compare_data)
        else:
            compare_data.insert(0, '')
            ReportItemSubCase.objects.create(report_item_conf_id=report_item_conf.id,
                                             sub_case_name=func_result.sub_case_name,
                                             result=FUNC_CASE_RESULT_TYPE_MAP.get(
                                                 func_result.sub_case_result),
                                             compare_data=compare_data)

    def get_test_env(self):
        compare_groups = list()
        server_info = self.get_server_info()
        compare_groups.append(server_info)
        env_info = {
            'base_group': {
                'tag': self.get_baseline_name(),
                'server_info': [],
                'is_job': 0
            },
            'compare_groups': compare_groups,
        }
        count = len(server_info.get('server_info'))
        env_info['count'] = count
        self.logger.info(f'server_info')
        return env_info

    def get_test_conclusion(self, report, perf_count, func_count):
        compare_groups = []
        product_version = self.job_obj.product_version
        tag_name = product_version if product_version else '对比标识'
        compare_groups.append({
            'tag': report.product_version,
            'is_job': 1,
            'func_data': func_count,
            'perf_data': perf_count
        })
        test_conclusion = {
            'custom': None,
            'summary': {
                'base_group': {
                    'tag': f'{tag_name}(1)',
                    'is_job': 0
                },
                'compare_groups': compare_groups
            }
        }
        return test_conclusion

    def get_server_info(self):
        server_li = list()
        ip_li = list()
        self.package_li(server_li, ip_li)
        env_info = {
            'tag': self.job_obj.product_version,
            'server_info': server_li,
            'is_job': 1
        }
        return env_info

    def package_li(self, server_li, ip_li):
        job = self.job_obj
        snap_shot_objs = TestServerSnapshot.objects.filter(
            job_id=job.id) if job.server_provider == 'aligroup' else CloudServerSnapshot.objects.filter(job_id=job.id)
        for snap_shot_obj in snap_shot_objs:
            ip = snap_shot_obj.ip if job.server_provider == 'aligroup' else snap_shot_obj.private_ip
            if ip not in ip_li:
                if not (snap_shot_obj.distro or snap_shot_obj.rpm_list or snap_shot_obj.gcc):
                    continue
                server_li.append({
                    'ip/sn': ip,
                    'distro': snap_shot_obj.sm_name if job.server_provider == 'aligroup' else
                    snap_shot_obj.instance_type,
                    'os': snap_shot_obj.distro,
                    'rpm': snap_shot_obj.rpm_list.split('\n') if snap_shot_obj.rpm_list else list(),
                    'kernel': snap_shot_obj.kernel_version,
                    'gcc': snap_shot_obj.gcc,
                    'glibc': snap_shot_obj.glibc,
                    'memory_info': snap_shot_obj.memory_info,
                    'disk': snap_shot_obj.disk,
                    'cpu_info': snap_shot_obj.cpu_info,
                    'ether': snap_shot_obj.ether,
                })
                ip_li.append(ip)

    def get_compare_result(self, base_test_value, compare_test_value, cv_value, metric_obj):
        try:
            res = _change_rate = 'na'
            if float(base_test_value) != 0:
                change_rate = (float(compare_test_value) - float(base_test_value)) / float(base_test_value)
                if metric_obj:
                    if float(cv_value.split('%')[0]) > metric_obj.cv_threshold * 100:
                        res = 'invalid'
                    else:
                        if change_rate > metric_obj.cmp_threshold:
                            res = 'increase' if metric_obj.direction == 'increase' else 'decline'
                        elif change_rate < -metric_obj.cmp_threshold:
                            res = 'decline' if metric_obj.direction == 'increase' else 'increase'
                        else:
                            res = 'normal'
                _change_rate = '%.2f%%' % (change_rate * 100)
        except Exception as err:
            logging.error(f"err: {err}")
            res = _change_rate = 'na'
        return _change_rate, res
