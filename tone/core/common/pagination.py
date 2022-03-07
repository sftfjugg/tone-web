import urllib.parse

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultPagination(PageNumberPagination):
    page_size_query_param = 'page_size'
    page_query_param = 'page_num'
    max_page_size = 500
    page_size = 20

    def get_paginated_response(self, data):
        return Response(
            {
                'total': self.page.paginator.count,
                'page_num': self.page.number,
                'total_page': self.page.paginator.num_pages,
                'page_size': self.get_page_size(self.request),
                'previous': urllib.parse.unquote(self.get_previous_link()) if self.get_previous_link() else None,
                'next': urllib.parse.unquote(self.get_next_link()) if self.get_next_link() else None,
                'data': data,
            }
        )
