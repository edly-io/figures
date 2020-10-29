"""
Tests Figures multisite/standalone site support handlers

The multisite tests require Appsembler's fork of edx-organizations installed

The test classes in this module handle the following conditions
* Standalone mode (run regardless if organizations supports sites)
* Multisite mode when organizations supports sites
* Multisite mode when organizations does not support sites

Current structure
=================

We're structuring the test classes around the data setup required so that we're
minimizing extra data set up:

* Single test class for standalone mode
* Multiple test classes for multisite mode

TODOs: Create base test class for the multisite setup (and teardown if needed)
or restructure into fixtures and standalone test functions, depending on how
figures.sites evolves
"""

import figures.helpers
import figures.sites
import mock
import organizations
import pytest
from courseware.tests.factories import StudentModuleFactory
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from openedx.core.djangoapps.content.course_overviews.models import (
    CourseOverview,
)
from openedx.features.edly.tests.factories import (
    EdlySubOrganizationFactory,
    EdlyUserProfileFactory,
)
from organizations.tests.factories import OrganizationFactory
from tests.factories import (
    CourseEnrollmentFactory,
    CourseOverviewFactory,
    OrganizationCourseFactory,
    SiteFactory,
    UserFactory,
)
from tests.helpers import organizations_support_sites

if organizations_support_sites():
    from tests.factories import UserOrganizationMappingFactory


@pytest.mark.django_db
class TestHandlersForStandaloneMode(object):
    """
    Tests figures.sites site handling functions in standalone site mode
    These tests should pass regardless of whether or not and if so how
    organizations supports organization-site mapping
    """

    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        settings.FEATURES['FIGURES_IS_MULTISITE'] = False
        is_multisite = figures.helpers.is_multisite()
        assert not is_multisite

        self.default_site = Site.objects.get()
        self.features = {'FIGURES_IS_MULTISITE': False}
        self.site = Site.objects.first()
        self.organization = OrganizationFactory()
        self.edly_sub_organization = EdlySubOrganizationFactory(
            lms_site=self.site,
            edx_organization=self.organization
        )

        assert Site.objects.count() == 2

    def test_get_site_for_course(self):
        """

        """
        with mock.patch('figures.helpers.settings.FEATURES', self.features):
            co = CourseOverviewFactory()
            site = figures.sites.get_site_for_course(str(co.id))
            assert site == Site.objects.first()

    @pytest.mark.parametrize('course_count', [0, 1, 2])
    def test_get_course_keys_for_site(self, course_count):
        sites = Site.objects.all()
        assert sites.count() == 1
        with mock.patch('figures.helpers.settings.FEATURES', self.features):
            course_overviews = [CourseOverviewFactory() for i in range(course_count)]
            course_keys = figures.sites.get_course_keys_for_site(sites[0])
            expected_ids = [str(co.id) for co in course_overviews]
            assert set([str(key) for key in course_keys]) == set(expected_ids)

    def test_get_courses_for_site(self):
        with mock.patch('figures.helpers.settings.FEATURES', self.features):
            courses = figures.sites.get_courses_for_site(self.site)
            assert set(courses) == set(CourseOverview.objects.all())

    def test_get_user_ids_for_site(self):
        expected_users = [UserFactory() for i in range(3)]
        with mock.patch('figures.helpers.settings.FEATURES', self.features):
            user_ids = figures.sites.get_user_ids_for_site(self.site)
            assert set(user_ids) == set([user.id for user in expected_users])

    def test_get_users_for_site(self):
        expected_users = [UserFactory() for i in range(3)]
        with mock.patch('figures.helpers.settings.FEATURES', self.features):
            users = figures.sites.get_users_for_site(self.site)
            assert set([user.id for user in users]) == set(
                [user.id for user in expected_users])

    def test_get_course_enrollments_for_site(self):
        expected_ce = [CourseEnrollmentFactory() for i in range(3)]
        with mock.patch('figures.helpers.settings.FEATURES', self.features):
            course_enrollments = figures.sites.get_course_enrollments_for_site(self.site)
            assert set([ce.id for ce in course_enrollments]) == set(
                [ce.id for ce in expected_ce])


@pytest.mark.django_db
class TestHandlersForMultisiteMode(object):
    """
    Tests figures.sites site handling functions in multisite mode

    Assumptions:
    * We're using Appsembler's fork of `edx-organizations` for the multisite
      tests

    """
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        settings.FEATURES['FIGURES_IS_MULTISITE'] = True
        is_multisite = figures.helpers.is_multisite()
        assert is_multisite
        assert Site.objects.count() == 1

        self.site = SiteFactory(domain='foo.test')
        self.organization = OrganizationFactory()
        self.edly_sub_organization = EdlySubOrganizationFactory(
            lms_site=self.site,
            edx_organization=self.organization
        )
        # Now verify that "EdlySubOrganizationFactory" has created a studio site along with the lms site
        assert Site.objects.count() == 3
        self.features = {'FIGURES_IS_MULTISITE': True}

    def test_get_site_for_courses(self):
        """
        Can we get the site for a given course?

        We shouldn't care what the other site is. For reference, it is the
        default site with 'example.com' for both the domain and name fields
        """
        # We want to move the patch to the class level if possible

        co = CourseOverviewFactory()
        OrganizationCourseFactory(organization=self.organization,
                                  course_id=str(co.id))
        site = figures.sites.get_site_for_course(str(co.id))
        assert site == self.site

    def test_get_site_for_course_not_in_site(self):
        """
        We create a course but don't add the course to OrganizationCourse
        We expect that a site cannot be found
        """
        co = CourseOverviewFactory()
        site = figures.sites.get_site_for_course(str(co.id))
        assert not site

    @pytest.mark.parametrize('course_id', ['', None])
    def test_get_site_for_non_existing_course(self, course_id):
        """
        We expect no site returned for None for the course
        """
        site = figures.sites.get_site_for_course(course_id)
        assert not site

    @pytest.mark.parametrize('course_count', [0, 1, 2])
    def test_get_course_keys_for_site(self, course_count):

        course_overviews = [CourseOverviewFactory() for i in range(course_count)]
        for co in course_overviews:
            OrganizationCourseFactory(organization=self.organization,
                                      course_id=str(co.id))
        course_keys = figures.sites.get_course_keys_for_site(self.site)
        expected_ids = [str(co.id) for co in course_overviews]
        assert set([str(key) for key in course_keys]) == set(expected_ids)

    @pytest.mark.parametrize('course_count', [0, 1, 2])
    def test_get_courses_for_site(self, course_count):
        course_overviews = [CourseOverviewFactory() for i in range(course_count)]
        for co in course_overviews:
            OrganizationCourseFactory(organization=self.organization,
                                      course_id=str(co.id))
        courses = figures.sites.get_courses_for_site(self.site)
        expected_ids = [str(co.id) for co in course_overviews]
        assert set([str(co.id) for co in courses]) == set(expected_ids)

    @pytest.mark.parametrize('ce_count', [0, 1, 2])
    def test_get_course_enrollments_for_site(self, ce_count):

        course_overview = CourseOverviewFactory()
        OrganizationCourseFactory(organization=self.organization,
                                  course_id=str(course_overview.id))
        expected_ce = [CourseEnrollmentFactory(
            course_id=course_overview.id) for i in range(ce_count)]
        course_enrollments = figures.sites.get_course_enrollments_for_site(self.site)
        assert set([ce.id for ce in course_enrollments]) == set(
            [ce.id for ce in expected_ce])

    def test_get_student_modules_for_course_in_site(self):
        course_overviews = [CourseOverviewFactory() for i in range(3)]

        for co in course_overviews[:-1]:
            OrganizationCourseFactory(organization=self.organization,
                                      course_id=str(co.id))

        assert get_user_model().objects.count() == 0
        user = UserFactory()
        EdlyUserProfileFactory(
            user=user,
            edly_sub_organizations=[self.edly_sub_organization]
        )

        student_module_count = 1
        student_module_expected = [StudentModuleFactory(course_id=course_overviews[0].id,
                                                        student=user
                                                        ) for i in range(student_module_count)]

        # StudentModule for other course
        StudentModuleFactory(course_id=course_overviews[1].id)

        # StudentModule for course not in organization
        StudentModuleFactory(course_id=course_overviews[2].id)

        student_module = figures.sites.get_student_modules_for_course_in_site(
            site=self.site, course_id=course_overviews[0].id)

        assert student_module.count() == len(student_module_expected)

        # test that course id as a string works
        student_module = figures.sites.get_student_modules_for_course_in_site(
            site=self.site, course_id=str(course_overviews[0].id))

        assert student_module.count() == len(student_module_expected)

        student_module = figures.sites.get_student_modules_for_site(site=self.site)
        assert student_module.count() == len(student_module_expected) + 1


@pytest.mark.django_db
class TestUserHandlersForMultisiteMode(object):
    """
    Tests figures.sites site handling functions in multisite mode

    Test does not yet provide multiple sites/orgs to test leakiness

    Assumptions:
    * We're using Appsembler's fork of `edx-organizations` for the multisite
      tests

    """
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        settings.FEATURES['FIGURES_IS_MULTISITE'] = True
        is_multisite = figures.helpers.is_multisite()
        assert is_multisite
        assert Site.objects.count() == 1

        self.site = SiteFactory(domain='foo.test')
        self.organization = OrganizationFactory()
        self.edly_sub_organization = EdlySubOrganizationFactory(
            lms_site=self.site,
            edx_organization=self.organization
        )
        assert get_user_model().objects.count() == 0
        self.users = [UserFactory() for i in range(3)]
        for user in self.users:
            EdlyUserProfileFactory(
                user=user,
                edly_sub_organizations=[self.edly_sub_organization]
            )
        # Now verify that "EdlySubOrganizationFactory" has created a studio site along with the lms site
        assert Site.objects.count() == 3
        self.features = {'FIGURES_IS_MULTISITE': True}

    def test_get_user_ids_for_site(self):
        expected_users = self.users
        with mock.patch('figures.helpers.settings.FEATURES', self.features):
            user_ids = figures.sites.get_user_ids_for_site(self.site)
            assert set(user_ids) == set([user.id for user in expected_users])

    def test_get_users_for_site(self):
        expected_users = self.users
        with mock.patch('figures.helpers.settings.FEATURES', self.features):
            users = figures.sites.get_users_for_site(self.site)
            assert set([user.id for user in users]) == set(
                [user.id for user in expected_users])


@pytest.mark.skipif(organizations_support_sites(),
                    reason='Organizations package does not support sites')
@pytest.mark.django_db
class TestOrganizationsLacksSiteSupport(object):
    """
    This class tests how the figures.sites module handles multisite mode when
    organizations models do not associate organizations with sites

    TODO: Improve test coverage
    """
    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.site = SiteFactory(domain='foo.test')
        assert Site.objects.count() == 2
        self.features = {'FIGURES_IS_MULTISITE': True}

    def test_create_organiztion_with_site(self):
        """
        Make sure that we cannot associate an organization with a site

        Another way to check is if organizations.models.Organization has the
        'sites' field via `hasattr`
        """
        with pytest.raises(TypeError):
            OrganizationFactory(sites=[self.site])

    def test_org_course_missing_sites_field(self):
        with mock.patch('figures.helpers.settings.FEATURES', self.features):
            # orgs = organizations.models.Organization.objects.all()
            # assert orgs
            msg = 'Not supposed to have "sites" attribute'
            assert not hasattr(
                organizations.models.Organization, 'sites'), msg


@pytest.mark.django_db
def test_site_iterator():
    sites = [SiteFactory() for i in range(5)]
    collected_ids = []
    for site_id in figures.sites.site_id_iterator(sites):
        collected_ids.append(site_id)

    assert set(collected_ids) == set([site.id for site in sites])
