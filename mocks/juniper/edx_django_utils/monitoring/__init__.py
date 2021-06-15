"""
Metrics utilities public api
See README.rst for details.
"""
from .internal.utils import (
    accumulate,
    increment,
    record_exception,
    set_custom_attribute,
    set_custom_attributes_for_course_key
)
from .internal.transactions import function_trace
