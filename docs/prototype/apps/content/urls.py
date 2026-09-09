from django.urls import path

from .views import PublicArticleDetailView, PublicArticleListView

urlpatterns = [
    path("articles/", PublicArticleListView.as_view(), name="public-article-list"),
    path("articles/<int:pk>/", PublicArticleDetailView.as_view(), name="public-article-detail"),
]
