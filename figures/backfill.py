"""Backfills metrics models

Initially developed to support API performance improvements
"""

from __future__ import absolute_import
import logging
from datetime import datetime
from dateutil.rrule import rrule, MONTHLY
from dateutil.relativedelta import relativedelta

from django.utils.timezone import utc

from figures.compat import CourseNotFound, StudentModule
from figures.sites import get_course_enrollments_for_site, get_student_modules_for_site
from figures.pipeline.site_monthly_metrics import fill_month
from figures.models import EnrollmentData, LearnerCourseGradeMetrics
from figures.pipeline.enrollment_metrics import _collect_total_progress_data
from figures.sites import (
    student_modules_for_course_enrollment,
    course_enrollments_for_course,
    get_courses_for_site,
)
from openedx.features.edly.models import EdlyUserProfile
from util.query import read_replica_or_default

logger = logging.getLogger(__name__)


def backfill_monthly_metrics_for_site(site, overwrite=False):
    """Backfill all historical site metrics for the specified site
    """
    site_sm = get_student_modules_for_site(site)
    if not site_sm:
        return None

    first_created = site_sm.order_by('created').first().created

    start_month = datetime(year=first_created.year,
                           month=first_created.month,
                           day=1,
                           tzinfo=utc)
    last_month = datetime.utcnow().replace(tzinfo=utc) - relativedelta(months=1)
    backfilled = []
    for dt in rrule(freq=MONTHLY, dtstart=start_month, until=last_month):
        obj, created = fill_month(site=site,
                                  month_for=dt,
                                  student_modules=site_sm,
                                  overwrite=overwrite)
        backfilled.append(dict(obj=obj, created=created, dt=dt))

    backfill_learners_course_data_for_site(site)

    return backfilled


def backfill_enrollment_data_for_site(site):
    """Convenience function to fill EnrollmentData records

    This backfills EnrollmentData records for existing CourseEnrollment
    and LearnerCourseGradeMetrics records

    ```

    Potential improvements: iterate by course id within site, have a function
    specific to a course. more queries, but breaks up the work
    """
    enrollment_data = []
    errors = []
    site_course_enrollments = get_course_enrollments_for_site(site)
    for rec in site_course_enrollments:
        try:
            obj, created = EnrollmentData.objects.set_enrollment_data(
                site=site,
                user=rec.user,
                course_id=rec.course_id)
            enrollment_data.append((obj, created))
        except CourseNotFound:
            msg = ('CourseNotFound for course "{course}". '
                   ' CourseEnrollment ID={ce_id}')
            errors.append(msg.format(course=str(rec.course_id),
                                     ce_id=rec.id))

    return dict(results=enrollment_data, errors=errors)


def backfill_course_activity_date():
    """
    Backfill historical "course_activity_date" for learners who performed course activity in the past.
    """
    student_ids = StudentModule.objects.values_list('student__id', flat=True).distinct()
    for student_id in student_ids:
        student_activity = StudentModule.objects.filter(student__id=student_id).order_by('-modified').first()
        EdlyUserProfile.objects.filter(
            user_id=student_activity.student_id,
        ).update(course_activity_date=student_activity.modified)


def backfill_learners_course_data_for_site(site):
    """
    Back fill learner course grade metrics data
    """

    try:
        courses = get_courses_for_site(site)
    except Exception:  # pylint: disable=broad-except
        courses = []
        msg = ('FIGURES:FAIL populate_daily_metrics unhandled site level'
               ' exception for site[{}]={}')
        logger.exception(msg.format(site.id, site.domain))

    for course in courses:
        try:
            for course_enrollment in course_enrollments_for_course(course.id):
                most_recent_lcgm = LearnerCourseGradeMetrics.objects.filter(
                    user=course_enrollment.user,
                    course_id=str(course_enrollment.course_id)
                ).using(read_replica_or_default()).order_by('date_for').last()

                if most_recent_lcgm:
                    most_recent_lcgm.total_progress_percent = _collect_total_progress_data(
                        user_id=course_enrollment.user.id,
                        course_id=str(course_enrollment.course_id)
                    )
                    most_recent_lcgm.save()

        except Exception as exp:
            logger.exception('populate_daily_metrics failed for course: {0}'.format(course.id))
            logger.exception(exp)
