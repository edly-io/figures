import datetime

from dateutil.rrule import rrule, DAILY
import pytest

from django.contrib.sites.models import Site
from django.utils.timezone import utc

from figures.metrics import (
    get_last_month_site_metrics
)
from figures.helpers import (
    days_in_month
)
from openedx.features.edly.tests.factories import (
    EdlySubOrganizationFactory,
    EdlyUserProfileFactory,
)
from student.tests.factories import UserFactory
from tests.factories import (
    CourseOverviewFactory,
    SiteFactory,
    StudentModuleFactory,
)


def create_edly_sub_org_user(edly_sub_org):
    """
    Helper method to create 'EdlySubOrganization`'s User.
    """
    edly_user = UserFactory()
    edly_user_profile = EdlyUserProfileFactory(user=edly_user)
    edly_user_profile.edly_sub_organizations.add(edly_sub_org)
    return edly_user


@pytest.mark.django_db
class TestGetCurrentMonthSiteMetrics(object):
    """
    This test also exercises the time period getters used in
    figures.metrics.get_current_month_site_metrics
    """

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.site = SiteFactory()
        self.date_for = datetime.datetime.utcnow().date()
        self.start_date = datetime.date(year=self.date_for.year, month=self.date_for.month, day=1)
        self.end_date = datetime.date(
            year=self.date_for.year,
            month=self.date_for.month,
            day=days_in_month(self.date_for)
        )

        self.students_data = self.create_students_record(self.start_date, self.end_date)

    def create_students_record(self, start_date, end_date):
        student_modules = []
        edly_sub_org = EdlySubOrganizationFactory(lms_site=self.site)
        for dt in rrule(DAILY, dtstart=start_date, until=end_date):
            course_overview = CourseOverviewFactory()
            student_modules.append(StudentModuleFactory(
                student=create_edly_sub_org_user(edly_sub_org),
                course_id=course_overview.id,
                created=dt,
                modified=dt,
            ))

        return student_modules

    def test_get_last_month_site_metrics(self):
        expected_data = {
            'active_users': 0,
            'active_learners': 0,
            'site_courses': 0,
            'course_enrollments': 0,
            'registered_users': len(self.students_data),
            'new_users': 0,
            'new_learners': 0,
            'course_completions': 0
        }

        received_data = get_last_month_site_metrics(self.site)
        assert received_data == expected_data
