"""
ConfigurationModel for the mobile_api djangoapp.
"""

from config_models.models import ConfigurationModel


class IgnoreMobileAvailableFlagConfig(ConfigurationModel):
    """
    Configuration for the mobile_available flag. Default is false.

    Enabling this configuration will cause the mobile_available flag check in
    access.py._is_descriptor_mobile_available to ignore the mobile_available
    flag.

    .. no_pii:
    """

    class Meta(object):
        app_label = "mobile_api"
