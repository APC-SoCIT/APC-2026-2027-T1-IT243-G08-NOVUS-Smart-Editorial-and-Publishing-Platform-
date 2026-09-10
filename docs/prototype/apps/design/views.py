from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.common.permissions import role_permission

from .models import MagazineDesign
from .serializers import DesignRevisionSerializer, MagazineDesignSerializer


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

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """UC-1.13: Editor approves the layout for publication."""
        design = self.get_object()
        if design.status != MagazineDesign.Status.PENDING_REVIEW:
            return Response(
                {"detail": f"Cannot approve a design in status {design.status}."},
                status=status.HTTP_409_CONFLICT,
            )
        design.status = MagazineDesign.Status.APPROVED
        design.reviewed_by = request.user
        design.reviewed_at = timezone.now()
        design.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
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
        return Response(MagazineDesignSerializer(design).data)
