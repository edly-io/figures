"""
Test Figures Learner Detail PDF View.
"""


from __future__ import absolute_import
import pytest
from six.moves import range
from unittest.mock import MagicMock, patch

from django.test import override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

import figures.views as figures_views
from figures.views import LearnerDetailsPDFViewSet

from tests.factories import UserFactory
from tests.helpers import organizations_support_sites
from tests.views.base import BaseViewTest


@pytest.mark.skipif(organizations_support_sites(),
                    reason='Organizations support sites')
@pytest.mark.django_db
class TestLearnerDetailsPDFViewSet(BaseViewTest):
    """
    Test "LearnerDetailsPDFViewSet" view class.
    """

    request_path = 'api/users/pdf/'
    view_class = LearnerDetailsPDFViewSet
    @pytest.fixture(autouse=True)
    def setup(self, db, settings):
        super(TestLearnerDetailsPDFViewSet, self).setup(db)
        self.users = [UserFactory(edly_multisite_user__sub_org=self.edly_org) for i in range(3)]
        self.users.append(self.staff_user)


    @patch.object(
        figures_views,
        'get_current_site_configuration',
        MagicMock(return_value=MagicMock(get_value=MagicMock(return_value={
            'BRANDING': {'logo': 'test-logo-url', },
            'PLATFORM_NAME': 'test-platform',
            'email_from_address': 'test@example.com',
        })))
    )
    @patch.object(figures_views.LearnerDetailsPDFViewSet.send_learners_data_pdf,
        'delay',
        MagicMock(return_value=True)
    )
    @override_settings(PLATFORM_NAME='Test Platform')
    def test_get_learner_pdf(self):
        """Tests retrieving a list of users with abbreviated details

        The fields in each returned record are identified by
            `figures.serializers.UserIndexSerializer`

        """
        request = APIRequestFactory().get(self.request_path)
        request.site = self.site
        force_authenticate(request, user=self.staff_user)
        view = self.view_class.as_view({'get': 'list'})
        response = view(request)

        assert response.status_code == 200
        assert response.data == 'Learners overview email sent successfully'
