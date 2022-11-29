"""Helper functions to make data handling and conversions easier

# Figures 0.3.13 - Defining scope of this module
# Figures 0.4.x - Yep, this module is still handy and the scope hasn't exploded

The purpose of this module is to provide conveniece methods around commonly
executed statements. These convenience methods should serve as shorthand for
code we would repeatedly execute which don't yet have a module of their own.

The idea is that if there is not yet a module for some helper function, we put
it in here until we see a pattern. We then either identify a new module and
transplate these like functions out of this module into the new one. Or we
identify that functions in here actually should go in an existing module.

The purposes for this are:

1. Reduce development time cost by not having to stop and design (informally or
   formally) a new module or inspect all the existing modules to find an
   appropriate home. The second point is helpful for those not intimately
   familiar with the Figures codebase

2. Avoid premature optimization in building out new module functionality because
   we are adding a single method (Avoid the desire to fill this new module with
   more than the new functionality that serves our immediate needs)

3. Avoid over specificifity, which can results in an explosion of tiny modules
   that may be too specific in their context


## Background

Originally this module served as a variant of a 'utils' module, but with the
express purpose of providing convenience "helper" functions to help DRY (do not
repeat yourself) the code and make the code more readable

## What does not belong here?

* Most importantly, if you have to import from another figures module, it does
  not belong here!
* "Feature" functionality does not belong here
* Long functions do not belong here
* Code that communicates outside of Figures does not belong here. No database,
  filesystem, or network connectiviely functionality belongs here

This is not an exhaustive list. We'll grow it as needed.

An important point is that we should not expect this module to be a permanent
home for the functionality included. As we evolve Figures, we may find functions
here that have a stronger context with another module. For example, we've got
a decent set of date oriented functions that are candidatdes for a datetime and
date handling module.
"""

from __future__ import absolute_import
import calendar
import csv
import datetime
from dateutil import parser
from io import StringIO
import logging

from importlib import import_module
from django.conf import settings
from django.core.mail.message import EmailMultiAlternatives
from django.utils.timezone import utc
from django.template.loader import get_template
from fpdf import FPDF
from rest_framework import status
from rest_framework.response import Response

from dateutil.parser import parse as dateutil_parse
from dateutil.relativedelta import relativedelta

from opaque_keys.edx.keys import CourseKey
import six

from figures.constants import LEARNERS_OVERVIEW_REPORT, PDF_COPYRIGHT_TEXT, PDF_NOTE, PDF_EMAIL_SUBJECT

logger = logging.getLogger(__name__)


def is_multisite():
    """
    A naive but reliable check on whether Open edX is using multi-site setup or not.

    Override by setting ``FIGURES_IS_MULTISITE`` to true in the Open edX FEATURES.

    TODO: Move to `figures.sites`
    """
    return bool(settings.FEATURES.get('FIGURES_IS_MULTISITE', False))


def log_pipeline_errors_to_db():
    """
    Capture pipeline errors to the figures.models.PipelineError model.

    Override by setting ``FIGURES_LOG_PIPELINE_ERRORS_TO_DB`` to false in the Open edX FEATURES.

    TODO: This is an environment/setting "getter". Should be moved to `figures.settings`
    """
    return bool(settings.FEATURES.get('FIGURES_LOG_PIPELINE_ERRORS_TO_DB', True))


def import_from_path(path):
    """
    Import a function or class from a its string Python path.

    Note: This help does _not_ attempt to handle exceptions well.
      Instead it throws them as is. The rationale is that such exceptions are
      only fixable at the deploy time and attempting to handle such errors
      would risk hiding the errors and making it more difficult to fix.

    :param path: string path in the format "module.submodule:variable".
    :return object
    """
    module_path, variable_name = path.split(':', 1)
    module = import_module(module_path)
    return getattr(module, variable_name)


def as_course_key(course_id):
    """Returns course id as a CourseKey instance

    Convenience method to return the paramater unchanged if it is of type
    ``CourseKey`` or attempts to convert to ``CourseKey`` if of type str or
    unicode.

    Raises TypeError if an unsupported type is provided

    NOTE: This is a good example of a helper method that belongs here
    """
    if isinstance(course_id, CourseKey):
        return course_id
    elif isinstance(course_id, six.string_types):  # noqa: F821
        return CourseKey.from_string(course_id)
    else:
        raise TypeError('Unable to convert course id with type "{}"'.format(
            type(course_id)))


def as_datetime(val):
    '''
    TODO: Add arg flag to say if caller wants end of day, beginning of day
    or a particular time of day if the param is a datetime.date obj


    NOTE: The date functions here could be in a `figures.datetools` module.

    Not set on the name `datetools` but some date specific module
    '''
    if isinstance(val, datetime.datetime):
        return val
    elif isinstance(val, datetime.date):
        # Return the end of the day, set timezone to be UTC
        return datetime.datetime(
            year=val.year,
            month=val.month,
            day=val.day,
        ).replace(tzinfo=utc)

    elif isinstance(val, six.string_types):  # noqa: F821
        return dateutil_parse(val).replace(tzinfo=utc)
    else:
        raise TypeError(
            'value of type "{}" cannot be converted to a datetime object'.format(
                type(val)))


def as_date(val):
    """Casts the value to a ``datetime.date`` object if possible

    Else raises ``TypeError``

    NOTE: This is a good example of a helper method that belongs here
          We could also move this and the other date helpers to a "date"
          labeled module in Figures. Then at some future time, move those out
          into a "toolbox" package to abstrac
    """
    # Important to check if datetime first because datetime.date objects
    # pass the isinstance(obj, datetime.date) test
    if isinstance(val, datetime.datetime):
        return val.date()
    elif isinstance(val, datetime.date):
        return val
    elif isinstance(val, six.string_types):  # noqa: F821
        return dateutil_parse(val).date()
    else:
        raise TypeError(
            'date cannot be of type "{}".'.format(type(val)) +
            ' It must be able to be cast to a datetime.date')


def days_from(val, days):
    if isinstance(val, datetime.datetime):
        return as_datetime(val) + datetime.timedelta(days=days)
    elif isinstance(val, datetime.date):
        return as_date(val) + datetime.timedelta(days=days)
    else:
        raise TypeError(
            'val of type "{}" is not supported.'.format(type(val)))


def next_day(val):
    return days_from(val, 1)


def prev_day(val):
    return days_from(val, -1)


def utc_yesterday():
    """Get "yesterday" form the utc datetime

    We primarily use this for the daily metrics collection. However, it proves
    handy as a convenience function for exploring data in the Django shell
    """
    return prev_day(datetime.datetime.utcnow().date())


def days_in_month(month_for):
    _, num_days_in_month = calendar.monthrange(month_for.year, month_for.month)
    return num_days_in_month


def last_date_of_previous_month(date_for):
    """
    Returns the last date of the previous month.

    Arguments:
        date_for (datetime.date): the date for which last date of previous month is required.
    """
    last_date = date_for.replace(day=1) - datetime.timedelta(days=1)
    return last_date


def first_date_of_next_month(date_for):
    """
    Returns the first date of the next month.

    Arguments:
        date_for (datetime.date): the date for which first date of next month is required.
    """
    first_date = (date_for.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
    return first_date


def number_of_months_in_between(start_date, end_date):
    """
    Returns the number of months in bertween the start and end date.
    """
    months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
    return months


def is_past_date(val):
    return as_date(val) < datetime.date.today()


# TODO: Consider changing name to 'months_back_iterator' or similar
def previous_months_iterator(month_for, months_back):
    """Iterator returns a year,month tuple for n months including the month_for

    month_for is either a date, datetime, or tuple with year and month
    months back is the number of months to iterate
    """

    if isinstance(month_for, tuple):
        # TODO make sure we've got just two values in the tuple
        month_for = datetime.date(year=month_for[0], month=month_for[1], day=1)
    if isinstance(month_for, (datetime.datetime, datetime.date)):
        start_month = month_for - relativedelta(months=(max(0, months_back - 1)))

    for n_months in range(max(1, months_back)):
        dt = start_month + relativedelta(months=n_months)
        last_day_of_month = days_in_month(month_for=dt)
        yield (dt.year, dt.month, last_day_of_month)


def calculate_percentage_change(start_value, end_value):
    """
    Calculates the percentage change bbeetweeen end value and start value and
    returns the change up to 2 decimal places.
    Arguments:
        start_value (int): The numerator for percentage change
        end_value (int): The denominator for percentage change
    """
    if start_value == 0:
        return "NA"
    return str(round((end_value/start_value)*100, 2))


def get_previous_comparison_time_period(start_date, end_date):
    """
    For the given dates, retiurns the dates for comparision period before these dates.

    Arguments:
         start_date (datetime): The initial date for the timeframe.
         end_date (datetime): The final date for the timeframe.
    """
    days_in_between = (end_date - start_date).days

    comparison_start_date =  start_date - datetime.timedelta(days=days_in_between+1)
    comparison_end_date = start_date - datetime.timedelta(days=1)

    return (comparison_start_date, comparison_end_date)


def first_last_days_for_month(month_for):
    """Given a MM/YYYY string, derive the first and last days for the month

    Returns a tuple of first_day, last_day
    """
    month, year = [int(val) for val in month_for.split('/')]
    first_day = datetime.date(year=year,
                              month=month,
                              day=1)
    last_day = datetime.date(year=year,
                             month=month,
                             day=days_in_month(first_day))
    return first_day, last_day


def period_as_month(month_tuple, fmt='%b-%Y'):
    """
    Returns display date for the given month tuple containing year, month
    """
    return datetime.date(*month_tuple).strftime(fmt)


def get_required_registration_fields_for_user(user, site):
    """
    Returns only required registration fields from user profile of given site.

    Arguments:
        user (User): request user
        site (Site): request site

    Returns:
        list: required registration fields
    """
    registration_fields = site.configuration.site_values.get(
        'DJANGO_SETTINGS_OVERRIDE',
        {}
    ).get('REGISTRATION_EXTRA_FIELDS', {})

    required_registration_fields = [
        field for field, value in registration_fields.items()
        if value == 'required'
    ]
    user_required_fields = [
        field for field in required_registration_fields
        if hasattr(user.profile, field)
    ]
    return user_required_fields


def _get_completed_courses(courses):
    """
    Return number of completed courses from list of courses.
    """
    courses_count = 0
    for course in courses:
        if course['progress_data'] and course['progress_data']['course_completed']:
            courses_count += 1

    return str(courses_count)


def _render_template(path, context):
        """
        Takes a template path and context and returns a rendered template

        Arguments:
            path: path of the file
            context: context for the template
        """
        txt_template = get_template(path)
        return txt_template.render(context)


def send_email_with_attachment(recipient_email, username, platform_name, from_address, pdf_file=None):
    """
    Send email with attachments to given recipients.
    """
    html_template_path = 'figures/emails/learners_pdf_email.html'
    context = dict(platform_name=platform_name, username=username)
    html_content = _render_template(html_template_path, context)
    email_message = EmailMultiAlternatives(PDF_EMAIL_SUBJECT, html_content, from_address, to=[recipient_email])
    email_message.content_subtype = 'html'
    if pdf_file:
        email_message.attach(
            '{}.pdf'.format(LEARNERS_OVERVIEW_REPORT),
            pdf_file,
            'application/pdf'
        )

    email_message.send()
    logger.info('Learner overview report email sent to {}'.format(username))


def _get_formatted_datetime_string(datetime_string, time=False):
    """
    Parse string into datetime format and return custom formatted string.
    """
    datetime_format = '%Y-%m-%d %H:%M:%S' if time else '%Y-%m-%d'
    if not datetime_string:
        return ''

    parsed_datetime = parser.parse(datetime_string)
    return datetime.datetime.strftime(parsed_datetime, datetime_format)


def get_prepared_pdf(pdf_data, logo_url):
    """
    Prepare pdf for learners overview data.
    """
    class LearnerPDF(FPDF):
        """
        Custom class for FPDF.
        """
        def header(self):
            """
            Create header for pdf file.
            """
            self.set_left_margin(0)
            self.set_fill_color(242, 242, 242)
            self.set_font('Arial', size=14)
            self.cell(0, 18, '', 0, 0, 'C', True)
            self.ln(1)
            self.image(name=logo_url, x=70, w=65, h=15)
            self.ln(5)

        def footer(self):
            """
            Create footer for pdf file.
            """
            self.set_left_margin(0)
            self.set_text_color(255, 255, 255)
            self.set_fill_color(47, 42, 42)
            self.set_y(-15)
            self.set_font('Arial', '', 9)
            self.cell(0, 15, PDF_COPYRIGHT_TEXT, 0, 0, 'C', True)

    pdf = LearnerPDF()
    pdf.set_top_margin(0)
    pdf.set_left_margin(0)
    pdf.set_right_margin(0)
    pdf.add_page()
    pdf.set_left_margin(3)
    pdf.set_font('Arial', size=14, style='B')
    pdf.set_text_color(70, 64, 64)
    pdf.multi_cell(w=0, h=10, txt='Learners Overview', border=0, align='L', fill=False)
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 9)
    line_height = pdf.font_size * 2.5
    pdf.set_fill_color(242, 242, 242)
    pdf.set_draw_color(242, 242, 242)
    pdf.cell(50, line_height, 'Name', border='LTB', fill=True)
    pdf.cell(65, line_height, 'Email', border='TB', fill=True)
    pdf.cell(17, line_height, 'Courses', border='TB', fill=True)
    pdf.cell(20, line_height, 'Courses', border='TB', fill=True)
    pdf.cell(20, line_height, 'Account', border='TB', fill=True)
    pdf.cell(32, line_height, 'Login', border='TBR', fill=True)
    pdf.ln(line_height)
    pdf.cell(50, line_height, '', border='LTB', fill=True)
    pdf.cell(65, line_height, '', border='TB', fill=True)
    pdf.cell(17, line_height, 'Enrolled', border='TB', fill=True)
    pdf.cell(20, line_height, 'Completed', border='TB', fill=True)
    pdf.cell(20, line_height, 'Created', border='TB', fill=True)
    pdf.cell(32, line_height, '', border='TBR', fill=True)
    pdf.ln(line_height)
    pdf.set_font('Arial', size=9)
    for row in pdf_data:
        course_count = len(row['courses']) if row['courses'] else 0
        pdf.set_text_color(221, 31, 37)
        pdf.cell(50, line_height, row['name'], border='LTB')
        pdf.set_text_color(7, 64, 64)
        pdf.cell(65, line_height, row['email'], border='TB')
        pdf.cell(17, line_height, str(course_count), border='TB')
        pdf.cell(20, line_height, _get_completed_courses(row['courses']), border='TB')
        pdf.cell(20, line_height, _get_formatted_datetime_string(row['date_joined']), border='TB')
        pdf.cell(32, line_height, _get_formatted_datetime_string(row['last_login'], True), border='TBR')
        pdf.ln(line_height)
        pdf.set_left_margin(3)

    pdf.set_font('Arial', 'I', 8)
    pdf.multi_cell(w=0, h=pdf.font_size*2, txt=PDF_NOTE, border=0, align='L', fill=False)
    return pdf.output(dest='S')


def validate_year(year):
    """
    Validate the provided year.

    Arguments:
         year (str): Date string of format "%Y"

    Raises:
        ValueError: for invalid year string

    """
    try:
        return 2000 <= datetime.datetime.strptime(str(year), '%Y').year
    except ValueError:
        return False


def convert_date_to_str(date_value, date_format='%m-%Y'):
    """
    Returns the datetime object converted to a string.

    Arguments:
         date_value (datetime.date): Valid datetime.date object
         date_format (str): Date string format [optional].
    """
    return date_value.strftime(date_format)


def validate_date(date, date_format='%m-%Y'):
    """
    Validate the provided date.

    Arguments:
         date (str): Date string of format "%m-%Y"
         date_format (str): Date string format [optional].

    """
    try:
        return validate_year(datetime.datetime.strptime(date, date_format).year)
    except (ValueError, AttributeError):
        return False


def validate_date_range(start_date, end_date, date_format='%m-%Y'):
    """
    Validate the provided start and end date.

    Arguments:
         start_date (str): Date string of format "%m-%Y"
         end_date (str): Date string of format "%m-%Y"
         date_format (str): Date string format [optional].

    """
    try:
        start_date = datetime.datetime.strptime(start_date, date_format)
        end_date = datetime.datetime.strptime(end_date, date_format)
        is_invalid_date_range = (end_date.year - start_date.year < 0) or (
                start_date.month > end_date.month
                and start_date.year == end_date.year
        ) or (
            start_date.year == end_date.year
            and start_date.month == end_date.month
            and start_date.day > end_date.day
        )
        if is_invalid_date_range:
            return False

        # date difference beyond five years are not allowed
        if end_date.year - start_date.year > 5:
            return False

        return True
    except ValueError:
        return False


def return_invalid_date_range_response(start_date, end_date, date_format='%m-%Y'):
    """
    Return validation response for the provided start and end date.

    Arguments:
         start_date (str): Date string of format "%m-%Y"
         end_date (str): Date string of format "%m-%Y"
         date_format (str): Date string format [optional].

    Returns:
         HTTP_406_NOT_ACCEPTABLE: In case of invalid start and end date
         None: In case of valid start and end date

    """
    if not start_date or not end_date:
        return Response(
            {'error': 'Please provide valid type in the query params.'},
            status=status.HTTP_406_NOT_ACCEPTABLE
        )

    if not (validate_date(start_date, date_format) and validate_date(end_date, date_format)):
        return Response(
            {'error': 'Please provide valid start and end date.'},
            status=status.HTTP_406_NOT_ACCEPTABLE
        )

    if not validate_date_range(start_date, end_date, date_format):
        return Response(
            {'error': 'Please specify the valid date ranges.'},
            status=status.HTTP_406_NOT_ACCEPTABLE
        )


def get_date(date_value, date_format='%m-%Y'):
    """
    Return date object from provided `date_value`.

    Arguments:
         date_value (str): Valid date string of format "%m-%Y"
         date_format (str): Date string format [optional].

    """
    if isinstance(date_value, datetime.date):
        return date_value
    return datetime.datetime.strptime(date_value, date_format).date()


def dates_within_month(start_date, end_date, date_format='%d-%m-%Y'):
    """
    Check if "start_date" and "end_date" are within the same month or less than 30 days.

    Arguments:
         start_date (str): Date string of format "%m-%Y"
         end_date (str): Date string of format "%m-%Y"
         date_format (str): Date string format [optional].

    """
    st_date = start_date
    ed_date = end_date
    if st_date.month == ed_date.month and st_date.year == ed_date.year:
        return True
    elif (ed_date - st_date).days >= 30:
        return False
    else:
        return True


def _email_report_with_attachment(recipient_email, subject, username, platform, from_address, report_type, csv_file):
    """
    figures app is installed as plugin which are loaded before INSTALLED_APPS
    And this import causing to load the third party `social_django` app to load
    before its settings are properly configured in `common > djangoapps > third_party_auth`
    ref: https://edlyio.atlassian.net/browse/EDLY-4644
    """
    from edly_panel_app.api.v1.helpers import email_report_with_attachment

    email_report_with_attachment.delay(
        recipient_email, subject, username,
        platform, from_address,
        report_type, csv_file
    )


def send_insights_summary_report(raw_data, recipient_email, username, report_type, site_configuration):
    general_site_metrics = raw_data['general_site_metrics']
    maus = raw_data['maus'].get('data', {})
    monthly_course_completions = raw_data['monthly_course_completions'].get('data', {})
    courses_stats_by_enrollment = raw_data['courses_stats_by_enrollment']
    courses_stats_by_learners = raw_data['courses_stats_by_learners']

    csv_file = StringIO()
    csv_report_writer = csv.writer(csv_file)
    csv_report_writer.writerow(['Analytics Summary Report'])
    csv_report_writer.writerow([''])
    total_learners = general_site_metrics.get('total_site_learners', {}).get('current_month', 0)
    total_site_courses = general_site_metrics.get('total_site_courses', {}).get('current_month', 0)
    total_active_courses = general_site_metrics.get('total_active_courses', {}).get('current_month', 0)
    total_staff_users = general_site_metrics.get('total_site_staff_users', {}).get('current_month', 0)
    course_completions = monthly_course_completions.get('total_course_completions', 0)
    csv_report_writer.writerow(['Total Learners: ', total_learners])
    csv_report_writer.writerow(['Monthly Active Users: ', maus.get('total_users_count')])
    csv_report_writer.writerow(['Course completions: ', course_completions])
    csv_report_writer.writerow(['Total Courses: ', total_site_courses])
    csv_report_writer.writerow(['Active Courses: ', total_active_courses])
    csv_report_writer.writerow(['Staff Users: ', total_staff_users])

    csv_report_writer.writerow([''])
    csv_report_writer.writerow(['Top Course by Enrollment'])
    csv_report_writer.writerow([''])
    for courses in courses_stats_by_enrollment:
        csv_report_writer.writerow([courses.get('course_name'), courses.get('enrollment_count')])

    csv_report_writer.writerow([''])
    csv_report_writer.writerow(['Top Course by Completions'])
    csv_report_writer.writerow([''])
    for courses in courses_stats_by_learners:
        csv_report_writer.writerow([courses.get('course_name'), courses.get('num_learners_completed')])

    _email_report_with_attachment(
        recipient_email, 'Analytics Summary Report', username,
        site_configuration.get('platform_name'), site_configuration.get('from_address'),
        report_type, csv_file.getvalue()
    )


def send_insights_learner_report(raw_data, recipient_email, username, report_type, site_configuration):
    """
    Function to write the csv for the Learner Isgihts and send it via email to the recipient
    """
    monthly_course_completions = raw_data['monthly_course_completions'].get('data', {})
    all_learners_details = raw_data['all_learners_details']
    site_daily_metrics = raw_data['site_daily_metrics']
    site_monthly_metrics = raw_data['site_monthly_metrics']
    maus = raw_data['maus'].get('data', {})

    csv_file = StringIO()
    csv_report_writer = csv.writer(csv_file)

    csv_report_writer.writerow(['Learner Analytics Report'])
    csv_report_writer.writerow(['Total Learners: ', len(all_learners_details)])

    curr_new_users = site_monthly_metrics.get('current_month', {}).get('new_learners', 0)
    prev_new_users = site_monthly_metrics.get('last_month', {}).get('new_learners', 0)
    csv_report_writer.writerow(['New Learner Registrations (Current Month): ', curr_new_users])
    csv_report_writer.writerow(['New Learner Registrations (Last Month): ', prev_new_users])

    curr_month = datetime.datetime.now().month
    curr_new_users = maus['monthly_users_count'][curr_month - 1]
    prev_new_users = maus['monthly_users_count'][curr_month -2]
    csv_report_writer.writerow(['Monthly Active Learners (Current Month): ', curr_new_users])
    csv_report_writer.writerow(['Monthly Active Learners (Last Month): ', prev_new_users])

    today_users = (site_daily_metrics or [{}])[0].get('todays_active_learners_count', 0)
    csv_report_writer.writerow(['Active Users Today', today_users])

    curr_course_completion = monthly_course_completions['monthly_course_completions_count'][curr_month - 1]
    csv_report_writer.writerow(['Course Completions', curr_course_completion])

    registration_fields = all_learners_details[0].get('registration_fields', {}) if all_learners_details else {}
    registration_fields = [f.title().replace('_', ' ') for f in registration_fields.keys()]
    csv_report_writer.writerow([''])
    csv_report_writer.writerow(['Learners Overview'])
    csv_report_writer.writerow([''])
    
    csv_report_writer.writerow([
        'Name',
        'Username',
        'Email',
        *registration_fields,
        'Courses Enrolled',
        'Courses Completed',
        'Account Created',
        'Last Login',
        'Last Course Activity',
    ])
    csv_report_writer.writerow([''])

    for learner in all_learners_details:
        csv_report_writer.writerow([
            learner['name'],
            learner['username'],
            learner['email'],
            *learner['registration_fields'].values(),
            len(learner['courses']),
            len([course for course in learner['courses'] if course['progress_data']['course_completed']]),
            (learner.get('date_joined') or 'N/A').split('T')[0],
            (learner.get('last_login') or 'N/A').split('T')[0],
            (learner.get('course_activity_date') or 'N/A').split(' ')[0]
        ])

    csv_report_writer.writerow([''])

    _email_report_with_attachment(
        recipient_email, 'Analytics Learner Report', username,
        site_configuration.get('platform_name'), site_configuration.get('from_address'),
        report_type, csv_file.getvalue()
    )


def course_complete_rate(course):
    enrollment_count = course['metrics'].get('enrollment_count', 0)
    num_learners_completed = course['metrics'].get('num_learners_completed', 0)
    if enrollment_count and num_learners_completed:
        return round(num_learners_completed/enrollment_count * 100, 2)

    return 'N/A'


def send_insights_courses_report(courses, recipient_email, username, report_type, site_configuration):
    csv_file = StringIO()
    csv_report_writer = csv.writer(csv_file)
    csv_report_writer.writerow(['Courses Analytics Report'])
    csv_report_writer.writerow([''])

    csv_report_writer.writerow([
        'Course Id', 'Course Title', 'Instructors', 'Start Date', 'End Date',
        'Total Enrollments', 'Active Learners', 'Total completions',
        'Average days to complete', 'Completion Rate'
    ])
    csv_report_writer.writerow([''])

    for course in courses:
        if not course['metrics']:
            course['metrics'] = {}

        csv_report_writer.writerow([
            course['course_id'], course['course_name'],
            ','.join([staff['username'] for staff in course['staff'] if staff['role'] == 'instructor']),
            dateutil_parse(course['start_date']).strftime('%B %d, %Y'),
            dateutil_parse(course['end_date']).strftime('%B %d, %Y') if course['end_date'] else '',
            course['metrics'].get('enrollment_count', 0), 
            course['metrics'].get('active_learners_today', 0),
            course['metrics'].get('active_learners_this_month', 0),
            course['metrics'].get('num_learners_completed', 0),
            course['metrics'].get('average_days_to_complete', 0),
            course_complete_rate(course)
        ])

    _email_report_with_attachment(
        recipient_email, 'Analytics Course Report', username,
        site_configuration.get('platform_name'), site_configuration.get('from_address'),
        report_type, csv_file.getvalue()
    )


def get_farthest_complete_course_block(scp_objects, course_key=None, user=None):
    """
    This helper method retrieves "StudentCourseProgress" for given course_key.
    """
    course_progress = None
    if course_key is not None:
        course_progress = scp_objects.filter(course_id = course_key)
    elif user is not None:
        course_progress = scp_objects.filter(student__username = user)

    if course_progress:
        scp = course_progress.first()
        return [scp.completed_section, scp.completed_subsection, scp.completed_unit, scp.completed_block, scp.completion_date]

    return []


def send_learner_report(learners_data, scp_objects, recipient_email, username, report_type, site_configs):
    csv_file = StringIO()
    csv_report_writer = csv.writer(csv_file)
    csv_report_writer.writerow(['Learner Detail Report'])
    csv_report_writer.writerow([''])

    csv_report_writer.writerow(['Username', learners_data.get('username')])
    csv_report_writer.writerow(['Email', learners_data.get('email')])
    registration_fields = learners_data.get('registration_fields', {}) if learners_data else {}
    for registration_field in registration_fields:
        csv_report_writer.writerow([registration_field.title().replace('_', ' '), registration_fields.get(registration_field, '')])

    csv_report_writer.writerow(['Courses Enrolled', len(learners_data.get('courses'))])
    course_completed = len([
        course for course in learners_data.get('courses')
        if course.get('progress_data').get('course_completed')
    ])
    csv_report_writer.writerow(['Courses Completed', course_completed])
    csv_report_writer.writerow(['Status', 'Active' if learners_data.get('is_active') else 'False'])
    created_date = (learners_data.get('date_joined') or '').split('T')[0]
    csv_report_writer.writerow(['Account Created', created_date])
    last_login = (learners_data.get('last_login') or '').split('T')[0]
    csv_report_writer.writerow(['Last Login', last_login])
    course_activity = learners_data.get('course_activity_date')
    csv_report_writer.writerow([
        'Last Course Activity', course_activity.split(' ')[0] if course_activity else 'N/A'
    ])
    csv_report_writer.writerow([''])
    csv_report_writer.writerow([
        'Course Title',
        'Enrollment Date',
        'Completion Date',
        'Grade',
        'Graded Course Progress',
        'Total Course Progress',
        'Farthest Completed Block (Section)',
        'Farthest Completed Block (Subsection)',
        'Farthest Completed Block (Unit)',
        'Farthest Completed Block',
        'Farthest Completed Block Date',
    ])

    for course in learners_data.get('courses'):
        csv_report_writer.writerow([
            course.get('course_name'),
            course.get('date_enrolled'),
            (course.get('progress_data').get('passed_timestamp') or '').split(' ')[0],
            course.get('progress_data').get('letter_grade') or 'N/A',
            '{}%'.format(course.get('progress_data').get('course_progress')),
            '{}%'.format(course.get('progress_data').get('total_progress_percent')),
            *get_farthest_complete_course_block(scp_objects, course_key=course['course_id']),
        ])

    _email_report_with_attachment(
        recipient_email, 'Learner Detail Report', username,
        site_configs.get('platform_name'), site_configs.get('from_address'),
        report_type, csv_file.getvalue()
    )


def send_insights_course_detail_report(
    course_overview, course_details, course_maus, learners,
    recipient_email, username, report_type, site_configs, scp_objects
):
    csv_file = StringIO()
    csv_report_writer = csv.writer(csv_file)
    csv_report_writer.writerow(['Course Detail Report'])
    csv_report_writer.writerow([''])

    course_name = course_overview.get('course_name', '')
    csv_report_writer.writerow(['Course Name', course_name])

    course_id = course_overview.get('course_id', '')
    csv_report_writer.writerow(['Course ID', course_id])

    course_code = course_overview.get('course_code', '')
    csv_report_writer.writerow(['Course Code', course_code])
    csv_report_writer.writerow([''])
    
    total_learners = (course_overview.get('metrics') or {}).get('enrollment_count', 0)
    csv_report_writer.writerow(['Total Learners', total_learners])

    total_completion = (course_overview.get('metrics') or {}).get('num_learners_completed', 0)
    csv_report_writer.writerow(['Total Completions', total_completion])

    completion_rate = round(0 if total_learners == 0 else (total_completion / total_learners) * 100, 2)
    csv_report_writer.writerow(['Completion Rate', '{}%'.format(completion_rate)])

    csv_report_writer.writerow(['Active Learners (Active in last thirty days)', sum(course_maus.get('counts', []))])

    avg_course_progress = float((course_overview.get('metrics') or {}).get('average_progress', 0)) * 100
    csv_report_writer.writerow(['Average Course Progress', '{}%'.format(avg_course_progress)])

    avg_days_to_complete = (course_overview.get('metrics') or {}).get('average_days_to_complete', 0)
    csv_report_writer.writerow(['Average Days to Complete', '{}%'.format(avg_days_to_complete)])

    enrols_over_time = (course_details.get('learners_enrolled') or {}).get('current_month', 0)
    csv_report_writer.writerow(['Enrollments Over Time', enrols_over_time])

    completion_over_time = (course_details.get('users_completed') or {}).get('current_month', 0)
    csv_report_writer.writerow(['Completions Over Time', completion_over_time])
    csv_report_writer.writerow([''])
    csv_report_writer.writerow([''])

    csv_report_writer.writerow([
        'Name',
        'Username',
        'Email',
        'Enrollment Mode',
        'Enrollment Date',
        'Completion Date',
        'Grade',
        'Graded Course Progress',
        'Total Course Progress',
        'Farthest Completed Block (Section)',
        'Farthest Completed Block (Subsection)',
        'Farthest Completed Block (Unit)',
        'Farthest Completed Block',
        'Farthest Completed Block Date',
        'Account Created',
        'Last Login'
    ])
    for learner in learners:
        csv_report_writer.writerow([
            learner['user']['fullname'],
            learner['user']['username'],
            learner['user']['email'],
            learner.get('mode') or 'N/A',
            learner['courses'][0]['date_enrolled'],
            learner['courses'][0]['progress_data']['passed_timestamp'],
            learner['courses'][0]['progress_data']['letter_grade'],
            '{}%'.format(learner['courses'][0]['progress_data']['course_progress']),
            '{}%'.format(learner['courses'][0]['progress_data']['total_progress_percent']),
            *get_farthest_complete_course_block(scp_objects, user=learner['user']['username']),
            learner['user']['date_joined'] or 'N/A',
            learner['user']['last_login'] or 'N/A',
        ])

    _email_report_with_attachment(
        recipient_email, 'Course Detail Report', username,
        site_configs.get('platform_name'), site_configs.get('from_address'),
        report_type, csv_file.getvalue()
    )


def get_course_block_name(course_block_structure, block):
    """
    This helper methods fetches the block 'display_name'.
    """
    return course_block_structure.get_xblock_field(
        usage_key=block,
        field_name='display_name',
    )
