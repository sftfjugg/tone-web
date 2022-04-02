# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
import datetime
from django.db.models import Q, Case, When
from django.db import transaction

from tone.models import Product, Project, Repo, RepoBranch, ProjectBranchRelation, Baseline, FuncBaselineDetail, \
    PerfBaselineDetail, Workspace
from tone.core.common.services import CommonService
from tone.core.common.expection_handler.error_code import ErrorCode
from tone.core.common.expection_handler.custom_error import ProductException


class ProductService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(name=data.get('name')) if data.get('name') else q
        q &= Q(id=data.get('prd_id')) if data.get('prd_id') else q
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        return queryset.filter(q)

    def update(self, data):
        prd_id = data.get('prd_id')
        assert prd_id, ProductException(ErrorCode.PRODUCT_ID_NEED)
        obj = Product.objects.get(id=prd_id)
        for key, value in data.items():
            if key == 'name':
                if value != obj.name:
                    self.check_name(value, obj.ws_id)
            if hasattr(obj, key):
                setattr(obj, key, value)
            else:
                pass
        obj.save()

    def create(self, data):
        name = data.get('name')
        description = data.get('description')
        ws_id = data.get('ws_id')
        command = data.get('command')
        assert name, ProductException(ErrorCode.NAME_NEED)
        assert ws_id, ProductException(ErrorCode.WS_NEED)
        self.check_name(name, ws_id)
        Product.objects.create(name=name, description=description, ws_id=ws_id, command=command)

    @staticmethod
    def delete(data):
        prd_id = data.get('prd_id')
        assert prd_id, ProductException(ErrorCode.PRODUCT_ID_NEED)
        if Product.objects.filter(id=prd_id, is_default=True).exists():
            raise ProductException(ErrorCode.DEFAULT_PRODUCT_CAN_NOT_DELETE)
        with transaction.atomic():
            Product.objects.filter(id=prd_id).delete()
            Project.objects.filter(product_id=prd_id).delete()

    @staticmethod
    def check_name(name, ws_id):
        obj = Product.objects.filter(name=name, ws_id=ws_id)
        if obj.exists():
            if name in obj.values_list('name', flat=True):
                raise ProductException(ErrorCode.PRODUCT_DUPLICATION)


class ProjectService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(name__icontains=data.get('name')) if data.get('name') else q
        q &= Q(id=data.get('project_id')) if data.get('project_id') else q
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        q &= Q(product_id=data.get('product_id')) if data.get('product_id') else q
        q &= Q(product_version=data.get('product_version')) if data.get('product_version') else q
        q &= Q(is_show=data.get('is_show')) if data.get('is_show') else q
        return queryset.filter(q)

    def update(self, data):
        project_id = data.get('project_id')
        is_show = data.get('is_show') if data.get('is_show') else 0
        assert project_id, ProductException(ErrorCode.PROJECT_ID_NEED)
        obj = Project.objects.get(id=project_id)
        obj.drag_modified = obj.drag_modified
        obj.is_show = is_show
        for key, value in data.items():
            if key == 'name':
                if value != obj.name:
                    self.check_name(value)
            if key == 'is_default':
                self.check_default(value, obj.ws_id, obj.product_id)
            if hasattr(obj, key):
                setattr(obj, key, value)
            else:
                pass
        obj.save()

    def create(self, data):
        name = data.get('name')
        description = data.get('description')
        ws_id = data.get('ws_id')
        product_id = data.get('product_id')
        product_version = data.get('product_version')
        is_show = data.get('is_show')
        assert name, ProductException(ErrorCode.NAME_NEED)
        assert ws_id, ProductException(ErrorCode.WS_NEED)
        assert product_id, ProductException(ErrorCode.PRODUCT_NEED)
        self.check_name(name)
        Project.objects.create(name=name, description=description, ws_id=ws_id, product_version=product_version,
                               product_id=product_id, is_show=is_show)

    @staticmethod
    def delete(data):
        project_id = data.get('project_id')
        assert project_id, ProductException(ErrorCode.PROJECT_ID_NEED)
        if Project.objects.filter(id=project_id, is_default=True).exists():
            raise ProductException(ErrorCode.DEFAULT_PROJECT_CAN_NOT_DELETE)
        with transaction.atomic():
            project_obj = Project.objects.get(id=project_id)
            baseline_queryset = Baseline.objects.filter(ws_id=project_obj.ws_id, version=project_obj.product_version)
            baseline_id_list = baseline_queryset.values_list('id')
            FuncBaselineDetail.objects.filter(baseline_id__in=baseline_id_list).delete()
            PerfBaselineDetail.objects.filter(baseline_id__in=baseline_id_list).delete()
            baseline_queryset.delete()
            Project.objects.filter(id=project_id).delete()

    @staticmethod
    def check_product_version(product_version, ws_id):
        if product_version:
            if Project.objects.filter(product_version=product_version, ws_id=ws_id).exists():
                raise ProductException(ErrorCode.PRODUCT_VERSION_DUPLICATION)

    @staticmethod
    def check_name(name):
        obj = Project.objects.filter(name=name)
        if obj.exists():
            for tmp_obj in obj:
                if tmp_obj.name == name:
                    workspace = Workspace.objects.filter(id=tmp_obj.ws_id).first()
                    if workspace is not None:
                        raise ProductException((ErrorCode.PROJECT_DUPLICATION[0],
                                                'Workspace: {} 下{}'.format(workspace.show_name,
                                                                           ErrorCode.PROJECT_DUPLICATION[1])))

    @staticmethod
    def check_default(is_default, ws_id, product_id):
        if not is_default:
            return
        with transaction.atomic():
            Project.objects.filter(is_default=True, ws_id=ws_id).update(is_default=False)
            Product.objects.filter(is_default=True, ws_id=ws_id).update(is_default=False)
            Product.objects.filter(id=product_id).update(is_default=True)


class RepoService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(name=data.get('name')) if data.get('name') else q
        q &= Q(id=data.get('repo_id')) if data.get('repo_id') else q
        q &= Q(git_url=data.get('git_url')) if data.get('git_url') else q
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        return queryset.filter(q)

    def update(self, data):
        repo_id = data.get('repo_id')
        ws_id = data.get('ws_id')
        assert repo_id, ProductException(ErrorCode.REPOSITORY_ID_NEED)
        assert ws_id, ProductException(ErrorCode.WS_NEED)
        with transaction.atomic():
            obj = Repo.objects.get(id=repo_id)
            for key, value in data.items():
                if key == 'name':
                    if value != obj.name:
                        self.check_name(value, ws_id)
                if key == 'git_url':
                    self.check_repo(value)
                    value == obj.git_url or RepoBranch.objects.filter(repo_id=repo_id).delete()
                if hasattr(obj, key):
                    setattr(obj, key, value)
                else:
                    pass
            obj.save()

    def create(self, data):
        name = data.get('name')
        description = data.get('description')
        git_url = data.get('git_url')
        ws_id = data.get('ws_id')
        assert name, ProductException(ErrorCode.NAME_NEED)
        assert git_url, ProductException(ErrorCode.PRODUCT_NEED)
        assert ws_id, ProductException(ErrorCode.WS_NEED)
        self.check_name(name, ws_id)
        self.check_repo(git_url)
        Repo.objects.create(name=name, description=description, git_url=git_url, ws_id=ws_id)

    @staticmethod
    def delete(data):
        repo_id = data.get('repo_id')
        assert repo_id, ProductException(ErrorCode.REPOSITORY_ID_NEED)
        with transaction.atomic():
            Repo.objects.filter(id=repo_id).delete()
            RepoBranch.objects.filter(repo_id=repo_id).delete()
            ProjectBranchRelation.objects.filter(repo_id=repo_id).delete()

    @staticmethod
    def check_name(name, ws_id):
        obj = Repo.objects.filter(name=name, ws_id=ws_id)
        if obj.exists():
            raise ProductException(ErrorCode.PROJECT_DUPLICATION)

    @staticmethod
    def check_repo(repo):
        pass


class RepoBranchService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(name=data.get('name')) if data.get('name') else q
        q &= Q(id=data.get('branch_id')) if data.get('branch_id') else q
        q &= Q(repo_id=data.get('repo_id')) if data.get('repo_id') else q
        return queryset.filter(q)

    def update(self, data):
        branch_id = data.get('branch_id')
        assert branch_id, ProductException(ErrorCode.BRANCH_ID_NEED)
        obj = RepoBranch.objects.get(id=branch_id)
        for key, value in data.items():
            if key == 'name':
                if value != obj.name:
                    self.check_name(value, obj.repo_id)
            if key == 'name':
                self.check_branch(Repo.objects.get(id=obj.repo_id).git_url, value)
            if hasattr(obj, key):
                setattr(obj, key, value)
            else:
                pass
        obj.save()

    def create(self, data):
        name = data.get('name')
        description = data.get('description')
        repo_id = data.get('repo_id')
        assert name, ProductException(ErrorCode.NAME_NEED)
        assert repo_id, ProductException(ErrorCode.REPOSITORY_ID_NEED)
        self.check_name(name, repo_id)
        self.check_branch(Repo.objects.get(id=repo_id).git_url, name)
        RepoBranch.objects.create(name=name, description=description, repo_id=repo_id)

    @staticmethod
    def delete(data):
        branch_id = data.get('branch_id')
        assert branch_id, ProductException(ErrorCode.BRANCH_ID_NEED)
        RepoBranch.objects.filter(id=branch_id).delete()

    @staticmethod
    def check_name(name, repo_id):
        obj = RepoBranch.objects.filter(name=name, repo_id=repo_id)
        if obj.exists():
            raise ProductException(ErrorCode.BRANCH_DUPLICATION)

    @staticmethod
    def check_branch(repo, branch):
        pass


class CheckGitLabService(CommonService):

    @staticmethod
    def check_gitlab(data, operator):
        pass


class ProjectBranchService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(project_id=data.get('project_id')) if data.get('project_id') else q
        return queryset.filter(q)

    @staticmethod
    def create(data):
        project_id = data.get('project_id')
        repo_id = data.get('repo_id')
        branch_id = data.get('branch_id')
        is_master = data.get('is_master')
        assert project_id, ProductException(ErrorCode.PROJECT_ID_NEED)
        assert repo_id, ProductException(ErrorCode.REPOSITORY_ID_NEED)
        assert branch_id, ProductException(ErrorCode.BRANCH_ID_NEED)
        ProjectBranchRelation.objects.create(project_id=project_id, repo_id=repo_id, branch_id=branch_id,
                                             is_master=is_master)

    @staticmethod
    def delete(data):
        relation_id = data.get('relation_id')
        assert relation_id, ProductException(ErrorCode.RELATION_ID_NEED)
        ProjectBranchRelation.objects.filter(id=relation_id).delete()

    @staticmethod
    def update(data):
        relation_id = data.get('relation_id')
        assert relation_id, ProductException(ErrorCode.RELATION_ID_NEED)
        obj = ProjectBranchRelation.objects.get(id=relation_id)
        is_master = data.get('is_master', None)
        if is_master:
            ProjectBranchRelation.objects.filter(project_id=obj.project_id, is_master=True).update(is_master=False)
            obj.is_master = True
        obj.save()


class ProductDragService(CommonService):
    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        return queryset.filter(q).order_by('drag_modified')

    @staticmethod
    def get_distinct_product_queryset(data):
        ws_id = data.get('ws_id')
        start_location = data.get('from')
        end_location = data.get('to')
        if start_location < end_location:
            queryset_id_list = []
            queryset_old = Product.objects.filter(ws_id=ws_id).order_by('drag_modified')
            queryset_old_list = list(queryset_old.values('id'))
            for queryset_dict in queryset_old_list:
                if queryset_dict['id']:
                    queryset_id_list.append(queryset_dict['id'])
            queryset_id_list.insert(end_location, queryset_id_list[start_location - 1])
            del queryset_id_list[start_location - 1]
            preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(queryset_id_list)])
            querysets_order = Product.objects.filter(ws_id=ws_id).order_by(preserved)
            for querysets in querysets_order:
                now = datetime.datetime.now()
                querysets.drag_modified = now
                querysets.save()
            queryset = Product.objects.filter(ws_id=ws_id).order_by('drag_modified')
            return True, queryset
        else:
            queryset_id_list = []
            queryset_old = Product.objects.filter(ws_id=ws_id).order_by('drag_modified')
            queryset_old_list = list(queryset_old.values('id'))
            for queryset_dict in queryset_old_list:
                if queryset_dict['id']:
                    queryset_id_list.append(queryset_dict['id'])
            queryset_id_list.insert(end_location - 1, queryset_id_list[start_location - 1])
            queryset_id_new_list = []
            for queryset_id in queryset_id_list:
                if queryset_id not in queryset_id_new_list:
                    queryset_id_new_list.append(queryset_id)
            preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(queryset_id_new_list)])
            querysets_order = Product.objects.filter(ws_id=ws_id).order_by(preserved)
            for querysets in querysets_order:
                now = datetime.datetime.now()
                querysets.drag_modified = now
                querysets.save()
            queryset = Product.objects.filter(ws_id=ws_id).order_by('drag_modified')
            return True, queryset


class ProjectDragService(CommonService):

    @staticmethod
    def filter(queryset, data):
        q = Q()
        q &= Q(ws_id=data.get('ws_id')) if data.get('ws_id') else q
        q &= Q(product_id=data.get('product_id')) if data.get('product_id') else q
        return queryset.filter(q).order_by('drag_modified')

    @staticmethod
    def get_distinct_project_queryset(data):
        ws_id = data.get('ws_id')
        product_id = data.get('product_id')
        start_location = data.get('from')
        end_location = data.get('to')
        if start_location < end_location:
            queryset_id_list = []
            queryset_old = Project.objects.filter(ws_id=ws_id, product_id=product_id).order_by('drag_modified')
            queryset_old_list = list(queryset_old.values('id'))
            for queryset_dict in queryset_old_list:
                if queryset_dict['id']:
                    queryset_id_list.append(queryset_dict['id'])
            queryset_id_list.insert(end_location, queryset_id_list[start_location - 1])
            del queryset_id_list[start_location - 1]
            preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(queryset_id_list)])
            querysets_order = Project.objects.filter(ws_id=ws_id, product_id=product_id).order_by(preserved)
            for querysets in querysets_order:
                now = datetime.datetime.now()
                querysets.drag_modified = now
                querysets.save()
            queryset = Project.objects.filter(ws_id=ws_id, product_id=product_id).order_by('drag_modified')
            return True, queryset
        else:
            queryset_id_list = []
            queryset_old = Project.objects.filter(ws_id=ws_id, product_id=product_id).order_by('drag_modified')
            queryset_old_list = list(queryset_old.values('id'))
            for queryset_dict in queryset_old_list:
                if queryset_dict['id']:
                    queryset_id_list.append(queryset_dict['id'])
            queryset_id_list.insert(end_location - 1, queryset_id_list[start_location - 1])
            queryset_id_new_list = []
            for queryset_id in queryset_id_list:
                if queryset_id not in queryset_id_new_list:
                    queryset_id_new_list.append(queryset_id)
            preserved = Case(*[When(id=pk, then=pos) for pos, pk in enumerate(queryset_id_new_list)])
            querysets_order = Project.objects.filter(ws_id=ws_id, product_id=product_id).order_by(preserved)
            for querysets in querysets_order:
                now = datetime.datetime.now()
                querysets.drag_modified = now
                querysets.save()
            queryset = Project.objects.filter(ws_id=ws_id, product_id=product_id).order_by('drag_modified')
            return True, queryset


class BranchProjectService(CommonService):

    @staticmethod
    def filter(queryset, data):
        q = Q()
        project_id = data.get('project_id') if data.get('project_id') else None
        branch_id_list = []
        if project_id:
            branch_id_list = list(ProjectBranchRelation.objects.filter(project_id=project_id).values('branch_id',
                                                                                                     'repo_id'))
            for branch_id in branch_id_list:
                q |= Q(id=branch_id['branch_id'], repo_id=branch_id['repo_id'])
        if branch_id_list:
            repo_ids = []
            for qs in queryset.filter(q):
                if qs.repo_id in repo_ids:
                    continue
                else:
                    repo_ids.append(qs.repo_id)
            repo_list = []
            for repo_id in repo_ids:
                list_repo = list(Repo.objects.filter(id=repo_id).values('git_url', 'name'))
                branch_ids = list(RepoBranch.objects.filter(repo_id=repo_id).values('id'))
                branch_list = []
                for branch_id in list(branch_ids):
                    repo_branch = \
                        list(RepoBranch.objects.filter(id=branch_id['id']).values('id', 'name', 'description'))
                    branch_dict = {
                        "id": repo_branch[0]['id'],
                        "name": repo_branch[0]['name'],
                        "description": repo_branch[0]['description']
                    }
                    branch_list.append(branch_dict)
                repo = {
                    "repo_id": repo_id,
                    "repo_git_url": list_repo[0]['git_url'],
                    "repo_name": list_repo[0]['name'],
                    "branch_dict": branch_list
                }
                repo_list.append(repo)
            return repo_list
        else:
            return []