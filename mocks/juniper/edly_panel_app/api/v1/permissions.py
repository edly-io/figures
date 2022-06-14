
"""
Permissions for Edly Panel API.
"""
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.permissions import BasePermission

from openedx.features.edly.utils import user_has_edly_organization_access


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
