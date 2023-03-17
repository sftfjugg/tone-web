# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import random
import string
import json
from datetime import datetime
import logging
from tone.core.utils.common_utils import query_all_dict

from django.db import transaction

from tone.models import TestJob, ReportTemplate, Report, TestServerSnapshot, CloudServerSnapshot, ReportItemConf, \
    ReportItemSuite, ReportItem, ReportItemMetric, ReportItemSubCase, ReportObjectRelation, ReportTmplItem, \
    ReportTmplItemSuite, TestJobCase, TestJobSuite, TestCase, FuncResult, PerfResult, TestSuite, TestMetric, \
    PerfBaselineDetail, Baseline, ReportDetail, FuncBaselineDetail, BaselineServerSnapshot
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
            is_default_tmp = self.report_template_obj.is_default
            if not is_default_tmp:
                report_tmpl_items = ReportTmplItem.objects.filter(tmpl_id=self.report_template_obj.id)
                if len(report_tmpl_items) == 0:
                    is_default_tmp = True
            if is_default_tmp:
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
                        tmp_suite = TestSuite.objects.filter(id=suite_id).first()
                        suite_doc = None
                        if tmp_suite and tmp_suite.doc and tmp_suite.doc.find('Description') > -1 and \
                                tmp_suite.doc.find('## Homepage') > -1:
                            suite_doc = tmp_suite.doc.split('Description')[1].split('## Homepage')[0]
                        report_item_suite = ReportItemSuite.objects.create(
                            report_item_id=report_item.id, test_suite_id=suite_id, show_type=0,
                            test_suite_name=tmp_suite.name, test_suite_description=suite_doc)
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
            save_report_detail(report.id, 0, 0, 1)

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
                    test_env = snapshot.private_ip
        return test_env

    def create_report_item(self, conf_id, conf_source, report_item_suite):
        compare_conf_list = list()
        compare_conf_list.append(conf_source)
        return ReportItemConf.objects.create(
            report_item_suite_id=report_item_suite.id, test_conf_id=conf_id,
            test_conf_name=TestCase.objects.get_value(id=conf_id).name,
            conf_source=conf_source, compare_conf_list=compare_conf_list)

    def handle_perf_result(self, conf_id, perf_result, report_item_conf):
        metric_obj = TestMetric.objects.filter(name=perf_result.metric, object_type='case', object_id=conf_id).first()
        decline = increase = 0
        compare_obj = dict()
        compare_data = list()
        if self.job_obj.baseline_id:
            perf_baseline = PerfBaselineDetail.objects.filter(baseline_id=perf_result.compare_baseline,
                                                              test_case_id=conf_id, metric=perf_result.metric).first()
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
        compare_data.append(dict(
            test_value=format(float(perf_result.test_value), '.2f'),
            cv_value=perf_result.cv_value.replace('±', ''),
            unit=perf_result.unit,
            max_value=format(float(perf_result.max_value), '.2f'),
            min_value=format(float(perf_result.min_value), '.2f'),
            value_list=perf_result.value_list,
            compare_value=compare_obj.get('compare_value', None),
            compare_result=compare_obj.get('compare_result', None)
        ))
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
        ReportItemSubCase.objects.create(report_item_conf_id=report_item_conf.id,
                                         sub_case_name=func_result.sub_case_name,
                                         result=FUNC_CASE_RESULT_TYPE_MAP.get(
                                             func_result.sub_case_result),
                                         compare_data=compare_data)

    def get_test_env(self):
        server_info = get_server_info(self.job_obj.product_version, [{'is_baseline': 0, 'obj_id': self.job_id}])
        env_info = {
            'base_group': server_info,
            'compare_groups': list(),
        }
        count = len(server_info.get('server_info'))
        env_info['count'] = count
        return env_info

    def get_test_conclusion(self, report, perf_count, func_count):
        test_conclusion = {
            'custom': None,
            'summary': {
                'base_group': {
                    'tag': report.product_version,
                    'is_baseline': 0,
                    'func_data': func_count,
                    'perf_data': perf_count
                },
                'compare_groups': list()
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
            'is_baseline': 0
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


def save_report_detail(report_id, base_index, is_old_report, is_automatic):
    detail_perf_data = get_perf_data(report_id, base_index, is_old_report, is_automatic)
    detail_func_data = get_func_data(report_id, base_index, is_old_report, is_automatic)
    report_detail = ReportDetail.objects.filter(report_id=report_id).first()
    if report_detail:
        report_detail.func_data = detail_func_data
        report_detail.perf_data = detail_perf_data
        report_detail.save()
    else:
        ReportDetail.objects.create(report_id=report_id, perf_data=detail_perf_data, func_data=detail_func_data)


def get_perf_data(report_id, base_index, is_old_report, is_automatic):
    item_map = dict()
    item_objs = ReportItem.objects.filter(report_id=report_id, test_type='performance')
    for item in item_objs:
        name = item.name
        name_li = name.split(':')
        if is_old_report:
            package_name(0, item_map, name_li, item.id, 'performance', base_index)
        else:
            package_name_v1(0, item_map, name_li, item.id, 'performance', base_index, is_automatic)
    return item_map


def get_func_data(report_id, base_index, is_old_report, is_automatic):
    item_map = dict()
    item_objs = ReportItem.objects.filter(report_id=report_id, test_type='functional')
    for item in item_objs:
        name = item.name
        name_li = name.split(':')
        if is_old_report:
            package_name(0, item_map, name_li, item.id, 'functional', base_index)
        else:
            package_name_v1(0, item_map, name_li, item.id, 'functional', base_index, is_automatic)
    return item_map


def get_old_report(report):
    return 1 if report.gmt_created < datetime.strptime('2022-09-13', '%Y-%m-%d') else 0


def package_name(index, _data, name_li, report_item_id, test_type, base_index):
    if index == len(name_li) - 1:
        _data[name_li[index]] = get_func_suite_list(
            report_item_id, base_index) if test_type == 'functional' else get_perf_suite_list(report_item_id)
    else:
        if name_li[index] in _data:
            package_name(index + 1, _data[name_li[index]], name_li, report_item_id, test_type, base_index)
        else:
            _data[name_li[index]] = dict()
            package_name(index + 1, _data[name_li[index]], name_li, report_item_id, test_type, base_index)


def get_func_suite_list(report_item_id, base_index):
    suite_list = list()
    test_suite_objs = ReportItemSuite.objects.filter(report_item_id=report_item_id)
    for test_suite_obj in test_suite_objs:
        suite_data = dict()
        suite_data['item_suite_id'] = test_suite_obj.id
        suite_data['suite_id'] = test_suite_obj.test_suite_id
        suite_data['suite_name'] = test_suite_obj.test_suite_name
        conf_list = list()
        test_conf_objs = ReportItemConf.objects.filter(report_item_suite_id=test_suite_obj.id)
        for test_conf_obj in test_conf_objs:
            conf_data = dict()
            conf_data['item_conf_id'] = test_conf_obj.id
            conf_data['conf_id'] = test_conf_obj.test_conf_id
            conf_data['conf_name'] = test_conf_obj.test_conf_name
            conf_data['conf_source'] = test_conf_obj.conf_source
            conf_data['compare_conf_list'] = test_conf_obj.compare_conf_list
            sub_case_list = list()
            sub_case_objs = ReportItemSubCase.objects.filter(report_item_conf_id=test_conf_obj.id)
            for sub_case_obj in sub_case_objs:
                sub_case_data = dict()
                sub_case_data['sub_case_name'] = sub_case_obj.sub_case_name
                sub_case_data['result'] = sub_case_obj.result
                sub_case_data['compare_data'] = sub_case_obj.compare_data
                sub_case_list.append(sub_case_data)
            conf_data['sub_case_list'] = sub_case_list
            conf_list.append(conf_data)
        suite_data['conf_list'] = conf_list
        suite_list.append(suite_data)
    return suite_list


def package_name_v1(index, _data, name_li, report_item_id, test_type, base_index, is_automatic):
    if index == len(name_li) - 1:
        _data[name_li[index]] = get_func_suite_list_v1(
            report_item_id) if test_type == 'functional' else \
            get_perf_suite_list_v1(report_item_id, base_index, is_automatic)
    else:
        if name_li[index] in _data:
            package_name_v1(index + 1, _data[name_li[index]], name_li, report_item_id, test_type, base_index,
                            is_automatic)
        else:
            _data[name_li[index]] = dict()
            package_name_v1(index + 1, _data[name_li[index]], name_li, report_item_id, test_type, base_index,
                            is_automatic)


def get_func_suite_list_v1(report_item_id):
    suite_list = list()
    raw_sql = 'SELECT a.id AS item_suite_id, a.test_suite_id AS suite_id, a.test_suite_name AS suite_name, ' \
              'b.id AS item_conf_id, b.test_conf_id AS conf_id,b.test_conf_name AS conf_name, b.conf_source,' \
              'b.compare_conf_list, c.sub_case_name, c.compare_data,c.result FROM report_item_suite a ' \
              'LEFT JOIN report_item_conf b ON b.report_item_suite_id=a.id ' \
              'LEFT JOIN report_item_sub_case c ON c.report_item_conf_id=b.id ' \
              'WHERE a.report_item_id=%s AND a.is_deleted=0 AND b.is_deleted=0 AND c.is_deleted=0'
    test_suite_objs = query_all_dict(raw_sql, [report_item_id])
    for test_suite_obj in test_suite_objs:
        exist_suite = [suite for suite in suite_list if suite['item_suite_id'] == test_suite_obj['item_suite_id']]
        if len(exist_suite) > 0:
            suite_data = exist_suite[0]
            if 'conf_list' in suite_data:
                conf_list = suite_data['conf_list']
            else:
                conf_list = list()
        else:
            suite_data = dict()
            suite_data['item_suite_id'] = test_suite_obj['item_suite_id']
            suite_data['suite_id'] = test_suite_obj['suite_id']
            suite_data['suite_name'] = test_suite_obj['suite_name']
            conf_list = list()
            suite_list.append(suite_data)
        exist_conf = [conf for conf in conf_list if conf['conf_id'] == test_suite_obj['conf_id']]
        if len(exist_conf) > 0:
            conf_data = exist_conf[0]
            if 'sub_case_list' in conf_data:
                sub_case_list = conf_data['sub_case_list']
            else:
                sub_case_list = list()
        else:
            compare_conf_list = json.loads(test_suite_obj['compare_conf_list'])
            conf_data = dict()
            conf_data['conf_id'] = test_suite_obj['conf_id']
            conf_data['conf_name'] = test_suite_obj['conf_name']
            conf_data['compare_conf_list'] = compare_conf_list
            sub_case_list = list()
            conf_list.append(conf_data)
        compare_data = list()
        if test_suite_obj['compare_data']:
            compare_data = json.loads(test_suite_obj['compare_data'])
        sub_case_data = dict()
        sub_case_data['sub_case_name'] = test_suite_obj['sub_case_name']
        sub_case_data['compare_data'] = compare_data
        sub_case_list.append(sub_case_data)
        conf_data['sub_case_list'] = sub_case_list
        suite_data['conf_list'] = conf_list
    return suite_list


def _get_compare_data(metric_obj):
    compare_data = list()
    for item in metric_obj:
        if item:
            metric_cmp = dict()
            metric_cmp['test_value'] = format(float(item.get('test_value')), '.2f')
            metric_cmp['cv_value'] = item.get('cv_value')
            metric_cmp['compare_result'] = item.get('compare_result')
            metric_cmp['compare_value'] = item.get('compare_value')
            compare_data.append(metric_cmp)
        else:
            compare_data.append(dict())
    return compare_data


def get_perf_suite_list(report_item_id):
    suite_list = list()
    test_suite_objs = ReportItemSuite.objects.filter(report_item_id=report_item_id)
    for test_suite_obj in test_suite_objs:
        suite_data = dict()
        suite_data['item_suite_id'] = test_suite_obj.id
        suite_data['suite_name'] = test_suite_obj.test_suite_name
        suite_data['suite_id'] = test_suite_obj.test_suite_id
        suite_data['show_type'] = test_suite_obj.show_type
        # suite_data['test_suite_description'] = test_suite_obj.test_suite_description
        suite_data['test_suite_description'] = TestSuite.objects.filter(name=test_suite_obj.test_suite_name).first().doc
        suite_data['test_env'] = test_suite_obj.test_env
        suite_data['test_description'] = test_suite_obj.test_description
        suite_data['test_conclusion'] = test_suite_obj.test_conclusion
        conf_list = list()
        test_conf_objs = ReportItemConf.objects.filter(report_item_suite_id=test_suite_obj.id)
        for test_conf_obj in test_conf_objs:
            conf_data = dict()
            conf_data['item_conf_id'] = test_conf_obj.id
            conf_data['conf_id'] = test_conf_obj.test_conf_id
            conf_data['conf_name'] = test_conf_obj.test_conf_name
            conf_data['conf_source'] = test_conf_obj.conf_source
            conf_data['compare_conf_list'] = test_conf_obj.compare_conf_list
            metric_list = list()
            metric_objs = ReportItemMetric.objects.filter(report_item_conf_id=test_conf_obj.id)
            for metric_obj in metric_objs:
                test_metric = TestMetric.objects.filter(name=metric_obj.test_metric, object_type='case').first()
                compare_data = _get_compare_data(metric_obj.compare_data)
                metric_data = dict()
                metric_data['metric'] = metric_obj.test_metric
                metric_data['test_value'] = format(float(metric_obj.test_value), '.2f')
                metric_data['cv_value'] = metric_obj.cv_value
                metric_data['unit'] = metric_obj.unit
                metric_data['max_value'] = metric_obj.max_value
                metric_data['min_value'] = metric_obj.min_value
                metric_data['value_list'] = metric_obj.value_list
                metric_data['direction'] = metric_obj.direction
                metric_data['cv_threshold'] = test_metric.cv_threshold if test_metric else None
                metric_data['cmp_threshold'] = test_metric.cmp_threshold if test_metric else None
                metric_data['compare_data'] = compare_data
                metric_list.append(metric_data)
            conf_data['metric_list'] = metric_list
            conf_list.append(conf_data)
        suite_data['conf_list'] = conf_list
        suite_list.append(suite_data)
    return suite_list


def get_perf_suite_list_v1(report_item_id, base_index, is_automatic):
    suite_list = list()
    case_metric_sql = 'SELECT c.test_metric' \
                      ' FROM report_item_suite a ' \
                      'LEFT JOIN report_item_conf b ON b.report_item_suite_id=a.id ' \
                      'LEFT JOIN report_item_metric c ON c.report_item_conf_id=b.id ' \
                      'LEFT JOIN test_suite d ON a.test_suite_name=d.name ' \
                      'LEFT JOIN test_track_metric e ON c.test_metric=e.name AND e.object_id=b.test_conf_id ' \
                      'WHERE e.object_type="case" AND a.report_item_id=%s AND a.is_deleted=0 AND b.is_deleted=0 ' \
                      'AND c.is_deleted=0 AND d.is_deleted=0 AND e.is_deleted=0'
    raw_sql = 'SELECT a.id AS item_suite_id, a.test_suite_id AS suite_id, a.test_suite_name AS suite_name,' \
              'a.show_type, a.test_env, a.test_description, a.test_conclusion, ' \
              'b.id AS item_conf_id, b.test_conf_id AS conf_id,b.test_conf_name AS conf_name, b.conf_source,' \
              'b.compare_conf_list, c.test_metric,c.test_value,c.cv_value,d.doc AS test_suite_description,' \
              'c.compare_data,e.cv_threshold,e.cmp_threshold,e.unit,e.direction' \
              ' FROM report_item_suite a ' \
              'LEFT JOIN report_item_conf b ON b.report_item_suite_id=a.id ' \
              'LEFT JOIN report_item_metric c ON c.report_item_conf_id=b.id ' \
              'LEFT JOIN test_suite d ON a.test_suite_name=d.name ' \
              'LEFT JOIN test_track_metric e ON c.test_metric=e.name AND e.object_id=b.test_conf_id ' \
              'WHERE e.object_type="case" AND a.report_item_id=%s AND a.is_deleted=0 AND b.is_deleted=0 ' \
              'AND c.is_deleted=0 AND d.is_deleted=0 AND e.is_deleted=0'
    raw_sql += " union "
    raw_sql += 'SELECT a.id AS item_suite_id, a.test_suite_id AS suite_id, a.test_suite_name AS suite_name,' \
               'a.show_type, a.test_env, a.test_description, a.test_conclusion, ' \
               'b.id AS item_conf_id, b.test_conf_id AS conf_id,b.test_conf_name AS conf_name, b.conf_source,' \
               'b.compare_conf_list, c.test_metric,c.test_value,c.cv_value,d.doc AS test_suite_description,' \
               'c.compare_data,e.cv_threshold,e.cmp_threshold,e.unit,e.direction' \
               ' FROM report_item_suite a ' \
               'LEFT JOIN report_item_conf b ON b.report_item_suite_id=a.id ' \
               'LEFT JOIN report_item_metric c ON c.report_item_conf_id=b.id ' \
               'LEFT JOIN test_suite d ON a.test_suite_name=d.name ' \
               'LEFT JOIN test_track_metric e ON c.test_metric=e.name AND e.object_id=a.test_suite_id ' \
               'WHERE e.object_type="suite" AND a.report_item_id=%s AND a.is_deleted=0 AND b.is_deleted=0 ' \
               'AND c.is_deleted=0 AND d.is_deleted=0 AND e.is_deleted=0 AND c.test_metric not in (' + \
               case_metric_sql + ')'
    test_suite_objs = query_all_dict(raw_sql, [report_item_id, report_item_id, report_item_id])
    for test_suite_obj in test_suite_objs:
        exist_suite = [suite for suite in suite_list if suite['item_suite_id'] == test_suite_obj['item_suite_id']]
        if len(exist_suite) > 0:
            suite_data = exist_suite[0]
            if 'conf_list' in suite_data:
                conf_list = suite_data['conf_list']
            else:
                conf_list = list()
        else:
            suite_data = dict()
            suite_data['item_suite_id'] = test_suite_obj['item_suite_id']
            suite_data['suite_name'] = test_suite_obj['suite_name']
            suite_data['suite_id'] = test_suite_obj['suite_id']
            suite_data['show_type'] = test_suite_obj['show_type']
            suite_data['test_suite_description'] = test_suite_obj['test_suite_description']
            suite_data['test_env'] = test_suite_obj['test_env']
            suite_data['test_description'] = test_suite_obj['test_description']
            suite_data['test_conclusion'] = test_suite_obj['test_conclusion']
            conf_list = list()
            suite_list.append(suite_data)
        exist_conf = [conf for conf in conf_list if conf['conf_id'] == test_suite_obj['conf_id']]
        if len(exist_conf) > 0:
            conf_data = exist_conf[0]
            if 'metric_list' in conf_data:
                metric_list = conf_data['metric_list']
            else:
                metric_list = list()
        else:
            compare_conf_list = json.loads(test_suite_obj['compare_conf_list'])
            conf_data = dict()
            conf_data['conf_id'] = test_suite_obj['conf_id']
            conf_data['conf_name'] = test_suite_obj['conf_name']
            conf_data['compare_conf_list'] = compare_conf_list
            metric_list = list()
            conf_list.append(conf_data)
        compare_data = list()
        suite_compare_data = json.loads(test_suite_obj['compare_data'])
        if suite_compare_data:
            compare_data = _get_compare_data(suite_compare_data)
        metric_base_data = dict()
        metric_base_data['test_value'] = format(float(test_suite_obj['test_value']), '.2f')
        metric_base_data['cv_value'] = test_suite_obj['cv_value'].split('±')[-1] if test_suite_obj[
            'cv_value'] else None,
        if not is_automatic:
            compare_data.insert(base_index, metric_base_data)
        metric_data = dict()
        metric_data['metric'] = test_suite_obj['test_metric']
        metric_data['cv_threshold'] = test_suite_obj['cv_threshold']
        metric_data['cmp_threshold'] = test_suite_obj['cmp_threshold']
        metric_data['unit'] = test_suite_obj['unit']
        metric_data['direction'] = test_suite_obj['direction']
        metric_data['compare_data'] = compare_data
        metric_list.append(metric_data)
        conf_data['metric_list'] = metric_list
        suite_data['conf_list'] = conf_list
    return suite_list


def get_server_info(tag, objs):  # nq  c901
    server_li = list()
    baseline_id_list = list()
    job_id_list = list()
    ip_list = list()
    for obj in objs:
        is_baseline = obj.get('is_baseline')
        obj_id = obj.get('obj_id')
        if is_baseline:
            baseline_id_list.append(obj_id)
        else:
            job_id_list.append(obj_id)
    job_id_str = ','.join(str(e) for e in job_id_list)
    if baseline_id_list:
        perf_base_detail = PerfBaselineDetail.objects.filter(baseline_id__in=baseline_id_list).values_list(
            'test_job_id', flat=True).distinct()
        if perf_base_detail.exists():
            job_id_str = ','.join(str(e) for e in perf_base_detail)
        func_base_detail = FuncBaselineDetail.objects.filter(baseline_id__in=baseline_id_list).values_list(
            'test_job_id', flat=True).distinct()
        if func_base_detail.exists():
            job_id_str = ','.join(str(e) for e in func_base_detail)
    if job_id_str:
        raw_sql = 'SELECT ip,sm_name,distro,rpm_list,kernel_version,gcc,' \
                  'glibc,memory_info,disk,cpu_info,ether FROM test_server_snapshot ' \
                  'WHERE is_deleted=0  AND ' \
                  'job_id IN (' + job_id_str + ') AND distro IS NOT NULL UNION ' \
                  'SELECT private_ip AS ip,instance_type AS sm_name,distro,rpm_list,' \
                  'kernel_version,gcc,glibc,memory_info,disk,cpu_info,ether ' \
                  'FROM cloud_server_snapshot ' \
                  'WHERE is_deleted=0 AND ' \
                  'job_id IN (' + job_id_str + ') AND distro IS NOT null'
        all_server_info = query_all_dict(raw_sql.replace('\'', ''), params=None)
        for server_info in all_server_info:
            ip = server_info.get('ip')
            if not (server_info.get('distro') or server_info.get('rpm_list') or server_info.get('gcc')) or \
                    ip in ip_list:
                continue
            ip_list.append(ip)
            server_li.append({
                'ip/sn': ip,
                'distro': server_info.get('sm_name'),
                'os': server_info.get('distro'),
                'rpm': server_info.get('rpm_list').split('\n') if server_info.get('rpm_list') else list(),
                'kernel': server_info.get('kernel_version'),
                'gcc': server_info.get('gcc'),
                'glibc': server_info.get('glibc'),
                'memory_info': server_info.get('memory_info'),
                'disk': server_info.get('disk'),
                'cpu_info': server_info.get('cpu_info'),
                'ether': server_info.get('ether')
            })
    env_info = {
        'tag': tag,
        'server_info': server_li,
        'is_baseline': objs[0].get('is_baseline') if objs else 0,
        'base_objs': objs
    }
    return env_info


def get_group_server_info(base_group, compare_groups):
    baseline_id_list = list()
    job_id_list = list()
    base_group['is_base'] = 1
    groups = list()
    groups.append(base_group)
    for group in compare_groups:
        group['is_base'] = 0
        groups.append(group)
    for group in groups:
        objs = group.get('base_objs')
        group['job_id'] = list()
        for obj in objs:
            is_baseline = obj.get('is_baseline', 0)
            group['is_baseline'] = is_baseline
            obj_id = obj.get('obj_id')
            group['job_id'].append(obj_id)
            if is_baseline:
                baseline_id_list.append(obj_id)
            else:
                job_id_list.append(obj_id)
    env_info = {
        'base_group': list(),
        'compare_groups': list()
    }
    job_id_str = ','.join(str(e) for e in job_id_list)
    baseline_server_info = None
    all_server_info = None
    if baseline_id_list:
        baseline_id_str = ','.join(str(e) for e in baseline_id_list)
        baseline_raw_sql = 'SELECT baseline_id,ip,sm_name,distro,rpm_list,kernel_version,gcc,' \
                           'glibc,memory_info,disk,cpu_info,ether FROM baseline_server_snapshot ' \
                           'WHERE baseline_id IN (' + baseline_id_str + ') '
        baseline_server_info = query_all_dict(baseline_raw_sql.replace('\'', ''), params=None)
    if job_id_str:
        raw_sql = 'SELECT job_id,ip,sm_name,distro,rpm_list,kernel_version,gcc,' \
                  'glibc,memory_info,disk,cpu_info,ether FROM test_server_snapshot ' \
                  'WHERE job_id IN (' + job_id_str + ') UNION ' \
                  'SELECT job_id,pub_ip AS ip,instance_type AS sm_name,distro,rpm_list,' \
                  'kernel_version,gcc,glibc,memory_info,disk,cpu_info,ether ' \
                  'FROM cloud_server_snapshot ' \
                  'WHERE job_id IN (' + job_id_str + ')'
        all_server_info = query_all_dict(raw_sql.replace('\'', ''), params=None)
    for group in groups:
        group_ip_list = list()
        server_li = list()
        if group.get('is_baseline', 0) and baseline_server_info:
            group_server_li = [server for server in baseline_server_info if server['baseline_id'] in group['job_id']]
        else:
            group_server_li = [server for server in all_server_info if server['job_id'] in group['job_id']] \
                if all_server_info else list()
        for server_info in group_server_li:
            ip = server_info.get('ip')
            if not (server_info.get('distro') or server_info.get('rpm_list') or server_info.get('gcc')) or \
                    ip in group_ip_list:
                continue
            group_ip_list.append(ip)
            server_li.append({
                'ip/sn': ip,
                'distro': server_info.get('sm_name'),
                'os': server_info.get('distro'),
                'rpm': server_info.get('rpm_list').split('\n') if server_info.get('rpm_list') else list(),
                'kernel': server_info.get('kernel_version'),
                'gcc': server_info.get('gcc'),
                'glibc': server_info.get('glibc'),
                'memory_info': server_info.get('memory_info'),
                'disk': server_info.get('disk'),
                'cpu_info': server_info.get('cpu_info'),
                'ether': server_info.get('ether')
            })
        group_env_info = {
            'tag': group['tag'],
            'server_info': server_li,
            'is_baseline': group.get('is_baseline', 0),
            'base_objs': group.get('base_objs')
        }
        if group['is_base']:
            env_info['base_group'] = group_env_info
        else:
            env_info['compare_groups'].append(group_env_info)
    return env_info
