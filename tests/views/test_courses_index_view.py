'''Tests Figures CourseIndexView class

'''

from __future__ import absolute_import
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import (
    APIRequestFactory,
    # RequestsClient, Not supported in older  rest_framework versions
    force_authenticate,
)

from figures.helpers import is_multisite
from figures.views import CoursesIndexViewSet

from collections import OrderedDict

from tests.factories import (
    CourseOverviewFactory,
    OrganizationFactory,
    OrganizationCourseFactory,
)
from tests.helpers import make_course_key_str
from tests.views.base import BaseViewTest

# Course data and generate method are duplicates course data in test_filters.py
COURSE_DATA = [
    {'id': u'course-v1:AlphaOrg+A001+RUN', 'name': u'Alpha Course 1', 'org': u'AlphaOrg'},
    {'id': u'course-v1:AlphaOrg+A002+RUN', 'name': u'Alpha Course 2', 'org': u'AlphaOrg'},
    {'id': u'course-v1:BravoOrg+A001+RUN', 'name': u'Bravo Course 1', 'org': u'BravoOrg'},
    {'id': u'course-v1:BravoOrg+B002+RUN', 'name': u'Bravo Course 2', 'org': u'BravoOrg'},
]


# Look into renaming 'name' to 'display_name'

def make_course(**kwargs):
    return CourseOverviewFactory(
        id=kwargs['id'], display_name=kwargs['name'], org=kwargs['org'])


@pytest.mark.django_db
class TestCoursesIndexViewSet(BaseViewTest):
    '''Tests the CourseIndexView view class
    '''
    request_path = 'api/courses-index/'
    view_class = CoursesIndexViewSet

    @pytest.fixture(autouse=True)
    def setup(self, db):
        super(TestCoursesIndexViewSet, self).setup(db)
        self.course_overviews = [make_course(**data) for data in COURSE_DATA]
        if is_multisite():
            self.organization = self.edly_org.edx_organization
            for co in self.course_overviews:
                OrganizationCourseFactory(organization=self.organization,
                                          course_id=str(co.id))

    def test_get_all(self):
        expected_data = COURSE_DATA
        request = APIRequestFactory().get(self.request_path)
        request.site = self.site
        force_authenticate(request, user=self.staff_user)
        view = self.view_class.as_view({'get': 'list'})
        response = view(request)
        assert response.status_code == 200
        assert set(response.data.keys()) == set(
            ['count', 'next', 'previous', 'results', ])
        assert [dict(data) for data in response.data['results']] == expected_data

    @pytest.mark.parametrize('query_params, filter_args', [
        ('?org=AlphaOrg', 'AlphaOrg'),
    ])
    def test_get_org_filtered(self, query_params, filter_args):
        expected_data = [rec for rec in COURSE_DATA if rec['org'] == filter_args]
        request = APIRequestFactory().get(self.request_path + query_params)
        force_authenticate(request, user=self.staff_user)
        view = self.view_class.as_view({'get': 'list'})
        response = view(request)
        assert response.status_code == 200
        assert set(response.data.keys()) == set(
            ['count', 'next', 'previous', 'results', ])
        assert [dict(data) for data in response.data['results']] == expected_data
