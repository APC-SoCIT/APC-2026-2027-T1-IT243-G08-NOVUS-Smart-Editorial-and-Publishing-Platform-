from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.editorial.models import Article

from .serializers import (
    PublicArticleDetailSerializer,
    PublicArticleListSerializer,
    PublicIssueDetailSerializer,
    PublicIssueListSerializer,
)


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


class PublicIssueListView(generics.ListAPIView):
    """UC-8.1: the published issue archive. Browsable by anyone; the download
    itself is subscriber-only."""

    serializer_class = PublicIssueListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        from apps.issues.models import Issue
        return Issue.objects.filter(
            status__in=[Issue.Status.PUBLISHED, Issue.Status.ARCHIVED]
        ).order_by("-number")


class PublicIssueDetailView(generics.RetrieveAPIView):
    serializer_class = PublicIssueDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        from apps.issues.models import Issue
        return Issue.objects.filter(
            status__in=[Issue.Status.PUBLISHED, Issue.Status.ARCHIVED]
        )


class BookmarkListView(generics.ListAPIView):
    """UC-7.1.1: the reader's saved articles."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return PublicArticleListSerializer

    def get_queryset(self):
        from apps.editorial.models import Article
        return (Article.objects
                .filter(bookmarked_by__reader=self.request.user,
                        status=Article.Status.PUBLISHED)
                .order_by("-bookmarked_by__created_at"))


class BookmarkToggleView(APIView):
    """Save or unsave an article.

    A toggle rather than separate create and delete endpoints: the interface
    shows one control whose meaning depends on current state, and splitting it
    would mean the client has to know that state before it can act.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from apps.content.models import Bookmark
        from apps.editorial.models import Article

        try:
            article = Article.objects.get(pk=pk, status=Article.Status.PUBLISHED)
        except Article.DoesNotExist:
            return Response({"detail": "Article not found."}, status=404)

        bookmark, created = Bookmark.objects.get_or_create(
            reader=request.user, article=article)

        if not created:
            bookmark.delete()
            return Response({"saved": False})

        return Response({"saved": True}, status=201)


class BookmarkStatusView(APIView):
    """Which of a set of articles the reader has saved.

    Batched deliberately: a listing page showing twelve articles would
    otherwise make twelve requests to render twelve icons.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.content.models import Bookmark
        ids = request.query_params.get("ids", "")
        wanted = [int(i) for i in ids.split(",") if i.strip().isdigit()]
        saved = set(
            Bookmark.objects.filter(reader=request.user, article_id__in=wanted)
            .values_list("article_id", flat=True)
        )
        return Response({"saved": sorted(saved)})


class IssueDownloadView(APIView):
    """UC-8.1 Download Digital Issues.

    Returns a short-lived signed URL rather than the file itself, and only to
    a subscriber. The object is not publicly addressable, so this endpoint is
    the only route to it — which is what makes the entitlement real rather
    than a decision about whether to show a button.

    The URL expires in fifteen minutes. Sharing one grants a brief window
    rather than permanent access.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        from apps.issues.models import Issue

        try:
            issue = Issue.objects.get(
                pk=pk, status__in=[Issue.Status.PUBLISHED, Issue.Status.ARCHIVED])
        except Issue.DoesNotExist:
            return Response({"detail": "Issue not found."}, status=404)

        user = request.user
        entitled = user.role != user.Role.READER
        if not entitled:
            profile = getattr(user, "reader_profile", None)
            entitled = bool(profile and profile.tier == profile.Tier.SUBSCRIBER)

        if not entitled:
            return Response(
                {"detail": "The digital edition is available to subscribers."},
                status=403)

        design = issue.approved_design
        if not design or not design.file:
            return Response(
                {"detail": "No digital edition is available for this issue."},
                status=404)

        return Response({
            "url": design.file.url,
            "expires_in": 900,
            "filename": f"BOSS-Issue-{issue.number}.pdf",
        })
