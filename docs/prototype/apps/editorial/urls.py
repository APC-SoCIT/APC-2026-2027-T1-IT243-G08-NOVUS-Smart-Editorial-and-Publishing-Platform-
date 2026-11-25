from rest_framework.routers import DefaultRouter

from .views import ArticleImageViewSet, ArticleViewSet, CategoryViewSet

router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="article")
router.register("images", ArticleImageViewSet, basename="article-image")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = router.urls
