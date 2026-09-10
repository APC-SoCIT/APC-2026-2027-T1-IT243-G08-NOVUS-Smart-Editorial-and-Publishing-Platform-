"""
Module 3: Manage Reports.

Every figure here is aggregated from records the pipeline already produces —
no reporting tables, no duplication. That keeps reports honest: they cannot
drift from the data they describe.
"""
from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import ReaderProfile, User
from apps.ai_eval.models import ArticleEvaluation
from apps.design.models import MagazineDesign
from apps.editorial.models import Article
from apps.issues.models import Issue


class IsStaffRole(permissions.BasePermission):
    message = "Reports are available to editorial staff."

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role != User.Role.READER)


def _window(request, default_days=90):
    days = int(request.query_params.get("days", default_days))
    return timezone.now() - timedelta(days=max(1, min(days, 365))), days


class PipelineReportView(APIView):
    """UC-3.2 Generate Editorial Pipeline Report."""

    permission_classes = [IsStaffRole]

    def get(self, request):
        since, days = _window(request)
        qs = Article.objects.filter(created_at__gte=since)
        today = timezone.now().date()

        by_status = dict(
            qs.values_list("status").annotate(n=Count("id")).values_list("status", "n")
        )
        by_category = list(
            qs.exclude(category="").values("category")
              .annotate(count=Count("id")).order_by("-count")
        )

        published = qs.filter(status=Article.Status.PUBLISHED, published_at__isnull=False)
        turnarounds = [
            (a.published_at - a.created_at).days
            for a in published.only("created_at", "published_at")
        ]

        open_statuses = [Article.Status.ASSIGNED, Article.Status.DRAFTING,
                         Article.Status.REVISION_REQUESTED]

        writers = list(
            User.objects.filter(role=User.Role.WRITER, is_active=True)
            .annotate(
                total=Count("written_articles",
                            filter=Q(written_articles__created_at__gte=since)),
                published=Count("written_articles",
                                filter=Q(written_articles__status=Article.Status.PUBLISHED,
                                         written_articles__created_at__gte=since)),
                open=Count("written_articles",
                           filter=Q(written_articles__status__in=open_statuses)),
                overdue=Count("written_articles",
                              filter=Q(written_articles__status__in=open_statuses,
                                       written_articles__deadline__lt=today)),
            )
            .values("id", "first_name", "last_name", "total", "published", "open", "overdue")
        )

        return Response({
            "window_days": days,
            "total": qs.count(),
            "by_status": by_status,
            "by_category": by_category,
            "published": published.count(),
            "withdrawn": qs.filter(status=Article.Status.WITHDRAWN).count(),
            "overdue_now": Article.objects.filter(
                status__in=open_statuses, deadline__lt=today).count(),
            "avg_turnaround_days": (
                round(sum(turnarounds) / len(turnarounds), 1) if turnarounds else None
            ),
            "writers": sorted(writers, key=lambda w: -w["total"]),
        })


class EvaluationReportView(APIView):
    """UC-3.3 Generate AI Evaluation Summary.

    The measure that matters is the override rate: it tells the desk how often
    editorial judgement disagreed with the gate, which is the evidence for
    whether the threshold is set correctly.
    """

    permission_classes = [IsStaffRole]

    def get(self, request):
        from django.conf import settings

        since, days = _window(request)
        qs = ArticleEvaluation.objects.filter(created_at__gte=since)
        total = qs.count()
        threshold = settings.AI_PASSING_SCORE

        passed = qs.filter(overall_score__gte=threshold).count()
        failed = total - passed
        overridden = qs.filter(is_overridden=True).count()

        # Ten-point score bands, so the shape of the distribution is visible.
        bands = []
        for low in range(0, 100, 10):
            bands.append({
                "band": f"{low}-{low + 9}",
                "count": qs.filter(overall_score__gte=low,
                                   overall_score__lt=low + 10).count(),
            })

        averages = qs.aggregate(
            grammar=Avg("grammar_score"),
            readability=Avg("readability_score"),
            overall=Avg("overall_score"),
        )

        # What the AI most often flags — the desk's recurring weakness.
        counts = {}
        for e in qs.only("suggestions"):
            for s in (e.suggestions or []):
                key = s.get("note_type", "OTHER")
                counts[key] = counts.get(key, 0) + 1
        common = sorted(
            ({"note_type": k, "count": v} for k, v in counts.items()),
            key=lambda x: -x["count"],
        )

        return Response({
            "window_days": days,
            "threshold": threshold,
            "total_evaluations": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total * 100, 1) if total else None,
            "overridden": overridden,
            "override_rate": round(overridden / failed * 100, 1) if failed else None,
            "averages": {k: round(v, 1) if v else None for k, v in averages.items()},
            "distribution": bands,
            "common_issues": common,
            "seeded_present": qs.filter(ai_model__in=["stub", "seed-demo"]).exists(),
        })


class RevenueReportView(APIView):
    """UC-3.1 Generate Revenue Report.

    Subscription counts are real; monetary totals are not, because payment
    processing is Phase 2 (Module 9). The response says so explicitly rather
    than reporting a zero that could be mistaken for a measurement.
    """

    permission_classes = [IsStaffRole]

    def get(self, request):
        since, days = _window(request)

        return Response({
            "window_days": days,
            "subscribers": ReaderProfile.objects.filter(
                tier=ReaderProfile.Tier.SUBSCRIBER).count(),
            "free_readers": ReaderProfile.objects.filter(
                tier=ReaderProfile.Tier.FREE).count(),
            "new_subscribers": ReaderProfile.objects.filter(
                tier=ReaderProfile.Tier.SUBSCRIBER,
                subscription_started_at__gte=since).count(),
            "premium_articles": Article.objects.filter(
                is_premium=True, status=Article.Status.PUBLISHED).count(),
            "issues_published": Issue.objects.filter(
                status=Issue.Status.PUBLISHED).count(),
            "issues_with_replica": sum(
                1 for i in Issue.objects.filter(status=Issue.Status.PUBLISHED)
                if i.approved_design
            ),
            "revenue_available": False,
            "note": ("Transaction totals require payment processing, which is "
                     "scoped for Phase 2 (Module 9). Subscription counts above "
                     "are actual."),
        })


class ProductionReportView(APIView):
    """Design and issue throughput — supports UC-3.2."""

    permission_classes = [IsStaffRole]

    def get(self, request):
        since, days = _window(request)
        designs = MagazineDesign.objects.filter(created_at__gte=since)

        return Response({
            "window_days": days,
            "layouts_submitted": designs.count(),
            "layouts_approved": designs.filter(
                status=MagazineDesign.Status.APPROVED).count(),
            "layouts_revised": designs.filter(
                status=MagazineDesign.Status.REVISION_REQUESTED).count(),
            "superseded_versions": designs.filter(
                status=MagazineDesign.Status.SUPERSEDED).count(),
            "issues": list(
                Issue.objects.annotate(
                    articles=Count("articles"),
                    approved=Count("articles",
                                   filter=Q(articles__status__in=[
                                       Article.Status.APPROVED,
                                       Article.Status.PUBLISHED])),
                ).values("id", "number", "title", "status", "articles", "approved")
                .order_by("-number")[:10]
            ),
        })
