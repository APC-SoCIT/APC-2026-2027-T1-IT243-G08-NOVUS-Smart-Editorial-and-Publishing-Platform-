from rest_framework.routers import DefaultRouter

from .views import MagazineDesignViewSet

router = DefaultRouter()
router.register("designs", MagazineDesignViewSet, basename="design")

urlpatterns = router.urls
