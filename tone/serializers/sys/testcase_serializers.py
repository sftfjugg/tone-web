from django.db.models import Q
from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models import TestCase, WorkspaceCaseRelation, TestSuite, TestMetric, Workspace, User, TestDomain, \
    DomainRelation, TestJobCase, TestJob, PerfResult, TestTemplate, TestTmplCase, TestBusiness, AccessCaseConf, \
    BusinessSuiteRelation


class TestCaseSerializer(CommonSerializer):
    suite_name = serializers.SerializerMethodField()
    domain_name_list = serializers.SerializerMethodField()
    domain_id_list = serializers.SerializerMethodField()
    ci_type = serializers.SerializerMethodField()
    host = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    token = serializers.SerializerMethodField()
    pipeline_id = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    params = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        exclude = ['is_deleted']

    @staticmethod
    def get_ci_type(obj):
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite and test_suite.test_type == 'business':
            access_case = AccessCaseConf.objects.filter(test_case_id=obj.id).first()
            if access_case:
                return access_case.ci_type

    @staticmethod
    def get_host(obj):
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite and test_suite.test_type == 'business':
            access_case = AccessCaseConf.objects.filter(test_case_id=obj.id).first()
            if access_case:
                return access_case.host

    @staticmethod
    def get_user(obj):
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite and test_suite.test_type == 'business':
            access_case = AccessCaseConf.objects.filter(test_case_id=obj.id).first()
            if access_case:
                return access_case.user

    @staticmethod
    def get_token(obj):
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite and test_suite.test_type == 'business':
            access_case = AccessCaseConf.objects.filter(test_case_id=obj.id).first()
            if access_case:
                return access_case.token

    @staticmethod
    def get_pipeline_id(obj):
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite and test_suite.test_type == 'business':
            access_case = AccessCaseConf.objects.filter(test_case_id=obj.id).first()
            if access_case:
                return access_case.pipeline_id

    @staticmethod
    def get_project_name(obj):
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite and test_suite.test_type == 'business':
            access_case = AccessCaseConf.objects.filter(test_case_id=obj.id).first()
            if access_case:
                return access_case.project_name

    @staticmethod
    def get_params(obj):
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite and test_suite.test_type == 'business':
            access_case = AccessCaseConf.objects.filter(test_case_id=obj.id).first()
            if access_case:
                return access_case.params

    @staticmethod
    def get_suite_name(obj):
        suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if suite is None:
            return None
        return suite.name

    @staticmethod
    def get_domain_name(obj):
        domain = TestDomain.objects.filter(id=obj.domain).first()
        if domain is None:
            return None
        return domain.name

    @staticmethod
    def get_domain_id_list(obj):
        domain_id_list = DomainRelation.objects.filter(object_type='case', object_id=obj.id).values_list(
            'domain_id', flat=True)
        return ','.join([str(domain_id) for domain_id in domain_id_list])

    @staticmethod
    def get_domain_name_list(obj):
        domain_id_list = DomainRelation.objects.filter(object_type='case', object_id=obj.id).values_list(
            'domain_id', flat=True)
        domain_name_list = [TestDomain.objects.filter(id=domain_id).first().name for domain_id in domain_id_list]
        return ','.join(domain_name_list)


class TestSuiteSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    domain_name_list = serializers.SerializerMethodField()
    emp_id = serializers.SerializerMethodField()
    domain_id_list = serializers.SerializerMethodField()
    view_type = serializers.CharField(source='get_view_type_display')

    class Meta:
        model = TestSuite
        exclude = ['is_deleted']

    @staticmethod
    def get_owner_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.last_name or owner.first_name

    @staticmethod
    def get_emp_id(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.emp_id

    @staticmethod
    def get_domain_id_list(obj):
        domain_id_list = DomainRelation.objects.filter(object_type='suite', object_id=obj.id).values_list(
            'domain_id', flat=True)
        return ','.join([str(domain_id) for domain_id in domain_id_list])

    @staticmethod
    def get_domain_name(obj):
        domain = TestDomain.objects.filter(id=obj.domain).first()
        if domain is None:
            return None
        return domain.name

    @staticmethod
    def get_domain_name_list(obj):
        domain_id_list = DomainRelation.objects.filter(object_type='suite', object_id=obj.id).values_list(
            'domain_id', flat=True)
        domain_name_list = [TestDomain.objects.filter(id=domain_id, query_scope='all').first().name
                            for domain_id in domain_id_list]
        return ','.join(domain_name_list)


class TestSuiteCaseSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    test_case_list = serializers.SerializerMethodField()
    domain_name_list = serializers.SerializerMethodField()

    class Meta:
        model = TestSuite
        exclude = ['is_deleted']

    @staticmethod
    def get_owner_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.last_name or owner.first_name

    @staticmethod
    def get_test_case_list(obj):
        return TestCaseSerializer(TestCase.objects.filter(test_suite_id=obj.id), many=True).data

    @staticmethod
    def get_domain_name(obj):
        domain = TestDomain.objects.filter(id=obj.domain).first()
        if domain is None:
            return None
        return domain.name

    @staticmethod
    def get_domain_name_list(obj):
        domain_id_list = DomainRelation.objects.filter(object_type='suite', object_id=obj.id).values_list(
            'domain_id', flat=True)
        domain_name_list = [TestDomain.objects.filter(id=domain_id).first().name for domain_id in domain_id_list]
        return ','.join(domain_name_list)


class BriefCaseSerializer(CommonSerializer):

    class Meta:
        model = TestCase
        fields = ['id', 'name', 'doc', 'var', 'test_suite_id']


class BriefSuiteSerializer(CommonSerializer):
    test_case_list = serializers.SerializerMethodField()

    class Meta:
        model = TestSuite
        fields = ['id', 'name', 'doc', 'test_case_list']

    def get_test_case_list(self, obj):
        ws_id = self.context['request'].query_params.get('ws_id')
        if ws_id:
            case_id_list = WorkspaceCaseRelation.objects.filter(ws_id=ws_id,
                                                                test_suite_id=obj.id
                                                                ).values_list('test_case_id', flat=True)
            test_cases = TestCase.objects.filter(id__in=case_id_list)
        else:
            test_cases = TestCase.objects.filter(test_suite_id=obj.id)
        return BriefCaseSerializer(test_cases, many=True).data


class SimpleCaseSerializer(CommonSerializer):
    domain_name_list = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        exclude = ['is_deleted', 'test_suite_id', 'description', 'is_default']

    @staticmethod
    def get_domain_name_list(obj):
        domain_id_list = DomainRelation.objects.filter(object_type='case', object_id=obj.id).values_list(
            'domain_id', flat=True)
        domain_name_list = [TestDomain.objects.filter(id=domain_id).first().name for domain_id in domain_id_list]
        return ','.join(domain_name_list)


class SimpleSuiteSerializer(CommonSerializer):
    domain_name_list = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = TestSuite
        exclude = ['is_deleted', 'test_type', 'owner', 'is_default', 'test_framework']

    @staticmethod
    def get_owner_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.last_name or owner.first_name

    @staticmethod
    def get_domain_name_list(obj):
        domain_id_list = DomainRelation.objects.filter(object_type='suite', object_id=obj.id).values_list(
            'domain_id', flat=True)
        domain_name_list = [TestDomain.objects.filter(id=domain_id).first().name for domain_id in domain_id_list]
        return ','.join(domain_name_list)


class TestSuiteWsCaseSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    business_name = serializers.SerializerMethodField()
    test_case_list = serializers.SerializerMethodField()
    domain_name_list = serializers.SerializerMethodField()

    @staticmethod
    def get_business_name(obj):
        if WorkspaceCaseRelation.objects.filter(test_type='business', test_suite_id=obj.id).exists():
            business_relation = BusinessSuiteRelation.objects.filter(test_suite_id=obj.id).first()
            if business_relation:
                test_business = TestBusiness.objects.filter(id=business_relation.business_id).first()
                if test_business:
                    return test_business.name

    @staticmethod
    def get_domain_name(obj):
        domain = TestDomain.objects.filter(id=obj.domain).first()
        if domain is None:
            return None
        return domain.name

    class Meta:
        model = TestSuite
        exclude = ['is_deleted']

    @staticmethod
    def get_owner_name(obj):
        owner = User.objects.filter(id=obj.owner).first()
        if owner is None:
            return None
        return owner.last_name or owner.first_name

    def get_test_case_list(self, obj):
        q = Q(test_suite_id=obj.id)
        ws_id = self.context['request'].query_params.get('ws_id')
        test_type = self.context['request'].query_params.get('test_type')
        if ws_id:
            q &= Q(ws_id=ws_id)
        if test_type:
            q &= Q(test_type=test_type)
        case_id_list = WorkspaceCaseRelation.objects.filter(q).values_list('test_case_id', flat=True)
        return SimpleCaseSerializer(TestCase.objects.filter(id__in=case_id_list), many=True).data

    @staticmethod
    def get_domain_name_list(obj):
        domain_id_list = DomainRelation.objects.filter(object_type='suite', object_id=obj.id).values_list(
            'domain_id', flat=True)
        domain_name_list = [TestDomain.objects.filter(id=domain_id).first().name for domain_id in domain_id_list]
        return ','.join(domain_name_list)


class TestMetricSerializer(CommonSerializer):
    obj_name = serializers.SerializerMethodField()
    direction = serializers.CharField(source='get_direction_display')
    cv_threshold = serializers.SerializerMethodField()
    cmp_threshold = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()

    class Meta:
        model = TestMetric
        exclude = ['is_deleted']

    @staticmethod
    def get_unit(obj):
        if obj.object_type == 'suite':
            perf_res = PerfResult.objects.filter(test_suite_id=obj.object_id, metric=obj.name, unit__isnull=False)
        else:
            perf_res = PerfResult.objects.filter(test_case_id=obj.object_id, metric=obj.name, unit__isnull=False)
        if perf_res.exists():
            unit = perf_res.first().unit
        else:
            unit = obj.unit
        return unit

    @staticmethod
    def get_cv_threshold(obj):
        return obj.cv_threshold * 100

    @staticmethod
    def get_cmp_threshold(obj):
        return obj.cmp_threshold * 100

    @staticmethod
    def get_obj_name(obj):
        if obj.object_type == 'suite':
            suite = TestSuite.objects.filter(id=obj.object_id).first()
            if suite is None:
                return None
            return suite.name
        else:
            case = TestCase.objects.filter(id=obj.object_id).first()
            if case is None:
                return None
            return case.name


class WorkspaceCaseRelationSerializer(CommonSerializer):
    suite_name = serializers.SerializerMethodField()
    case_name = serializers.SerializerMethodField()
    workspace_name = serializers.SerializerMethodField()

    class Meta:
        model = WorkspaceCaseRelation
        exclude = ['is_deleted']

    @staticmethod
    def get_suite_name(obj):
        suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if suite is None:
            return None
        return suite.name

    @staticmethod
    def get_case_name(obj):
        case = TestCase.objects.filter(id=obj.test_case_id).first()
        if case is None:
            return None
        return case.name

    @staticmethod
    def get_workspace_name(obj):
        workspace = Workspace.objects.filter(id=obj.ws_id).first()
        if workspace is None:
            return None
        return workspace.name


class TestDomainSerializer(CommonSerializer):
    creator = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()

    class Meta:
        model = TestDomain
        exclude = ['is_deleted']

    @staticmethod
    def get_creator(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_update_user(obj):
        update_user = None
        creator = User.objects.filter(id=obj.update_user).first()
        if creator:
            update_user = creator.first_name if creator.first_name else creator.last_name
        return update_user


class TestRetrieveSuiteSerializer(CommonSerializer):
    case_num = serializers.SerializerMethodField()

    class Meta:
        model = TestSuite
        fields = ['id', 'name', 'case_num']

    @staticmethod
    def get_case_num(obj):
        return TestCase.objects.filter(test_suite_id=obj.id).count()


class TestRetrieveCaseSerializer(CommonSerializer):

    class Meta:
        model = TestCase
        fields = ['id', 'name', 'certificated']


class RetrieveSuiteSerializer(CommonSerializer):
    owner_name = serializers.SerializerMethodField()
    domain_name_list = serializers.SerializerMethodField()

    class Meta:
        model = TestSuite
        exclude = ['is_deleted', 'test_framework', 'is_default', 'owner']

    @staticmethod
    def get_owner_name(obj):
        owner_name = ''
        user_obj = User.objects.filter(id=obj.owner).first()
        if user_obj is not None:
            owner_name = user_obj.last_name or user_obj.first_name
        return owner_name

    @staticmethod
    def get_domain_name_list(obj):
        domain_relation = DomainRelation.objects.filter(object_type='suite', object_id=obj.id).values_list(
            'domain_id', flat=True)
        domain_name_list = TestDomain.objects.filter(id__in=domain_relation).values_list('name', flat=True)
        return ','.join(domain_name_list)


class RetrieveCaseSerializer(CommonSerializer):
    domain_name_list = serializers.SerializerMethodField()
    suite_name = serializers.SerializerMethodField()
    recently_job = serializers.SerializerMethodField()
    run_mode = serializers.SerializerMethodField()
    test_type = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        exclude = ['is_deleted', 'is_default']

    @staticmethod
    def get_domain_name_list(obj):
        domain_relation = DomainRelation.objects.filter(object_type='case', object_id=obj.id).values_list(
            'domain_id', flat=True)
        domain_name_list = TestDomain.objects.filter(id__in=domain_relation).values_list('name', flat=True)
        return ','.join(domain_name_list)

    @staticmethod
    def get_test_type(obj):
        test_type = None
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite is not None:
            test_type = test_suite.test_type
        return test_type

    @staticmethod
    def get_suite_name(obj):
        suite_name = None
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite is not None:
            suite_name = test_suite.name
        return suite_name

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite is not None:
            creator = User.objects.filter(id=test_suite.owner).first()
            if creator is not None:
                creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_run_mode(obj):
        run_mode = None
        test_suite = TestSuite.objects.filter(id=obj.test_suite_id).first()
        if test_suite is not None:
            run_mode = test_suite.run_mode
        return run_mode

    @staticmethod
    def get_recently_job(obj):
        recently_job = None
        suc_job_list = TestJob.objects.filter(state='success').exclude(created_from='offline')
        test_job_case = TestJobCase.objects.filter(test_case_id=obj.id, job_id__in=suc_job_list).\
            order_by('-gmt_created').first()
        if test_job_case is not None:
            job_id = test_job_case.job_id
            test_job = TestJob.objects.filter(id=job_id).first()
            if test_job is not None:
                ws_id = test_job.ws_id
                recently_job = '/ws/{}/test_result/{}'.format(ws_id, job_id)
        return recently_job


class TestBusinessSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    update_user = serializers.SerializerMethodField()

    class Meta:
        model = TestBusiness
        exclude = ['is_deleted']

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_update_user(obj):
        update_user = None
        creator = User.objects.filter(id=obj.update_user).first()
        if creator:
            update_user = creator.first_name if creator.first_name else creator.last_name
        return update_user


class SysJobSerializer(CommonSerializer):
    ws_show_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    case_name_list = serializers.SerializerMethodField()

    class Meta:
        model = TestJob
        fields = ['id', 'name', 'ws_id', 'state', 'ws_show_name', 'creator', 'creator_name', 'gmt_created',
                  'state_desc', 'case_name_list']

    def get_case_name_list(self, obj):
        if hasattr(self.context['request'], 'case_id_list'):
            case_id_list = self.context['request'].case_id_list
            if case_id_list:
                case_list = TestJobCase.objects.filter(
                    job_id=obj.id, test_case_id__in=case_id_list).values_list('test_case_id', flat=True)
                case_name_list = TestCase.objects.filter(id__in=case_list).values_list('name', flat=True)
                return ' / '.join(case_name_list)

    @staticmethod
    def get_state(obj):
        if obj.state == 'pending_q':
            return 'pending'
        return obj.state

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_ws_show_name(obj):
        workspace_obj = Workspace.objects.filter(id=obj.ws_id).first()
        if workspace_obj is not None:
            return workspace_obj.show_name


class SysTemplateSerializer(CommonSerializer):
    ws_show_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    case_name_list = serializers.SerializerMethodField()

    class Meta:
        model = TestTemplate
        fields = ['id', 'name', 'ws_id', 'ws_show_name', 'creator', 'creator_name', 'gmt_created', 'case_name_list']

    def get_case_name_list(self, obj):
        if hasattr(self.context['request'], 'case_id_list'):
            case_id_list = self.context['request'].case_id_list
            if case_id_list:
                case_list = TestTmplCase.objects.filter(
                    tmpl_id=obj.id, test_case_id__in=case_id_list).values_list('test_case_id', flat=True)
                case_name_list = TestCase.objects.filter(id__in=case_list).values_list('name', flat=True)
                return ' / '.join(case_name_list)

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    @staticmethod
    def get_ws_show_name(obj):
        workspace_obj = Workspace.objects.filter(id=obj.ws_id).first()
        if workspace_obj is not None:
            return workspace_obj.show_name


class BusinessSuiteSerializer(CommonSerializer):
    creator_name = serializers.SerializerMethodField()
    test_suite_list = serializers.SerializerMethodField()

    class Meta:
        model = TestBusiness
        fields = ['id', 'name', 'gmt_created', 'gmt_modified', 'creator_name', 'description', 'test_suite_list',
                  'creator']

    @staticmethod
    def get_creator_name(obj):
        creator_name = None
        creator = User.objects.filter(id=obj.creator).first()
        if creator:
            creator_name = creator.first_name if creator.first_name else creator.last_name
        return creator_name

    def get_test_suite_list(self, obj):
        ws_id = self.context['request'].ws_id
        business_case_relation = WorkspaceCaseRelation.objects.filter(ws_id=ws_id, test_type='business')
        suite_id_list = business_case_relation.values_list('test_suite_id', flat=True)
        case_id_list = business_case_relation.values_list('test_case_id', flat=True)
        test_suite_list = list()
        business_suite = BusinessSuiteRelation.objects.filter(
            business_id=obj.id).values_list('test_suite_id', flat=True)
        tmp_suite_queryset = TestSuite.objects.filter(id__in=set(suite_id_list) & set(business_suite))
        for tmp_suite in tmp_suite_queryset:
            test_case_list = list()
            for tmp_case in TestCase.objects.filter(test_suite_id=tmp_suite.id, id__in=case_id_list):
                domain_list = DomainRelation.objects.filter(
                    object_type='case', object_id=tmp_case.id).values_list('domain_id', flat=True)
                domain_list = TestDomain.objects.filter(id__in=domain_list).values_list('name', flat=True)
                domain_name_list = ','.join(domain_list)
                ci_type = ''
                if tmp_suite.test_type == 'business':
                    access_case = AccessCaseConf.objects.filter(test_case_id=tmp_case.id).first()
                    if access_case:
                        ci_type = access_case.ci_type
                tmp_case_data = {
                    'id': tmp_case.id,
                    'name': tmp_case.name,
                    'domain_name_list': domain_name_list,
                    'timeout': tmp_case.timeout,
                    'ci_type': ci_type,
                    'gmt_created': str(tmp_suite.gmt_created).split('.')[0],
                    'doc': tmp_case.doc,
                }
                test_case_list.append(tmp_case_data)
            domain_list = DomainRelation.objects.filter(
                object_type='suite', object_id=tmp_suite.id).values_list('domain_id', flat=True)
            domain_list = TestDomain.objects.filter(id__in=domain_list).values_list('name', flat=True)
            domain_name_list = ','.join(domain_list)
            owner_name = None
            creator = User.objects.filter(id=obj.creator).first()
            if creator:
                owner_name = creator.first_name if creator.first_name else creator.last_name
            tmp_suite_data = {
                'id': tmp_suite.id,
                'name': tmp_suite.name,
                'run_mode': tmp_suite.run_mode,
                'domain_name_list': domain_name_list,
                'test_type': tmp_suite.test_type,
                'view_type': tmp_suite.view_type,
                'doc': tmp_suite.doc,
                'owner': tmp_suite.owner,
                'owner_name': owner_name,
                'description': tmp_suite.description,
                'gmt_created': str(tmp_suite.gmt_created).split('.')[0],
                'test_case_list': test_case_list,
            }
            test_suite_list.append(tmp_suite_data)
        return test_suite_list
