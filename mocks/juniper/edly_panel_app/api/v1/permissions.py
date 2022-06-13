
"""
Permissions for Edly Panel API.
"""
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import BasePermission

from lms.djangoapps.commerce.utils import is_account_activation_requirement_disabled
from openedx.features.edly.utils import user_has_edly_organization_access
from student.models import User
from edly_panel_app.api.v1.constants import EDLY_PANEL_WORKER_USER


class CanAccessEdlyPanel(BasePermission):

    def has_permission(self, request, view):
        is_edly_panel_user = request.user.groups.filter(
            name__in=[settings.EDLY_PANEL_USERS_GROUP, settings.EDLY_INSIGHTS_GROUP, settings.EDLY_PANEL_ADMIN_USERS_GROUP]
        ).exists()
        has_edly_panel_access = user_has_edly_organization_access(request) and (request.user.is_superuser or is_edly_panel_user)
        return has_edly_panel_access


class AdminAccessEdlyPanel(BasePermission):

    def has_permission(self, request, view):
        is_edly_panel_admin_user = request.user.groups.filter(
            name=settings.EDLY_PANEL_ADMIN_USERS_GROUP
        ).exists()
        has_edly_panel_access = user_has_edly_organization_access(request) and (request.user.is_superuser or is_edly_panel_admin_user)
        return has_edly_panel_access


class IsAuthenticatedOrActivationOverridden(BasePermission):
    """ Considers the account activation override switch when determining the authentication status of the user """

    def has_permission(self, request, view):
        if not request.user.is_authenticated and is_account_activation_requirement_disabled():
            try:
                request.user = User.objects.get(id=request.session.get('_auth_user_id'))
            except ObjectDoesNotExist:
                pass
        return request.user.is_authenticated


class CanAccessSiteCreation(BasePermission):
    """
    Checks if a user has the access to create and update methods for sites.
    """

    def has_permission(self, request, view):
        """
        Checks for user's permission for current site.
        """
        return request.user.is_staff or request.user.username == EDLY_PANEL_WORKER_USER
