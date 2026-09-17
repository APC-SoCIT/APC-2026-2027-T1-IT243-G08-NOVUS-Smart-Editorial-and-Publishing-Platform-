from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.accounts.models import User
from apps.common.permissions import role_permission
from apps.notifications.models import Notification
from apps.notifications.services import notify_many, notify

from .models import MagazineDesign
from .serializers import DesignRevisionSerializer, MagazineDesignSerializer


class UploadPresignView(APIView):
    """Issue a signed instruction permitting one direct upload.

    The key is chosen here rather than by the client, so a designer cannot
    target an existing object or choose where their file lands.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.design.uploads import UploadError, build_key, presign_put
        from apps.issues.models import Issue

        if request.user.role not in (request.user.Role.GRAPHIC_DESIGNER,
                                     request.user.Role.ADMIN):
            return Response({"detail": "Not permitted."}, status=403)

        try:
            issue = Issue.objects.get(pk=request.data.get("issue"))
        except (Issue.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "Issue not found."}, status=404)

        version = (request.data.get("version") or "").strip()
        filename = (request.data.get("filename") or "edition.pdf").strip()
        content_type = request.data.get("content_type") or ""

        if not version:
            return Response({"detail": "A version label is required."}, status=400)

        if issue.status in (Issue.Status.PUBLISHED, Issue.Status.ARCHIVED):
            return Response(
                {"detail": f"Issue #{issue.number} has already been published. "
                           f"Its edition is settled."},
                status=status.HTTP_409_CONFLICT)

        # One version under review at a time. Without this a designer can
        # stack versions the editor has not yet seen, which leaves several
        # editions for one issue in the review queue and no way to tell which
        # one the designer means.
        pending = MagazineDesign.objects.filter(
            issue=issue, status=MagazineDesign.Status.PENDING_REVIEW
        ).first()
        if pending:
            return Response(
                {"detail": f"Version {pending.version} is already with the "
                           f"editor for this issue. Wait for their response "
                           f"before submitting another."},
                status=status.HTTP_409_CONFLICT)
        if MagazineDesign.objects.filter(issue=issue, version=version).exists():
            return Response(
                {"detail": f"Version {version} already exists for this issue."},
                status=409)

        key = build_key(issue.number, version, filename)
        try:
            url = presign_put(key, content_type)
        except UploadError as e:
            return Response({"detail": str(e)}, status=400)

        return Response({"upload_url": url, "key": key, "expires_in": 900})


class UploadCompleteView(APIView):
    """Create the record, once the object is confirmed present.

    A client reporting success is not evidence that the upload happened. The
    storage service is asked directly, so an abandoned upload never produces a
    row claiming a file that does not exist.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.design.uploads import UploadError, confirm
        from apps.issues.models import Issue

        if request.user.role not in (request.user.Role.GRAPHIC_DESIGNER,
                                     request.user.Role.ADMIN):
            return Response({"detail": "Not permitted."}, status=403)

        key = (request.data.get("key") or "").strip()
        if not key.startswith("designs/"):
            return Response({"detail": "Invalid upload reference."}, status=400)

        try:
            issue = Issue.objects.get(pk=request.data.get("issue"))
        except (Issue.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "Issue not found."}, status=404)

        try:
            size = confirm(key, expected_type="application/pdf")
        except UploadError as e:
            return Response({"detail": str(e)}, status=400)

        version = (request.data.get("version") or "").strip()
        design = MagazineDesign(
            issue=issue, version=version, designer=request.user,
            notes_to_editor=request.data.get("notes_to_editor", ""),
            status=MagazineDesign.Status.PENDING_REVIEW,
            file_size=size,
        )
        design.file.name = key          # already in storage; do not re-upload
        cover = request.FILES.get("cover_image")
        if cover:
            design.cover_image = cover
        design.save()

        notify_many(
            User.objects.filter(role=User.Role.EDITOR, is_active=True),
            Notification.Kind.DESIGN_UPLOADED,
            f"A layout for Issue #{issue.number} awaits review.",
            "/editor")

        return Response(MagazineDesignSerializer(design).data, status=201)


class MagazineDesignViewSet(viewsets.ModelViewSet):
    """
    UC-1.12 Upload, UC-1.13 Review, UC-1.14 Request Revision,
    UC-1.15 Resubmit Magazine Design.
    """

    serializer_class = MagazineDesignSerializer
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = MagazineDesign.objects.select_related("designer", "reviewed_by")
        if user.role == user.Role.GRAPHIC_DESIGNER:
            return qs.filter(designer=user)
        return qs

    def get_permissions(self):
        if self.action == "create":
            return [role_permission("GRAPHIC_DESIGNER")()]
        if self.action in ("approve", "request_revision"):
            return [role_permission("EDITOR")()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        """A new version supersedes any earlier open version for the same
        issue, so the Editor only ever reviews the current layout (UC-1.15)."""
        design = serializer.save()
        (MagazineDesign.objects
            .filter(issue=design.issue)
            .exclude(pk=design.pk)
            .filter(status__in=[MagazineDesign.Status.PENDING_REVIEW,
                                MagazineDesign.Status.REVISION_REQUESTED])
            .update(status=MagazineDesign.Status.SUPERSEDED))

        from apps.accounts.models import User
        notify_many(User.objects.filter(role=User.Role.EDITOR, is_active=True),
                    Notification.Kind.DESIGN_UPLOADED,
                    f"A layout for {design.issue} awaits review.",
                    "/editor")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """UC-1.13: Editor approves the layout for publication."""
        design = self.get_object()
        if design.status != MagazineDesign.Status.PENDING_REVIEW:
            return Response(
                {"detail": f"Cannot approve a design in status {design.status}."},
                status=status.HTTP_409_CONFLICT,
            )
        # An issue has one edition. Approving this version settles the
        # question, so every other version for the issue becomes history —
        # not only previously approved ones, but anything still pending or
        # returned, which would otherwise sit in the editor's queue asking to
        # be reviewed after the decision was made.
        MagazineDesign.objects.filter(issue=design.issue).exclude(
            pk=design.pk
        ).exclude(
            status=MagazineDesign.Status.SUPERSEDED
        ).update(status=MagazineDesign.Status.SUPERSEDED)

        design.status = MagazineDesign.Status.APPROVED
        design.reviewed_by = request.user
        design.reviewed_at = timezone.now()
        design.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        notify(design.designer, Notification.Kind.DESIGN_APPROVED,
               f"Your layout {design.version} for {design.issue} was approved.",
               "/designer")
        return Response(MagazineDesignSerializer(design).data)

    @action(detail=True, methods=["post"], url_path="request-revision")
    def request_revision(self, request, pk=None):
        """UC-1.14: Editor returns the layout with design-specific corrections."""
        design = self.get_object()
        if design.status != MagazineDesign.Status.PENDING_REVIEW:
            return Response(
                {"detail": f"Cannot revise a design in status {design.status}."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = DesignRevisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        design.status = MagazineDesign.Status.REVISION_REQUESTED
        design.revision_notes = serializer.validated_data["notes"]
        design.reviewed_by = request.user
        design.reviewed_at = timezone.now()
        design.save(update_fields=["status", "revision_notes", "reviewed_by",
                                   "reviewed_at", "updated_at"])
        notify(design.designer, Notification.Kind.DESIGN_REVISION,
               f"Revisions requested on {design.version} for {design.issue}.",
               "/designer")
        return Response(MagazineDesignSerializer(design).data)
