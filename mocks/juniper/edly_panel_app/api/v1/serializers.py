from calendar import month_abbr
from collections import OrderedDict
from datetime import datetime, date, timedelta
from rest_framework import serializers

from edly_panel_app.api.v1.helpers import (
    dates_within_month,
    prepare_monthly_response_data_structure,
)


class UserInformationSerializer(serializers.Serializer):
    class Meta:
        fields = ('data', )

    data = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.query_params = kwargs.pop('context')['request'].GET
        super(UserInformationSerializer, self).__init__(*args, **kwargs)

    def get_data(self, monthly_activities):
        return {
            'detailed_report': self.get_users_info(monthly_activities)
        }

    def get_users_info(self, monthly_activities):
        user_activity_info = {}
        report_type = self.query_params.get('type')
        users_info = [['Report: ' + report_type.capitalize()]]

        for activity in monthly_activities:
            active_year = int(activity['year'])
            active_month = int(activity['month'])

            if active_year not in user_activity_info:
                user_activity_info[active_year] = {}

            if active_month not in user_activity_info[active_year]:
                user_activity_info[active_year][active_month] = []

            user_activity_info[active_year][active_month].append([
                activity['user__username'],
                activity['user__email'],
                activity['user__profile__name'],
            ])

        for year, user_activity in user_activity_info.items():
            for month, user_info in user_activity.items():
                users_info.append(['Month:' + date(1900, month, 1).strftime('%B') + ' - ' + str(year)])
                users_info.append(['Username', 'Email', 'Name'])
                users_info.extend(user_info)
                users_info.append([])

        return users_info


class UserActivitySerializer(serializers.Serializer):
    class Meta:
        fields = ('data', )

    data = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.query_params = kwargs.get('context')['request'].GET
        self.comparison = kwargs.get('context').get('comparison', False)
        self.comparison_st_date = kwargs.get('context').get('comparison_st_date', None)
        self.comparison_ed_date = kwargs.get('context').get('comparison_ed_date', None)
        super(UserActivitySerializer, self).__init__(*args, **kwargs)

    def get_data(self, monthly_activities):
        data = self.prepare_dummy_data()
        start_date = self.comparison_st_date if self.comparison else self.query_params.get('start_date')
        end_date = self.comparison_ed_date if self.comparison else self.query_params.get('end_date')
        if self.query_params.get('type') == 'custom' and dates_within_month(start_date, end_date):
            for activity in monthly_activities:
                data['{}-{}-{}'.format(activity[0], month_abbr[activity[1]], activity[2])] = activity[3]
        else:
            for activity in monthly_activities:
                data['{}-{}'.format(month_abbr[activity[0]], activity[1])] = activity[2]

        return {
            'month_names': list(data.keys()),
            'monthly_users_count': list(data.values())
        }

    def prepare_dummy_data(self):
        start_day, start_month, start_year, end_day, end_month, end_year = 1, 0, 0, 1, 0, 0
        dummy_data = OrderedDict()
        if self.query_params.get('type') == 'yearly':
            start_month = 1
            end_month = 12
            start_year = int(self.query_params.get('year'))
            end_year = start_year
        elif self.query_params.get('type') == 'quarterly':
            quarter = self.query_params.get('quarter')
            # Calculate starting month of the quarter
            start_month = (int(quarter) - 1) * 3 + 1
            start_year = int(self.query_params.get('year'))
            end_month = start_month + 2
            end_year = start_year
        elif self.query_params.get('type') == 'monthly':
            start_date = datetime.strptime(self.query_params.get('start_date'), '%m-%Y')
            end_date = datetime.strptime(self.query_params.get('end_date'), '%m-%Y')
            start_month, start_year = start_date.month, start_date.year
            end_month, end_year = end_date.month, end_date.year
        elif self.query_params.get('type') == 'custom':
            start_date = datetime.strptime(self.query_params.get('start_date'), '%d-%m-%Y')
            end_date = datetime.strptime(self.query_params.get('end_date'), '%d-%m-%Y')
            start_day, start_month, start_year = start_date.day, start_date.month, start_date.year
            end_day, end_month, end_year = end_date.day, end_date.month, end_date.year

            start_date_range = datetime(day=start_day, month=start_month, year=start_year).date()
            end_date_range = datetime(day=end_day, month=end_month, year=end_year).date()
            if dates_within_month(self.query_params.get('start_date'), self.query_params.get('end_date')):
                while start_date_range <= end_date_range:
                    dummy_data['{}-{}-{}'.format(
                        start_date_range.day,
                        month_abbr[start_date_range.month],
                        start_date_range.year,
                    )] = 0

                    start_date_range = start_date_range + timedelta(days=1)
                return dummy_data

        while datetime(
                day=1, month=start_month, year=start_year).date() <= datetime(
            day=1, month=end_month, year=end_year).date():

            dummy_data['{}-{}'.format(month_abbr[start_month], start_year)] = 0
            start_month = start_month + 1
            if start_month == 13:
                start_month = 1
                start_year = start_year + 1

        return dummy_data


class CourseCompletionsSerializer(serializers.Serializer):
    class Meta:
        fields = ('data', )

    data = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        self.query_params = kwargs.pop('context')['request'].GET
        super(CourseCompletionsSerializer, self).__init__(*args, **kwargs)

    def get_data(self, monthly_course_completions):
        data = prepare_monthly_response_data_structure(
            self.query_params.get('type'),
            self.query_params.get('start_date'),
            self.query_params.get('end_date'),
        )
        if self.query_params.get('type') == 'custom' and \
            dates_within_month(self.query_params.get('start_date'), self.query_params.get('end_date')):
            for course_completion in monthly_course_completions:
                data['{}-{}-{}'.format(
                    course_completion[0],
                    month_abbr[course_completion[1]],
                    course_completion[2],
                )] = course_completion[3]
        else:
            for course_completion in monthly_course_completions:
                data['{}-{}'.format(
                    month_abbr[course_completion[0]],
                    course_completion[1],
                )] = course_completion[2]

        return {
            'month_names': list(data.keys()),
            'monthly_course_completions_count': list(data.values()),
            'total_course_completions': sum(list(data.values())),
        }
