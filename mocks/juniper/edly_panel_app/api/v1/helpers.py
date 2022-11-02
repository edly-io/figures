"""
Helper methods for Edly API.
"""
from calendar import month_abbr
from collections import OrderedDict
import csv
from datetime import datetime, timedelta
from io import StringIO


from celery.task import task
from django.conf import settings
from django.core.mail.message import EmailMultiAlternatives
from django.db.models import Q
from django.template.loader import get_template
from edly_panel_app.api.v1.constants import (
    ERROR_MESSAGES,
    BLOCK_TYPES_TO_FILTER,
    CORE_BLOCK_TYPES,
    VIDEO_BLOCK_TYPES,
)
from lms.djangoapps.course_api.blocks.serializers import BlockDictSerializer
from lms.djangoapps.course_api.blocks.transformers.blocks_api import BlocksAPITransformer
from openedx.core.djangoapps.content.block_structure.transformers import BlockStructureTransformers
from rest_framework import status
from rest_framework.response import Response


def get_block_types_and_keys(course_block_structure):
    """
    Gets all completable course block types and block keys in the course block structure.

    Arguments:
        course_block_structure (CourseBlockStructure): CourseBlockStructure to get block types from

    Returns:
        block_types (list): list of block types in given course structure
        block_keys (list): list of block keys in given course structure
    """
    block_types = set()
    block_keys = set()
    for block_key in course_block_structure:
        block_type = course_block_structure.get_xblock_field(block_key, 'category')
        if block_type not in BLOCK_TYPES_TO_FILTER:
            block_types.add(block_type)
            block_keys.add(block_key)

    return block_types, block_keys


def accumulate_total_block_counts(total_block_type_counts):
    """
    Converts total_block_type_counts to required format.

    Accumulates all types of completable course blocks except html, problem and video
    into an 'other' category.

    Arguments:
        total_block_type_counts (dict): Total block type counts of required course

    Returns:
        accumulated_data (dict): Accumulated block type counts
    """
    accumulated_data = {
        'problem': 0,
        'video': 0,
        'html': 0,
        'other': 0
    }
    if total_block_type_counts:
        for block_type, count in total_block_type_counts.items():
            if block_type in CORE_BLOCK_TYPES:
                accumulated_data[block_type] = count
            else:
                accumulated_data['other'] += count

    return accumulated_data


def serialize_course_block_structure(request, course_block_structure):
    """
    Serializes course block structure into dict.

    Arguments:
        request (HttpReques): Request object for serializer context
        course_block_structure (CourseBlockStructure): Course block structure to serialize

    Returns:
        course_block_structure_serializer.data: Serialized course block structure
    """

    block_types, block_keys = get_block_types_and_keys(course_block_structure)
    transformers = BlockStructureTransformers()
    transformers += [
        BlocksAPITransformer(block_types_to_count=block_types, requested_student_view_data=set([]), depth=0)
    ]
    transformers.transform(course_block_structure)
    serializer_context = {
        'request': request,
        'block_structure': course_block_structure,
        'requested_fields': ['block_counts'],
    }
    course_block_structure_serializer = BlockDictSerializer(
        course_block_structure,
        context=serializer_context,
        many=False
    )

    return course_block_structure_serializer.data, block_keys


def _render_template(path, context):
    """
    Takes a template path and context and returns a rendered template

    Arguments:
        path: path of the file
        context: context for the template
    """
    txt_template = get_template(path)

    return txt_template.render(context)


@task()
def email_report_with_attachment(recipient_email, subject, username, platform_name, from_address, report_type, csv_file):
    """
    Send email with attachment to given recipient.

    Arguments:
        recipient_email (str): email of requesting user.
        username (str): username of requesting user.
        platform_name (str): LMS platform name of current site.
        from_address (str): email from address from site configurations.
        report_type (str): report type e.g; monthly, yearly.
        csv_file (StringIO): the csv file string to send in email.
    """
    html_template_path = 'edly_panel_app/emails/report.html'
    context = dict(platform_name=platform_name, username=username)
    html_content = _render_template(html_template_path, context)
    email_message = EmailMultiAlternatives(subject, html_content, from_address, to=[recipient_email])
    email_message.attach(
        '{}.csv'.format(report_type),
        csv_file,
        'text/csv'
    )
    email_message.send()


def dates_within_month(start_date, end_date, date_format='%d-%m-%Y', is_datetime=False):
    """
    Check if "start_date" and "end_date" are within the same month or less than 30 days.

    Arguments:
         start_date (str): Date string of format "%m-%Y"
         end_date (str): Date string of format "%m-%Y"
         date_format (str): Date string format [optional].
         is_datetime (bool): Boolean for datetime [optional].
    """
    st_date = start_date
    ed_date = end_date
    if not is_datetime:
        st_date = datetime.strptime(start_date, date_format).date()
        ed_date = datetime.strptime(end_date, date_format).date()

    if st_date.month == ed_date.month and st_date.year == ed_date.year:
        return True
    elif (ed_date - st_date).days >= 30:
        return False
    else:
        return True


def prepare_monthly_response_data_structure(type, start_date, end_date):
    """
    Construct a monthly response on the basis of provided start and end date.

    Returns:
        response_data_structure (dict): OrderedDict(
            [
                ('Nov-2019', 0),
                ('Dec-2019', 0),
                ('Jan-2020', 0),
                ('Feb-2020', 0)
            ]
        )
    """
    response_data_structure = OrderedDict()
    if type == 'monthly':
        start_date = datetime.strptime(start_date, '%m-%Y')
        end_date = datetime.strptime(end_date, '%m-%Y')
        start_month, start_year = start_date.month, start_date.year
        end_month, end_year = end_date.month, end_date.year
    elif type == 'custom':
        st_date = start_date
        ed_date = end_date
        start_date = datetime.strptime(start_date, '%d-%m-%Y')
        end_date = datetime.strptime(end_date, '%d-%m-%Y')
        start_day, start_month, start_year = start_date.day, start_date.month, start_date.year
        end_day, end_month, end_year = end_date.day, end_date.month, end_date.year

        start_date_range = datetime(day=start_day, month=start_month, year=start_year).date()
        end_date_range = datetime(day=end_day, month=end_month, year=end_year).date()
        if dates_within_month(st_date, ed_date, '%d-%m-%Y'):
            while start_date_range <= end_date_range:
                response_data_structure['{}-{}-{}'.format(
                    start_date_range.day,
                    month_abbr[start_date_range.month],
                    start_date_range.year,
                )] = 0

                start_date_range = start_date_range + timedelta(days=1)
            return response_data_structure
    else:
        return {}

    while datetime(
            day=1, month=start_month, year=start_year
    ).date() <= datetime(day=1, month=end_month, year=end_year).date():

        response_data_structure['{}-{}'.format(month_abbr[start_month], start_year)] = 0
        start_month = start_month + 1
        if start_month == 13:
            start_month = 1
            start_year = start_year + 1

    return response_data_structure


def get_date(date_value, date_format='%m-%Y'):
    """
    Return date object from provided `date_value`.

    Arguments:
         date_value (str): Valid date string of format "%m-%Y"
         date_format (str): Date string format [optional].

    """
    return datetime.strptime(date_value, date_format).date()

def get_first_day_of_month(date_value, date_format='%m-%Y'):
    """
    Return date object of first day of the month from the provided `date_value`.

    Arguments:
         date_value (str): Valid date string of format "%m-%Y"
         date_format (str): Date string format [optional].

    """
    date_object = datetime.strptime(date_value, date_format)
    return datetime(
        day=1,
        month=date_object.month,
        year=date_object.year
    ).date()


def get_last_day_of_month(date_value, date_format='%m-%Y'):
    """
    Return date object of last day of the month from the provided `date_value`.

    Arguments:
         date_value (str): Valid date string of format "%m-%Y"
         date_format (str): Date string format [optional].

    """
    date_object = datetime.strptime(date_value, date_format)
    return datetime(
        day=monthrange(date_object.year, date_object.month)[1],
        month=date_object.month,
        year=date_object.year
    ).date()


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
            {'error': ERROR_MESSAGES.get('INVALID_TYPE')},
            status=status.HTTP_406_NOT_ACCEPTABLE
        )

    if not (validate_date(start_date, date_format) and validate_date(end_date, date_format)):
        return Response(
            {'error': ERROR_MESSAGES.get('INVALID_START_AND_END_DATE')},
            status=status.HTTP_406_NOT_ACCEPTABLE
        )

    if not validate_date_range(start_date, end_date, date_format):
        return Response(
            {'error': ERROR_MESSAGES.get('INVALID_DATE_RANGE')},
            status=status.HTTP_406_NOT_ACCEPTABLE
        )


def validate_year(year):
    """
    Validate the provided year.

    Arguments:
         year (str): Date string of format "%Y"

    Raises:
        ValueError: for invalid year string

    """
    try:
        return 2000 <= datetime.strptime(str(year), '%Y').year
    except ValueError:
        return False


def filter_records_by_roles(records, roles):
    """
    Return filtered queryset against provided roles.

    Arguments:
         records (queryset): Records to be filtered against provided roles.
         roles (str): Comma separated roles to be used in filtering.

    Returns:
        queryset: Filtered queryset against provided roles

    """
    if not roles:
        return records

    roles = [role.strip() for role in roles.strip(',').split(',')]
    filter_query = Q()
    user_groups = []
    for role in roles:
        if role in settings.EDLY_USER_ROLES:
            user_groups.append(settings.EDLY_USER_ROLES[role])

    if len(user_groups) > 0:
        filter_query = filter_query | Q(user__groups__name__in=user_groups)

    if 'super_admin' in roles:
        filter_query = filter_query | Q(user__is_superuser=True)

    if 'staff' in roles:
        filter_query = filter_query | Q(user__courseaccessrole__role='global_course_creator')

    if 'course_creator' in roles:
        filter_query = filter_query | Q(user__courseaccessrole__role='course_creator_group')

    if 'learner' in roles:
        filter_query = filter_query | Q(
            Q(user__is_staff=False) &
            Q(user__is_superuser=False) &
            ~Q(user__courseaccessrole__role='course_creator_group')
        )

    return records.filter(filter_query)


def get_previous_comparison_time_period(period_type, **kwargs):
    """
    For the given period, returns the previous period for comparision.

    Arguments:
         period_type (str): Denotes the type of period.
    """
    if period_type == 'yearly':
        year = kwargs.get('year')
        return str(int(year)-1)

    elif period_type == 'quarterly':
        year = kwargs.get('year')
        quarter = kwargs.get('quarter')

        if quarter !='1':
            return year, str(int(quarter)-1)
        else:
            return str(int(year)-1), str(4)

    elif period_type == 'monthly':
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        days_in_between = (end_date - start_date).days
        comparison_start_date =  start_date - timedelta(days=days_in_between+1)
        comparison_end_date = start_date - timedelta(days=1)

        return (comparison_start_date, comparison_end_date)

    elif period_type == 'custom':
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')
        days_in_between = (end_date - start_date).days
        comparison_start_date =  start_date - timedelta(days=days_in_between+1)
        comparison_end_date = start_date - timedelta(days=1)

        return (comparison_start_date, comparison_end_date)


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


def convert_date_to_str(date_value, date_format='%m-%Y'):
    """
    Returns the datetime object converted to a string.

    Arguments:
         date_value (datetime.date): Valid datetime.date object
         date_format (str): Date string format [optional].
    """
    return date_value.strftime(date_format)


@task()
def send_maus_report(raw_data, recipient_email, username, report_type, site_configuration):
    csv_file = StringIO()
    csv_report_writer = csv.writer(csv_file)
    csv_report_writer.writerow(['Report: {}'.format(report_type)])
    months = raw_data.get('data', {}).get('month_names', [])
    months.insert(0, 'Months: ')
    csv_report_writer.writerow(months)
    maus = raw_data.get('data', {}).get('monthly_users_count', [])
    maus.insert(0, 'MAUs: ')
    csv_report_writer.writerow(maus)
    email_report_with_attachment.delay(
        recipient_email, 'Monthly Users Report', username, site_configuration.get('platform_name'),
        site_configuration.get('from_address'), report_type, csv_file.getvalue()
    )
