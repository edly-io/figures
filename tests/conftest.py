from __future__ import absolute_import

from datetime import datetime, date
import pytest
from django.utils.timezone import utc
from six.moves import range
from tests.helpers import organizations_support_sites

from openedx.features.edly.tests.factories import (
    EdlySubOrganizationFactory,
    EdlyUserProfileFactory,
)

from tests.factories import (
    CourseEnrollmentFactory,
    CourseOverviewFactory,
    OrganizationFactory,
    OrganizationCourseFactory,
    StudentModuleFactory,
    SiteFactory,
    UserFactory,
)

if organizations_support_sites():
    from tests.factories import UserOrganizationMappingFactory

    def map_users_to_org(org, users):
        [UserOrganizationMappingFactory(user=user,
                                        organization=org) for user in users]


@pytest.fixture
@pytest.mark.django_db
def sm_test_data(db):
    """
    WIP StudentModule test data to test MAU
    """
    date_today = date.today()
    year_for = date_today.year
    month_for = date_today.month
    created_date = datetime(year_for, month_for, 1).replace(tzinfo=utc)
    modified_date = datetime(year_for, month_for, 10).replace(tzinfo=utc)
    course_overviews = [CourseOverviewFactory() for i in range(3)]
    site = SiteFactory()
    org = OrganizationFactory()
    edly_sub_organization = EdlySubOrganizationFactory(
        lms_site=site,
        edx_organization=org
    )

    sm = []
    for co in course_overviews:
        user = UserFactory()
        EdlyUserProfileFactory(
            user=user,
            edly_sub_organizations=[edly_sub_organization]
        )
        OrganizationCourseFactory(organization=org, course_id=str(co.id))
        sm.append(
            StudentModuleFactory(
                course_id=co.id,
                created=created_date,
                modified=modified_date,
                student=user,
            )
        )

    if organizations_support_sites():
        org = OrganizationFactory(sites=[site])
        for co in course_overviews:
            OrganizationCourseFactory(organization=org, course_id=str(co.id))
        for rec in sm:
            UserOrganizationMappingFactory(user=rec.student, organization=org)
    else:
        org = OrganizationFactory()

    return dict(site=site,
                organization=org,
                course_overviews=course_overviews,
                student_modules=sm,
                year_for=year_for,
                month_for=month_for)


@pytest.mark.django_db
def make_site_data(num_users=3, num_courses=2):

    site = SiteFactory()
    if organizations_support_sites():
        org = OrganizationFactory(sites=[site])
    else:
        org = OrganizationFactory()

    edly_sub_org = EdlySubOrganizationFactory(lms_site=site, edx_organization=org)
    courses = [CourseOverviewFactory() for i in range(num_courses)]
    users = [UserFactory() for i in range(num_users)]
    enrollments = []

    users = [UserFactory(edly_profile__edly_sub_organizations=[edly_sub_org]) for i in range(num_users)]

    enrollments = []
    for i, user in enumerate(users):
        # Create increasing number of enrollments for each user, maximum to one less
        # than the number of courses
        for j in range(i):
            enrollments.append(
                CourseEnrollmentFactory(course=courses[j-1], user=user)
            )

    for course in courses:
        OrganizationCourseFactory(organization=org,
                                    course_id=str(course.id))

    if organizations_support_sites():
        # Set up user mappings
        map_users_to_org(org, users)

    return dict(
        site=site,
        org=org,
        courses=courses,
        users=users,
        enrollments=enrollments,
    )


@pytest.fixture
@pytest.mark.django_db
def lm_test_data(db, settings):
    """Learner Metrics Test Data

    user0 not enrolled in any courses
    user1 enrolled in 1 course
    user2 enrolled in 2 courses

    """
    if organizations_support_sites():
        settings.FEATURES['FIGURES_IS_MULTISITE'] = True

    our_site_data = make_site_data()
    other_site_data = make_site_data()
    return dict(us=our_site_data, them=other_site_data)
