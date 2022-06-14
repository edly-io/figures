"""
Constants for Edly Panel API.
"""
from django.utils.translation import ugettext as _


BLOCK_TYPES_TO_FILTER = ['course', 'chapter', 'sequential', 'vertical', 'discussion', 'openassessment']
CORE_BLOCK_TYPES = ['html', 'video', 'problem']

EDLY_PANEL_WORKER_USER = 'edly_panel_worker'

ERROR_MESSAGES = {
    'INVALID_TYPE': _('Please provide valid type in the query params.'),
    'INVALID_REPORT_REQUEST': _('Please provide valid report request type in the query params.'),
    'INVALID_QUARTER_OR_YEAR': _('Please provide valid quarter and year'),
    'INVALID_START_AND_END_DATE': _('Please provide valid start and end date.'),
    'INVALID_YEAR': _('Please provide valid year.'),
    'INVALID_DATE_RANGE': _('Please specify the valid date ranges.'),
    'USERS_NOT_FOUND': _('No user record found.'),
    'USER_STATUS_SUCCESS': _('Users status update completed.'),
    'USER_STATUS_FAILURE': _('Users status update failed.'),
    'USER_SELF_STATUS_UPDATE_FAILURE': _('User cannot change its status.'),
    'SITE_THEME_DIRECTORY_MISSING': _('Site theme directory not provided.'),
    'SITE_THEME_UPDATE_SUCCESS': _('Site theme update completed.'),
    'SITE_THEME_UPDATE_FAILURE': _('Site theme update failed.'),
    'CLIENT_SITES_SETUP_SUCCESS': _('Client sites setup successful.'),
    'CLIENT_SITES_SETUP_FAILURE': _('Client sites setup failed.'),
}
