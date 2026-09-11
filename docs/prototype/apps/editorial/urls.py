from rest_framework.routers import DefaultRouter

from .views import ArticleImageViewSet, ArticleViewSet

router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="article")
router.register("images", ArticleImageViewSet, basename="article-image")

urlpatterns = router.urls
