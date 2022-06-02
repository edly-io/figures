"""
Helper methods for Edly API.
"""
from celery.task import task
from django.core.mail.message import EmailMultiAlternatives
from django.template.loader import get_template

from edly_panel_app.api.v1.constants import (
    BLOCK_TYPES_TO_FILTER,
    CORE_BLOCK_TYPES
)
from lms.djangoapps.course_api.blocks.serializers import BlockDictSerializer
from lms.djangoapps.course_api.blocks.transformers.blocks_api import BlocksAPITransformer
from openedx.core.djangoapps.content.block_structure.transformers import BlockStructureTransformers


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
