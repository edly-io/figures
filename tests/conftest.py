from datetime import datetime
import pytest
from django.utils.timezone import utc

from openedx.features.edly.tests.factories import (
    EdlySubOrganizationFactory,
    EdlyUserProfileFactory,
)

from tests.factories import (
    CourseOverviewFactory,
    OrganizationFactory,
    OrganizationCourseFactory,
    StudentModuleFactory,
    SiteFactory,
    UserFactory,
)

from tests.helpers import organizations_support_sites

if organizations_support_sites():
    from tests.factories import UserOrganizationMappingFactory


@pytest.fixture
@pytest.mark.django_db
def sm_test_data(db):
    """
    WIP StudentModule test data to test MAU
    """
    year_for = 2019
    month_for = 10
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
        sm += [StudentModuleFactory(course_id=co.id,
                                    created=created_date,
                                    modified=modified_date,
                                    student=user,
                                    ) for co in course_overviews]

    if organizations_support_sites():
        org = OrganizationFactory(sites=[site])
        for co in course_overviews:
            OrganizationCourseFactory(organization=org, course_id=str(co.id))
        for rec in sm:
            UserOrganizationMappingFactory(user=rec.student, organization=org)

    return dict(
        site=site,
        organization=org,
        course_overviews=course_overviews,
        student_modules=sm,
        year_for=year_for,
        month_for=month_for
    )
