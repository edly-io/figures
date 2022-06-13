from __future__ import absolute_import
import pytest

from rest_framework.test import (
    APIRequestFactory,
    #RequestsClient, Not supported in older  rest_framework versions
    force_authenticate,
    )

from figures.edly_view.edly_reports import LearnersCSV
from tests.views.base import BaseViewTest
from tests.helpers import organizations_support_sites

if organizations_support_sites():
    from tests.factories import UserOrganizationMappingFactory


USER_DATA = [
    {'id': 101, 'username': u'alpha', 'fullname': u'Alpha One',
     'is_active': True, 'country': 'CA'},
    {'id': 102, 'username': u'alpha02', 'fullname': u'Alpha Two', 'is_active': False, 'country': 'UK'},
    {'id': 103, 'username': u'bravo', 'fullname': u'Bravo One', 'is_active': True, 'country': 'US'},
    {'id': 104, 'username': u'bravo02', 'fullname': u'Bravo Two', 'is_active': True, 'country': 'UY'},
]

COURSE_DATA = [
    { 'id': u'course-v1:AlphaOrg+A001+RUN', 'name': u'Alpha Course 1', 'org': u'AlphaOrg', 'number': u'A001' },
    { 'id': u'course-v1:AlphaOrg+A002+RUN', 'name': u'Alpha Course 2', 'org': u'AlphaOrg', 'number': u'A002' },
    { 'id': u'course-v1:BravoOrg+A001+RUN', 'name': u'Bravo Course 1', 'org': u'BravoOrg', 'number': u'B001' },
    { 'id': u'course-v1:BravoOrg+B002+RUN', 'name': u'Bravo Course 2', 'org': u'BravoOrg', 'number': u'B002' },
]


@pytest.mark.django_db
class TestLearnerDetailCSVView(BaseViewTest):
    request_path = 'api/edly/learner-report/'
    view_class = LearnersCSV

    @pytest.fixture(autouse=True)
    def setup(self db, settings):
        super(TestLearnerDetailCSVView, self).setup(db)
        settings.FEATURES['FIGURES_IS_MULTISITE'] = True
        is_multisite = figures.helpers.is_multisite()
        assert is_multisite
        self.my_site_org = OrganizationFactory(sites=[self.site])

        self.my_course_overviews = [
            CourseOverviewFactory() for i in range(0,4)
        ]

        for co in self.my_course_overviews:
            OrganizationCourseFactory(organization=self.my_site_org, course_id=str(co.id))

        # Set up users and enrollments for 'my site'
        self.my_site_users = [UserFactory() for i in range(3)]
        for user in self.my_site_users:
            UserOrganizationMappingFactory(user=user,
                                           organization=self.my_site_org)

        # Create a mix of enrollments:
        # one learner in one course, same for the other, then two learners in
        # the same course, and keep one course w/out learners
        self.my_enrollments = [
            CourseEnrollmentFactory(course=self.my_course_overviews[0],
                                    user=self.my_site_users[0]),
            CourseEnrollmentFactory(course=self.my_course_overviews[1],
                                    user=self.my_site_users[1]),
            CourseEnrollmentFactory(course=self.my_course_overviews[2],
                                    user=self.my_site_users[0]),
            CourseEnrollmentFactory(course=self.my_course_overviews[2],
                                    user=self.my_site_users[1]),
        ]

        self.caller = UserFactory()
        UserOrganizationMappingFactory(user=self.caller,
                                       organization=self.my_site_org,
                                       is_amc_admin=True)
        self.my_site_users.append(self.caller)


    def test_get_valid_learner(self):
        user = self.my_site_users[0]
        request_path = self.request_path + '?username={}'.format(user.username)
        request = APIRequestFactory().get(self.request_path)
        force_authenticate(request, user=self.caller)
        view = self.view_class.as_view()
        response = view(request)

        assert response.status_code == 200

    def test_get_invalid_learner(self):
        request_path = self.request_path + '?username={}'.format('anyuser')
        request = APIRequestFactory().get(self.request_path)
        force_authenticate(request, user=self.caller)
        view = self.view_class.as_view()
        response = view(request)

        assert response.status_code == 400
