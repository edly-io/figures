"""
Model used by Video module for Branding configuration.

Includes:
    BrandingInfoConfig: A ConfigurationModel for managing how Video Module will
        use Branding.
"""
from config_models.models import ConfigurationModel


class BrandingApiConfig(ConfigurationModel):
    """Configure Branding api's

    Enable or disable api's functionality.
    When this flag is disabled, the api will return 404.

    When the flag is enabled, the api will returns the valid reponse.

    .. no_pii:
    """

    class Meta(ConfigurationModel.Meta):
        app_label = "branding"
