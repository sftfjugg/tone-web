# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author:
"""
from django.db.models import Q

from tone.core.common.services import CommonService
from tone.core.utils.tone_thread import ToneThread
from tone.models import Baseline, FuncBaselineDetail, PerfBaselineDetail, TestJob, PerfResult, TestJobCase, \
    TestSuite, TestCase, Project, TestStep, FuncResult, TestMetric, TestServerSnapshot, \
    CloudServerSnapshot
from tone.services.portal.sync_portal_task_servers import sync_baseline, sync_baseline_del
from tone.serializers.sys.baseline_serializers import FuncBaselineDetailSerializer, PerfBaselineDetialSerializer


def back_fill_version(func):
    """加入基线详情，基线产品版本为空，进行回填"""
    def init(_, data):
        res = func(_, data)
        baseline_id = PerfBaselineService().get_baseline_id(data)
        baseline = Baseline.objects.filter(id=baseline_id).first()
        if baseline is not None and not baseline.version:
            test_job_id = data.get('job_id')
            test_job = TestJob.objects.filter(id=test_job_id).first()
            if test_job is not None:
                project_id = test_job.project_id
                project = Project.objects.filter(id=project_id).first()
                if project is not None:
                    baseline.version = project.product_version
                    baseline.save()
        return res
    return init


class BaselineService(CommonService):

    def filter(self, queryset, data):
        q = Q()
        if data.get('id'):
            q &= Q(id=data.get('id'))
        if data.get('name'):
            q &= Q(name__icontains=data.get('name'))
        if data.get('version'):
            q &= Q(version=data.get('version')) | Q(version='')
        if data.get('test_type'):
            q &= Q(test_type=data.get('test_type'))
        if data.get('server_provider'):
            q &= Q(server_provider=data.get('server_provider'))
        if data.get('ws_id'):
            q &= Q(ws_id=data.get('ws_id'))
        if data.get('creator'):
            q &= Q(creator__in=data.getlist('creator'))
        if data.get('update_user'):
            q &= Q(update_user__in=data.getlist('update_user'))
        q = self.expand_filter(data, q)
        return queryset.filter(q)

    @staticmethod
    def expand_filter(data, q):
        if data.get('filter_id'):
            q &= ~Q(id__in=data.get('filter_id').split(','))
        if data.get('filter_version'):
            q &= Q(version=data.get('filter_version'))
        return q

    @staticmethod
    def create(data, operator):
        creator = operator.id
        name = data.get('name')
        ws_id = data.get('ws_id')
        baseline = Baseline.objects.filter(name=name, ws_id=ws_id).first()
        if baseline:
            return False, '基线已存在'
        data.update({'creator': creator})
        form_fields = ['name', 'version', 'description', 'test_type', 'creator', 'ws_id']
        create_data = dict()
        for field in form_fields:
            create_data.update({field: data.get(field)})
        baseline = Baseline.objects.create(**create_data)
        return True, baseline

    @staticmethod
    def update(data, operator):
        update_user = operator.id
        name = data.get('name')
        test_type = data.get('test_type')
        ws_id = data.get('ws_id')
        baseline_id = data.get("baseline_id")
        baseline = Baseline.objects.filter(name=name, test_type=test_type, ws_id=ws_id).first()
        if baseline is not None and str(baseline.id) != str(baseline_id):
            return False, '基线已存在'
        allow_modify_fields = ['name', 'description']
        baseline = Baseline.objects.filter(id=baseline_id)
        if baseline.first() is None:
            return False, '基线不存在.'
        sync_baseline.delay(baseline_id)
        update_data = dict()
        data.update({'update_user': update_user})
        for field in allow_modify_fields:
            if data.get(field) is not None:
                update_data.update({field: data.get(field)})
        baseline.update(**update_data)
        return True, baseline.first()

    @staticmethod
    def delete(data):
        baseline_id = data.get("baseline_id")
        sync_baseline_del.delay(baseline_id)
        # 删除基线分类
        Baseline.objects.filter(id=baseline_id).delete()
        # 删除基线相关的其他信息
        for func_baseline_detail in FuncBaselineDetail.objects.filter(baseline_id=baseline_id):
            FuncResult.objects.filter(test_job_id=func_baseline_detail.source_job_id,
                                      test_suite_id=func_baseline_detail.test_suite_id,
                                      test_case_id=func_baseline_detail.test_case_id,
                                      sub_case_name=func_baseline_detail.sub_case_name,
                                      ).update(bug=None, description=None, match_baseline=False)
        FuncBaselineDetail.objects.filter(baseline_id=baseline_id).delete()
        PerfBaselineDetail.objects.filter(baseline_id=baseline_id).delete()


class FuncBaselineService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('baseline_id'):
            q &= Q(baseline_id=data.get('baseline_id'))
        if data.get('test_suite_id'):
            q &= Q(test_suite_id=data.get('test_suite_id'))
        if data.get('test_case_id'):
            q &= Q(test_case_id=data.get('test_case_id'))
        return queryset.filter(q)

    @staticmethod
    def get(queryset, data):
        """根据请求参数判断请求返回信息"""
        response_data = []
        baseline_id = data.get("baseline_id")
        queryset = queryset.filter(baseline_id=baseline_id)
        test_suite_id = data.get("test_suite_id")

        # 参数为空，返回Test Suite列表
        if not test_suite_id:
            suite_id_list = queryset.values_list("test_suite_id", flat=True)
            for suite_id in set(suite_id_list):
                # 被删除suite的基线不再展示
                if not TestSuite.objects.filter(id=suite_id).exists():
                    continue
                # 被删除case的基线suite不再展示
                case_id_list = queryset.filter(test_suite_id=suite_id).values_list("test_case_id", flat=True)
                if not TestCase.objects.filter(id__in=case_id_list).exists():
                    continue
                suite_data = {}
                suite_name = TestSuite.objects.get(id=suite_id).name
                suite_data["test_suite_name"] = suite_name
                suite_data["test_suite_id"] = suite_id
                response_data.append(suite_data)
        else:
            suite_id = data.get("test_suite_id", "")
            case_id = data.get("test_case_id", "")

            if suite_id:
                queryset = queryset.filter(test_suite_id=suite_id)
                # failcase展开, 展示信息
                # sub_case_name, bug, source_job_id, impact_result, note
                if case_id:
                    queryset = queryset.filter(test_case_id=case_id)
                    return True, queryset
                # conf展开
                else:
                    case_id_list = queryset.values_list("test_case_id", flat=True)
                    for case_id in set(case_id_list):
                        # 被删除case的基线不再展示
                        if not TestCase.objects.filter(id=case_id).exists():
                            continue
                        case_data = {}
                        case_name = TestCase.objects.get(id=case_id).name
                        case_data["test_case_name"] = case_name
                        case_data["test_case_id"] = case_id
                        response_data.append(case_data)

        return False, response_data

    @staticmethod
    def back_fill_version(baseline_id_list, data):
        """回填Job版本号"""
        # 详情加入成功后，会填基线版本
        tmp_baselines = Baseline.objects.filter(id__in=baseline_id_list)
        for tmp_baseline in tmp_baselines:
            if tmp_baseline is not None and not tmp_baseline.version:
                test_job_id = data.get('test_job_id')
                test_job = TestJob.objects.filter(id=test_job_id).first()
                if test_job is not None:
                    project_id = test_job.project_id
                    project = Project.objects.filter(id=project_id).first()
                    if project is not None:
                        tmp_baseline.version = project.product_version
                        tmp_baseline.save()

    def create(self, data):
        baseline_id_list = data.get('baseline_id', [])
        test_type = data.get('test_type', 'functional')
        ws_id = data.get('ws_id', 'xwgpiwkk')
        test_job_id = data.get('test_job_id')
        test_suite_id = data.get('test_suite_id')
        test_case_id = data.get('test_case_id')
        sub_case_name = data.get('sub_case_name')
        result_id = data.get('result_id')
        func_result = None
        if result_id is not None:
            func_result = FuncResult.objects.filter(id=result_id).first()
            if func_result is not None:
                sub_case_name = func_result.sub_case_name
        func_baseline_detail_list = list()
        msg = 'Required request parameters'
        if not all([baseline_id_list, test_type, ws_id, test_job_id, test_suite_id, test_case_id, sub_case_name]):
            return False, msg
        for baseline_id in baseline_id_list:
            func_baseline_detail = FuncBaselineDetail.objects.filter(
                baseline_id=baseline_id, test_suite_id=test_suite_id,
                test_case_id=test_case_id, sub_case_name=sub_case_name).first()
            if data.get('impact_result'):
                func_result.match_baseline = True
            func_result.bug = data.get('bug')
            func_result.description = data.get('description')
            func_result.save()
            # 功能基线详情已经存在，更新 impact_result bug note description
            if func_baseline_detail is not None:
                for tmp_field in ['impact_result', 'bug', 'note', 'description']:
                    setattr(func_baseline_detail, tmp_field, data.get(tmp_field, ''))
                func_baseline_detail.source_job_id = test_job_id
                func_baseline_detail.save()
                continue
            data.update({
                'source_job_id': test_job_id,
                'baseline_id': baseline_id,
                'sub_case_name': sub_case_name
            })
            form_fields = ['baseline_id', 'test_job_id', 'test_suite_id', 'test_case_id', 'source_job_id',
                           'impact_result', 'bug', 'note', 'description', 'sub_case_name']
            create_data = dict()
            for field in form_fields:
                create_data.update({field: data.get(field)})
            func_baseline_detail_list.append(FuncBaselineDetail(**create_data))
        self.back_fill_version(baseline_id_list, data)
        # 加入基线和测试基线相同时，匹配基线
        # self.func_match_baseline(func_result, compare_baseline, baseline_id)
        return True, FuncBaselineDetail.objects.bulk_create(func_baseline_detail_list)

    @staticmethod
    def func_match_baseline(func_result, compare_baseline, baseline_id):
        """功能匹配基线"""
        if func_result is not None and compare_baseline == baseline_id:
            func_result.match_baseline = True
            func_result.save()

    @staticmethod
    def update(data):
        """编辑FailCase信息"""
        detail_id = data.get("id")
        allow_modify_fields = ['bug', 'impact_result', 'note', 'description']
        baseline_detail = FuncBaselineDetail.objects.filter(id=detail_id)
        if baseline_detail.first() is None:
            return False, '功能基线详情不存在'
        update_data = dict()
        for field in allow_modify_fields:
            if data.get(field) is not None:
                update_data.update({field: data.get(field)})
        baseline_detail.update(**update_data)
        sync_baseline.delay(baseline_detail.first().baseline_id)
        return True, baseline_detail.first()

    @staticmethod
    def delete(data):
        detail_id = data.get("id")
        # 基线删除，匹配基线更新为 False
        func_detail = FuncBaselineDetail.objects.filter(id=detail_id).first()
        if func_detail is not None:
            FuncResult.objects.filter(test_suite_id=func_detail.test_suite_id,
                                      test_job_id=func_detail.source_job_id,
                                      test_case_id=func_detail.test_case_id,
                                      sub_case_name=func_detail.sub_case_name).update(bug=None,
                                                                                      description=None,
                                                                                      match_baseline=False)

        baseline_id = func_detail.baseline_id
        func_detail.delete()
        sync_baseline.delay(baseline_id)


class PerfBaselineService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('baseline_id'):
            q &= Q(baseline_id=data.get('baseline_id'))
        if data.get('test_suite_id'):
            q &= Q(test_suite_id=data.get('test_suite_id'))
        # 集团 机型
        if data.get('server_sm_name'):
            q &= Q(server_sm_name=data.get('server_sm_name'))
        # 云上 规格
        if data.get('server_instance_type'):
            q &= Q(server_instance_type=data.get('server_instance_type'))
        if data.get('test_case_id'):
            q &= Q(test_case_id=data.get('test_case_id'))
        if data.get('metric'):
            q &= Q(metric=data.get('metric'))
        return queryset.filter(q)

    def get(self, queryset, data):
        """获取性能基线详情"""
        baseline_id = data.get("baseline_id")
        # 查询集团/云上
        queryset = queryset.filter(baseline_id=baseline_id)
        response_data = []
        test_suite_id = data.get("test_suite_id")
        test_case_id = data.get("test_case_id")
        machine = data.get("server_sn")
        # 展开suite
        if not any([test_suite_id, machine, test_case_id]):
            response_data = self.get_test_suite_name(queryset)
        elif test_suite_id:
            queryset = queryset.filter(test_suite_id=test_suite_id)
            if machine is not None:
                queryset = queryset.filter(server_sn=machine)
                # 展开conf
                if not test_case_id:
                    response_data = self.get_conf_info(queryset)
                # 展开metric
                else:
                    queryset = queryset.filter(test_case_id=test_case_id)
                    return True, queryset
            # 展开机器
            else:
                if test_case_id:
                    queryset = queryset.filter(test_case_id=test_case_id)
                    return True, queryset
                else:
                    response_data = self.get_conf_info(queryset)
        return False, response_data

    def create(self, data):
        """新增性能详情"""
        perf_baseline_detail = self.filter(PerfBaselineDetail.objects.all(), data).first()
        if perf_baseline_detail:
            return False, '性能基线详情不存在'
        form_fields = ['baseline_id', 'test_job_id', 'test_suite_id', 'test_case_id', 'server_ip',
                       'server_sn', 'server_sm_name', 'server_instance_type', 'server_image',
                       'server_bandwidth', 'run_mode', 'source_job_id', 'metric', 'test_value',
                       'cv_value', 'max_value', 'min_value', 'value_list', 'note']
        create_data = dict()
        for field in form_fields:
            create_data.update({field: data.get(field)})
        perf_baseline_detail = PerfBaselineDetail.objects.create(**create_data)
        return True, perf_baseline_detail

    @staticmethod
    def delete(data):
        """删除Metric信息"""
        detail_id = data.get("id")
        if PerfBaselineDetail.objects.filter(id=detail_id).exists():
            baseline_id = PerfBaselineDetail.objects.filter(id=detail_id).first().baseline_id
            PerfBaselineDetail.objects.filter(id=detail_id).delete()
            sync_baseline.delay(baseline_id)

    @staticmethod
    def get_test_suite_name(queryset):
        """获取suite_name展开信息"""
        suite_id_list = queryset.values_list("test_suite_id", flat=True)
        suite_list = []
        for suite_id in set(suite_id_list):
            # 被删除suite的基线不再展示
            if not TestSuite.objects.filter(id=suite_id).exists():
                continue
            suite_name_data = {}
            suite_name = TestSuite.objects.get(id=suite_id).name
            suite_name_data["test_suite_name"] = suite_name
            suite_name_data["test_suite_id"] = suite_id
            suite_list.append(suite_name_data)
        return suite_list

    @staticmethod
    def get_conf_info(queryset):
        """展开conf"""
        conf_list = []
        case_id_list = queryset.values_list("test_case_id", flat=True)
        # 根据case_id返回 case_name
        for case_id in set(case_id_list):
            # 被删除case的基线不再展示
            if not TestCase.objects.filter(id=case_id).exists():
                continue
            case_name_data = {}
            case_name = TestCase.objects.get(id=case_id).name
            case_name_data["test_case_name"] = case_name
            case_name_data["test_case_id"] = case_id
            conf_list.append(case_name_data)
        return conf_list

    @staticmethod
    def get_baseline_id(data):
        """baseline_id不存在, 则创建基线"""
        baseline_id = data.get('baseline_id')
        baseline_name = data.get('baseline_name')
        test_type = data.get('test_type', 'performance')
        ws_id = data.get('ws_id')
        if baseline_id is None:
            tmp_baseline = Baseline.objects.filter(name=baseline_name, test_type=test_type, ws_id=ws_id).first()
            # 基线名称不存在则创建基线
            if tmp_baseline is None:
                tmp_data = {
                    'name': baseline_name,
                    'test_type': test_type,
                    'ws_id': ws_id,
                }
                tmp_baseline = Baseline.objects.create(**tmp_data)
            baseline_id = tmp_baseline.id
        return baseline_id

    @back_fill_version
    def add_one_perf(self, data):
        """通过conf加入基线"""
        sm_name = ''
        instance_type = ''
        image = ''
        bandwidth = 10
        machine = None
        machine_ip = ''
        baseline_id = data.get('baseline_id')
        job_id = data.get('job_id')
        suite_id = data.get('suite_id')
        case_id = data.get('case_id')
        if not TestSuite.objects.filter(id=suite_id).exists() or not TestCase.objects.filter(id=case_id).exists():
            return False, "suite 或 case 已经被删除"
        if not all([baseline_id, case_id, job_id, suite_id]):
            return False, "Required request parameters: 1.baseline_id, 2.job_id, 3.suite_id, 4.case_id"
        test_job = TestJob.objects.filter(id=job_id).first()
        if not test_job:
            return False, "关联job不存在!"
        source_job_id = job_id
        test_job_case = TestJobCase.objects.filter(job_id=job_id, test_suite_id=suite_id,
                                                   test_case_id=case_id).first()
        job_case_id = test_job_case.id
        test_step_case = TestStep.objects.filter(job_id=job_id, job_case_id=job_case_id).first()
        if test_step_case and test_step_case.server:
            server_object_id = test_step_case.server
            machine = TestServerSnapshot.objects.filter(id=server_object_id, query_scope='all').first()
            if machine is not None:
                sm_name = machine.sm_name
                machine_ip = machine.ip
            else:
                machine = CloudServerSnapshot.objects.filter(id=server_object_id, query_scope='all').first()
                if machine is not None:
                    instance_type = machine.instance_type
                    image = machine.image
                    bandwidth = machine.bandwidth
                    machine_ip = machine.private_ip
        perf_res_list = PerfResult.objects.filter(test_job_id=job_id, test_suite_id=suite_id, test_case_id=case_id)
        create_list = []
        update_dict = dict()
        thread_tasks = []
        for perf_res in perf_res_list:
            thread_tasks.append(
                ToneThread(self._get_add_perf_baseline_detail,
                           (bandwidth, baseline_id, case_id, create_list, image, instance_type,
                            job_id, machine, machine_ip, perf_res, sm_name, source_job_id, suite_id,
                            test_job_case, update_dict))
            )
            thread_tasks[-1].start()
        for thread_task in thread_tasks:
            thread_task.join()
            thread_task.get_result()
        perf_baseline_detail_list = self._add_perf_baseline_detail(job_id, suite_id, case_id, create_list, update_dict,
                                                                   test_job, baseline_id)
        return True, perf_baseline_detail_list

    def _get_add_perf_baseline_detail(self, bandwidth, baseline_id, case_id, create_list, image, instance_type, job_id,
                                      machine, machine_ip, perf_res, sm_name, source_job_id, suite_id, test_job_case,
                                      update_dict):
        perf_detail = PerfBaselineDetail.objects.filter(baseline_id=baseline_id, test_suite_id=suite_id,
                                                        test_case_id=case_id, metric=perf_res.metric)
        create_data = PerfBaselineDetail(
            baseline_id=baseline_id,
            test_job_id=job_id,
            test_suite_id=suite_id,
            test_case_id=case_id,
            server_ip=machine_ip,
            server_sn='' if machine is None else machine.sn,
            server_sm_name=sm_name,
            server_instance_type=instance_type,
            server_image=image,
            server_bandwidth=bandwidth,
            run_mode=test_job_case.run_mode,
            source_job_id=source_job_id,
            metric=perf_res.metric,
            test_value=perf_res.test_value,
            cv_value=perf_res.cv_value,
            max_value=perf_res.max_value,
            min_value=perf_res.min_value,
            value_list=perf_res.value_list,
            note=test_job_case.note
        )
        if not perf_detail.exists():
            create_list.append(create_data)
        else:
            update_dict.setdefault(str(perf_detail[0].id), create_data)

    def _add_perf_baseline_detail(self, job_id, suite_id, case_id, create_list, update_dict, test_job, baseline_id):
        add_list = []
        if create_list:
            add_list.extend([perf for perf in PerfBaselineDetail.objects.bulk_create(create_list)])
            if test_job.baseline_id == baseline_id:
                metric_list = [metric.metric for metric in create_list]
                PerfResult.objects.filter(test_job_id=job_id, test_suite_id=suite_id, test_case_id=case_id,
                                          metric__in=metric_list).update(match_baseline=True)
        if update_dict:
            id_list = list(update_dict.keys())
            perf_detail = PerfBaselineDetail.objects.filter(id__in=id_list)
            for perf_obj in perf_detail:
                update_data = update_dict.get(str(perf_obj.id))
                if update_data:
                    perf_obj.baseline_id = update_data.baseline_id
                    perf_obj.test_job_id = update_data.test_job_id
                    perf_obj.test_suite_id = update_data.test_suite_id
                    perf_obj.test_case_id = update_data.test_case_id
                    perf_obj.server_ip = update_data.server_ip
                    perf_obj.server_sn = update_data.server_sn
                    perf_obj.server_sm_name = update_data.server_sm_name
                    perf_obj.server_instance_type = update_data.server_instance_type
                    perf_obj.server_image = update_data.server_image
                    perf_obj.server_bandwidth = update_data.server_bandwidth
                    perf_obj.run_mode = update_data.run_mode
                    perf_obj.source_job_id = update_data.source_job_id
                    perf_obj.metric = update_data.metric
                    perf_obj.test_value = update_data.test_value
                    perf_obj.cv_value = update_data.cv_value
                    perf_obj.max_value = update_data.max_value
                    perf_obj.min_value = update_data.min_value
                    perf_obj.value_list = update_data.value_list
                    perf_obj.note = update_data.note

            update_fields = ['baseline_id', 'test_job_id', 'test_suite_id', 'test_case_id', 'server_ip', 'server_sn',
                             'server_sm_name', 'server_instance_type', 'server_image', 'server_bandwidth', 'run_mode',
                             'source_job_id', 'metric', 'test_value', 'cv_value', 'max_value', 'min_value',
                             'value_list', 'note']
            PerfBaselineDetail.objects.bulk_update(perf_detail, update_fields)
            add_list.extend([perf for perf in perf_detail])
        return add_list

    @staticmethod
    def get_perf_res_id_list(job_id, suite_id_list, suite_data_list):
        """批量加入性能基线获取 结果id列表"""
        # 批量修改的性能测试结果id列表
        perf_res_id_list = list()
        # 根据job id过滤测试结果
        query_set = PerfResult.objects.filter(test_job_id=job_id)
        # suite 直接批量加入结果基线
        if suite_id_list:
            perf_res_id_list.extend(query_set.filter(test_suite_id__in=suite_id_list).values_list('id', flat=True))

        # suite下的多项 case加入基线
        for suite_data in suite_data_list:
            tmp_suite_id = suite_data.get('suite_id')
            tmp_case_id_list = suite_data.get('case_list', [])
            for tmp_case_id in tmp_case_id_list:
                perf_res_id_list.extend(query_set.filter(test_suite_id=tmp_suite_id,
                                                         test_case_id=tmp_case_id).values_list('id', flat=True))
        return perf_res_id_list

    @back_fill_version
    def add_perf(self, data):
        """
        批量加入基线
        请求数据：
        {
            "baseline_id": 1,
            "job_id": "13",
            "suite_list": [5, 6],
            "suite_data": [
                           {
                            suite_id: 1,
                            case_list: [1, 2, 3]
                           },
                           {
                            suite_id: 2,
                            case_list: [4, 5]
                           },
                           {
                            suite_id: 4,
                            case_list: [7]
                           },
                       ]
        }
        """
        job_id = data.get('job_id')
        baseline_id = self.get_baseline_id(data)
        if not all([baseline_id, job_id]):
            return False, "Required request parameters: 1.baseline_id, 2.job_id, 3.suite_list, 4.suite_data"
        suite_data_list = data.get('suite_data', [])
        suite_id_list = data.get('suite_list')
        perf_baseline_detail_list = list()

        perf_res_id_list = self.get_perf_res_id_list(job_id, suite_id_list, suite_data_list)
        thread_tasks = []
        for perf_res_id in set(perf_res_id_list):
            thread_tasks.append(
                ToneThread(self._add_perf_baseline, (perf_res_id, job_id, baseline_id))
            )
            thread_tasks[-1].start()
        for thread_task in thread_tasks:
            thread_task.join()
            perf_baseline_detail_obj = thread_task.get_result()
            if perf_baseline_detail_obj:
                perf_baseline_detail_list.append(perf_baseline_detail_obj)
        return True, PerfBaselineDetail.objects.bulk_create(perf_baseline_detail_list)

    def _add_perf_baseline(self, perf_res_id, job_id, baseline_id):
        sm_name = ''
        instance_type = ''
        image = ''
        bandwidth = 10
        machine = None
        machine_ip = ''
        test_job = TestJob.objects.filter(id=job_id).first()
        if not test_job:
            return False, "关联job不存在!"
        perf_result = PerfResult.objects.filter(id=perf_res_id).first()
        suite_id = perf_result.test_suite_id
        case_id = perf_result.test_case_id
        test_job_case = TestJobCase.objects.filter(job_id=job_id, test_suite_id=suite_id,
                                                   test_case_id=case_id).first()
        job_case_id = test_job_case.id
        test_step_case = TestStep.objects.filter(job_id=job_id, job_case_id=job_case_id).first()
        server_object_id = test_step_case.server

        if server_object_id:
            machine = TestServerSnapshot.objects.filter(id=int(server_object_id), query_scope='all').first()
            if machine is not None:
                sm_name = machine.sm_name
                machine_ip = machine.ip
            else:
                machine = CloudServerSnapshot.objects.filter(id=server_object_id, query_scope='all').first()
                if machine is not None:
                    instance_type = machine.instance_type
                    image = machine.image
                    bandwidth = machine.bandwidth
                    machine_ip = machine.private_ip
        perf_detail = PerfBaselineDetail.objects.filter(baseline_id=baseline_id, test_suite_id=suite_id,
                                                        test_case_id=case_id, metric=perf_result.metric)
        # 重复详情不再加入
        if not perf_detail.exists():
            perf_baseline_detail_obj = PerfBaselineDetail(
                baseline_id=baseline_id,
                test_job_id=job_id,
                test_suite_id=suite_id,
                test_case_id=case_id,
                server_ip=machine_ip,
                server_sn='' if machine is None else machine.sn,
                server_sm_name=sm_name,
                server_instance_type=instance_type,
                server_image=image,
                server_bandwidth=bandwidth,
                run_mode=test_job_case.run_mode,
                source_job_id=job_id,
                metric=perf_result.metric,
                test_value=perf_result.test_value,
                cv_value=perf_result.cv_value,
                max_value=perf_result.max_value,
                min_value=perf_result.min_value,
                value_list=perf_result.value_list,
                note=test_job_case.note
            )
            # 加入基线和测试基线相同时，匹配基线
            if test_job.baseline_id == baseline_id:
                perf_result.match_baseline = True
                perf_result.save()
            return perf_baseline_detail_obj
        else:
            PerfBaselineDetail.objects.filter(id=perf_detail[0].id).update(
                baseline_id=baseline_id,
                test_job_id=job_id,
                test_suite_id=suite_id,
                test_case_id=case_id,
                server_ip=machine_ip,
                server_sn='' if machine is None else machine.sn,
                server_sm_name=sm_name,
                server_instance_type=instance_type,
                server_image=image,
                server_bandwidth=bandwidth,
                run_mode=test_job_case.run_mode,
                source_job_id=job_id,
                metric=perf_result.metric,
                test_value=perf_result.test_value,
                cv_value=perf_result.cv_value,
                max_value=perf_result.max_value,
                min_value=perf_result.min_value,
                value_list=perf_result.value_list,
                note=test_job_case.note
            )
            return None


class SuiteSearchServer(CommonService):
    @staticmethod
    def search_suite(data):
        # 查询集团/云上
        baseline_id = data.get("baseline_id")
        baseline = Baseline.objects.all().filter(id=baseline_id).first()
        test_type = baseline.test_type
        if test_type == "functional":
            base_model = FuncBaselineDetail
            base_serializer = FuncBaselineDetailSerializer
        else:
            base_model = PerfBaselineDetail
            base_serializer = PerfBaselineDetialSerializer
        queryset = base_model.objects.all()
        serializer_class = base_serializer
        queryset = queryset.filter(baseline_id=baseline_id)
        search_suite = data.get("search_suite")
        if not search_suite:
            return serializer_class, queryset

        suite_name_data = []
        suite_id_list = queryset.values_list("test_suite_id", flat=True)
        for suite_id in set(suite_id_list):
            suite_data = {}
            suite_name = TestSuite.objects.get(id=suite_id).name
            # 模糊查询suite名称
            if search_suite in suite_name:
                suite_data['test_suite_name'] = suite_name
                suite_data['test_suite_id'] = suite_id
                suite_name_data.append(suite_data)
        return None, suite_name_data


class ContrastBaselineService(CommonService):
    @staticmethod
    def get_res_list(job_id, suite_id_list, suite_data_list):
        """获取性能结果列表"""
        perf_res_list = PerfResult.objects.filter(test_job_id=job_id, test_suite_id__in=suite_id_list)
        for suite_data in suite_data_list:
            tmp_suite_id = suite_data.get('suite_id')
            tmp_case_id_list = suite_data.get('case_list', [])
            for tmp_case_id in tmp_case_id_list:
                perf_res_list = perf_res_list | PerfResult.objects.filter(test_job_id=job_id,
                                                                          test_suite_id=tmp_suite_id,
                                                                          test_case_id=tmp_case_id)
        return perf_res_list

    @staticmethod
    def modify_perf_res(perf_res, baseline_id, perf_detail):
        """对比性能基线，更新性能测试结果信息"""
        # 对比基线的id , compare_baseline
        perf_res.compare_baseline = baseline_id
        # 回填结果基线值baseline_value、 baseline_cv_value （AVG ± CV）,
        if perf_detail.test_value:
            perf_res.baseline_value = round(float(perf_detail.test_value), 2)
        perf_res.baseline_cv_value = perf_detail.cv_value
        # 获取对比结果: （测试结果值-基线值）/基线值
        if perf_detail.test_value and float(perf_detail.test_value) != 0.0:
            perf_res.compare_result = round((float(perf_res.test_value) - float(perf_detail.test_value)
                                             ) / float(perf_detail.test_value), 2)
        else:
            perf_res.compare_result = 0.00
        # 获取跟踪结果 increase, decline, normal, na, invalid
        # 获取阈值 test_track_metric中 cmp_threshold
        tmp_metric = TestMetric.objects.filter(name=perf_res.metric, object_type='case',
                                               object_id=perf_res.test_case_id).first()
        # 优先找case级别的对比，没有对比suite级
        if tmp_metric is None:
            tmp_metric = TestMetric.objects.filter(name=perf_res.metric, object_type='suite',
                                                   object_id=perf_res.test_suite_id).first()
        # 如果大于cmp_threshold上界则track_result结果记为increase ，小于区间下界，则记为decline，
        # 在区间范围内则normal， 其它无法对比的异常情况记为na （test_track_metric 中找不到记录或没有指定对比基线)
        if tmp_metric is None:
            perf_res.track_result = 'na'
        else:
            # cv在cv阈值范围内
            cv_value = perf_res.cv_value.split('±')[-1] if perf_res.cv_value else None
            if cv_value is None:
                perf_res.track_result = 'na'
            else:
                cv_value = float(cv_value.split('%')[0])
                if cv_value > tmp_metric.cv_threshold * 100:
                    perf_res.track_result = 'invalid'
                else:
                    strand_value = perf_res.compare_result
                    # 方向为下降时， 与上升是相反的比较方式
                    if tmp_metric.direction == 'decline':
                        strand_value = -strand_value
                    threshold_range = tmp_metric.cmp_threshold
                    if -threshold_range <= strand_value <= threshold_range:
                        perf_res.track_result = 'normal'
                    elif strand_value < -threshold_range:
                        perf_res.track_result = 'decline'
                    else:
                        perf_res.track_result = 'increase'
        return perf_res

    def contrast_perf(self, data):
        baseline_id = data.get('baseline_id')
        job_id = data.get('job_id')
        suite_id_list = data.get('suite_list', [])
        suite_data_list = data.get('suite_data', [])

        perf_res_list = self.get_res_list(job_id, suite_id_list, suite_data_list)
        thread_tasks = []
        for perf_res in perf_res_list:
            thread_tasks.append(
                ToneThread(self.save_compare_baseline, (baseline_id, perf_res))
            )
            thread_tasks[-1].start()
        for thread_task in thread_tasks:
            thread_task.join()
            perf_res = thread_task.get_result()
            if perf_res:
                perf_res.save()
        return True, '对比基线完成'

    def save_compare_baseline(self, baseline_id, perf_res):
        # 获取性能基线详情信息
        perf_detail = PerfBaselineDetail.objects.filter(baseline_id=baseline_id,
                                                        test_suite_id=perf_res.test_suite_id,
                                                        test_case_id=perf_res.test_case_id, metric=perf_res.metric
                                                        ).first()
        if perf_detail:
            return self.modify_perf_res(perf_res, baseline_id, perf_detail)
