"""
Paginators for Figures
"""

from rest_framework.pagination import LimitOffsetPagination, PageNumberPagination


class FiguresTopStatsPagination(PageNumberPagination):
    """
    Custom Figures paginator to make the number of records returned consistent
    """
    page_size = 10
    page_size_query_param = 'page'
    max_page_size = 1000


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
