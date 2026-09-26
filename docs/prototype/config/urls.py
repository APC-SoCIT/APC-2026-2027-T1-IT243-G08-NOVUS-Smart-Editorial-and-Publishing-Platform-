from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.common.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/editorial/", include("apps.editorial.urls")),
    path("api/ai-eval/", include("apps.ai_eval.urls")),
    path("api/content/", include("apps.content.urls")),
    path("api/design/", include("apps.design.urls")),
    path("api/publication/", include("apps.issues.urls")),
    path("api/", include("apps.notifications.urls")),
    path("api/", include("apps.messaging.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/platform/", include("apps.platform.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
