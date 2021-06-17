"""
SubsectionGrade Class
"""


from abc import ABCMeta
from collections import OrderedDict
from logging import getLogger

import six
from django.utils.html import escape
from lazy import lazy

from lms.djangoapps.grades.scores import compute_percent, get_score, possibly_scored
from xmodule import block_metadata_utils, graders
from xmodule.graders import AggregatedScore, ShowCorrectness

log = getLogger(__name__)


class SubsectionGradeBase(six.with_metaclass(ABCMeta, object)):
    """
    Abstract base class for Subsection Grades.
    """

    def __init__(self, subsection):
        self.location = subsection.location
        self.display_name = escape(block_metadata_utils.display_name_with_default(subsection))
        self.url_name = block_metadata_utils.url_name_for_block(subsection)

        self.format = getattr(subsection, 'format', '')
        self.due = getattr(subsection, 'due', None)
        self.graded = getattr(subsection, 'graded', False)
        self.show_correctness = getattr(subsection, 'show_correctness', '')

        self.course_version = getattr(subsection, 'course_version', None)
        self.subtree_edited_timestamp = getattr(subsection, 'subtree_edited_on', None)

        self.override = None

    @property
    def attempted(self):
        """
        Returns whether any problem in this subsection
        was attempted by the student.
        """
        # pylint: disable=no-member
        assert self.all_total is not None, (
            "SubsectionGrade not fully populated yet.  Call init_from_structure or init_from_model "
            "before use."
        )
        return self.all_total.attempted

    def show_grades(self, has_staff_access):
        """
        Returns whether subsection scores are currently available to users with or without staff access.
        """
        return ShowCorrectness.correctness_available(self.show_correctness, self.due, has_staff_access)

    @property
    def attempted_graded(self):
        """
        Returns whether the user had attempted a graded problem in this subsection.
        """
        raise NotImplementedError

    @property
    def percent_graded(self):
        """
        Returns the percent score of the graded problems in this subsection.
        """
        raise NotImplementedError


class ZeroSubsectionGrade(SubsectionGradeBase):
    """
    Class for Subsection Grades with Zero values.
    """

    def __init__(self, subsection, course_data):
        super(ZeroSubsectionGrade, self).__init__(subsection)
        self.course_data = course_data

    @property
    def attempted_graded(self):
        return False

    @property
    def percent_graded(self):
        return 0.0

    @property
    def all_total(self):
        """
        Returns the total score (earned and possible) amongst all problems (graded and ungraded) in this subsection.
        NOTE: This will traverse this subsection's subtree to determine
        problem scores.  If self.course_data.structure is currently null, this means
        we will first fetch the user-specific course structure from the data store!
        """
        return self._aggregate_scores[0]

    @property
    def graded_total(self):
        """
        Returns the total score (earned and possible) amongst all graded problems in this subsection.
        NOTE: This will traverse this subsection's subtree to determine
        problem scores.  If self.course_data.structure is currently null, this means
        we will first fetch the user-specific course structure from the data store!
        """
        return self._aggregate_scores[1]

    @lazy
    def _aggregate_scores(self):
        return graders.aggregate_scores(list(self.problem_scores.values()))

    @lazy
    def problem_scores(self):
        """
        Overrides the problem_scores member variable in order
        to return empty scores for all scorable problems in the
        course.
        NOTE: The use of `course_data.structure` here is very intentional.
        It means we look through the user-specific subtree of this subsection,
        taking into account which problems are visible to the user.
        """
        locations = OrderedDict()  # dict of problem locations to ProblemScore
        for block_key in self.course_data.structure.post_order_traversal(
                filter_func=possibly_scored,
                start_node=self.location,
        ):
            block = self.course_data.structure[block_key]
            if getattr(block, 'has_score', False):
                problem_score = get_score(
                    submissions_scores={}, csm_scores={}, persisted_block=None, block=block,
                )
                if problem_score is not None:
                    locations[block_key] = problem_score
        return locations
