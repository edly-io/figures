"""
Feature flag support for experiments
"""

import logging

from openedx.core.djangoapps.waffle_utils import CourseWaffleFlag

log = logging.getLogger(__name__)


class ExperimentWaffleFlag(CourseWaffleFlag):
    """
    ExperimentWaffleFlag handles logic around experimental bucketing and whitelisting.

    You'll have one main flag that gates the experiment. This allows you to control the scope
    of your experiment and always provides a quick kill switch.

    But you'll also have smaller related flags that can force bucketing certain users into
    specific buckets of your experiment. Those can be set using a waffle named like
    "main_flag.BUCKET_NUM" (e.g. "course_experience.animated_exy.0") to force
    users that pass the first main waffle check into a specific bucket experience.

    If you pass this flag a course key, tracking calls to segment will be made per-course-run
    (rather than one call overall) and will include the course key.

    You can also control whether the experiment only affects future enrollments by setting
    an ExperimentKeyValue model object with a key of 'enrollment_start' to the date of the
    first enrollments that should be bucketed.

    Bucket 0 is assumed to be the control bucket.

    See a HOWTO here: https://openedx.atlassian.net/wiki/spaces/AC/pages/1250623700/Bucketing+users+for+an+experiment

    When writing tests involving an ExperimentWaffleFlag you must not use the
    override_waffle_flag utility. That will only turn the experiment on or off and won't
    override bucketing. Instead use ExperimentWaffleFlag's override method which
    will do both. Example:

        with MY_EXPERIMENT_WAFFLE_FLAG.override(active=True, bucket=1):
            ...

    or as a decorator:

        @MY_EXPERIMENT_WAFFLE_FLAG.override(active=True, bucket=1)
        def test_my_experiment(self):
            ...

    """
    def __init__(self, waffle_namespace, flag_name, num_buckets=2, experiment_id=None, **kwargs):
        super().__init__(waffle_namespace, flag_name, **kwargs)
        self.num_buckets = num_buckets
        self.experiment_id = experiment_id
        self.bucket_flags = [
            CourseWaffleFlag(waffle_namespace, '{}.{}'.format(flag_name, bucket), flag_undefined_default=False)
            for bucket in range(num_buckets)
        ]
