from rest_framework import generics, permissions

from apps.editorial.models import Article

from .serializers import PublicArticleDetailSerializer, PublicArticleListSerializer


class PublicArticleListView(generics.ListAPIView):
    """UC-7.1 Browse Featured Content. No auth required — matches the
    'Homepage' / 'Article Listing Page' wireframes, which are reachable
    without logging in.

    Phase 2: split this into free vs. premium (UC-8.x paywall) once
    apps.payments/ReaderProfile.tier is wired up — for now every published
    article is public."""

    serializer_class = PublicArticleListSerializer
    permission_classes = [permissions.AllowAny]
    def get_queryset(self):
        qs = Article.objects.filter(status=Article.Status.PUBLISHED).order_by("-published_at")
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs


class PublicArticleDetailView(generics.RetrieveAPIView):
    serializer_class = PublicArticleDetailSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Article.objects.filter(status=Article.Status.PUBLISHED)
