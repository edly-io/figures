"""

figuers.sites provides a single point to retrieve site specific data

In general, the rest of Figures should call this module to retrieve all site
specific data in edx-platform, such as users, course overviews, and
course enrollments as examples

TODO:
Document how organization site mapping works
"""

from __future__ import absolute_import
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.conf import settings
from django.db.models import Q

# TODO: Add exception handling
import organizations

from openedx.core.djangoapps.content.course_overviews.models import CourseOverview  # noqa pylint: disable=import-error
from openedx.features.edly.models import (
    EdlySubOrganization,
    EdlyUserProfile,
)  # pylint: disable=import-error
from figures.compat import CourseEnrollment, GeneratedCertificate, StudentModule
from figures.helpers import as_course_key
import figures.helpers
from util.query import read_replica_or_default


class CrossSiteResourceError(Exception):
    """
    Raised when a cross site resource access is attempted
    """
    pass


class CourseNotInSiteError(CrossSiteResourceError):
    """
    Raise when an attempt to access a course not in the specified site
    """
    pass


class UnlinkedCourseError(Exception):
    """Raise when we need to fail if we can't get the site for a course

    This will happen in multisite mode if the course is not linked to the site.
    In Tahoe Hawthorn, we use the Appsembler fork of `edx-organizations` to map
    courses to sites. For community and standalone deployments, we don't expect
    courses to map to sites, so we just return the app instance's default site.

    * This is new to support enrollment metrics rework (May 2020)
    * We need to evaluate if we want to make sites.get_site_for_course` to
      raise this automatically. But first we need to make sure we have test
      coverage to make sure we don't introduce new bugs
    """
    pass


def site_to_id(site):
    """
    Helper to cast site or site id to id
    This is helpful for celery tasks that require primitives for
    function parameters
    """
    if isinstance(site, Site):
        return site.id
    else:
        return site


def site_id_iterator(sites_or_site_ids):
    """
    Convenience method to iterate over site or site id iterables.

    This is helpful for iterating over site objects or site ids for
    Celery tasks
    """
    for obj in sites_or_site_ids:
        yield site_to_id(obj)


def default_site():
    """Returns the default site instance if Django settings defines SITE_ID, else None

    Tech debt note: Open edX monkeypatches django.contrib.sites to override
    behavior for getting the current site.
    """
    if getattr(settings, 'SITE_ID', ''):
        return Site.objects.using(read_replica_or_default()).get(pk=settings.SITE_ID)

    return None


def get_site_for_course(course_id):
    """
    Given a course, return the related site or None

    For standalone mode, will always return the site
    For multisite mode, will return the site if there is a mapping between the
    course and the site. Otherwise `None` is returned

    # Implementation notes

    There should be only one organization per course.
    TODO: Figure out how we want to handle ``DoesNotExist``
    whether to let it raise back up raw or handle with a custom exception
    """
    if figures.helpers.is_multisite():
        org_courses = organizations.models.OrganizationCourse.objects.filter(
            course_id=str(course_id)).using(read_replica_or_default())
        if org_courses:
            # Keep until this assumption analyzed
            msg = 'Multiple orgs found for course: {}'
            assert org_courses.count() == 1, msg.format(course_id)
            first_org = org_courses.first().organization
            if hasattr(first_org, 'sites'):
                msg = 'Must have one and only one site. Org is "{}"'
                assert first_org.sites.count() == 1, msg.format(first_org.name)
                site = first_org.sites.first()
            else:
                try:
                    site = first_org.edlysuborganization.lms_site
                except EdlySubOrganization.DoesNotExist:
                    site = None
        else:
            # We don't want to make assumptions of who our consumers are
            # TODO: handle no organizations found for the course
            site = None
    else:
        # Operating in single site / standalone mode, return the default site
        site = Site.objects.using(read_replica_or_default()).get(id=settings.SITE_ID)
    return site


def get_organizations_for_site(site):
    """
    TODO: Refactor the functions in this module that make this call
    """
    return organizations.models.Organization.objects.filter(edlysuborganization__lms_site=site).using(read_replica_or_default())


def get_course_keys_for_site(site):
    if figures.helpers.is_multisite():
        orgs = organizations.models.Organization.objects.filter(
            edlysuborganization__lms_site=site).using(read_replica_or_default())
        org_courses = organizations.models.OrganizationCourse.objects.filter(
            organization__in=orgs).using(read_replica_or_default())
        course_ids = org_courses.values_list('course_id', flat=True)
    else:
        course_ids = CourseOverview.objects.using(
            read_replica_or_default()).all().values_list('id', flat=True)

    return [as_course_key(cid) for cid in course_ids]

def site_course_ids(site):
    """Return a list of string course ids for the site
    """
    if figures.helpers.is_multisite():
        return organizations.models.OrganizationCourse.objects.filter(
                organization__edlysuborganization=site.edly_sub_org_for_lms
            ).values_list('course_id', flat=True)
    else:
        # Needs work. See about returning a queryset
        return [str(key) for key in CourseOverview.objects.all().values_list(
            'id', flat=True)]

def get_courses_for_site(site):
    """Returns the courses accessible by the user on the site

    This function relies on Appsembler's fork of edx-organizations
    """
    if figures.helpers.is_multisite():
        course_keys = get_course_keys_for_site(site)
        courses = CourseOverview.objects.filter(id__in=course_keys).using(read_replica_or_default())
    else:
        courses = CourseOverview.objects.using(read_replica_or_default()).all()
    return courses

def get_user_ids_for_site(site):
    if figures.helpers.is_multisite():
        edx_organizations = organizations.models.Organization.objects.filter(
            edlysuborganization__lms_site=site).using(read_replica_or_default())
        edly_user_profiles = EdlyUserProfile.objects.filter(
            edly_sub_organizations__edx_organization__in=edx_organizations
        ).using(read_replica_or_default()).exclude(
            user__groups__name=settings.ADMIN_CONFIGURATION_USERS_GROUP
        )

        user_ids = edly_user_profiles.values_list('user', flat=True)
    else:
        user_ids = get_user_model().objects.using(read_replica_or_default()).all().exclude(
            groups__name=settings.ADMIN_CONFIGURATION_USERS_GROUP
        ).values_list('id', flat=True)
    return user_ids


def get_users_for_site(site):
    if figures.helpers.is_multisite():
        user_ids = get_user_ids_for_site(site)
        users = get_user_model().objects.filter(id__in=user_ids).using(
            read_replica_or_default())
    else:
        users = get_user_model().objects.using(read_replica_or_default()).all()
    return users


def get_course_enrollments_for_site(site):
    course_keys = get_course_keys_for_site(site)
    return CourseEnrollment.objects.filter(
        course_id__in=course_keys
    ).filter(
        ~Q(user__courseaccessrole__role='course_creator_group'),
        user__edly_profile__edly_sub_organizations=site.edly_sub_org_for_lms,
        user__is_staff=False,
        user__is_superuser=False,
    ).using(read_replica_or_default())


def get_student_modules_for_course_in_site(site, course_id):
    if figures.helpers.is_multisite():
        site_id = site.id
        check_site = get_site_for_course(course_id)
        if not check_site or site_id != check_site.id:
            CourseNotInSiteError('course "{}"" does not belong to site "{}"'.format(
                course_id, site_id))
    return StudentModule.objects.filter(course_id=as_course_key(course_id)).using(read_replica_or_default())


def get_student_modules_for_site(site):
    course_ids = get_course_keys_for_site(site)
    return StudentModule.objects.filter(course_id__in=course_ids).using(read_replica_or_default())


def course_enrollments_for_course(course_id):
    """Return a queryset of all `CourseEnrollment` records for a course

    TODO: Update this to require the site
    Relies on the fact that course_ids are globally unique
    """
    return CourseEnrollment.objects.filter(course_id=as_course_key(course_id)).using(read_replica_or_default())


def enrollments_for_course_ids(course_ids):
    """
    TODO: Update this to require the site
    """
    ckeys = [as_course_key(cid) for cid in course_ids]
    return CourseEnrollment.objects.filter(course_id__in=ckeys)


def users_enrolled_in_courses(course_ids):
    """
    TODO: Update this to require the site
    """
    enrollments = enrollments_for_course_ids(course_ids)
    user_ids = enrollments.order_by('user_id').values('user_id').distinct()
    return get_user_model().objects.filter(id__in=user_ids)


def student_modules_for_course_enrollment(ce):
    """Return a queryset of all `StudentModule` records for a `CourseEnrollment`
    """
    return StudentModule.objects.filter(student=ce.user, course_id=ce.course_id).using(read_replica_or_default())

def site_certificates(site):
    """
    If we want to be clever, we can abstract a function:
    ```
    def site_user_related(site, model_class):
        if is_multisite():
            return model_class.objects.filter(user__organizations__sites__in=[site])
        else:
            return model_class.objects.all()

    def site_certificates(site):
        return site_user_related(GeneratedCertificate)
    ```
    Then:
    """
    if figures.helpers.is_multisite():
        return GeneratedCertificate.objects.filter(
            user__organizations__sites__in=[site])
    else:
        return GeneratedCertificate.objects.all()
