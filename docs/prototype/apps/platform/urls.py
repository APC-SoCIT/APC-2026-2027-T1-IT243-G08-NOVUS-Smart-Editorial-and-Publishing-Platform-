from django.urls import path

from .views import PlatformSettingView

urlpatterns = [
    path("settings/", PlatformSettingView.as_view(), name="platform-settings"),
]
