import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ai_eval.models import ArticleEvaluation
from apps.ai_eval.serializers import ArticleEvaluationSerializer
from apps.ai_eval.services import evaluate_article
from apps.common.permissions import role_permission
from apps.publishing.services import publish_article

from .models import Article, RevisionNote

logger = logging.getLogger(__name__)
from .serializers import (
    ArticleCreateSerializer,
    ArticleDetailSerializer,
    ArticleListSerializer,
    OverrideSerializer,
    RequestRevisionSerializer,
)


class ArticleViewSet(viewsets.ModelViewSet):
    """
    Module 1: Manage Editorial Pipeline.

    Plain CRUD covers UC-1.3 (Draft) / UC-1.2 (edit while drafting).
    Everything state-changing is a dedicated action below so each one can
    carry its own role permission and match a single use case 1:1 — this is
    what makes the E-AUTH exception-flow test cases pass without extra work.
    """

    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = (Article.objects.select_related("writer", "editor")
              .prefetch_related("evaluations", "revision_notes")
              .order_by("-updated_at"))
        if user.role == user.Role.WRITER:
            return qs.filter(writer=user)
        # Editor / Publisher / Admin see the full pipeline; Reader/Subscriber
        # never hit this queryset — they're routed to apps.content instead.
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return ArticleListSerializer
        if self.action in ("create", "partial_update"):
            return ArticleCreateSerializer
        return ArticleDetailSerializer

    def get_permissions(self):
        if self.action in ("create", "partial_update"):
            return [role_permission("WRITER")()]
        if self.action == "request_revision":
            return [role_permission("EDITOR")()]
        if self.action in ("approve", "override"):
            return [role_permission("EDITOR")()]
        if self.action == "publish":
            return [role_permission("PUBLISHER")()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """UC-1.2 Submit Article for Review, chained into UC-1.11 Generate
        Article Evaluation — the Writer only takes one action; the AI score
        appears automatically on the Editor's queue, matching the wireframes."""
        article = self.get_object()
        if article.writer != request.user:
            return Response({"detail": "Not your article."}, status=status.HTTP_403_FORBIDDEN)
        if article.status not in (Article.Status.DRAFTING, Article.Status.REVISION_REQUESTED):
            return Response(
                {"detail": f"Cannot submit an article in status {article.status}."},
                status=status.HTTP_409_CONFLICT,
            )

        article.status = Article.Status.AWAITING_EVALUATION
        article.save(update_fields=["status", "updated_at"])

        # UC-1.4 E1: an evaluation failure must not strand the article.
        try:
            result = evaluate_article(article)
            evaluation = ArticleEvaluation.objects.create(article=article, **result)
        except Exception:
            logger.exception("Evaluation failed for article %s", article.pk)
            # No score means no gate: send it on for manual review rather than
            # auto-rejecting work the system failed to assess.
            article.status = Article.Status.UNDER_REVIEW
            article.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": "Evaluation unavailable; sent for manual review.",
                 "gate": "BYPASSED", "overall_score": None},
                status=status.HTTP_201_CREATED,
            )

        # AI pre-screening gate. Below the threshold the article goes back to the
        # Writer with the AI's suggestions recorded as revision notes; at or above
        # it, the article reaches the Editor with its evaluation attached.
        threshold = settings.AI_PASSING_SCORE
        passed = evaluation.overall_score >= threshold

        article.returned_by_ai = not passed
        if passed:
            article.status = Article.Status.UNDER_REVIEW
        else:
            article.status = Article.Status.REVISION_REQUESTED
            for s_ in evaluation.suggestions:
                RevisionNote.objects.create(
                    article=article,
                    editor=None,
                    section=s_.get("section", ""),
                    note_type=s_.get("note_type", "STRUCTURE"),
                    instruction=s_.get("instruction", "")[:500],
                    priority=s_.get("priority", "MEDIUM"),
                )
        article.save(update_fields=["status", "returned_by_ai", "updated_at"])

        payload = ArticleEvaluationSerializer(evaluation).data
        payload["gate"] = "PASSED" if passed else "RETURNED"
        payload["threshold"] = threshold
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="request-revision")
    def request_revision(self, request, pk=None):
        """UC-1.4 Request Revision."""
        article = self.get_object()
        serializer = RequestRevisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(article=article, editor=request.user)
        return Response(ArticleDetailSerializer(article).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """UC-1.6 Verify Update Workflow Status — Editor approves a
        non-overridden AI-evaluated article for the Publisher/Designer."""
        article = self.get_object()
        article.status = Article.Status.APPROVED
        article.editor = request.user
        article.save(update_fields=["status", "editor", "updated_at"])
        return Response(ArticleDetailSerializer(article).data)

    @action(detail=True, methods=["post"])
    def override(self, request, pk=None):
        """UC-1.5 Verify Override AI — Editor overrides the AI verdict with
        a mandatory justification, then the article is still approved."""
        article = self.get_object()
        serializer = OverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        evaluation = article.evaluations.order_by("-created_at").first()
        if evaluation is None:
            return Response({"detail": "No AI evaluation to override."}, status=status.HTTP_409_CONFLICT)

        evaluation.is_overridden = True
        evaluation.override_reason = serializer.validated_data["reason"]
        evaluation.overridden_by = request.user
        evaluation.overridden_at = timezone.now()
        evaluation.save()

        article.status = Article.Status.APPROVED
        article.editor = request.user
        article.save(update_fields=["status", "editor", "updated_at"])
        return Response(ArticleDetailSerializer(article).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """UC-2.3 Execute Live Publishing — simplified to a single Article
        for the Phase-1 demo. See README 'Deliberate MVP simplification'."""
        article = self.get_object()
        try:
            publish_article(article)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ArticleDetailSerializer(article).data)
