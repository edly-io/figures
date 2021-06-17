# Factories are self documenting

import factory
from factory.django import DjangoModelFactory
from opaque_keys.edx.locator import CourseLocator

from lms.djangoapps.courseware.models import StudentModule
# Imported to re-export
from student.tests.factories import UserFactory  # Imported to re-export


class StudentModuleFactory(DjangoModelFactory):
    class Meta(object):
        model = StudentModule

    module_type = "problem"
    student = factory.SubFactory(UserFactory)
    course_id = CourseLocator("MITx", "999", "Robot_Super_Course")
    state = None
    grade = None
    max_grade = None
    done = 'na'
