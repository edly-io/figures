'''Paginatiors for Figures

'''

from rest_framework.pagination import LimitOffsetPagination


class FiguresTopStatsPagination(LimitOffsetPagination):
    '''Custom Figures paginator to make the number of records returned consistent
    '''
    default_limit = 10

class FiguresLimitOffsetPagination(LimitOffsetPagination):
    '''Custom Figures paginator to make the number of records returned consistent
    '''
    default_limit = 20


class FiguresKiloPagination(LimitOffsetPagination):
    '''Custom Figures paginator to make the number of records returned consistent
    '''
    default_limit = 1000
