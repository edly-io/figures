"""Utilities to assist with commerce tasks."""

import waffle
from django.conf import settings
from django.contrib.auth import get_user_model
from course_modes.models import CourseMode
from openedx.core.djangoapps.commerce.utils import ecommerce_api_client, is_commerce_service_configured
from openedx.core.djangoapps.site_configuration import helpers as configuration_helpers
from openedx.core.djangoapps.theming import helpers as theming_helpers
from common.djangoapps.student.models  import CourseEnrollment

from .models import CommerceConfiguration

log = logging.getLogger(__name__)


def is_account_activation_requirement_disabled():
    """
    Checks to see if the django-waffle switch for disabling the account activation requirement is active

    Returns:
        Boolean value representing switch status
    """
    switch_name = configuration_helpers.get_value(
        'DISABLE_ACCOUNT_ACTIVATION_REQUIREMENT_SWITCH',
        settings.DISABLE_ACCOUNT_ACTIVATION_REQUIREMENT_SWITCH
    )
    return waffle.switch_is_active(switch_name)
