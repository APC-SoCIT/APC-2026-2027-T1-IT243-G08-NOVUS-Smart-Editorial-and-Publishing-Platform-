from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import DeadlineCheckView, NotificationViewSet

router = DefaultRouter()
router.register("notifications", NotificationViewSet, basename="notification")

urlpatterns = router.urls + [
    path("scheduler/check-deadlines/", DeadlineCheckView.as_view(),
         name="scheduler-deadlines"),
]
