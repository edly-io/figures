"""
Paginators for Figures
"""

from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination
from rest_framework.response import Response


class FiguresPageLevelPagination(PageNumberPagination):
    """
    Custom Figures paginator to make the number of records returned consistent
    """
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data,
            'total_pages': self.page.paginator.num_pages
        })


class FiguresLimitOffsetPagination(LimitOffsetPagination):
    """
    Custom Figures paginator to make the number of records returned consistent
    """
    default_limit = 20


class FiguresKiloPagination(LimitOffsetPagination):
    """
    Custom Figures paginator to make the number of records returned consistent
    """
    default_limit = 1000
