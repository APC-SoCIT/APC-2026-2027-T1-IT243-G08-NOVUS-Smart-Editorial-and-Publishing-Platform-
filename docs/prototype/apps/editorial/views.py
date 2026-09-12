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
            return self._apply_filters(qs.filter(writer=user))
        if user.role == user.Role.GRAPHIC_DESIGNER:
            # UC-1.12: designers lay out issues, not loose articles. Approval
            # alone is an editorial milestone — the handover to production is
            # assignment to an issue, because that is when the article has a
            # page to sit on. An approved article with no issue is still
            # waiting on an editorial decision and is not theirs yet.
            #
            # A consequence worth naming: a standalone web article never
            # reaches a designer, which is correct. Web-only pieces have no
            # print layout.
            qs = qs.filter(
                status__in=[Article.Status.APPROVED, Article.Status.PUBLISHED],
                issue__isnull=False,
            ).exclude(issue__status=("ARCHIVED"))
        return self._apply_filters(qs)

    def _apply_filters(self, qs):
        """UC-1.16: search and narrow the pipeline. Applied after the role
        scope so filtering can never widen what a user is permitted to see."""
        from django.db.models import Q

        p = self.request.query_params

        term = (p.get("q") or "").strip()
        if term:
            qs = qs.filter(
                Q(title__icontains=term)
                | Q(excerpt__icontains=term)
                | Q(writer__first_name__icontains=term)
                | Q(writer__last_name__icontains=term)
            )

        if p.get("status"):
            qs = qs.filter(status__in=p["status"].split(","))
        if p.get("category"):
            qs = qs.filter(category=p["category"])
        if p.get("writer"):
            qs = qs.filter(writer_id=p["writer"])
        if p.get("issue"):
            qs = qs.filter(issue_id=p["issue"])

        if p.get("overdue") == "true":
            from django.utils import timezone
            qs = qs.filter(
                deadline__lt=timezone.now().date(),
                status__in=[Article.Status.ASSIGNED, Article.Status.DRAFTING,
                            Article.Status.REVISION_REQUESTED],
            )

        allowed = {"updated_at", "-updated_at", "deadline", "-deadline",
                   "created_at", "-created_at", "title", "-title"}
        ordering = p.get("sort")
        return qs.order_by(ordering) if ordering in allowed else qs
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
        if self.action == "create":
            # Editors write too — leaders, columns, editorials. The
            # constraint is not who may write but who may sign it off.
            return [permissions.IsAuthenticated()]
        if self.action == "partial_update":
            # editor_image_edit: an Editor may correct photography and
            # metadata on an article under review; a Writer may edit
            # their own draft. Both routes are scoped by get_queryset.
            return [permissions.IsAuthenticated()]
        if self.action == "request_revision":
            return [role_permission("EDITOR")()]
        if self.action == "pull_back":
            # Either role may pull back; which articles each may touch is
            # decided in the view, since it depends on whether the article
            # has been assigned to an issue.
            return [role_permission("EDITOR", "PUBLISHER")()]
        if self.action in ("approve", "override", "assign_to_issue",
                           "assign", "reassign", "set_access"):
            return [role_permission("EDITOR")()]
        if self.action in ("publish", "sign_off"):
            return [role_permission("PUBLISHER")()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        """UC-1.2 Submit Article for Review, chained into UC-1.11 Generate
        Article Evaluation — the Writer only takes one action; the AI score
        appears automatically on the Editor's queue, matching the wireframes."""
        article = self.get_object()
        if article.writer != request.user:
            return Response({"detail": "Not your article."},
                            status=status.HTTP_403_FORBIDDEN)
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
            # self_approval: nobody signs off their own copy. An
            # Editor's article goes to the Publisher, who is already
            # the final checkpoint before an issue ships.
            article.status = (
                Article.Status.PENDING_SIGNOFF
                if article.writer.role in (
                    article.writer.Role.EDITOR, article.writer.Role.ADMIN)
                else Article.Status.UNDER_REVIEW
            )
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
        """UC-1.9 Approve Article. An article the pre-screening gate returned
        cannot be approved here — UC-1.8 Override AI is the only route, and it
        requires a written justification so the decision is auditable."""
        article = self.get_object()

        # Approval requires an article that has actually been submitted and
        # assessed. Approving a draft would bypass the pre-screening gate
        # entirely, which is the control the whole pipeline rests on.
        if article.status != Article.Status.UNDER_REVIEW:
            return Response(
                {"detail": f"Only an article under review can be approved "
                           f"(this one is {article.get_status_display().lower()})."},
                status=status.HTTP_409_CONFLICT,
            )

        latest = article.evaluations.order_by("-created_at").first()
        if article.returned_by_ai and not (latest and latest.is_overridden):
            return Response(
                {"detail": "This article was returned by pre-screening. "
                           "Use Override AI to approve it with a justification."},
                status=status.HTTP_409_CONFLICT,
            )
        article.status = Article.Status.APPROVED
        article.editor = request.user
        article.save(update_fields=["status", "editor", "updated_at"])
        notify(article.writer, Notification.Kind.APPROVED,
               f'"{article.title}" was approved.',
               f"/writer/compose/{article.id}")
        return Response(ArticleDetailSerializer(article).data)

    @action(detail=True, methods=["post"], url_path="sign-off")
    def sign_off(self, request, pk=None):
        """Publisher sign-off on editor-authored copy. An editor approving
        their own article would defeat the purpose of the gate, so the
        publisher acts as the second reader."""
        article = self.get_object()

        if article.status != Article.Status.PENDING_SIGNOFF:
            return Response(
                {"detail": "This article is not awaiting sign-off."},
                status=status.HTTP_409_CONFLICT,
            )

        # Sign-off resolves the gate the same way an override does: the
        # article has been accepted on a person's judgement, so the flag no
        # longer describes where it sits. Leaving it set made published
        # articles keep appearing in the editor's "returned" group.
        article.status = Article.Status.APPROVED
        article.editor = request.user
        article.returned_by_ai = False
        article.save(update_fields=["status", "editor", "returned_by_ai",
                                    "updated_at"])
        notify(article.writer, Notification.Kind.APPROVED,
               f'"{article.title}" was signed off by the publisher.',
               f"/editor/review/{article.id}")
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

        # The override resolves the gate's verdict, so the flag no longer
        # applies: the decision now rests with the editor, on record. Leaving
        # it set makes the interface keep offering an override that has
        # already happened.
        article.status = Article.Status.APPROVED
        article.editor = request.user
        article.returned_by_ai = False
        article.save(update_fields=["status", "editor", "returned_by_ai",
                                    "updated_at"])
        return Response(ArticleDetailSerializer(article).data)

    @action(detail=False, methods=["get"])
    def archive(self, request):
        """The published back catalogue.

        Published articles otherwise disappear from every staff view, which
        leaves an editor unable to answer the questions they ask most often:
        what did we run last month, has anyone covered this before, what was
        in Issue 12. For a magazine the back catalogue is the asset, so it
        needs to be reachable rather than merely stored.
        """
        from django.db.models import Q

        qs = (Article.objects
              .filter(status=Article.Status.PUBLISHED)
              .select_related("writer", "editor", "issue")
              .order_by("-published_at"))

        p = request.query_params

        term = (p.get("q") or "").strip()
        if term:
            qs = qs.filter(
                Q(title__icontains=term)
                | Q(excerpt__icontains=term)
                | Q(body__icontains=term)
                | Q(writer__first_name__icontains=term)
                | Q(writer__last_name__icontains=term)
            )

        if p.get("category"):
            qs = qs.filter(category=p["category"])
        if p.get("issue"):
            qs = qs.filter(issue_id=p["issue"])
        if p.get("writer"):
            qs = qs.filter(writer_id=p["writer"])
        if p.get("year"):
            qs = qs.filter(published_at__year=p["year"])

        page = self.paginate_queryset(qs)
        data = ArticleListSerializer(page or qs, many=True).data
        return self.get_paginated_response(data) if page is not None \
            else Response(data)

    @action(detail=False, methods=["get"], url_path="archive-facets")
    def archive_facets(self, request):
        """The filter values that actually exist, so the interface offers only
        categories and years something was published in."""
        from django.db.models.functions import ExtractYear

        qs = Article.objects.filter(status=Article.Status.PUBLISHED)

        years = sorted(
            {y for y in qs.annotate(y=ExtractYear("published_at"))
                          .values_list("y", flat=True) if y},
            reverse=True,
        )
        categories = sorted(
            {c for c in qs.values_list("category", flat=True) if c}
        )

        from apps.issues.models import Issue
        issues = list(
            Issue.objects.filter(articles__status=Article.Status.PUBLISHED)
            .distinct().order_by("-number")
            .values("id", "number", "title")
        )

        return Response({
            "years": years,
            "categories": categories,
            "issues": issues,
            "total": qs.count(),
        })

    @action(detail=False, methods=["get"])
    def pipeline(self, request):
        """UC-1.16 View Pipeline Dashboard. Counts by status, deadline
        pressure, and per-writer workload — the assignment tracking the
        Publisher pipeline view depends on."""
        from datetime import timedelta

        from django.utils import timezone

        qs = self.get_queryset()
        today = timezone.now().date()
        open_statuses = [Article.Status.ASSIGNED, Article.Status.DRAFTING,
                         Article.Status.REVISION_REQUESTED]

        by_status = {}
        for value, _label in Article.Status.choices:
            by_status[value] = qs.filter(status=value).count()

        open_qs = qs.filter(status__in=open_statuses)
        overdue = open_qs.filter(deadline__lt=today)
        near = open_qs.filter(deadline__gte=today,
                              deadline__lte=today + timedelta(days=2))

        workload = {}
        for a in open_qs.select_related("writer"):
            name = a.writer.get_full_name() if a.writer else "Unassigned"
            entry = workload.setdefault(name, {"open": 0, "overdue": 0})
            entry["open"] += 1
            if a.deadline and a.deadline < today:
                entry["overdue"] += 1

        return Response({
            "by_status": by_status,
            "total": qs.count(),
            "open": open_qs.count(),
            "overdue": overdue.count(),
            "due_soon": near.count(),
            "unassigned_to_issue": qs.filter(
                status=Article.Status.APPROVED, issue__isnull=True).count(),
            "workload": [
                {"writer": k, **v}
                for k, v in sorted(workload.items(), key=lambda x: -x[1]["open"])
            ],
            "overdue_articles": ArticleListSerializer(
                overdue.select_related("writer")[:10], many=True).data,
        })

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

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        """UC-1.17: the article's journey, assembled from the records that
        already exist — assignment, submissions, evaluations, revision notes,
        and publication. Nothing new is stored to produce this."""
        article = self.get_object()
        events = []

        events.append({
            "at": article.created_at,
            "kind": "created",
            "title": "Assigned" if article.assigned_by else "Draft started",
            "detail": (f"{article.assigned_by.get_full_name()} assigned this to "
                       f"{article.writer.get_full_name()}"
                       if article.assigned_by
                       else f"{article.writer.get_full_name()} started the draft"),
        })

        for v in article.versions.all().order_by("number"):
            events.append({
                "at": v.created_at,
                "kind": "submitted",
                "title": f"Submitted (v{v.number})",
                "detail": (f"{v.submitted_by.get_full_name()} submitted "
                           f"{v.word_count} words"
                           if v.submitted_by else f"{v.word_count} words"),
            })

        for e in article.evaluations.all().order_by("created_at"):
            passed = e.overall_score >= settings.AI_PASSING_SCORE
            events.append({
                "at": e.created_at,
                "kind": "evaluated" if passed else "returned",
                "title": f"Pre-screening scored {e.overall_score}",
                "detail": ("Passed to the editor's queue" if passed
                           else f"Below the passing mark of {settings.AI_PASSING_SCORE}, "
                                "returned to the writer"),
            })
            if e.is_overridden:
                events.append({
                    "at": e.overridden_at or e.created_at,
                    "kind": "override",
                    "title": "AI verdict overridden",
                    "detail": (f"{e.overridden_by.get_full_name()}: {e.override_reason}"
                               if e.overridden_by else e.override_reason),
                })

        for n in article.revision_notes.filter(editor__isnull=False):
            events.append({
                "at": n.created_at,
                "kind": "revision",
                "title": "Revision requested",
                "detail": f"{n.editor.get_full_name()} — {n.instruction[:110]}",
            })

        if article.status in (Article.Status.APPROVED, Article.Status.PUBLISHED):
            events.append({
                "at": article.updated_at,
                "kind": "approved",
                "title": "Approved",
                "detail": (f"Approved by {article.editor.get_full_name()}"
                           if article.editor else "Approved"),
            })

        if article.published_at:
            events.append({
                "at": article.published_at,
                "kind": "published",
                "title": "Published",
                "detail": (f"Released with Issue #{article.issue.number}"
                           if article.issue else "Published as a standalone article"),
            })

        if article.status == Article.Status.WITHDRAWN:
            events.append({
                "at": article.updated_at,
                "kind": "withdrawn",
                "title": "Withdrawn",
                "detail": article.withdrawal_reason or "No reason recorded",
            })

        events.sort(key=lambda e: e["at"])
        return Response(events)

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

    @action(detail=True, methods=["post"], url_path="pull-back")
    def pull_back(self, request, pk=None):
        """Return an approved article to review.

        Approval is reversible until publication: an editor who approved too
        early needs a way back that is not withdrawal, which is destructive and
        removes the article from its issue.
        """
        article = self.get_object()

        if article.status != Article.Status.APPROVED:
            return Response(
                {"detail": f"Only an approved article can be pulled back "
                           f"(this one is {article.get_status_display().lower()})."},
                status=status.HTTP_409_CONFLICT,
            )

        # Approval is not the handover — assignment to an issue is. Until
        # then the article is still editorial and an editor may correct their
        # own decision. Once a publisher is planning an issue around it, only
        # they should be able to take it out.
        is_publisher = request.user.role in (
            request.user.Role.PUBLISHER, request.user.Role.ADMIN
        ) or request.user.is_superuser

        if article.issue_id and not is_publisher:
            return Response(
                {"detail": f"This article is in Issue #{article.issue.number}. "
                           f"Only the publisher can pull it back now."},
                status=status.HTTP_403_FORBIDDEN,
            )

        reason = (request.data.get("reason") or "").strip()
        if len(reason) < 5:
            return Response({"detail": "Give a reason for pulling this back."},
                            status=status.HTTP_400_BAD_REQUEST)

        # A pull-back must never leave an issue quietly unpublishable. Removing
        # the article corrects the readiness count, the same cascade UC-1.10
        # defines for withdrawal.
        left_issue = None
        if article.issue_id:
            left_issue = article.issue
            article.issue = None
            article.is_premium = False

        article.status = Article.Status.UNDER_REVIEW
        article.save(update_fields=["status", "issue", "is_premium", "updated_at"])

        if left_issue:
            from apps.accounts.models import User
            from apps.notifications.services import notify_many
            notify_many(
                User.objects.filter(role=User.Role.PUBLISHER, is_active=True),
                Notification.Kind.REVISION,
                f'"{article.title}" was pulled out of Issue #{left_issue.number}.',
                f"/publisher/issue/{left_issue.id}",
            )

        RevisionNote.objects.create(
            article=article, editor=request.user, section="",
            note_type="STRUCTURE",
            instruction=f"Pulled back from approved: {reason}",
            priority="HIGH",
        )
        notify(article.writer, Notification.Kind.REVISION,
               f'"{article.title}" was pulled back into review.',
               f"/writer/compose/{article.id}")
        return Response(ArticleDetailSerializer(article).data)

    @action(detail=True, methods=["post"], url_path="set-access")
    def set_access(self, request, pk=None):
        """Choose whether an article is free or subscriber-only.

        Assignment to an issue defaults it to premium, since the issue is the
        paid product — but an editor may want a piece from the issue running
        free to draw readers in, or a standalone feature behind the paywall.
        """
        article = self.get_object()
        article.is_premium = bool(request.data.get("is_premium"))
        article.save(update_fields=["is_premium", "updated_at"])
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
        """Only the authoring Writer or an Editor may attach images. The
        endpoint previously accepted any authenticated user, which would have
        let a reader post to it."""
        from rest_framework.exceptions import PermissionDenied

        article = serializer.validated_data["article"]
        user = self.request.user
        allowed = (
            user.role in (user.Role.EDITOR, user.Role.ADMIN)
            or article.writer_id == user.id
        )
        if not allowed:
            raise PermissionDenied("You cannot add images to this article.")
        serializer.save(uploaded_by=user)

    def perform_destroy(self, instance):
        from rest_framework.exceptions import PermissionDenied

        user = self.request.user
        allowed = (
            user.role in (user.Role.EDITOR, user.Role.ADMIN)
            or instance.article.writer_id == user.id
        )
        if not allowed:
            raise PermissionDenied("You cannot remove images from this article.")
        instance.delete()
