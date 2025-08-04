"""URL patterns includes for Figures development website
"""

from __future__ import absolute_import
from django.urls import include, path, re_path
from django.contrib import admin
from django.conf import settings
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='homepage.html'), name='homepage'),
    re_path(r'^admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path('figures/', include(('figures.urls', 'figures'), namespace='figures')),
]

if settings.ENABLE_OPENAPI_DOCS:
    from rest_framework import permissions
    from drf_yasg2.views import get_schema_view
    from drf_yasg2 import openapi
    schema_view = get_schema_view(
       openapi.Info(
          title="Figures API",
          default_version='v1',
          description="Figures devsite API",
          terms_of_service="https://www.google.com/policies/terms/",
          contact=openapi.Contact(email="contact@snippets.local"),
          license=openapi.License(name="BSD License"),
       ),
       public=True,
       permission_classes=[permissions.AllowAny],
    )
    urlpatterns += [
        re_path(r'^api-docs(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0),
            name='schema-json'),
        path('api-docs/',
            schema_view.with_ui('swagger', cache_timeout=0),
            name='schema-swagger-ui'),
        path('redoc/',
            schema_view.with_ui('redoc', cache_timeout=0),
            name='schema-redoc'),
    ]


if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
