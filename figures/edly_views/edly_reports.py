from datetime import datetime, timedelta
import six

from celery.task import task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.contrib.sites.shortcuts import get_current_site
from django.http.request import HttpRequest
from django.db.models import Q
from django.shortcuts import get_object_or_404
from edly_panel_app.api.v1.permissions import AdminAccessEdlyPanel
from edly_panel_app.api.v1.views import (
    GetMonthlyActiveUsers, GetMonthlyCourseCompletions
)
from opaque_keys.edx.keys import CourseKey
from openedx.core.djangoapps.site_configuration.helpers import get_current_site_configuration
from openedx.core.lib.api.authentication import OAuth2Authentication
from openedx.features.course_experience.utils import get_course_outline_block_tree
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from util.query import read_replica_or_default

from figures.compat import CourseEnrollment, CourseOverview
import figures.helpers
from figures.mau import retrieve_live_course_learners_mau_data
from figures import metrics
from figures.models import (
    CourseDailyMetrics, LearnerCourseGradeMetrics,
    SiteDailyMetrics
)
import figures.sites
from figures.serializers import (
    CourseDetailsSerializer,
    CourseTopStatsSerializer,
    GeneralCourseDataSerializer,
    LearnerDetailsSerializer,
    SiteDailyMetricsSerializer
)
from figures.views import CourseEnrollmentViewSet, LearnerDetailsViewSet


class InsightSummaryCSV(APIView):
    """
    Email edly_insight summary report
    """

    authentication_classes = (OAuth2Authentication, SessionAuthentication,)
    permission_classes = [IsAuthenticated, AdminAccessEdlyPanel]

    @staticmethod
    def _get_figures_general_site_metrics(site, query_params):
        date_format = '%d-%m-%Y'
        start_date = query_params.get('start_date')
        end_date = query_params.get('end_date')

        data = metrics.get_edly_monthly_site_metrics(
            site=site,
            date_for=datetime.utcnow().date(),
            start_date=start_date,
            end_date=end_date
        )
        comparison_start_date, comparison_end_date = figures.helpers.get_previous_comparison_time_period(
                                                    figures.helpers.get_date(start_date, date_format),
                                                    figures.helpers.get_date(end_date, date_format),
                                                    )
        comparison_data = metrics.get_edly_monthly_site_metrics(
            site=site,
            date_for=datetime.utcnow().date(),
            start_date=comparison_start_date,
            end_date=comparison_end_date,
        )

        data = metrics.get_total_site_metric_counts_and_percentage_change_for_custom_dates(data, comparison_data)
        return data

    @staticmethod
    def _get_courses_stats(site, order_by):
        course_ids = figures.sites.get_course_keys_for_site(site)
        queryset = CourseDailyMetrics.objects.filter(
            course_id__in=course_ids, date_for=datetime.utcnow()).using(read_replica_or_default())

        if order_by:
            order_by_name = order_by.split(',')[0]
            order_by_sign = order_by.split(',')[1]
            order_by_sign = '' if order_by_sign == 'asc' else '-'
            queryset = queryset.order_by(order_by_sign + order_by_name)

        queryset = queryset[:10]
        serialized_data = CourseTopStatsSerializer(queryset, many=True)
        return serialized_data.data

    @staticmethod
    def _get_maus(request):
        maus = GetMonthlyActiveUsers()
        maus.request = request
        return maus.get(request)

    @staticmethod
    def _get_monthly_course_completions(request):
        monthly_course_completions = GetMonthlyCourseCompletions()
        monthly_course_completions.request = request
        return monthly_course_completions.get(request)

    @staticmethod
    @task()
    def _prepare_summary_data(site, maus, monthly_course_completions, username, user_email, site_configs, query_params):
        general_site_matrics = InsightSummaryCSV._get_figures_general_site_metrics(site, query_params)
        courses_stats_by_enrollment = InsightSummaryCSV._get_courses_stats(site, 'enrollment_count,desc')
        courses_stats_by_learners = InsightSummaryCSV._get_courses_stats(site, 'num_learners_completed,desc')
        raw_data = {
            'courses_stats_by_enrollment': courses_stats_by_enrollment,
            'monthly_course_completions': monthly_course_completions,
            'courses_stats_by_learners': courses_stats_by_learners,
            'general_site_matrics': general_site_matrics,
            'maus': maus,
        }
        figures.helpers.send_insights_summary_report(
            raw_data, user_email, username,
            'Analytics Summary Report', site_configs
        )

    def get(self, request):
        """
        GET /api/edly/insights-summary
        """
        query_params = request.query_params.dict()
        date_format = '%d-%m-%Y'
        start_date = query_params.get('start_date')
        end_date = query_params.get('end_date')
        error_response = figures.helpers.return_invalid_date_range_response(start_date, end_date, date_format)
        if error_response:
            return error_response

        site = getattr(request, 'site', get_current_site(request))
        current_site_configuration = get_current_site_configuration()
        platform_name = current_site_configuration.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
        from_address =  current_site_configuration.get_value('email_from_address', settings.DEFAULT_FROM_EMAIL)
        site_configs = dict(
            platform_name=platform_name,
            from_address=from_address,
        )
        maus = InsightSummaryCSV._get_maus(request).data
        monthly_course_completions = InsightSummaryCSV._get_monthly_course_completions(request).data
        self._prepare_summary_data.delay(
            site.id, maus, monthly_course_completions,
            request.user.username, request.user.email,
            site_configs, query_params
        )
        return Response({
            "message": "Report is being sent. You will recieve an email shortly.",
            "error": False,
        })


class InsightLearnersCSV(APIView):
    """
    Email edly_insight learners report
    """

    authentication_classes = (OAuth2Authentication, SessionAuthentication,)
    permission_classes = [IsAuthenticated, AdminAccessEdlyPanel]

    @staticmethod
    def _get_site_monthly_matrics(site):
        return {
            'current_month': metrics.get_current_month_site_metrics(site),
            'last_month': metrics.get_last_month_site_metrics(site)
        }

    @staticmethod
    def _get_site_daily_matrics(site):
        queryset = SiteDailyMetrics.objects.filter(site=site).using(read_replica_or_default())
        serialized_data = SiteDailyMetricsSerializer(queryset, many=True)
        return serialized_data.data

    @staticmethod
    def _get_maus(request):
        maus = GetMonthlyActiveUsers()
        maus.request = request
        return maus.get(request)

    @staticmethod
    def _get_monthly_course_completions(request):
        monthly_course_completions = GetMonthlyCourseCompletions()
        monthly_course_completions.request = request
        return monthly_course_completions.get(request)

    @staticmethod
    def _get_learners_analytics(site, context, query_params):
        learners_only = query_params.get('learners_only', None)
        queryset = figures.sites.get_edly_users_for_site(site)
        if learners_only and learners_only.lower() == "true":
            queryset = queryset.filter(
                ~Q(courseaccessrole__role='course_creator_group'),
                is_staff=False,
                is_superuser=False
            ).using(read_replica_or_default())

        serialized_data = LearnerDetailsSerializer(queryset, context=context, many=True)
        return serialized_data.data

    @staticmethod
    @task()
    def _prepare_learners_data(site, maus, monthly_course_completions, username, user_email, context, site_configs, query_params):
        site_obj = Site.objects.get(id=site)
        context['course_enrollments'] = figures.sites.get_course_enrollments_for_site(
            site_obj
        )
        context['completed_courses'] = set(
            LearnerCourseGradeMetrics.objects.passed_ids_for_site(
            site=site_obj,
        ))
        site_monthly_matrics = InsightLearnersCSV._get_site_monthly_matrics(site)
        site_daily_matrics = InsightLearnersCSV._get_site_daily_matrics(site)
        all_learners_details = InsightLearnersCSV._get_learners_analytics(site, context, query_params)

        raw_data = {
            'monthly_course_completions': monthly_course_completions,
            'all_learners_details': all_learners_details,
            'site_monthly_matrics': site_monthly_matrics,
            'site_daily_matrics': site_daily_matrics,
            'maus': maus,
        }
        figures.helpers.send_insights_learner_report(
            raw_data, user_email, username,
            'Analytics Learners Report', site_configs
        )

    def get(self, request):
        """
        GET /api/edly/insights-learners
        """
        query_params = request.query_params.dict()
        date_format = '%d-%m-%Y'
        start_date = query_params.get('start_date')
        end_date = query_params.get('end_date')
        error_response = figures.helpers.return_invalid_date_range_response(start_date, end_date, date_format)
        if error_response:
            return error_response

        site = getattr(request, 'site', get_current_site(request))
        current_site_configuration = get_current_site_configuration()
        platform_name = current_site_configuration.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
        from_address =  current_site_configuration.get_value('email_from_address', settings.DEFAULT_FROM_EMAIL)
        site_configs = dict(
            platform_name=platform_name,
            from_address=from_address,
        )
        monthly_course_completions = InsightLearnersCSV._get_monthly_course_completions(request).data
        maus = InsightLearnersCSV._get_maus(request).data
        context = dict()
        context['required_fields'] = figures.helpers.get_required_registration_fields_for_user(
            self.request.user,
            site,
        )
        self._prepare_learners_data.delay(
            site.id, maus, monthly_course_completions,
            request.user.username, request.user.email,
            context, site_configs, query_params
        )
        return Response({
            "message": "Report is being sent. You will recieve an email shortly.",
            "error": False,
        })


class InsightCoursesCSV(APIView):
    """
    Email edly_insight courses report
    """

    authentication_classes = (OAuth2Authentication, SessionAuthentication,)
    permission_classes = [IsAuthenticated, AdminAccessEdlyPanel]

    @staticmethod
    def _get_course_enrollments(request):
        course_enrol_vs = CourseEnrollmentViewSet()
        course_enrol_vs.request = request
        course_enrol_vs.format_kwarg = None
        return course_enrol_vs.list(request).data

    @staticmethod
    def _get_serialized_enrollments(enrollments):
        for enrollment in enrollments:
            for course in enrollment.get('courses', []):
                passed_timestamp = course['progress_data']['passed_timestamp']
                course['progress_data']['passed_timestamp'] = str(passed_timestamp) if passed_timestamp else None

        return enrollments

    @staticmethod
    def _get_course_generals(site):
        queryset = figures.sites.get_courses_for_site(site)
        serialized_data = GeneralCourseDataSerializer(queryset, many=True)
        return serialized_data.data

    @staticmethod
    def _get_course_overview_and_details(site, course_id):
        course_key = CourseKey.from_string(course_id.replace(' ', '+'))
        if figures.helpers.is_multisite():
            course_site = figures.sites.get_site_for_course(course_key)
            if not course_site or site != course_site.id:
                # Raising NotFound instead of PermissionDenied
                raise NotFound()

        course_overview = get_object_or_404(CourseOverview, pk=course_key)
        return (
            GeneralCourseDataSerializer(course_overview).data,
            CourseDetailsSerializer(course_overview).data
        )

    @staticmethod
    @task()
    def _prepare_courses_data(site, user_email, username, site_configs):
        course_generals = InsightCoursesCSV._get_course_generals(site)
        figures.helpers.send_insights_courses_report(
            course_generals, user_email,
            username, 'Courses Analytics Report', site_configs
        )

    @staticmethod
    def _get_courses_maus(site, course_id):
        today = datetime.today()
        thirty_days_ago = today - timedelta(days=30)
        site_obj = site_obj = Site.objects.get(id=site)

        return retrieve_live_course_learners_mau_data(
            site_obj,
            CourseKey.from_string(course_id.replace(' ', '+')),
            thirty_days_ago, today
        )

    @staticmethod
    @task()
    def _prepare_advance_course_data(
        site, user_email, username,
        host, path, site_config, course_id, query_params
    ):
        course_overview, course_details = InsightCoursesCSV._get_course_overview_and_details(site, course_id)
        fake_req = LearnersCSV._get_fake_httprequest(host, path)
        fake_req.site = Site.objects.get(id=site)
        fake_req.user = get_user_model().objects.get(username=username)
        fake_req.query_params = query_params
        course_enrollments = InsightCoursesCSV._get_course_enrollments(fake_req)
        course_enrollments = InsightCoursesCSV._get_serialized_enrollments(course_enrollments)

        learners = get_user_model().objects.filter(
            username__in=[l['user']['username'] for l in course_enrollments]
        )
        all_blocks = dict()
        for learner in learners:
            fake_req.user = learner
            all_blocks[learner.username] = get_course_outline_block_tree(
                fake_req, six.text_type(course_id.replace(' ', '+')),
                learner, allow_start_dates_in_future=True
            )

        course_maus = InsightCoursesCSV._get_courses_maus(site, course_id)
        figures.helpers.send_insights_course_detail_report(
            course_overview, course_details, course_maus, course_enrollments,
            all_blocks, user_email, username, 'Course Detail Report', site_config
        )

    def get(self, request):
        """
        GET /api/edly/insights-courses
        """
        site = getattr(request, 'site', get_current_site(request))
        current_site_configuration = get_current_site_configuration()
        platform_name = current_site_configuration.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
        from_address =  current_site_configuration.get_value('email_from_address', settings.DEFAULT_FROM_EMAIL)
        site_configs = dict(
            platform_name=platform_name,
            from_address=from_address,
        )
        course_id = request.GET.get('course_id')
        if course_id:
            self._prepare_advance_course_data(
                site.id,
                request.user.email,
                request.user.username,
                request.get_host(),
                request.path,
                site_configs,
                course_id,
                request.query_params.copy().dict(),
            )
        else:
            self._prepare_courses_data.delay(site.id, request.user.email, request.user.username, site_configs)

        return Response({
            "message": "Report is being sent. You will recieve an email shortly.",
            "error": False,
        })


class LearnersCSV(APIView):
    """
    Email edly_insights individual learner report
    """

    @staticmethod
    def _get_learner_analytics(request):
        learner_vs = LearnerDetailsViewSet()
        learner_vs.request = request
        learner_vs.format_kwarg = None
        return learner_vs.list(request).data

    @staticmethod
    def _get_fake_httprequest(host, path):
        req = HttpRequest()
        req.path = path
        req.META['HTTP_HOST'] = host
        return req

    @staticmethod
    def _get_serialzied_learner_data(learner_data):
        for course in learner_data.get('courses', []):
            passed_timestamp = course['progress_data']['passed_timestamp']
            course['progress_data']['passed_timestamp'] = str(passed_timestamp) if passed_timestamp else None

        return learner_data

    @staticmethod
    @task()
    def _prepare_learner_data(learner, admin_username, admin_email, host, path, learners_data, site_configs):
        user = get_user_model().objects.get(username=learner)
        req = LearnersCSV._get_fake_httprequest(host, path)
        req.user = user
        course_ids = CourseEnrollment.objects.filter(
            user=user).using(read_replica_or_default()).values_list('course_id', flat=True).distinct()

        all_blocks = dict()
        for course_id in course_ids:
            all_blocks[six.text_type(course_id)] = get_course_outline_block_tree(
                req, six.text_type(course_id),
                user, allow_start_dates_in_future=True
            )

        figures.helpers.send_learner_report(
            learners_data, all_blocks, admin_email, admin_username,
            'Learner Report', site_configs
        )

    def get(self, request):
        """
        GET /api/edly/learner-report
        """
        username = request.GET.get('username')
        if not username:
            return Response({
                "message": "Username missing",
                "error": True,
            }, status=status.HTTP_400_BAD_REQUEST)

        site = getattr(request, 'site', get_current_site(request))
        current_site_configuration = get_current_site_configuration()
        platform_name = current_site_configuration.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
        from_address =  current_site_configuration.get_value('email_from_address', settings.DEFAULT_FROM_EMAIL)
        site_configs = dict(
            platform_name=platform_name,
            from_address=from_address,
        )
        learners_data = self._get_learner_analytics(request)
        learners_data = (learners_data.get('results') or [{}])[0]
        if not learners_data:
            return Response({
                "message": "No Learner Found with this username",
                "error": True,
            }, status=status.HTTP_400_BAD_REQUEST)

        learners_data = self._get_serialzied_learner_data(learners_data)
        self._prepare_learner_data.delay(
            username,
            request.user.username,
            request.user.email,
            request.get_host(),
            request.path,
            learners_data,
            site_configs
        )
        return Response({
            "message": "Report is being sent. You will recieve an email shortly.",
            "error": False,
        })
