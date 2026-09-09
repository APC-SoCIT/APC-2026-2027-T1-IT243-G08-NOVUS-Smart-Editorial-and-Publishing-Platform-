from rest_framework.routers import DefaultRouter

from .views import ArticleEvaluationViewSet

router = DefaultRouter()
router.register("evaluations", ArticleEvaluationViewSet, basename="evaluation")

urlpatterns = router.urls
