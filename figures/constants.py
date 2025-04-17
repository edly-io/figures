"""
Constant variables for figures app.
"""
from datetime import datetime


LEARNERS_OVERVIEW_REPORT = 'learners_overview_report'
PDF_COPYRIGHT_TEXT = '© Edly {}. All rights reserved.'.format(datetime.today().year)
PDF_EMAIL_BODY = 'The learners overview report for your platform'
PDF_NOTE = "*If a learner is converted to a staff user, they will no longer be counted as a learner. However, their \
learner history will still be included in calculation of course enrollments and completions."
PDF_EMAIL_SUBJECT = 'Learners Overview Report'
TRIAL_EXPIRED = 'trial expired'
DEACTIVATED = 'deactivated'
EDLY_SAAS = 'edly_saas'
