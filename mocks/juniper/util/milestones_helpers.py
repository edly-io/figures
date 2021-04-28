"""
Utility library for working with the edx-milestones app
"""


from django.conf import settings

def is_entrance_exams_enabled():
    """
    Checks to see if the Entrance Exams feature is enabled
    Use this operation instead of checking the feature flag all over the place
    """
    return settings.FEATURES.get('ENTRANCE_EXAMS')
