from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import UploadCompleteView, UploadPresignView, MagazineDesignViewSet

router = DefaultRouter()
router.register("designs", MagazineDesignViewSet, basename="design")

urlpatterns = router.urls + [
    path("uploads/presign/", UploadPresignView.as_view(), name="design-presign"),
    path("uploads/complete/", UploadCompleteView.as_view(), name="design-complete"),
]
