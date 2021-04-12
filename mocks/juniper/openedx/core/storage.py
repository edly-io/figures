"""
Django storage backends for Open edX.
"""


from django.conf import settings
from django.core.files.storage import get_storage_class
from django.utils.lru_cache import lru_cache


class PipelineForgivingMixin(object):
    """
    An extension of the django-pipeline storage backend which forgives missing files.
    """
    def hashed_name(self, name, content=None, **kwargs):
        try:
            out = super(PipelineForgivingMixin, self).hashed_name(name, content, **kwargs)
        except ValueError:
            # This means that a file could not be found, and normally this would
            # cause a fatal error, which seems rather excessive given that
            # some packages have missing files in their css all the time.
            out = name
        return out

    def stored_name(self, name):
        try:
            out = super(PipelineForgivingMixin, self).stored_name(name)
        except ValueError:
            # This means that a file could not be found, and normally this would
            # cause a fatal error, which seems rather excessive given that
            # some packages have missing files in their css all the time.
            out = name
        return out


@lru_cache()
def get_storage(storage_class=None, **kwargs):
    """
    Returns a storage instance with the given class name and kwargs. If the
    class name is not given, an instance of the default storage is returned.
    Instances are cached so that if this function is called multiple times
    with the same arguments, the same instance is returned. This is useful if
    the storage implementation makes http requests when instantiated, for
    example.
    """
    return get_storage_class(storage_class)(**kwargs)
