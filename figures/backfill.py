"""Backfills metrics models

Initially developed to support API performance improvements
"""

from datetime import datetime
from dateutil.rrule import rrule, MONTHLY
from dateutil.relativedelta import relativedelta

from django.utils.timezone import utc

from courseware.models import StudentModule
from figures.sites import get_student_modules_for_site
from figures.pipeline.site_monthly_metrics import fill_month
from openedx.features.edly.models import EdlyUserProfile


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

    return backfilled


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
