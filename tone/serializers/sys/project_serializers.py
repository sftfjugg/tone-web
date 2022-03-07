# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework import serializers

from tone.core.common.serializers import CommonSerializer
from tone.models import Product, Project, Repo, RepoBranch, ProjectBranchRelation


class ProductSerializer(CommonSerializer):
    projects = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'description', 'ws_id', 'name', 'projects', 'command', 'is_default']

    @staticmethod
    def get_projects(obj):
        objects = Project.objects.filter(product_id=obj.id)
        projects = [{
            'id': obj.id,
            'name': obj.name,
            'description': obj.description,
            'ws_id': obj.ws_id,
            'product_id': obj.product_id,
            'product_version': obj.product_version,
            'is_default': obj.is_default,
        } for obj in objects]
        return projects


class ProjectSerializer(CommonSerializer):
    product_name = serializers.SerializerMethodField()
    is_show = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'description', 'ws_id', 'name', 'product_id', 'product_version', 'is_default', 'product_name',
                  'is_show']

    @staticmethod
    def get_product_name(obj):
        return Product.objects.get(id=obj.product_id).name

    @staticmethod
    def get_is_show(obj):
        if Project.objects.get(id=obj.id).is_show:
            return 1
        else:
            return 0


class RepositorySerializer(CommonSerializer):
    branches = serializers.SerializerMethodField()

    class Meta:
        model = Repo
        fields = ['id', 'name', 'git_url', 'branches', 'description']

    @staticmethod
    def get_branches(obj):
        objects = RepoBranch.objects.filter(repo_id=obj.id)
        branches = [{
            'name': obj.name,
            'description': obj.description,
            'repo_id': obj.repo_id,
            'id': obj.id,
        } for obj in objects]
        return branches


class RepoBranchSerializer(CommonSerializer):
    class Meta:
        model = RepoBranch
        fields = ['id', 'name', 'repo_id', 'description']


class ProjectBranchSerializer(CommonSerializer):
    project_name = serializers.SerializerMethodField()
    git_url = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    product_version = serializers.SerializerMethodField()
    repo_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectBranchRelation
        fields = ['id', 'project_id', 'branch_id', 'repo_id', 'is_master', 'project_name', 'git_url', 'branch_name',
                  'description', 'product_version', 'repo_name']

    @staticmethod
    def get_project_name(obj):
        project_name = Project.objects.get(id=obj.project_id).name if Project.objects.filter(
            id=obj.project_id).exists() else None
        return project_name

    @staticmethod
    def get_description(obj):
        description = Project.objects.get(id=obj.project_id).description if Project.objects.filter(
            id=obj.project_id).exists() else None
        return description

    @staticmethod
    def get_product_version(obj):
        product_version = Project.objects.get(id=obj.project_id).product_version if Project.objects.filter(
            id=obj.project_id).exists() else None
        return product_version

    @staticmethod
    def get_git_url(obj):
        git_url = Repo.objects.get(id=obj.repo_id).git_url if Repo.objects.filter(
            id=obj.repo_id).exists() else None
        return git_url

    @staticmethod
    def get_branch_name(obj):
        branch_name = RepoBranch.objects.get(id=obj.branch_id).name if RepoBranch.objects.filter(
            id=obj.branch_id).exists() else None
        return branch_name

    @staticmethod
    def get_repo_name(obj):
        repo_name = Repo.objects.get(id=obj.repo_id).name if Repo.objects.filter(
            id=obj.repo_id).exists() else None
        return repo_name
