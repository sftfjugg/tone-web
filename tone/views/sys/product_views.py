# _*_ coding:utf-8 _*_
"""
Module Description:
Date:
Author: Yfh
"""
from rest_framework.response import Response
from django.utils.decorators import method_decorator

from tone.core.common.views import CommonAPIView
from tone.serializers.sys.project_serializers import ProductSerializer, ProjectSerializer, RepositorySerializer, \
    RepoBranchSerializer, ProjectBranchSerializer
from tone.models import Product, Project, RepoBranch, Repo, ProjectBranchRelation
from tone.services.sys.product_services import ProductService, ProjectService, RepoService, RepoBranchService, \
    CheckGitLabService, ProjectBranchService, ProductDragService, ProjectDragService
from tone.core.common.expection_handler.error_catch import views_catch_error


class ProductView(CommonAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    service_class = ProductService
    permission_classes = []
    order_by = ['-gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询Product
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建Product
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改Product
        """
        self.service.update(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除Product
        """
        self.service.delete(request.data, operator=request.user)
        return Response(self.get_response_code())


class ProjectView(CommonAPIView):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
    service_class = ProjectService
    permission_classes = []
    order_by = ['-gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询Project
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建Project
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改Project
        """
        self.service.update(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除Project
        """
        self.service.delete(request.data, operator=request.user)
        return Response(self.get_response_code())


class RepositoryView(CommonAPIView):
    serializer_class = RepositorySerializer
    queryset = Repo.objects.all()
    service_class = RepoService
    permission_classes = []
    order_by = ['-gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询Repository
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建Repository
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改Repository
        """
        self.service.update(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除Repository
        """
        self.service.delete(request.data, operator=request.user)
        return Response(self.get_response_code())


class CodeBranchView(CommonAPIView):
    serializer_class = RepoBranchSerializer
    queryset = RepoBranch.objects.all()
    service_class = RepoBranchService
    permission_classes = []
    order_by = ['-gmt_created']

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询CodeBranch
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建CodeBranch
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改CodeBranch
        """
        self.service.update(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除CodeBranch
        """
        self.service.delete(request.data, operator=request.user)
        return Response(self.get_response_code())


class CheckGitLabView(CommonAPIView):
    permission_classes = []
    service_class = CheckGitLabService

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建CodeBranch
        """
        self.service.check_gitlab(request.data, operator=request.user)
        return Response(self.get_response_code())


class ProjectBranchView(CommonAPIView):
    permission_classes = []
    serializer_class = ProjectBranchSerializer
    service_class = ProjectBranchService
    queryset = ProjectBranchRelation.objects.all()
    order_by = ['gmt_created']

    @method_decorator(views_catch_error)
    def post(self, request):
        """
        创建Project Branch关联
        """
        self.service.create(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改Project Branch关联
        """
        self.service.update(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def delete(self, request):
        """
        删除Project Branch关联
        """
        self.service.delete(request.data, operator=request.user)
        return Response(self.get_response_code())

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询Project Branch关联
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)


class ProductDragView(CommonAPIView):
    serializer_class = ProductSerializer
    queryset = Product.objects.all()
    service_class = ProductDragService
    permission_classes = []
    order_by = None

    @method_decorator(views_catch_error)
    def get(self, request):
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改Product顺序
        """
        success, instances = self.service.get_distinct_product_queryset(data=request.data)
        if success:
            response_data = self.get_response_data(instances)
        else:
            response_data = self.get_response_code(code=201, msg=instances)
        return Response(response_data)


class ProjectDragView(CommonAPIView):
    serializer_class = ProjectSerializer
    queryset = Project.objects.all()
    service_class = ProjectDragService
    permission_classes = []
    order_by = None

    @method_decorator(views_catch_error)
    def get(self, request):
        """
        查询Project
        """
        queryset = self.service.filter(self.get_queryset(), request.GET)
        response_data = self.get_response_data(queryset, page=True)
        return Response(response_data)

    @method_decorator(views_catch_error)
    def put(self, request):
        """
        修改Project顺序
        """
        success, instances = self.service.get_distinct_project_queryset(data=request.data)
        if success:
            response_data = self.get_response_data(instances)
        else:
            response_data = self.get_response_code(code=201, msg=instances)
        return Response(response_data)