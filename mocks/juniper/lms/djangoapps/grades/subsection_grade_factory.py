"""
SubsectionGrade Factory Class
"""


from collections import OrderedDict
from logging import getLogger


from .course_data import CourseData

log = getLogger(__name__)


class SubsectionGradeFactory(object):
    """
    Factory for Subsection Grades.
    """
    def __init__(self, student, course=None, course_structure=None, course_data=None):
        self.student = student
        self.course_data = course_data or CourseData(student, course=course, structure=course_structure)

        self._cached_subsection_grades = None
        self._unsaved_subsection_grades = OrderedDict()
