"""Root URL conf.

Per-app routers are included via `apps.<name>.urls`.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

API_V1 = "api/v1/"

urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAPI / docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    # App routes (registered as each phase lands)
    path(API_V1, include("apps.users.urls")),
    path(API_V1, include("apps.references.urls")),
    path(API_V1, include("apps.objects.urls")),
    path(API_V1, include("apps.clients.urls")),
    path(API_V1, include("apps.contracts.urls")),
    path(API_V1, include("apps.finance.urls")),
    path(API_V1, include("apps.notifications.urls")),
    path(API_V1, include("apps.reports.urls")),
    path(API_V1, include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
