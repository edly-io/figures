from __future__ import absolute_import
import pytest
from unittest.mock import MagicMock, patch

from django.test import override_settings
from edly_panel_app.api.v1 import helpers as edly_helpers
from rest_framework.test import (
    APIRequestFactory,
    force_authenticate,
)

import figures
from figures.edly_views.edly_reports import LearnersCSV
from tests.views.base import BaseViewTest
from tests.factories import UserFactory
from tests.helpers import organizations_support_sites


@pytest.mark.skipif(organizations_support_sites(),
                    reason='Organizations support sites')
@pytest.mark.django_db
class TestLearnerDetailCSVView(BaseViewTest):
    """Test edly_views/LearnerCSV View
    """

    request_path = 'api/edly/learner-report/'
    view_class = LearnersCSV

    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        super(TestLearnerDetailCSVView, self).setup(db)
        self.users = [UserFactory(edly_multisite_user__sub_org=self.edly_org) for i in range(3)]
        self.users.append(self.staff_user)

    @patch.object(
        figures.edly_views.edly_reports,
        'get_current_site_configuration',
        MagicMock(return_value=MagicMock(get_value=MagicMock(return_value={
            'PLATFORM_NAME': 'test-platform',
            'email_from_address': 'test@example.com',
        })))
    )
    @patch.object(
        figures.edly_views.edly_reports.LearnersCSV,
        '_get_learner_analytics',
        MagicMock(return_value={
            "previous": None, "total_pages": 1, "count": 1, "next": None, "current_page": 1,
            "results": [{
                "email": "alilaila393+2nd@gmail.com", "courses": [{
                    "course_name": "course 102", "course_code": "CS102",
                    "course_id": "course-v1:edly+CS102+2022_t2",
                    "date_enrolled": "2022-06-07", "progress_data": {
                        "percent_grade": 0.0, "letter_grade": "", "course_progress": 0.0,
                        "course_progress_history": [], "passed_timestamp": None,
                        "course_progress_details": None, "total_progress_percent": 0.0,
                        "course_completed": False
                    }, "enrollment_id": 12
                }, {
                    "course_name": "tester", "course_code": "edly101",
                    "course_id": "course-v1:edly+edly101+2022_t1",
                    "date_enrolled": "2022-06-07", "progress_data": {
                        "percent_grade": 0.0, "letter_grade": "", "course_progress": 0.0,
                        "course_progress_history": [], "passed_timestamp": None,
                        "course_progress_details": None, "total_progress_percent": 0.0,
                        "course_completed": False
                    }, "enrollment_id": 9
                }, {
                    "course_name": "New Tester", "course_code": "Testing101",
                    "course_id": "course-v1:edly+Testing101+2022_T1",
                    "date_enrolled": "2022-06-07", "progress_data": {
                        "percent_grade": 0.0, "letter_grade": "", "course_progress": 0.0,
                        "course_progress_history": [], "passed_timestamp": None,
                        "course_progress_details": None, "total_progress_percent": 0.0,
                        "course_completed": False
                    }, "enrollment_id": 10
                }], "gender": "", "is_active": True, "bio": None, "course_activity_date": None,
                "username": "ali", "registration_fields": {},
                "date_joined": "2022-06-07T10:55:22Z", "name": "ali", "level_of_education": "",
                "year_of_birth": None, "id": 15, "country": "", "last_login": "2022-06-07T10:55:22Z"
            }]
        })
    )
    @patch.object(edly_helpers.email_report_with_attachment,
        'delay',
        MagicMock(return_value=True)
    )
    @patch.object(LearnersCSV._prepare_learner_data,
        'delay',
        MagicMock(return_value=True)
    )
    def test_get_valid_learner(self):
        request = self.request_path + '?username={}'.format(self.users[0].username)
        request = APIRequestFactory().get(request)
        request.site = self.site
        force_authenticate(request, self.staff_user)
        view = self.view_class.as_view()
        response = view(request)

        assert response.status_code == 200
        assert response.data['message'] == 'Report is being sent. You will recieve an email shortly.'

    @patch.object(
        figures.edly_views.edly_reports.LearnersCSV,
        '_get_learner_analytics',
        MagicMock(return_value={
            "previous": None, "total_pages": 1, "count": 1, "next": None, "current_page": 1,
            "results": []
        })
    )
    @patch.object(
        figures.edly_views.edly_reports,
        'get_current_site_configuration',
        MagicMock(return_value=MagicMock(get_value=MagicMock(return_value={
            'PLATFORM_NAME': 'test-platform',
            'email_from_address': 'test@example.com',
        })))
    )
    def test_get_invalid_learner(self):
        request = self.request_path + '?username=anyone'
        request = APIRequestFactory().get(request)
        request.site = self.site
        force_authenticate(request, self.staff_user)
        view = self.view_class.as_view()
        response = view(request)

        assert response.status_code == 400
        assert response.data['message'] == 'No Learner Found with this username'

    def test_get_without_learner(self):
        request = self.request_path
        request = APIRequestFactory().get(request)
        request.site = self.site
        force_authenticate(request, self.staff_user)
        view = self.view_class.as_view()
        response = view(request)

        assert response.status_code == 400
        assert response.data['message'] == 'Username missing'
