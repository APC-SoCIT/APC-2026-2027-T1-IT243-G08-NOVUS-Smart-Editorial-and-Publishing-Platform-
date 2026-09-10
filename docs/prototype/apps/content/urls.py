from django.urls import path

from .views import (
    PublicArticleDetailView,
    PublicArticleListView,
    PublicIssueDetailView,
    PublicIssueListView,
)

urlpatterns = [
    path("articles/", PublicArticleListView.as_view(), name="public-article-list"),
    path("articles/<int:pk>/", PublicArticleDetailView.as_view(), name="public-article-detail"),
    path("issues/", PublicIssueListView.as_view(), name="public-issue-list"),
    path("issues/<int:pk>/", PublicIssueDetailView.as_view(), name="public-issue-detail"),
]
