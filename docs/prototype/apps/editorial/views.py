import logging

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.ai_eval.models import ArticleEvaluation
from apps.ai_eval.serializers import ArticleEvaluationSerializer
from apps.ai_eval.services import evaluate_article
from apps.common.permissions import role_permission
from apps.notifications.models import Notification
from apps.notifications.services import notify
from apps.publishing.services import NotReady, publish_article

from .models import Article, ArticleImage, ArticleVersion, RevisionNote

logger = logging.getLogger(__name__)
from .serializers import (
    ArticleCreateSerializer,
    ArticleImageSerializer,
    AssignArticleSerializer,
    ArticleDetailSerializer,
    ArticleListSerializer,
    OverrideSerializer,
    RequestRevisionSerializer,
    WithdrawSerializer,
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
    # Hero images arrive as multipart alongside the text fields.
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        qs = (Article.objects.select_related("writer", "editor")
              .prefetch_related("evaluations", "revision_notes")
              .order_by("-updated_at"))
        if user.role == user.Role.WRITER:
            return qs.filter(writer=user)
        if user.role == user.Role.GRAPHIC_DESIGNER:
            # UC-1.12: a Designer lays out finalised copy only. Drafts and
            # articles still under review are not theirs to see.
            return qs.filter(status__in=[Article.Status.APPROVED,
                                         Article.Status.PUBLISHED])
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
        if self.action in ("approve", "override", "assign_to_issue",
                           "assign", "reassign"):
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
        if article.status not in (Article.Status.ASSIGNED, Article.Status.DRAFTING,
                                  Article.Status.REVISION_REQUESTED):
            return Response(
                {"detail": f"Cannot submit an article in status {article.status}."},
                status=status.HTTP_409_CONFLICT,
            )

        # UC-1.4: snapshot the submitted copy before evaluation so the
        # revision loop keeps a record of what was actually sent.
        last = article.versions.first()
        ArticleVersion.objects.create(
            article=article,
            number=(last.number + 1) if last else 1,
            title=article.title,
            body=article.body,
            excerpt=article.excerpt,
            submitted_by=request.user,
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

        if passed:
            notify(article.editor or article.assigned_by,
                   Notification.Kind.SUBMITTED,
                   f'"{article.title}" passed pre-screening and awaits review.',
                   f"/editor/review/{article.id}")
        else:
            notify(article.writer, Notification.Kind.RETURNED_BY_AI,
                   f'"{article.title}" scored {evaluation.overall_score} and was returned for revision.',
                   f"/writer/compose/{article.id}")

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
        notify(article.writer, Notification.Kind.REVISION,
               f'{request.user.get_full_name()} requested revisions on "{article.title}".',
               f"/writer/compose/{article.id}")
        return Response(ArticleDetailSerializer(article).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """UC-1.6 Verify Update Workflow Status — Editor approves a
        non-overridden AI-evaluated article for the Publisher/Designer."""
        article = self.get_object()
        article.status = Article.Status.APPROVED
        article.editor = request.user
        article.save(update_fields=["status", "editor", "updated_at"])
        notify(article.writer, Notification.Kind.APPROVED,
               f'"{article.title}" was approved.',
               f"/writer/compose/{article.id}")
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

    @action(detail=False, methods=["post"])
    def assign(self, request):
        """UC-1.1 Assign Article. Creates the record in ASSIGNED status and
        hands it to the named Writer with a brief and a deadline."""
        serializer = AssignArticleSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        article = serializer.save()
        notify(article.writer, Notification.Kind.ASSIGNED,
               f'You have been assigned "{article.title}".',
               f"/writer/compose/{article.id}")
        return Response(ArticleDetailSerializer(article).data,
                        status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reassign(self, request, pk=None):
        """UC-1.1 A1: move an assignment to a different Writer, for reallocation
        when the original Writer cannot deliver."""
        from apps.accounts.models import User

        article = self.get_object()
        if article.status not in (Article.Status.ASSIGNED, Article.Status.DRAFTING):
            return Response(
                {"detail": "Only an unsubmitted article can be reassigned."},
                status=status.HTTP_409_CONFLICT,
            )
        try:
            writer = User.objects.get(pk=request.data.get("writer"),
                                      role=User.Role.WRITER)
        except User.DoesNotExist:
            return Response({"detail": "Writer not found."},
                            status=status.HTTP_404_NOT_FOUND)

        article.writer = writer
        if request.data.get("deadline"):
            article.deadline = request.data["deadline"]
        article.save(update_fields=["writer", "deadline", "updated_at"])
        notify(writer, Notification.Kind.ASSIGNED,
               f'"{article.title}" has been reassigned to you.',
               f"/writer/compose/{article.id}")
        return Response(ArticleDetailSerializer(article).data)

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        """UC-1.10 Withdraw Article. Removes an unpublished article from the
        active pipeline and corrects any issue it belonged to."""
        article = self.get_object()

        if article.status == Article.Status.PUBLISHED:
            return Response(
                {"detail": "A published article cannot be withdrawn; "
                           "archive its issue instead."},
                status=status.HTTP_409_CONFLICT,
            )
        if article.status == Article.Status.WITHDRAWN:
            return Response({"detail": "Already withdrawn."},
                            status=status.HTTP_409_CONFLICT)

        if (request.user.role == request.user.Role.WRITER
                and article.writer_id != request.user.id):
            return Response({"detail": "Not your article."},
                            status=status.HTTP_403_FORBIDDEN)

        serializer = WithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # UC-1.10 A1: leaving it in an issue would corrupt the readiness count.
        article.issue = None
        article.status = Article.Status.WITHDRAWN
        article.withdrawal_reason = serializer.validated_data["reason"]
        article.save(update_fields=["issue", "status", "withdrawal_reason",
                                    "updated_at"])
        return Response(ArticleDetailSerializer(article).data)

    @action(detail=True, methods=["post"], url_path="assign-issue")
    def assign_to_issue(self, request, pk=None):
        """UC-1.11 Assign Article to Issue. Only approved articles can be
        assigned, and only to an issue that still accepts them."""
        from apps.issues.models import Issue

        article = self.get_object()
        if article.status != Article.Status.APPROVED:
            return Response(
                {"detail": "Only an approved article can be assigned to an issue."},
                status=status.HTTP_409_CONFLICT,
            )

        issue_id = request.data.get("issue")
        if issue_id in (None, ""):
            # Leaving an issue makes it a free standalone web piece.
            article.issue = None
            article.is_premium = False
            article.save(update_fields=["issue", "is_premium", "updated_at"])
            return Response(ArticleDetailSerializer(article).data)

        try:
            issue = Issue.objects.get(pk=issue_id)
        except Issue.DoesNotExist:
            return Response({"detail": "Issue not found."},
                            status=status.HTTP_404_NOT_FOUND)

        if issue.status in (Issue.Status.PUBLISHED, Issue.Status.ARCHIVED):
            return Response(
                {"detail": f"Issue #{issue.number} no longer accepts articles."},
                status=status.HTTP_409_CONFLICT,
            )

        # The issue is the paid product (UC-8.2).
        article.issue = issue
        article.is_premium = True
        article.save(update_fields=["issue", "is_premium", "updated_at"])
        return Response(ArticleDetailSerializer(article).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """UC-2.5, standalone path: publish an approved article that is not
        assigned to an issue. Issue-bound articles publish via the issue."""
        article = self.get_object()
        try:
            publish_article(article, request.user)
        except NotReady as exc:
            return Response({"detail": exc.reasons[0], "reasons": exc.reasons},
                            status=status.HTTP_409_CONFLICT)
        return Response(ArticleDetailSerializer(article).data)


class ArticleImageViewSet(viewsets.ModelViewSet):
    """Inline article images (UC-1.2). Uploaded by the Writer while composing
    or by the Editor during review; handed to the Designer for the replica."""

    serializer_class = ArticleImageSerializer
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post", "delete", "head", "options"]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ArticleImage.objects.select_related("article")
        article = self.request.query_params.get("article")
        return qs.filter(article_id=article) if article else qs

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)
