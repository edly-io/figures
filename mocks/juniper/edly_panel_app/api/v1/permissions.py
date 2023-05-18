
"""
Permissions for Edly Panel API.
"""
from django.conf import settings
from rest_framework.permissions import BasePermission

from edly_panel_app.api.v1.constants import EDLY_PANEL_WORKER_USER
from openedx.features.edly.utils import get_edly_sub_org_from_request, user_has_edly_organization_access


class CanAccessEdlyPanel(BasePermission):

    def has_permission(self, request, view):
        sub_org = get_edly_sub_org_from_request(request)
        is_edly_access_user = request.user.edly_multisite_user.filter(
            sub_org=sub_org,
            groups__name__in=[settings.EDLY_PANEL_USERS_GROUP, settings.EDLY_INSIGHTS_GROUP, settings.EDLY_PANEL_ADMIN_USERS_GROUP]
        ).exists()
        has_edly_user_access = user_has_edly_organization_access(request) and (request.user.is_superuser or is_edly_access_user)
        return has_edly_user_access


class AdminAccessEdlyPanel(BasePermission):

    def has_permission(self, request, view):
        sub_org = get_edly_sub_org_from_request(request)
        is_edly_access_user = request.user.edly_multisite_user.filter(
            sub_org=sub_org,
            groups__name=settings.EDLY_PANEL_ADMIN_USERS_GROUP
        ).exists()
        has_edly_user_access = user_has_edly_organization_access(request) and (request.user.is_superuser or is_edly_access_user)
        return has_edly_user_access or request.user.username == EDLY_PANEL_WORKER_USER
