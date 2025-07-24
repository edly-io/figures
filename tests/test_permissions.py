"""Test the permission classes we define in Figures
"""

from __future__ import absolute_import
import pytest

from django.conf import settings
from django.contrib.auth import get_user_model
import django.contrib.sites.shortcuts
from rest_framework.test import APIRequestFactory

from openedx.features.edly.tests.factories import (
    EdlyMultiSiteAccessFactory,
    EdlySubOrganizationFactory,
)

import figures.permissions
import figures.helpers
from student.tests.factories import GroupFactory, UserFactory

from tests.factories import SiteFactory

# For multisite testing
try:
    from tests.factories import UserOrganizationMappingFactory
except ImportError:
    pass

from tests.helpers import organizations_support_sites
from tests.views.helpers import create_test_users


@pytest.mark.skipif(
    not organizations_support_sites(),
    reason='Organizations support sites'
)
@pytest.mark.django_db
class TestPermissionsForStandaloneMode(object):

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.site = SiteFactory()
        self.edly_org = EdlySubOrganizationFactory(lms_site=self.site)
        self.callers = create_test_users(self.edly_org)

    @pytest.mark.parametrize('username, allow', [
        ('regular_user', False),
        ('staff_user', True),
        ('super_user', True),
        ('superstaff_user', True),
    ])
    def test_is_site_admin_user(self, username, allow):
        """Tests a set of users against the IsSiteAdminUser permission class
        """
        request = APIRequestFactory().get('/')
        request.user = get_user_model().objects.get(username=username)
        permission = figures.permissions.IsSiteAdminUser().has_permission(request, None)
        assert permission == allow, 'username: "{username}"'.format(username=username)

        # verify that inactive users are denied permission
        request.user.is_active = False
        permission = figures.permissions.IsSiteAdminUser().has_permission(request, None)
        assert permission == False, 'username: "{username}"'.format(username=username)

    @pytest.mark.parametrize('username, allow', [
        ('regular_user', False),
        ('staff_user', True),
        ('super_user', True),
        ('superstaff_user', True),
    ])
    def test_is_staff_user_on_default_site(self, username, allow):
        """Tests a set of users against the IsStaffUserOnDefaultSite permission class
        """
        request = APIRequestFactory().get('/')
        request.user = get_user_model().objects.get(username=username)
        permission = figures.permissions.IsStaffUserOnDefaultSite().has_permission(request, None)
        assert permission == allow, 'username: "{username}"'.format(username=username)

        # verify that inactive users are denied permission
        request.user.is_active = False
        permission = figures.permissions.IsStaffUserOnDefaultSite().has_permission(request, None)
        assert permission == False, 'username: "{username}"'.format(username=username)


@pytest.mark.django_db
class TestSiteAdminPermissionsForMultisiteMode(object):

    @pytest.fixture(autouse=True)
    def setup(self, db):
        self.site = SiteFactory()
        self.edly_sub_organization = EdlySubOrganizationFactory(lms_site=self.site)
        self.edly_admin_group = GroupFactory(name=settings.EDLY_PANEL_ADMIN_USERS_GROUP)
        self.edly_user_group = GroupFactory(name=settings.EDLY_PANEL_USERS_GROUP)

        edly_panel_admin = UserFactory(
            username='edly_panel_admin',
            edly_multisite_user__sub_org=self.edly_sub_organization
        )
        edly_panel_admin.edly_multisite_user.get(
            sub_org=self.edly_sub_organization
        ).groups.add(self.edly_admin_group)

        edly_panel_user = UserFactory(
            username='edly_panel_user',
            edly_multisite_user__sub_org=self.edly_sub_organization,
        )
        edly_panel_user.edly_multisite_user.get(
            sub_org=self.edly_sub_organization
        ).groups.add(self.edly_user_group)

        self.callers = [
            UserFactory(
                username='alpha_nonadmin',
                edly_multisite_user__sub_org=self.edly_sub_organization
            ),
            edly_panel_admin,
            edly_panel_user,
            UserFactory(
                username='nosite_staff',
                edly_multisite_user__sub_org=self.edly_sub_organization
            ),
        ]
        self.callers += create_test_users(self.edly_sub_organization)
        self.features = {'FIGURES_IS_MULTISITE': True}

    @pytest.mark.parametrize('username, allow', [
        ('regular_user', False),
        ('staff_user', True),
        ('super_user', True),
        ('superstaff_user', True),
        ('alpha_nonadmin', False),
        ('edly_panel_admin', True),
        ('edly_panel_user', True),
        ('nosite_staff', False),
        ])
    def test_is_site_admin_user(self, monkeypatch, settings, username, allow):

        def test_site(request):
            return self.site

        request = APIRequestFactory().get('/')
        request.META['HTTP_HOST'] = self.site.domain
        request.user = get_user_model().objects.get(username=username)
        request.site = self.site
        monkeypatch.setattr(django.contrib.sites.shortcuts, 'get_current_site', test_site)
        settings.FEATURES['FIGURES_IS_MULTISITE'] = True
        assert figures.helpers.is_multisite()
        permission = figures.permissions.IsSiteAdminUser().has_permission(
            request, None)
        assert permission == allow, 'User "{username}" should have access'.format(
            username=username)

        # verify that inactive users are denied permission
        request.user.is_active = False
        permission = figures.permissions.IsSiteAdminUser().has_permission(
            request, None)
        assert permission == False, 'username: "{username}"'.format(
            username=username)

    @pytest.mark.parametrize('username, allow', [
        ('regular_user', False),
        ('staff_user', True),
        ('super_user', True),
        ('superstaff_user', True),
        ('alpha_nonadmin', False),
        ('edly_panel_admin', True),
        ('edly_panel_user', True),
        ('nosite_staff', False),
        ])
    def test_multiple_user_orgs(self, monkeypatch, settings, username, allow):
        """
        We updated `figures.permissions` so that a user can belong to multiple
        organizations
        """
        def test_site(request):
            return self.site

        request = APIRequestFactory().get('/')
        request.META['HTTP_HOST'] = self.site.domain
        request.user = get_user_model().objects.get(username=username)
        request.site = self.site
        monkeypatch.setattr(django.contrib.sites.shortcuts, 'get_current_site', test_site)
        settings.FEATURES['FIGURES_IS_MULTISITE'] = True
        assert figures.helpers.is_multisite()
        org2 = EdlySubOrganizationFactory()
        param_user = EdlyMultiSiteAccessFactory(
            user=request.user,
            sub_org=org2,
        )

        permission = figures.permissions.IsSiteAdminUser().has_permission(request, None)
        assert permission == allow, 'User "{username}" should have access'.format(
            username=username)

    @pytest.mark.parametrize('username, allow', [
        ('regular_user', False),
        ('staff_user', True),
        ('super_user', True),
        ('superstaff_user', True),
    ])
    def test_is_staff_user_on_default_site(self, username, allow):
        """Tests a set of users against the IsStaffUserOnDefaultSite permission class
        """

        request = APIRequestFactory().get('/')
        request.user = get_user_model().objects.get(username=username)
        request.site = self.site
        permission = figures.permissions.IsStaffUserOnDefaultSite().has_permission(request, None)
        assert permission == allow, 'username: "{username}"'.format(username=username)

        # verify that inactive users are denied permission
        request.user.is_active = False
        permission = figures.permissions.IsStaffUserOnDefaultSite().has_permission(request, None)
        assert permission == False, 'username: "{username}"'.format(username=username)
