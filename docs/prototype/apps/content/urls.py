from django.urls import path

from .views import (
    BookmarkListView,
    BookmarkStatusView,
    BookmarkToggleView,
    PublicArticleDetailView,
    PublicArticleListView,
    PublicIssueDetailView,
    PublicIssueListView,
)

urlpatterns = [
    path("articles/", PublicArticleListView.as_view(), name="public-article-list"),
    path("articles/<int:pk>/", PublicArticleDetailView.as_view(), name="public-article-detail"),
    path("bookmarks/", BookmarkListView.as_view(), name="bookmarks"),
    path("bookmarks/status/", BookmarkStatusView.as_view(), name="bookmark-status"),
    path("bookmarks/<int:pk>/toggle/", BookmarkToggleView.as_view(),
         name="bookmark-toggle"),
    path("issues/", PublicIssueListView.as_view(), name="public-issue-list"),
    path("issues/<int:pk>/", PublicIssueDetailView.as_view(), name="public-issue-detail"),
]
