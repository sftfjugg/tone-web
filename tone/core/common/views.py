from django.db.models import Q
from django.db.models.query import QuerySet
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.views import APIView

from tone.core.common.exceptions.exception_class import NoMorePageException
from tone.core.common.schemas import BaseSchema
from tone.core.common.expection_handler.error_code import ErrorCode


class BaseView(APIView):
    code = ErrorCode.CODE
    msg = ErrorCode.SUCCESS
    service_class = None
    schema_class = BaseSchema

    def get_response_code(self, code=None, msg=None, data=None, field=None, position='center'):
        code = code or self.code
        msg = msg or self.msg
        if data is not None:
            return {'code': code, 'msg': msg, 'data': data}
        if field is not None:
            return {'code': code, 'msg': msg, 'position': position, 'field': field}
        return {'code': code, 'msg': msg}

    @property
    def service(self):
        return self.service_class()


class CommonAPIView(GenericAPIView, BaseView):
    order_by = ('-id',)
    filter_fields = []
    search_param = 'keyword'
    search_fields = []

    def get_response_data(self, queryset, many=True, page=True):
        serializer_data = self.get_serializer_data(queryset, many, page)
        serializer_data.update({'code': self.code, 'msg': self.msg})
        return serializer_data

    def get_serializer_data(self, queryset, many, page):
        if not many:
            return {'data': self.get_serializer(queryset, many=many).data}
        if queryset and page:
            if isinstance(queryset, QuerySet):
                queryset = self.order(queryset)
                queryset = self.filter(queryset)
                queryset = self.search(queryset)
            return self._get_pagination_serializer(queryset).data
        if queryset and not page:
            queryset = self.order(queryset)
        return {'data': self.get_serializer(queryset, many=many).data}

    def _get_pagination_serializer(self, queryset):
        try:
            page = self.paginate_queryset(queryset)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        except NotFound:
            raise NoMorePageException

    @property
    def serializer(self):
        return self.get_serializer()

    def order(self, queryset):
        if not self.order_by:
            return queryset
        for order_field in self.order_by:
            queryset = queryset.order_by(order_field)
        return queryset

    def filter(self, queryset):
        if not self.filter_fields:
            return queryset
        filter_q = Q()
        for filter_field in self.filter_fields:
            if self.request.GET.get(filter_field):
                filter_q &= Q(**{filter_field: self.request.GET.get(filter_field)})
        return queryset.filter(filter_q)

    def search(self, queryset):
        search_q = Q()
        search_value = self.request.GET.get(self.search_param)
        if not (self.search_fields and search_value):
            return queryset
        for search_key in self.search_fields:
            if search_key.startswith('='):
                search_q |= Q(**{'%s' % search_key.strip('='): search_value})
            else:
                search_q |= Q(**{'%s__contains' % search_key: search_value})
        return queryset.filter(search_q)

    def get_response_only_for_data(self, data):
        new_data = {'data': data}
        new_data.update({'code': self.code, 'msg': self.msg})
        return new_data
