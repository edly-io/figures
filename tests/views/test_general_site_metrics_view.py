'''

'''


from __future__ import absolute_import
from functools import total_ordering
import pytest

from rest_framework.test import (
    APIRequestFactory,
    #RequestsClient, Not supported in older  rest_framework versions
    force_authenticate,
    )

from figures.views import GeneralSiteMetricsView
from tests.views.base import BaseViewTest


def mock_get_monthly_site_metrics(date_for=None, **kwargs):
    return dict(
        total_site_learners=3,
        total_site_staff_users=4,
        total_site_coures=5,
        total_active_courses=8,
    )

def mock_get_monthly_site_metrics_custom_date(date_for, **kwargs):
    return dict(
        total_site_learners=10,
        total_site_staff_users=10,
        total_site_coures=10,
        total_active_courses=10,
    )

@pytest.mark.django_db
class TestGeneralSiteMetricsView(BaseViewTest):
    '''Tests the GeneralSiteMetricsView view class
    '''
    request_path = 'api/general-site-metrics'
    view_class = GeneralSiteMetricsView
    view_class_with_custom_date = GeneralSiteMetricsView

    # Because we are testing an APIView and not a ViewSetMixin,
    # we set the 'get' action to None because the view 'as_view'
    # method takes no argument
    get_action=None

    @pytest.fixture(autouse=True)
    def setup(self, db):
        super(TestGeneralSiteMetricsView, self).setup(db)
        self.view_class.metrics_method = property(
            lambda self: mock_get_monthly_site_metrics)

        self.view_class_with_custom_date.metrics_method = property(
            lambda self: mock_get_monthly_site_metrics_custom_date)

    def test_get(self):
        request = APIRequestFactory().get(self.request_path)
        force_authenticate(request, user=self.staff_user)
        view = self.view_class.as_view()
        response = view(request)
        assert response.status_code == 200

        assert response.data == mock_get_monthly_site_metrics()


    def test_get_with_custom_date_range(self):
        request = APIRequestFactory().get(
            self.request_path,
            dict(start_date='1-12-2021', end_date='10-12-2021')
        )
        force_authenticate(request, user=self.staff_user)
        view = self.view_class.as_view()
        response = view(request)
        assert response.status_code == 200

        assert response.data == mock_get_monthly_site_metrics_custom_date()
