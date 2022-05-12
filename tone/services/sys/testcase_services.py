import os
import json

from django.db import transaction
from django.db.models import Q

from tone.core.common.constant import TEST_SUITE_REDIS_KEY
from tone.core.common.redis_cache import redis_cache
from tone.core.common.services import CommonService
from tone.core.utils.config_parser import get_config_from_db
from tone.models import TestCase, TestSuite, TestMetric, WorkspaceCaseRelation, PerfResult, TestDomain, \
    DomainRelation, datetime, SuiteData, CaseData, BaseConfig, RoleMember, Role, TestJobCase, TestJob, \
    TestTmplCase, TestTemplate, TestBusiness, BusinessSuiteRelation, AccessCaseConf, User
from tone.serializers.sys.testcase_serializers import RetrieveCaseSerializer
from tone.tasks import sync_suite_case_toneagent


class TestCaseService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('suite_id'):
            q &= Q(test_suite_id=data.get('suite_id'))
        if data.get('case_id'):
            q &= Q(id=data.get('case_id'))
        if data.get('certificated'):
            q &= Q(certificated=data.get('certificated'))
        if data.get('name'):
            q &= Q(name__contains=data.get('name'))
        return queryset.filter(q)

    def create(self, data):
        test_case = TestCase.objects.filter(test_suite_id=data.get('test_suite_id'), name=data.get('name')).first()
        if test_case:
            return False, 'case 已存在'
        # domain兼容多选
        domain_list = self.get_domain_list(data)
        form_fields = ['name', 'test_suite_id', 'repeat', 'timeout', 'doc',
                       'description', 'var', 'is_default', 'alias', 'certificated']
        create_data = {'repeat': 1, 'timeout': 3600, 'is_default': False, 'certificated': False}
        for field in form_fields:
            if data.get(field):
                create_data.update({field: data.get(field)})
        short_name = '-'.join([item.split('=')[-1] for item in data.get('name').split(',')])
        create_data['short_name'] = short_name
        test_case = TestCase.objects.create(**create_data)
        # domain 关联
        self.create_domain_relation([test_case.id], domain_list)
        ci_type = data.get('ci_type')
        if ci_type:
            create_data = {'test_case_id': test_case.id, 'ci_type': ci_type, 'host': '', 'user': '', 'token': ''}
            update_fields = ['host', 'user', 'token', 'pipeline_id', 'project_name', 'params']
            for field in update_fields:
                if data.get(field) is not None:
                    create_data.update({field: data.get(field)})
            AccessCaseConf.objects.create(**create_data)
        return True, test_case

    @staticmethod
    def get_domain_list(data):
        domain_list = list()
        domain_list_str = data.get('domain_list_str')
        if domain_list_str:
            domain_list = [int(domain.strip()) for domain in domain_list_str.split(',')]
        return domain_list

    @staticmethod
    def create_domain_relation(case_id_list, domain_list, is_delete=False):
        for case_id in case_id_list:
            if is_delete:
                DomainRelation.objects.filter(object_type='case', object_id=case_id).delete()
            [DomainRelation.objects.create(object_type='case', object_id=case_id, domain_id=domain_id
                                           ) for domain_id in domain_list]

    def update(self, data, pk):
        allow_modify_fields = ['name', 'test_suite_id', 'repeat', 'timeout',
                               'doc', 'description', 'var', 'is_default', 'alias', 'certificated']
        test_case = TestCase.objects.filter(id=pk)
        if test_case is None:
            return False, 'case 不存在.'
        # domain兼容多选
        domain_list = self.get_domain_list(data)
        update_data = dict()
        for field in allow_modify_fields:
            if data.get(field) is not None:
                update_data.update({field: data.get(field)})
        test_case.update(**update_data)
        # 更新domain关系
        self.create_domain_relation([pk], domain_list, is_delete=True)
        ci_type = data.get('ci_type')
        if ci_type:
            update_data = {'ci_type': ci_type}
            update_fields = ['host', 'user', 'token', 'pipeline_id', 'project_name', 'params']
            for field in update_fields:
                if data.get(field) is not None:
                    update_data.update({field: data.get(field)})
            AccessCaseConf.objects.filter(test_case_id=pk).update(**update_data)
        return True, test_case.first()

    @staticmethod
    def delete(pk):
        with transaction.atomic():
            TestCase.objects.filter(id=pk).delete()
            # 删除Domain关联
            DomainRelation.objects.filter(object_type='case', object_id=pk).delete()
            AccessCaseConf.objects.filter(test_case_id=pk).delete()
            # 删除WS关联的case
            WorkspaceCaseRelation.objects.filter(test_case_id=pk).delete()

    def update_batch(self, data, operator):
        # domain兼容多选
        domain_list = self.get_domain_list(data)
        case_list = data.get('case_id_list').split(',') or [data.get('case_id')]
        timeout = data.get('timeout')
        repeat = data.get('repeat')
        self.create_domain_relation(case_list, domain_list, is_delete=True)
        return TestCase.objects.filter(id__in=case_list).update(timeout=timeout, repeat=repeat)

    @staticmethod
    def remove_case(data, operator):
        id_list = data.get('id_list').split(',')
        TestCase.objects.filter(id__in=id_list).delete()
        # 删除Domain关联
        DomainRelation.objects.filter(object_type='case', object_id__in=id_list).delete()


class TestSuiteService(CommonService):
    def filter(self, queryset, data):
        test_framework = get_config_from_db('TEST_FRAMEWORK', 'tone')
        q = Q(test_framework=test_framework)
        order = ['gmt_created']
        if data.get('order'):
            order = data.get('order').split(',')
        if data.get('is_default') is not None:
            q &= Q(is_default=data.get('is_default'))
        q = self.base_filter(data, q)
        return queryset.filter(q).order_by(*order)

    @staticmethod
    def filter_test_type(data, q):
        if data.get('test_type'):
            # TODO 过滤业务测试中添加的功能和性能suite
            if data.get('test_type') in ('functional', 'performance'):
                business_suite = BusinessSuiteRelation.objects.all().values_list('test_suite_id', flat=True)
                q &= ~Q(id__in=business_suite)
            q &= Q(test_type=data.get('test_type'))
        return q

    def base_filter(self, data, q):
        if data.get('suite_id'):
            q &= Q(id=data.get('suite_id'))
        if data.get('test_type'):
            q &= self.filter_test_type(data, q)
        if data.get('certificated') is not None:
            q &= Q(certificated=data.get('certificated'))
        if data.get('run_mode'):
            run_mode_list = data.get('run_mode').split(',')
            q &= Q(run_mode__in=run_mode_list)
        if data.get('domain'):
            domain_list = data.get('domain').split(',')
            domain_suite_list = DomainRelation.objects.filter(object_type='suite', domain_id__in=domain_list
                                                              ).values_list('object_id', flat=True)
            q &= Q(id__in=domain_suite_list)
        if data.get('owner'):
            owner_list = data.get('owner').split(',')
            q &= Q(owner__in=owner_list)
        if data.get('name'):
            q &= Q(name__icontains=data.get('name'))
        if data.get('view_type'):
            view_type_list = data.get('view_type').split(',')
            q &= Q(view_type__in=view_type_list)
        if data.get('scope'):
            suite_id_list = TestCase.objects.all().values_list('test_suite_id', flat=True)
            q &= Q(id__in=suite_id_list)
        return q

    @staticmethod
    def filter_business(data):
        domain = data.get('domain')
        name = data.get('name')
        test_suite_list = []
        for tmp_business in TestBusiness.objects.all():
            suite_id_list = BusinessSuiteRelation.objects.filter(
                business_id=tmp_business.id).values_list('test_suite_id', flat=True)
            q = Q(id__in=suite_id_list)
            if domain:
                domain_suite = DomainRelation.objects.filter(
                    domain_id=domain, object_type='suite').values_list('object_id', flat=True)
                q &= Q(id__in=domain_suite)
            if name:
                q &= Q(name__icontains=name)
            tmp_suite_queryset = TestSuite.objects.filter(q)
            if not tmp_suite_queryset:
                continue
            for tmp_suite in tmp_suite_queryset:
                test_case_list = list()
                for tmp_case in TestCase.objects.filter(test_suite_id=tmp_suite.id):
                    tmp_case_data = {
                        'id': tmp_case.id,
                        'name': tmp_case.name,
                        'var': tmp_case.var,
                        'description': tmp_case.description,
                    }
                    test_case_list.append(tmp_case_data)
                tmp_suite_data = {
                    'id': tmp_suite.id,
                    'name': tmp_suite.name,
                    'test_type': tmp_suite.test_type,
                    'description': tmp_suite.description,
                    'test_case_list': test_case_list,
                    'business_name': tmp_business.name,
                }
                test_suite_list.append(tmp_suite_data)
        return test_suite_list

    @staticmethod
    def filter_ws_business(request, data):
        ws_id = data.get('ws_id')
        business_case_relation = WorkspaceCaseRelation.objects.filter(ws_id=ws_id, test_type='business')
        ws_business_suite = business_case_relation.values_list('test_suite_id', flat=True)
        ws_business_case = business_case_relation.values_list('test_case_id', flat=True)
        business_id_list = BusinessSuiteRelation.objects.filter(
            test_suite_id__in=ws_business_suite).values_list('business_id', flat=True)
        q = Q(id__in=business_id_list)
        if data.get('name'):
            q &= Q(name__icontains=data.get('name'))
        if data.get('owner'):
            q &= Q(creator=data.get('owner'))
        business_queryset = TestBusiness.objects.filter(q)
        if not data.get('scope'):
            request.ws_id = ws_id
            return business_queryset
        test_suite_list = []
        for tmp_business in business_queryset:
            suite_id_list = BusinessSuiteRelation.objects.filter(
                business_id=tmp_business.id).values_list('test_suite_id', flat=True)
            q = Q(id__in=set(suite_id_list) & set(ws_business_suite))
            tmp_suite_queryset = TestSuite.objects.filter(q)
            if not tmp_suite_queryset:
                continue
            for tmp_suite in tmp_suite_queryset:
                test_case_list = list()
                for tmp_case in TestCase.objects.filter(test_suite_id=tmp_suite.id, id__in=ws_business_case):
                    tmp_case_data = {
                        'id': tmp_case.id,
                        'name': tmp_case.name,
                    }
                    test_case_list.append(tmp_case_data)
                tmp_suite_data = {
                    'id': tmp_suite.id,
                    'name': tmp_suite.name,
                    'test_case_list': test_case_list,
                    'business_name': tmp_business.name,
                }
                test_suite_list.append(tmp_suite_data)
        return test_suite_list

    def create(self, data, operator):
        data.update({'suite_name': data.get('name', '')})
        code, msg = self.exist(data)
        if code != 200:
            return False, msg
        # domain兼容多选
        domain_list = list()
        domain_list_str = data.get('domain_list_str')
        if domain_list_str:
            domain_list = [int(domain) for domain in domain_list_str.split(',')]
        form_fields = ['name', 'test_type', 'run_mode', 'doc', 'description', 'owner', 'is_default',
                       'view_type', 'certificated']
        self.update_owner(data)
        create_data = dict()
        for field in form_fields:
            create_data.update({field: data.get(field)})
        if not create_data.get('view_type'):
            create_data['view_type'] = ''
        test_framework = get_config_from_db('TEST_FRAMEWORK', 'tone')
        suite = TestSuite.objects.filter(name=data.get('name'), test_framework=test_framework).first()
        if suite:
            return False, 'suite 已存在.'
        else:
            create_data.update({'test_framework': test_framework})
            if data.get('test_type') == 'business':
                create_data.update({
                    'is_default': False,
                    'certificated': False,
                    'owner': operator,
                })
            test_suite = TestSuite.objects.create(**create_data)
            # domain 关联
            [DomainRelation.objects.create(object_type='suite', object_id=test_suite.id, domain_id=domain_id
                                           ) for domain_id in domain_list]
            if data.get('business_id'):
                BusinessSuiteRelation.objects.create(business_id=data.get('business_id'), test_suite_id=test_suite.id)
            return True, test_suite

    def update(self, data, pk):
        # domain兼容多选
        domain_list = list()
        domain_list_str = data.get('domain_list_str')
        if domain_list_str:
            domain_list = [int(domain) for domain in domain_list_str.split(',')]
        allow_modify_fields = ['name', 'test_type', 'run_mode', 'doc', 'description', 'owner', 'is_default',
                               'view_type', 'certificated']
        test_suite = TestSuite.objects.filter(id=pk)
        if test_suite.first() is None:
            return False, 'suite not existed.'
        update_data = dict()
        self.update_owner(data)
        for field in allow_modify_fields:
            if data.get(field) is not None:
                update_data.update({field: data.get(field)})
        update_data.update({'gmt_modified': datetime.now()})
        if not update_data.get('view_type'):
            update_data['view_type'] = ''
        test_suite.update(**update_data)
        TestCase.objects.filter(test_suite_id=pk).update(is_default=data.get('is_default'))
        TestCase.objects.filter(test_suite_id=pk).update(certificated=data.get('certificated'))
        # 更新domain关系
        DomainRelation.objects.filter(object_type='suite', object_id=pk).delete()
        [DomainRelation.objects.create(object_type='suite', object_id=pk, domain_id=domain_id
                                       ) for domain_id in domain_list]
        return True, test_suite.first()

    @staticmethod
    def delete(pk, data, operator):
        with transaction.atomic():
            test_suite_queryset = TestSuite.objects.filter(id=pk)
            test_suite = test_suite_queryset.first()
            if test_suite is not None:
                # 获取当前角色, 测试管理员只能删除自己创建的
                current_role_id = RoleMember.objects.filter(user_id=operator).first().role_id
                current_role = Role.objects.filter(id=current_role_id).first().title
                allow_role = ['super_admin', 'sys_admin', 'sys_test_admin']
                if current_role in allow_role or test_suite.owner == operator:
                    test_suite_queryset.delete()
                    # 删除Domain关联
                    DomainRelation.objects.filter(object_type='suite', object_id=pk).delete()
                    WorkspaceCaseRelation.objects.filter(test_suite_id=pk).delete()
                    if data.get('business_id'):
                        BusinessSuiteRelation.objects.filter(business_id=data.get('business_id'),
                                                             test_suite_id=test_suite.id).delete()
                    return True, "Success"
                else:
                    return False, '测试管理员仅能删除自己创建'
            else:
                return False, "TestSuite doesn't existed"

    @staticmethod
    def update_owner(data):
        """兼容emp_id,从集团添加/修改 owner"""
        emp_id = data.get('emp_id')
        if emp_id is not None:
            # tone数据库存在 emp_id, 查询user_id, 否则先添加用户
            user = User.objects.filter(emp_id=emp_id.upper()).first()
            data.update({'owner': user.id})

    @staticmethod
    def check_exist_from_tone(data, test_framework):
        suite_id = data.get('suite_id')
        if data.get('test_type') != 'business':
            suite_obj = SuiteData.objects.filter(name=data.get('suite_name')).first()
            if suite_obj is None:
                return 201, '请检查该suite是否已集成（集成后需等待用例缓存进系统）'
            if suite_obj.test_type != data.get('test_type'):
                return 201, '该suite是{}类型'.format(suite_obj.test_type)
        test_suite = TestSuite.objects.filter(name=data.get('suite_name'), test_framework=test_framework).first()
        if test_suite:
            if suite_id is not None and str(suite_id) == str(test_suite.id):
                return 200, 'success'
            business_relation = BusinessSuiteRelation.objects.filter(test_suite_id=test_suite.id).first()
            if business_relation:
                test_business = TestBusiness.objects.filter(id=business_relation.business_id).first()
                if test_business:
                    return 201, f'该suite已存在于 {test_business.name} 业务'
            return 201, '该suite已经存在'
        return 200, 'success'

    def exist(self, data):
        test_framework = get_config_from_db('TEST_FRAMEWORK', 'tone')
        if test_framework == 'tone':
            return self.check_exist_from_tone(data, test_framework)
        else:
            test_suite = TestSuite.objects.filter(name=data.get('suite_name')).first()
            if test_suite:
                return 201, 'suite existed'
            result, code = TestSuiteService.get_cases(data.get('suite_name'))
            if code == 200:
                try:
                    assert result['JOBRESULT'].strip(), 'LKP_SYNC returns null args:%s' % test_suite.name
                    assert result['SUCCESS'], result['ERRORMSG']
                    for line in [r for r in result['JOBRESULT'].split('\n') if r.strip()]:
                        items = line.split(' ')
                        if len(items) < 1:
                            return 202, 'suite name查询失败'
                        if items[1] != data.get('test_type'):
                            return 202, '该suite为[%s]，无法添加到[%s]' % (items[1], data.get('test_type'))
                except Exception as err:
                    return 403, "检测失败:" + str(err)
                return code, ''
            return code, result

    def sync_case(self, suite_id):
        suite = TestSuite.objects.filter(id=suite_id)
        if not suite.exists():
            return 202, 'suite不存在'
        if suite.first().test_framework == 'aktf':
            return self._sync_case_from_aktf(suite_id)
        return self._sync_case_from_tone(suite_id)

    @staticmethod
    def _sync_case_from_tone(suite_id):
        suite = TestSuite.objects.get(id=suite_id)
        case_obj_list = []
        # 从SuiteData中查询 suite_name, 获取suite下的case name list
        suite_data = SuiteData.objects.filter(name=suite.name, test_type=suite.test_type).first()
        if suite_data is None:
            return 201, '该suite不存在'
        suite.doc = suite_data.description
        suite.save()
        case_name_list = CaseData.objects.filter(suite_id=suite_data.id).values_list('name', flat=True)
        for case_name in case_name_list:
            short_name = '-'.join([item.split('=')[-1] for item in case_name.split(',')])
            cases = TestCase.objects.filter(test_suite_id=suite_id, name=case_name)
            if cases.exists():
                cases.update(doc=suite_data.description, short_name=short_name)
                continue
            case_obj_list.append(TestCase(
                name=case_name,
                test_suite_id=suite.id,
                repeat=1 if suite.test_type == 'functional' else 3,
                timeout=3600,
                doc=suite_data.description,
                description='',
                is_default=suite.is_default,
                short_name=short_name
            ))
        with transaction.atomic():
            TestCase.objects.bulk_create(case_obj_list)
            TestCase.objects.filter(test_suite_id=suite.id).exclude(name__in=case_name_list).delete()
        return 200, 'sync case success'

    def _sync_case_from_aktf(self, pk):
        test_suite = TestSuite.objects.filter(id=pk).first()
        if not test_suite:
            return 201, 'suite not exist'
        result, success = TestSuiteService.get_cases(test_suite.name)
        if success == 200:
            try:
                assert result['JOBRESULT'].strip(), 'LKP_SYNC returns null args:%s' % test_suite.name
                assert result['SUCCESS'], result['ERRORMSG']
                for line in [r for r in result['JOBRESULT'].split('\n') if r.strip()]:
                    TestSuiteService._case_add(test_suite, line)
            except Exception as err:
                return 202, "同步失败:" + str(err)
        return success, ''

    @staticmethod
    def get_cases(suite_name, test_framework='LKP_SYNC'):
        return None, False

    @staticmethod
    def _case_add(test_suite, case_info):
        items = case_info.split(' ')
        try:
            name = os.path.splitext(items[0][2:])[0]
        except Exception:
            name = items[0][2:]
        if not name.strip():
            return
        cases = TestCase.objects.filter(Q(test_suite_id=test_suite.id), Q(name=name) | Q(name=items[0][2:]))
        if cases.exists():
            for case in cases:
                case.name = name
                case.save()
        else:
            repeat = 1
            if items[1] == 'performance':
                repeat = 3
            case = TestCase(
                name=name,
                test_suite_id=test_suite.id,
                repeat=repeat,
                timeout=3600,
                doc='',
                description='',
                is_default=test_suite.is_default
            )
            case.save()

    @staticmethod
    def sys_case_confirm(request, data):
        suite_id = data.get('suite_id', 0)
        suite_id_list_str = data.get('suite_id_list', '')
        case_id_list_str = data.get('case_id_list', '')
        flag = data.get('flag', 'job')
        case_id_list = []
        suite_id_list = []
        if suite_id_list_str:
            suite_id_list = suite_id_list_str.split(',')
        if suite_id or suite_id_list:
            suite_id_list.append(suite_id)
            case_id_list = TestCase.objects.filter(test_suite_id__in=suite_id_list).values_list('id', flat=True)
        if case_id_list_str:
            case_id_list = case_id_list_str.split(',')
        if flag == 'job':
            job_id_list = TestJobCase.objects.filter(
                test_case_id__in=case_id_list, state__in=['running', 'pending']).values_list('job_id', flat=True)
            res_queryset = TestJob.objects.filter(id__in=job_id_list, state__in=['running', 'pending'])
        elif flag == 'pass':
            job_id_list = TestJobCase.objects.filter(
                test_case_id__in=case_id_list, state__in=['running', 'pending']).values_list('job_id', flat=True)
            if TestJob.objects.filter(id__in=job_id_list).exists():
                return 200, flag
            tmpl_id_list = TestTmplCase.objects.filter(
                test_case_id__in=case_id_list).values_list('tmpl_id', flat=True)
            if TestTemplate.objects.filter(id__in=tmpl_id_list).exists():
                return 200, flag
            return 201, flag
        else:
            tmpl_id_list = TestTmplCase.objects.filter(
                test_case_id__in=case_id_list).values_list('tmpl_id', flat=True)
            res_queryset = TestTemplate.objects.filter(id__in=tmpl_id_list)
        return res_queryset, flag

    @staticmethod
    def ws_case_confirm(request, data):
        ws_id = data.get('ws_id')
        case_list = []
        test_type = data.get('test_type')
        flag = data.get('flag', 'job')
        origin_case_list = WorkspaceCaseRelation.objects.filter(
            ws_id=ws_id, test_type=test_type).values_list('test_case_id', flat=True)
        if data.get('case_id_list') or data.get('case_id'):
            case_list = data.get('case_id_list').split(',') or [data.get('case_id')]
        if data.get('suite_id_list'):
            suite_list = data.get('suite_id_list').split(',')
            case_list = TestCase.objects.filter(test_suite_id__in=suite_list).values_list('id', flat=True)
        case_list = [int(case) for case in case_list if case.isdigit()]
        delete_case_list = list(set(origin_case_list) - set(case_list))
        if delete_case_list:
            if flag == 'job':
                job_id_list = TestJobCase.objects.filter(
                    state__in=['running', 'pending'],
                    test_case_id__in=delete_case_list).values_list('job_id', flat=True)
                res_queryset = TestJob.objects.filter(ws_id=ws_id, id__in=job_id_list, state__in=['running', 'pending'])
            elif flag == 'pass':
                job_id_list = TestJobCase.objects.filter(
                    state__in=['running', 'pending'],
                    test_case_id__in=delete_case_list).values_list('job_id', flat=True)
                if TestJob.objects.filter(ws_id=ws_id, id__in=job_id_list).exists():
                    return 200, flag
                tmpl_id_list = TestTmplCase.objects.filter(
                    test_case_id__in=delete_case_list).values_list('tmpl_id', flat=True)
                if TestTemplate.objects.filter(ws_id=ws_id, id__in=tmpl_id_list).exists():
                    return 200, flag
                return 201, flag
            else:
                tmpl_id_list = TestTmplCase.objects.filter(
                    test_case_id__in=delete_case_list).values_list('tmpl_id', flat=True)
                res_queryset = TestTemplate.objects.filter(ws_id=ws_id, id__in=tmpl_id_list)
            request.case_id_list = delete_case_list
            return res_queryset, flag
        else:
            return '非删除操作', 'pass'

    @staticmethod
    def update_batch(data):
        pass

    @staticmethod
    def remove_suite(data):
        suite_id_list = data.get('id_list').split(',')
        with transaction.atomic():
            TestSuite.objects.filter(id__in=suite_id_list).delete()
            DomainRelation.objects.filter(object_type='suite', object_id__in=suite_id_list).delete()
            WorkspaceCaseRelation.objects.filter(test_suite_id__in=suite_id_list).delete()
            BusinessSuiteRelation.objects.filter(test_suite_id__in=suite_id_list).delete()
            case_queryset = TestCase.objects.filter(test_suite_id__in=suite_id_list)
            case_id_list = case_queryset.values_list('id', flat=True)
            DomainRelation.objects.filter(object_type='case', object_id__in=case_id_list).delete()
            case_queryset.delete()


class TestMetricService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('suite_id'):
            q &= Q(object_type='suite')
            q &= Q(object_id=data.get('suite_id'))
        if data.get('case_id'):
            case_id = data.get('case_id')
            q &= Q(object_type='case') & Q(object_id=case_id)
        if data.get('run_mode'):
            q &= Q(run_mode=data.get('run_mode'))
        if data.get('owner'):
            q &= Q(owner=data.get('owner'))
        return queryset.filter(q)

    def create(self, data):
        metric_list = []
        for metric_name in data.get('name'):
            test_metric = TestMetric.objects.filter(object_type=data.get('object_type'),
                                                    object_id=data.get('object_id'), name=metric_name).first()
            if test_metric:
                return False, 'metric %s 已存在' % metric_name
            if data.get('object_type') == 'suite' and data.get('is_sync'):
                test_case = TestCase.objects.filter(test_suite_id=data.get('object_id'))
                for case in test_case:
                    TestMetric.objects.filter(object_type='case', object_id=case.id, name=metric_name).delete()
                    metric_list.append(
                        TestMetric(
                            name=metric_name,
                            object_type='case',
                            object_id=case.id,
                            cv_threshold=data.get('cv_threshold') / 100,
                            cmp_threshold=data.get('cmp_threshold') / 100,
                            direction=data.get('direction')
                        )
                    )
            metric_list.append(
                TestMetric(
                    name=metric_name,
                    object_type=data.get('object_type'),
                    object_id=data.get('object_id'),
                    cv_threshold=data.get('cv_threshold') / 100,
                    cmp_threshold=data.get('cmp_threshold') / 100,
                    direction=data.get('direction')
                )
            )
        TestMetric.objects.bulk_create(metric_list)
        return True, None

    @staticmethod
    def update(data, pk):
        allow_modify_fields = ['name', 'cv_threshold', 'cmp_threshold', 'direction']
        test_metric = TestMetric.objects.filter(id=pk)
        if test_metric.first() is None:
            return False, 'metric not existed.'
        update_data = dict()
        for field in allow_modify_fields:
            if data.get(field):
                if field in {'cv_threshold', 'cmp_threshold'}:
                    update_data.update({field: data.get(field) / 100})
                else:
                    update_data.update({field: data.get(field)})
        test_metric.update(**update_data)
        if data.get('object_type') == 'suite' and data.get('is_sync'):
            test_case = TestCase.objects.filter(test_suite_id=data.get('object_id'))
            for case in test_case:
                test_conf_metric = TestMetric.objects.filter(name=data.get('name'), object_type='case',
                                                             object_id=case.id)
                if test_metric.first():
                    test_conf_metric.update(**update_data)
        return True, test_metric.first()

    @staticmethod
    def delete(data, pk):
        TestMetric.objects.filter(id=pk).delete()
        if data.get('object_type') == 'suite' and data.get('is_sync'):
            test_case = TestCase.objects.filter(test_suite_id=data.get('object_id'))
            for case in test_case:
                TestMetric.objects.filter(name=data.get('name'), object_type='case', object_id=case.id).delete()

    @staticmethod
    def get_metric_list(data):
        q = Q()
        suite_id = data.get('suite_id')
        case_id = data.get('case_id')
        if suite_id is not None:
            q &= Q(test_suite_id=suite_id)
        if case_id is not None:
            q &= Q(test_case_id=case_id)
        metrics = PerfResult.objects.filter(q).values_list('metric', flat=True).distinct().order_by('metric')
        metric_list = list()
        for metric_name in metrics:
            metric_info = dict()
            metric_info['name'] = metric_name
            last_metric = PerfResult.objects.filter(metric=metric_name).last()
            metric_info['unit'] = last_metric.unit if last_metric else ''
            metric_list.append(metric_info)
        return metric_list


class WorkspaceCaseService(CommonService):
    @staticmethod
    def _get_search_q(data):
        test_framework = get_config_from_db('TEST_FRAMEWORK', 'tone')
        q = Q(test_framework=test_framework)
        if data.get('suite_id'):
            q &= Q(id=data.get('suite_id'))
        if data.get('test_type'):
            business_suite = WorkspaceCaseRelation.objects.filter(
                test_type='business', ws_id=data.get('ws_id')).values_list('test_suite_id', flat=True)
            if data.get('test_type') == 'business':
                if data.get('business_type'):
                    business_type_suite = TestSuite.objects.filter(
                        test_type=data.get('business_type')).values_list('id', flat=True)
                    q &= Q(id__in=business_type_suite)
                q &= Q(id__in=business_suite)
            else:
                q &= ~Q(id__in=business_suite)
                q &= Q(test_type=data.get('test_type'))
        if data.get('run_mode'):
            run_mode_list = data.get('run_mode').split(',')
            q &= Q(run_mode__in=run_mode_list)
        if data.get('domain'):
            domain_list = data.get('domain').split(',')
            suite_list = DomainRelation.objects.filter(
                domain_id__in=domain_list, object_type='suite').values_list('object_id')
            q &= Q(id__in=suite_list)
        if data.get('owner'):
            owner_list = data.get('owner').split(',')
            q &= Q(owner__in=owner_list)
        if data.get('name'):
            q &= Q(name__icontains=data.get('name'))
        return q

    @staticmethod
    def filter(queryset, data):
        if data.get('object_type') and data.get('object_id'):
            return TestMetric.objects.filter(object_type=data.get('object_type'), object_id=data.get('object_id'))
        if data.get('suite_id'):
            case_id_list = queryset.filter(ws_id=data.get('ws_id'),
                                           test_suite_id=data.get('suite_id')).values_list('test_case_id', flat=True)
            return TestCase.objects.filter(id__in=case_id_list)
        if data.get('ws_id'):
            order = 'gmt_created'
            q = WorkspaceCaseService._get_search_q(data)
            if data.get('order'):
                order = data.get('order')
            suite_id_list = queryset.filter(ws_id=data.get('ws_id')).values_list('test_suite_id', flat=True).distinct()
            q &= Q(id__in=suite_id_list)
            return TestSuite.objects.filter(q).order_by(order)

    @staticmethod
    def has_suite(queryset, data):
        return WorkspaceCaseRelation.objects.filter(ws_id=data.get('ws_id'), **{'query_scope': 'all'}).count()

    def create(self, data):
        form_fields = ['test_type', 'test_suite_id', 'test_case_id', 'ws_id']
        create_data = dict()
        for field in form_fields:
            create_data.update({field: data.get(field)})
        test_metric = WorkspaceCaseRelation.objects.create(**create_data)
        return test_metric

    @staticmethod
    def update(data, pk):
        allow_modify_fields = ['test_type', 'test_suite_id', 'test_case_id', 'ws_id']
        workspace_case = WorkspaceCaseRelation.objects.filter(id=pk)
        if workspace_case.first() is None:
            pass
        update_data = dict()
        for field in allow_modify_fields:
            if data.get(field):
                update_data.update({field: data.get(field)})
        workspace_case.update(**update_data)
        return workspace_case.first()

    def delete(self, data, pk):
        WorkspaceCaseRelation.objects.filter(id=pk).delete()

    @staticmethod
    def add_case(data, operator):
        ws_id = data.get('ws_id')
        workspace_case_list = []
        case_list = []
        test_type = data.get('test_type')
        if data.get('case_id_list') or data.get('case_id'):
            case_list = data.get('case_id_list').split(',') or [data.get('case_id')]
        if data.get('suite_id_list'):
            suite_list = data.get('suite_id_list').split(',')
            case_list = TestCase.objects.filter(test_suite_id__in=suite_list).values_list('id', flat=True)
        for case_id in case_list:
            case = TestCase.objects.filter(id=case_id).first()
            workspace_case_list.append(
                WorkspaceCaseRelation(
                    test_type=test_type,
                    test_suite_id=case.test_suite_id,
                    test_case_id=case_id,
                    ws_id=ws_id
                )
            )
        with transaction.atomic():
            WorkspaceCaseRelation.objects.filter(ws_id=ws_id, test_type=test_type).delete()
            bulk_create_obj = WorkspaceCaseRelation.objects.bulk_create(workspace_case_list)
        return bulk_create_obj

    @staticmethod
    def remove_case(data, operator):
        id_list = data.get('id_list').split(',') or [data.get('id')]
        ws_id = data.get('ws_id')
        WorkspaceCaseRelation.objects.filter(ws_id=ws_id, id__in=id_list).delete()


class TestDomainService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        order_by = list()
        if data.get('id'):
            q &= Q(id=data.get('id'))
        if data.get('name'):
            q &= Q(name__icontains=data.get('name'))
        if data.get('creator'):
            q &= Q(creator__in=data.getlist('creator'))
        if data.get('update_user'):
            q &= Q(update_user__in=data.getlist('update_user'))
        if "gmt_created" in data.get('gmt_created', []):
            order_by.append('{}gmt_created'.format('-' if '-' in data.get('gmt_created') else ''))
        if 'gmt_modified' in data.get('gmt_modified', []):
            order_by.append('{}gmt_modified'.format('-' if '-' in data.get('gmt_modified') else ''))
        return order_by, queryset.filter(q)

    @staticmethod
    def create(data, operator):
        creator = operator.id
        test_domain = TestDomain.objects.filter(name=data.get('name'))
        if test_domain.first() is not None:
            return False, 'domain name already exists'
        form_fields = ['name', 'description']
        create_data = dict()
        for field in form_fields:
            create_data.update({field: data.get(field)})
        create_data.update({'creator': creator})
        test_domain = TestDomain.objects.create(**create_data)
        return True, test_domain

    @staticmethod
    def update(data, operator):
        update_user = operator.id
        domain_id = data.get('id')
        test_domain = TestDomain.objects.filter(name=data.get('name')).first()
        if test_domain is not None and str(test_domain.id) != str(domain_id):
            return False, 'domain name already exists'
        test_domain = TestDomain.objects.filter(id=domain_id)
        if test_domain.first() is None:
            return False, 'domain id not exists'
        allow_modify_fields = ['name', 'description']
        update_data = dict()
        for field in allow_modify_fields:
            if data.get(field):
                update_data.update({field: data.get(field)})
        update_data.update({'update_user': update_user, 'gmt_modified': datetime.now()})
        test_domain.update(**update_data)
        return True, test_domain.first()

    @staticmethod
    def delete(data):
        msg = "请先将该domain下的 suite/case 全部解绑，再尝试删除"
        # domain下关联case未解绑，不能删除domain
        if DomainRelation.objects.filter(domain_id__in=data.get('id_list')).exists():
            return False, msg
        TestDomain.objects.filter(id__in=data.get('id_list')).delete()
        return True, '删除成功'


class SyncCaseToCacheService(CommonService):
    def sync_case_to_cache(self, scope='suite'):
        success, test_suites_data = self._get_suites_data()
        if not success:
            return False, test_suites_data
        if scope == 'all':
            for test_suite in test_suites_data.keys():
                success, test_cases_data = self._get_cases_data(test_suite)
                if success:
                    test_suites_data[test_suite]['test_cases'] = test_cases_data
        self._sync_result_to_redis(test_suites_data)
        return True, test_suites_data

    def _get_suites_data(self):
        agent_exec_result, success = TestSuiteService.get_cases('', test_framework='TONE_SYNC')
        if not success == 200:
            return False, agent_exec_result
        result_data = agent_exec_result['JOBRESULT']
        suite_data = dict()
        for item in result_data.split('\n'):
            test_suite_data = item.split(' ', 1)
            if len(test_suite_data) < 2:
                continue
            test_suite_name = test_suite_data[0]
            if not test_suite_name:
                continue
            test_type = 'functional' if 'functional' in test_suite_data[1] else 'performance'
            suite_data.update({
                test_suite_name: {'test_type': test_type, 'test_cases': list()}
            })
        return True, suite_data

    @staticmethod
    def _get_cases_data(suite_name):
        agent_exec_result, success = TestSuiteService.get_cases(suite_name, test_framework='TONE_SYNC')
        if success == 200:
            result_data = agent_exec_result['JOBRESULT']
        else:
            return False, agent_exec_result
        test_cases_list = list()
        for index, line in enumerate([r for r in result_data.split('\n') if r.strip()]):
            if index == 0:
                continue
            case_name = line.split(' ')[-1].split(':')[-1]
            test_cases_list.append(case_name)
        return True, test_cases_list

    @staticmethod
    def _sync_result_to_redis(test_suites_data):
        ret = redis_cache.set_info(TEST_SUITE_REDIS_KEY, json.dumps(test_suites_data))
        return ret


class WorkspaceRetrieveService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        test_framework = get_config_from_db('TEST_FRAMEWORK', 'tone')
        suite_id_list = TestSuite.objects.filter(test_framework=test_framework).values_list('id', flat=True)
        queryset = queryset.filter(test_suite_id__in=suite_id_list)
        # 获取性能测试、功能测试总数
        if data.get('total_num'):
            func_suite_id_list = TestSuite.objects.filter(test_framework=test_framework, test_type='functional'
                                                          ).values_list('id', flat=True)
            perm_suite_id_list = TestSuite.objects.filter(test_framework=test_framework, test_type='performance'
                                                          ).values_list('id', flat=True)
            res = {
                'functional_num': TestCase.objects.filter(test_suite_id__in=func_suite_id_list).count(),
                'performance_num': TestCase.objects.filter(test_suite_id__in=perm_suite_id_list).count(),
            }
            return False, res
        # conf展开
        if data.get('suite_id'):
            if data.get('ws_id'):
                ws_case_id = queryset.filter(test_type=data.get('test_type'), test_suite_id=data.get('suite_id'),
                                             ws_id=data.get('ws_id')).values_list('test_case_id', flat=True)

                case_data_list = [
                    {'id': case.id, 'name': case.name, 'certificated': case.certificated,
                     'add_state': 1 if case.id in ws_case_id else 0}
                    for case in TestCase.objects.filter(test_suite_id=data.get('suite_id'))]
                return False, case_data_list

            test_case_queryset = TestCase.objects.filter(test_suite_id=data.get('suite_id'))
            if data.get('case_id'):
                test_case_queryset = test_case_queryset.exclude(id=data.get('case_id'))
            return True, test_case_queryset
        # 性能、功能测试suite信息
        if data.get('test_type'):
            q &= Q(test_type=data.get('test_type'))
        ws_suite_id = queryset.filter(test_type=data.get('test_type'),
                                      ws_id=data.get('ws_id')).values_list('test_suite_id', flat=True)
        # suite_id_list = queryset.filter(q).values_list('test_suite_id', flat=True).distinct()
        test_type_suite = TestSuite.objects.filter(id__in=suite_id_list, test_type=data.get('test_type'))
        suite_data_list = [{'id': suite.id, 'name': suite.name, 'certificated': suite.certificated,
                            'add_state': 1 if suite.id in ws_suite_id else 0,
                            'case_count': TestCase.objects.filter(test_suite_id=suite.id).count()}
                           for suite in test_type_suite]
        return False, suite_data_list

    @staticmethod
    def search(data, retrieve_view):
        search_key = data.get('search_key')
        search_type = data.get('search_type')  # all, suite, docker, domain
        result = list()
        test_suite_queryset = None
        test_case_queryset = None
        case_domain_queryset = None
        suite_case_id_list = None
        test_case_id_list = None
        domain_case_id_list = None
        test_framework = get_config_from_db('TEST_FRAMEWORK', 'tone')
        # 存在关键字
        if search_key is None:
            return False, 'search_key not find'
        # 根据查询类型， 返回不同搜索结果
        # suite 信息中包含搜索关键字
        if search_type in {'all', 'suite'}:
            suite_id_list = TestSuite.objects.filter(name__icontains=search_key, test_framework=test_framework
                                                     ).values_list('id', flat=True)
            test_suite_queryset = TestCase.objects.filter(test_suite_id__in=suite_id_list)
            suite_case_id_list = test_suite_queryset.values_list('id', flat=True)

        suite_id_list = TestSuite.objects.filter(test_framework=test_framework).values_list('id', flat=True)
        # conf  信息中包含搜索关键字 1.suite_name包含关键字 2.conf信息中包含关键字
        if search_type in {'all', 'conf'}:
            test_case_queryset = TestCase.objects.filter(name__icontains=search_key, test_suite_id__in=suite_id_list)
            test_case_id_list = test_case_queryset.values_list('id', flat=True)

        # domain 中包含搜索关键字的 suite和conf
        if search_type in {'all', 'domain'}:
            domain_queryset = TestDomain.objects.filter(name__icontains=search_key)
            domain_id_list = domain_queryset.values_list('id', flat=True)
            case_id_list = DomainRelation.objects.filter(
                object_type='case', domain_id__in=domain_id_list).values_list('object_id', flat=True)
            case_domain_queryset = TestCase.objects.filter(id__in=case_id_list, test_suite_id__in=suite_id_list)
            domain_case_id_list = case_domain_queryset.values_list('id', flat=True)
        retrieve_view.serializer_class = RetrieveCaseSerializer
        if search_type == 'suite':
            result = test_suite_queryset
        elif search_type == 'conf':
            result = test_case_queryset
        elif search_type == 'domain':
            result = case_domain_queryset
        elif search_type == 'all':
            result = TestCase.objects.filter(id__in=(suite_case_id_list | test_case_id_list | domain_case_id_list))
        return True, result

    @staticmethod
    def get_quantity(data):
        """获取检索页搜索结果数量"""
        search_key = data.get('search_key')
        test_framework = get_config_from_db('TEST_FRAMEWORK', 'tone')
        # suite count
        suite_id_list = TestSuite.objects.filter(name__icontains=search_key, test_framework=test_framework
                                                 ).values_list('id', flat=True)
        test_suite_queryset = TestCase.objects.filter(test_suite_id__in=suite_id_list)
        suite_case_id_list = test_suite_queryset.values_list('id', flat=True)
        # conf count
        suite_id_list = TestSuite.objects.filter(test_framework=test_framework).values_list('id', flat=True)
        test_case_queryset = TestCase.objects.filter(name__icontains=search_key, test_suite_id__in=suite_id_list)
        test_case_id_list = test_case_queryset.values_list('id', flat=True)
        # domain 中包含搜索关键字的 suite和conf
        domain_queryset = TestDomain.objects.filter(name__icontains=search_key)
        domain_id_list = domain_queryset.values_list('id', flat=True)
        case_id_list = DomainRelation.objects.filter(
            object_type='case', domain_id__in=domain_id_list).values_list('object_id', flat=True)
        case_domain_queryset = TestCase.objects.filter(id__in=case_id_list, test_suite_id__in=suite_id_list)
        domain_case_id_list = case_domain_queryset.values_list('id', flat=True)
        suite_num = len(test_suite_queryset)
        conf_num = len(test_case_queryset)
        domain_num = len(case_domain_queryset)
        return {
            'total_num': len(suite_case_id_list | test_case_id_list | domain_case_id_list),
            'suite_num': suite_num,
            'conf_num': conf_num,
            'domain_num': domain_num,
        }


class ManualSyncService(CommonService):
    @staticmethod
    def manual_sync(data):
        base_config_obj = BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_STATE').first()
        if base_config_obj is None:
            base_config_obj = BaseConfig.objects.create(config_type='sys', config_key='SUITE_SYNC_STATE',
                                                        config_value='running')
        if base_config_obj.config_value == 'waiting':
            sync_suite_case_toneagent.delay()
            BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_STATE').update(config_value='running')
            return True, '同步命令开始执行成功'
        return False, '同步任务执行中，稍后再试'

    @staticmethod
    def get_last_datetime():
        config_obj = BaseConfig.objects.filter(config_type='sys', config_key='SUITE_SYNC_LAST_TIME').first()
        if config_obj is None:
            config_obj = BaseConfig.objects.create(config_type='sys', config_key='SUITE_SYNC_LAST_TIME')
        last_sync_time = str(config_obj.config_value)
        if '.' in last_sync_time:
            last_sync_time = last_sync_time[0: last_sync_time.rfind('.')]
        return last_sync_time


class TestBusinessService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        if data.get('id'):
            q &= Q(id=data.get('id'))
        if data.get('creator'):
            q &= Q(creator=data.get('creator'))
        if data.get('name'):
            q &= Q(name__icontains=data.get('name'))
        return queryset.filter(q)

    @staticmethod
    def create(data, operator):
        test_business = TestBusiness.objects.filter(name=data.get('name')).first()
        if test_business:
            return False, 'business existed'
        create_data = {'name': data.get('name'),
                       'description': data.get('description'),
                       'creator': operator}
        test_business = TestBusiness.objects.create(**create_data)
        return True, test_business

    @staticmethod
    def update(data, pk, operator):
        test_business_queryset = TestBusiness.objects.filter(id=pk)
        test_business = test_business_queryset.first()
        if test_business is None:
            return False, 'business not existed.'
        exist_business = TestBusiness.objects.filter(name=data.get('name')).first()
        if exist_business is not None and exist_business.id != test_business.id:
            return False, 'name existed.'
        test_business_queryset.update(name=data.get('name'), description=data.get('description'), update_user=operator)
        return True, test_business_queryset.first()

    @staticmethod
    def delete(pk):
        with transaction.atomic():
            TestBusiness.objects.filter(id=pk).delete()
            BusinessSuiteRelation.objects.filter(business_id=pk).delete()

    @staticmethod
    def filter_suite(pk):
        suite_list = BusinessSuiteRelation.objects.filter(business_id=pk).values_list('test_suite_id', flat=True)
        return TestSuite.objects.filter(id__in=suite_list)
