from copy import deepcopy
from django.conf import settings
from django.db.models import Count
from django.db.models import Q
from django.db.models.functions import ExtractDay, ExtractMonth, ExtractYear
from django.db.models.query import QuerySet

from edly_panel_app.api.v1.constants import ERROR_MESSAGES

from edly_panel_app.api.v1.helpers import (
    dates_within_month,
    get_date,
    get_first_day_of_month,
    get_last_day_of_month,
    return_invalid_date_range_response,
    validate_year,
    filter_records_by_roles,
    get_previous_comparison_time_period,
    calculate_percentage_change,
    convert_date_to_str,
    send_maus_report,
)
from edly_panel_app.api.v1.serializers import (
    CourseCompletionsSerializer,
    UserActivitySerializer,
    UserInformationSerializer,
)
from edly_panel_app.models import EdlyUserActivity
from openedx.core.djangoapps.site_configuration.helpers import get_current_site_configuration
from openedx.core.lib.api.authentication import OAuth2Authentication
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from edly_panel_app.api.v1.permissions import CanAccessEdlyPanel
from rest_framework.response import Response
from rest_framework.views import APIView
from student.models import User
from util.query import read_replica_or_default


class GetMonthlyActiveUsers(APIView):
    """
    Get monthly active users on the basis of year, quarter, and month.
    """
    authentication_classes = (OAuth2Authentication, SessionAuthentication,)
    permission_classes = [IsAuthenticated, CanAccessEdlyPanel]

    def get_queryset(self, comparison=False):
        """
        Return a queryset on the basis of filter type.
        """
        MONTHLY_USER_TYPE = {
            'yearly': self.get_queryset_by_year,
            'quarterly': self.get_queryset_by_quarter,
            'monthly': self.get_queryset_by_date_range,
            'custom': self.get_queryset_by_custom_range,
        }

        try:
            request_type = self.request.GET.get('type')
            if request_type == 'yearly':
                year = self.request.GET.get('year')
                if comparison:
                    year = get_previous_comparison_time_period(request_type, year=year)

                queryset =  MONTHLY_USER_TYPE.get(request_type)(year=year)
                return queryset
            elif request_type == 'quarterly':
                year = self.request.GET.get('year')
                quarter = self.request.GET.get('quarter')
                if comparison:
                    year, quarter = get_previous_comparison_time_period(
                        request_type,
                        year=year,
                        quarter=quarter,
                    )

                queryset = MONTHLY_USER_TYPE.get(request_type)(year=year, quarter=quarter)
                return queryset
            elif request_type == 'monthly':
                start_date = self.request.GET.get('start_date')
                end_date = self.request.GET.get('end_date')
                queryset = MONTHLY_USER_TYPE.get(request_type)(start_date=start_date, end_date=end_date)
            elif request_type == 'custom':
                start_date = self.request.GET.get('start_date')
                end_date = self.request.GET.get('end_date')
                date_format = '%d-%m-%Y'
                if comparison:
                    start_date, end_date = get_previous_comparison_time_period(
                            request_type,
                            start_date=get_date(start_date, date_format=date_format),
                            end_date=get_date(end_date, date_format=date_format),
                        )
                    start_date = convert_date_to_str(start_date, date_format=date_format)
                    end_date = convert_date_to_str(end_date, date_format=date_format)

                queryset = MONTHLY_USER_TYPE.get(request_type)(start_date=start_date, end_date=end_date)
                return queryset
            else:
                queryset = MONTHLY_USER_TYPE.get(request_type)()

            return queryset
        except TypeError:
            return Response(
                {'error': ERROR_MESSAGES.get('INVALID_TYPE')},
                status=status.HTTP_406_NOT_ACCEPTABLE
            )

    def get_queryset_by_year(self,  **kwargs):
        """
        Filter data on the basis of year.
        """
        year = kwargs.get('year')
        include_users_data = self.request.GET.get('include_users_data')
        course_activity_filter = self.request.GET.get('course_activity_filter', None)
        roles = self.request.GET.get('roles', None)
        if not validate_year(year):
            return Response(
                {'error': ERROR_MESSAGES.get('INVALID_YEAR')},
                status=status.HTTP_406_NOT_ACCEPTABLE
            )

        if not self._validate_report_request(include_users_data):
            return Response(
                {'error': ERROR_MESSAGES.get('INVALID_REPORT_REQUEST')},
                status=status.HTTP_406_NOT_ACCEPTABLE
            )

        monthly_activities = EdlyUserActivity.objects.filter(
            activity_date__year=year,
            edly_sub_organization=self.request.site.edly_sub_org_for_lms
        ).using(
            read_replica_or_default()
        ).exclude(
            user__groups__name=settings.ADMIN_CONFIGURATION_USERS_GROUP
        ).annotate(
            year=ExtractYear('activity_date')
        ).annotate(
            month=ExtractMonth('activity_date')
        )

        if roles:
            monthly_activities = filter_records_by_roles(monthly_activities, roles)

        if course_activity_filter and course_activity_filter.lower() == "true":
            monthly_activities = monthly_activities.filter(
                user__edly_profile__course_activity_date__year=year
            )

        if include_users_data:
            monthly_activities = monthly_activities.order_by('month').values(
                'user__username', 'user__email', 'user__profile__name', 'month', 'year'
            ).distinct()
        else:
            monthly_activities = monthly_activities.values_list('month', 'year').annotate(Count('user', distinct=True))

        return monthly_activities

    def get_queryset_by_quarter(self, **kwargs):
        """
        Filter data on the basis of specific quarter of a particular year.
        """
        year = kwargs.get('year')
        quarter = kwargs.get('quarter')
        include_users_data = self.request.GET.get('include_users_data')
        course_activity_filter = self.request.GET.get('course_activity_filter', None)
        roles = self.request.GET.get('roles', None)
        if not (self._validate_quarter(quarter) and validate_year(year)):
            return Response(
                {'error': ERROR_MESSAGES.get('INVALID_QUARTER_OR_YEAR')},
                status=status.HTTP_406_NOT_ACCEPTABLE
            )

        if not self._validate_report_request(include_users_data):
            return Response(
                {'error': ERROR_MESSAGES.get('INVALID_REPORT_REQUEST')},
                status=status.HTTP_406_NOT_ACCEPTABLE
            )

        quarter_months = {
            '1': [1, 2, 3],
            '2': [4, 5, 6],
            '3': [7, 8, 9],
            '4': [10, 11, 12],
        }
        months = quarter_months[quarter]
        monthly_activities = EdlyUserActivity.objects.filter(
            activity_date__year=year,
            activity_date__month__in=months,
            edly_sub_organization=self.request.site.edly_sub_org_for_lms
        ).using(
            read_replica_or_default()
        ).exclude(
            user__groups__name=settings.ADMIN_CONFIGURATION_USERS_GROUP
        ).annotate(
            year=ExtractYear('activity_date')
        ).annotate(
            month=ExtractMonth('activity_date')
        )

        if roles:
            monthly_activities = filter_records_by_roles(monthly_activities, roles)

        if course_activity_filter and course_activity_filter.lower() == "true":
            monthly_activities = monthly_activities.filter(
                user__edly_profile__course_activity_date__year=year,
                user__edly_profile__course_activity_date__month__in=months
            )

        if include_users_data:
            monthly_activities = monthly_activities.order_by('month').values(
                'user__username', 'user__email', 'user__profile__name', 'month', 'year'
            ).distinct()
        else:
            monthly_activities = monthly_activities.values_list('month', 'year').annotate(Count('user', distinct=True))

        return monthly_activities

    def get_queryset_by_date_range(self, **kwargs):
        """
        Filter data on the basis of particular date range.
        """
        start_date = kwargs.get('start_date')
        end_date =  kwargs.get('end_date')
        include_users_data = self.request.GET.get('include_users_data')
        course_activity_filter = self.request.GET.get('course_activity_filter', None)
        roles = self.request.GET.get('roles', None)

        error_response = return_invalid_date_range_response(start_date, end_date)
        if error_response:
            return error_response

        if not self._validate_report_request(include_users_data):
            return Response(
                {'error': ERROR_MESSAGES.get('INVALID_REPORT_REQUEST')},
                status=status.HTTP_406_NOT_ACCEPTABLE
            )

        start_date = get_date(start_date)
        end_date = get_last_day_of_month(end_date)

        monthly_activities = EdlyUserActivity.objects.filter(
            activity_date__range=[start_date, end_date],
            edly_sub_organization=self.request.site.edly_sub_org_for_lms
        ).using(
            read_replica_or_default()
        ).exclude(
            user__groups__name=settings.ADMIN_CONFIGURATION_USERS_GROUP
        ).annotate(
            year=ExtractYear('activity_date')
        ).annotate(
            month=ExtractMonth('activity_date')
        )

        if roles:
            monthly_activities = filter_records_by_roles(monthly_activities, roles)

        if course_activity_filter and course_activity_filter.lower() == "true":
            monthly_activities = monthly_activities.filter(
                user__edly_profile__course_activity_date__range=[start_date, end_date]
            )

        if include_users_data:
            monthly_activities = monthly_activities.order_by('month').values(
                'user__username', 'user__email', 'user__profile__name', 'month', 'year'
            ).distinct()
        else:
            monthly_activities = monthly_activities.values_list('month', 'year').annotate(Count('user', distinct=True))

        return monthly_activities

    def get_queryset_by_custom_range(self, **kwargs):
        """
        Filter data on the basis of particular date range.
        """
        start_date = kwargs.get('start_date')
        end_date =  kwargs.get('end_date')
        include_users_data = self.request.GET.get('include_users_data')
        course_activity_filter = self.request.GET.get('course_activity_filter', None)
        roles = self.request.GET.get('roles', None)
        monthly_values = ['user__username', 'user__email', 'user__profile__name', 'month', 'year']
        activity_granularity = ['month', 'year']

        error_response = return_invalid_date_range_response(start_date, end_date, '%d-%m-%Y')
        if error_response:
            return error_response

        if not self._validate_report_request(include_users_data):
            return Response(
                {'error': ERROR_MESSAGES.get('INVALID_REPORT_REQUEST')},
                status=status.HTTP_406_NOT_ACCEPTABLE
            )

        date_format = '%d-%m-%Y'
        start_date = get_date(start_date, date_format)
        end_date = get_date(end_date, date_format)
        monthly_activities = EdlyUserActivity.objects.filter(
            activity_date__range=[start_date, end_date],
            edly_sub_organization=self.request.site.edly_sub_org_for_lms
        ).using(
            read_replica_or_default()
        ).exclude(
            user__groups__name=settings.ADMIN_CONFIGURATION_USERS_GROUP
        ).annotate(
            year=ExtractYear('activity_date')
        ).annotate(
            month=ExtractMonth('activity_date')
        )
        if dates_within_month(kwargs.get('start_date'), kwargs.get('end_date')):
            monthly_activities = monthly_activities.annotate(
                day=ExtractDay('activity_date')
            )
            monthly_values.append('day')
            activity_granularity.insert(0, 'day')

        if roles:
            monthly_activities = filter_records_by_roles(monthly_activities, roles)

        if course_activity_filter and course_activity_filter.lower() == "true":
            monthly_activities = monthly_activities.filter(
                user__edly_profile__course_activity_date__range=[start_date, end_date]
            )

        if include_users_data:
            monthly_activities = monthly_activities.order_by('month').values(
                *monthly_values
            ).distinct()
        else:
            monthly_activities = monthly_activities.values_list(
                *activity_granularity
            ).annotate(Count('user', distinct=True))

        return monthly_activities

    def _get_users_count(self, start_date, end_date):
        users_count = EdlyUserActivity.objects.filter(
            activity_date__range=[start_date, end_date],
            edly_sub_organization=self.request.site.edly_sub_org_for_lms
        ).using(
            read_replica_or_default()
        ).values('user').distinct().count()

        return users_count

    def get(self, request):
        include_users_data = request.GET.get('include_users_data')
        request_type = request.GET.get('type')
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')

        if not include_users_data:
            queryset = self.get_queryset()
            if not isinstance(queryset, QuerySet):
                return queryset

            comparison_queryset = self.get_queryset(comparison=True)
            if not isinstance(comparison_queryset, QuerySet):
                return comparison_queryset

            if request_type == 'custom':
                date_format = '%d-%m-%Y'
                comparison_st_date, comparison_ed_date = get_previous_comparison_time_period(
                    request_type,
                    start_date=get_date(start_date, date_format=date_format),
                    end_date=get_date(end_date, date_format=date_format),
                )
                comparison_serializer_data = UserActivitySerializer(
                    comparison_queryset,
                    context={
                        'request': request,
                        'comparison': True,
                        'comparison_st_date': convert_date_to_str(comparison_st_date, date_format=date_format),
                        'comparison_ed_date': convert_date_to_str(comparison_ed_date, date_format=date_format),
                    }
                ).data
            else:
                comparison_serializer_data = UserActivitySerializer(
                    comparison_queryset,
                    context={
                        'request': request,
                        'comparison': True,
                    }
                ).data

            serializer_data = UserActivitySerializer(queryset, context={'request': request}).data
            total_users_count = 0
            if request_type == 'monthly':
                total_users_count = serializer_data.get('data').get('monthly_users_count')[-1]
                monthly_users_count = comparison_serializer_data.get('data').get('monthly_users_count')
                comparison_total_users_count = monthly_users_count[-2] if len(monthly_users_count) > 1 else 0
            elif request_type == 'custom' and dates_within_month(start_date, end_date):
                date_format = '%d-%m-%Y'
                total_users_count = self._get_users_count(
                    start_date=get_date(start_date, date_format=date_format),
                    end_date=get_date(end_date, date_format=date_format),
                )
                comparison_st_date, comparison_ed_date = get_previous_comparison_time_period(
                    request_type,
                    start_date=get_date(start_date, date_format=date_format),
                    end_date=get_date(end_date, date_format=date_format),
                )
                comparison_total_users_count = self._get_users_count(
                    comparison_st_date, comparison_ed_date
                )
            else:
                total_users_count = sum(serializer_data.get('data').get('monthly_users_count'))
                comparison_total_users_count = sum(comparison_serializer_data.get('data').get('monthly_users_count'))

            serializer_data.get('data')['total_users_count'] = total_users_count
            percentage_change = calculate_percentage_change(comparison_total_users_count, total_users_count)
            serializer_data.get('data')['percentage_change'] = percentage_change

        else:
            queryset = self.get_queryset()
            if not isinstance(queryset, QuerySet):
                return queryset

            serializer_data = UserInformationSerializer(queryset, context={'request': request}).data

        csv_flag = self.request.GET.get('csv', 'false')
        if csv_flag.lower() == 'true':
            current_site_configuration = get_current_site_configuration()
            platform_name = current_site_configuration.get_value('PLATFORM_NAME', settings.PLATFORM_NAME)
            from_address =  current_site_configuration.get_value('email_from_address', settings.DEFAULT_FROM_EMAIL)
            site_configuration_dict = dict(
                platform_name=platform_name,
                from_address=from_address,
            )
            send_maus_report.delay(
                deepcopy(serializer_data), self.request.user.email,
                self.request.user.username, request_type, site_configuration_dict
            )
            return Response("Report is being sent. You will recieve an email shortly.", status=status.HTTP_200_OK)

        return Response(serializer_data)

    def _validate_quarter(self, quarter):
        try:
            quarter = int(quarter)
            return 1 <= quarter <= 4
        except (ValueError, TypeError):
            return False

    def _validate_report_request(self, include_users_data):
        if include_users_data:
            return include_users_data.lower() == 'true'

        return True


class GetMonthlyCourseCompletions(APIView):
    """
    Get monthly courses completions of all users on the basis of month.
    """
    permission_classes = [IsAuthenticated, CanAccessEdlyPanel]

    def get_queryset(self, start_date, end_date):
        """
        Return queryset on the basis of filter type.
        """
        USER_ENROLLMENT_TYPE = {
            'monthly': self.get_queryset_by_date_range,
            'custom': self.get_queryset_by_custom_date_range,
        }

        request_type = self.request.GET.get('type')
        try:
            if request_type  == 'custom' and not dates_within_month(start_date, end_date, is_datetime=True):
                request_type = 'monthly'

            queryset = USER_ENROLLMENT_TYPE.get(request_type)(start_date, end_date)
            return queryset
        except TypeError:
            return Response(
                {
                    'error': ERROR_MESSAGES.get('INVALID_TYPE')
                },
                status=status.HTTP_406_NOT_ACCEPTABLE
            )

    def get_queryset_by_date_range(self, start_date, end_date):
        """
        Filter enrollments data on the basis of particular date range.
        """
        learners_only = self.request.GET.get('learners_only', None)
        users = User.objects.filter(
            edly_multisite_user__sub_org=self.request.site.edly_sub_org_for_lms
        ).using(
            read_replica_or_default()
        )
        if learners_only and learners_only.lower() == "true":
            users = users.filter(
                ~Q(courseaccessrole__role='course_creator_group'),
                is_staff=False,
                is_superuser=False
            ).using(
                read_replica_or_default()
            )

        monthly_course_completions = PersistentCourseGrade.objects.filter(
            passed_timestamp__isnull=False
        ).filter(
            passed_timestamp__range=[start_date, end_date],
            user_id__in=users.values_list('pk', flat=True)
        ).using(
            read_replica_or_default()
        ).annotate(
            year=ExtractYear('passed_timestamp')
        ).annotate(
            month=ExtractMonth('passed_timestamp')
        )

        serialized_monthly_course_completions = monthly_course_completions.values_list(
            'month', 'year',
        ).annotate(Count('id', distinct=True)).order_by('month', 'year')

        return serialized_monthly_course_completions

    def get_queryset_by_custom_date_range(self, start_date, end_date):
        """
        Filter enrollments data on the basis of a custom date range.
        """
        learners_only = self.request.GET.get('learners_only', None)
        users = User.objects.filter(
            edly_multisite_user__sub_org=self.request.site.edly_sub_org_for_lms
        ).using(
            read_replica_or_default()
        )
        if learners_only and learners_only.lower() == "true":
            users = users.filter(
                ~Q(courseaccessrole__role='course_creator_group'),
                is_staff=False,
                is_superuser=False
            ).using(
                read_replica_or_default()
            )

        monthly_course_completions = PersistentCourseGrade.objects.filter(
            passed_timestamp__isnull=False
        ).filter(
            passed_timestamp__range=[start_date, end_date],
            user_id__in=users.values_list('pk', flat=True)
        ).using(
            read_replica_or_default()
        ).annotate(
            year=ExtractYear('passed_timestamp')
        ).annotate(
            month=ExtractMonth('passed_timestamp')
        ).annotate(
            day=ExtractDay('passed_timestamp')
        )

        serialized_monthly_course_completions = monthly_course_completions.values_list(
            'day', 'month', 'year',
        ).annotate(Count('id', distinct=True)).order_by('day', 'month', 'year')
        return serialized_monthly_course_completions

    def get(self, request):
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        date_format = '%d-%m-%Y' if request.GET.get('type') == 'custom' else '%m-%Y'
        error_response = return_invalid_date_range_response(start_date, end_date, date_format)
        if error_response:
            return error_response

        if request.GET.get('type') == 'custom' and \
            dates_within_month(request.GET.get('start_date'), request.GET.get('end_date')):
            start_date = get_date(start_date, date_format)
            end_date = get_date(end_date, date_format)
        else:
            start_date = get_first_day_of_month(start_date, date_format)
            end_date = get_last_day_of_month(end_date, date_format)

        queryset = self.get_queryset(start_date, end_date)
        comparison_start_date, comparison_end_date = get_previous_comparison_time_period(
            'custom',
            start_date=start_date,
            end_date=end_date
        )
        comparison_queryset = self.get_queryset(comparison_start_date, comparison_end_date)
        if not isinstance(queryset, QuerySet):
            return queryset

        serializer_data = CourseCompletionsSerializer(queryset, context={'request': request}).data

        comparison_course_completions_total = 0

        if request.GET.get('type') == 'custom' and \
            dates_within_month(comparison_start_date, comparison_end_date, is_datetime=True):
            for course_completions in  comparison_queryset:
                comparison_course_completions_total += course_completions[3]
        else:
            for course_completions in  comparison_queryset:
                comparison_course_completions_total += course_completions[2]

        percentage_change = calculate_percentage_change(comparison_course_completions_total,serializer_data['data']['total_course_completions'])
        serializer_data.get('data')['percentage_change'] = percentage_change

        return Response(serializer_data)
