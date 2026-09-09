from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/editorial/", include("apps.editorial.urls")),
    path("api/ai-eval/", include("apps.ai_eval.urls")),
    path("api/content/", include("apps.content.urls")),
]
