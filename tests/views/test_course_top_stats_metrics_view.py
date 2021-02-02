from datetime import datetime
import mock
import pytest

from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

from django.contrib.auth import get_user_model
from django.test import RequestFactory

from figures.compat import CourseOverview
from openedx.features.edly.tests.factories import (
    EdlySubOrganizationFactory,
)

from figures.helpers import as_course_key
from figures.helpers import is_multisite
from figures.views import CourseTopStatsViewSet

from tests.factories import (
    CourseDailyMetricsFactory,
    CourseOverviewFactory,
    OrganizationFactory,
    OrganizationCourseFactory,
    SiteFactory,
)
from tests.views.helpers import create_test_users


@pytest.mark.django_db
class TestCourseTopStatsViewSet(object):
    """
    Tests the CourseTopStatsViewSet class
    """

    request_path_top_enrollments = 'api/courses/stats/?order_by=enrollment_count,desc'
    request_path_top_completions = 'api/courses/stats/?order_by=num_learners_completed,desc'
    view_class = CourseTopStatsViewSet

    def setup(self):
        self.callers = create_test_users()
        self.course_overviews = [CourseOverviewFactory() for i in range(4)]
        self.expected_result_keys = [
            'course_name', 'enrollment_count', 'num_of_learners_completed'
        ]
        if is_multisite():
            self.site = SiteFactory(domain='foo.test')
            self.organization = OrganizationFactory()
            self.edly_sub_organization = EdlySubOrganizationFactory(
                lms_site=self.site,
                edx_organization=self.organization
            )
            for course_overview in self.course_overviews:
                OrganizationCourseFactory(
                    organization=self.organization,
                    course_id=str(course_overview.id)
                )
                CourseDailyMetricsFactory(
                    course_id=str(course_overview.id),
                    site=self.site,
                    date_for=datetime.utcnow()
                )

    @property
    def staff_user(self):
        return get_user_model().objects.get(username='staff_user')

    def test_get_list_top_enrollments(self):
        """
        Tests retrieving a list of courses with maximum number of enrollments.
        """
        request = RequestFactory(SERVER_NAME=self.site.domain).get(self.request_path_top_enrollments)
        request.site = self.site
        force_authenticate(request, user=self.staff_user)
        view = self.view_class.as_view({'get': 'list'})
        response = view(request)

        assert response.status_code == 200
        assert set(response.data.keys()) == set(
            ['count', 'current_page', 'total_pages', 'results', 'next', 'previous', ])
        assert len(response.data['results']) == len(self.course_overviews)

        for rec in response.data['results']:
            assert CourseOverview.objects.get(id=as_course_key(rec['course_id']))
            assert CourseOverview.objects.get(display_name=rec['course_name'])
        assert response.data['results'][0]['enrollment_count'] >= response.data['results'][1]['enrollment_count']


    def test_get_list_top_completions(self):
        """
        Tests retrieving a list of courses with maximum number of completions.
        """
        request = RequestFactory(SERVER_NAME=self.site.domain).get(self.request_path_top_completions)
        request.site = self.site
        force_authenticate(request, user=self.staff_user)
        view = self.view_class.as_view({'get': 'list'})
        response = view(request)

        assert response.status_code == 200
        assert set(response.data.keys()) == set(
            ['count', 'current_page', 'total_pages', 'results', 'next', 'previous', ])
        assert len(response.data['results']) == len(self.course_overviews)

        for rec in response.data['results']:
            assert CourseOverview.objects.get(display_name=rec['course_name'])
        assert response.data['results'][0]['num_learners_completed'] >= response.data['results'][1]['num_learners_completed']
