from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import role_permission
from apps.publishing.services import NotReady, publish_issue

from .models import Issue
from .serializers import (
    IssueDetailSerializer,
    IssueListSerializer,
    ScheduleSerializer,
)


class IssueViewSet(viewsets.ModelViewSet):
    """
    Module 2: Manage Publication.

    The Publisher creates and releases issues (UC-2.1, UC-2.4, UC-2.5, UC-2.7).
    Editors and other staff read them, since assignment (UC-1.11) and layout
    (UC-1.12) both need to know which issues are open.
    """

    queryset = Issue.objects.prefetch_related("articles", "designs").select_related("created_by")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        return IssueListSerializer if self.action == "list" else IssueDetailSerializer

    def get_permissions(self):
        if self.action in ("create", "partial_update", "schedule", "publish", "archive"):
            return [role_permission("PUBLISHER")()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        """UC-2.4 Schedule Issue Release."""
        issue = self.get_object()
        if not issue.is_ready:
            return Response(
                {"detail": "Issue is not ready.", "reasons": issue.blocking_reasons()},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = ScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        issue.scheduled_for = serializer.validated_data["scheduled_for"]
        issue.status = Issue.Status.SCHEDULED
        issue.save(update_fields=["scheduled_for", "status", "updated_at"])
        return Response(IssueDetailSerializer(issue).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        """UC-2.5 Execute Live Publishing."""
        issue = self.get_object()
        try:
            publish_issue(issue, request.user)
        except NotReady as exc:
            return Response(
                {"detail": "Issue is not ready to publish.", "reasons": exc.reasons},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(IssueDetailSerializer(issue).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """UC-2.7 Archive Previous Issue."""
        issue = self.get_object()
        if issue.status != Issue.Status.PUBLISHED:
            return Response(
                {"detail": "Only a published issue can be archived."},
                status=status.HTTP_409_CONFLICT,
            )
        issue.status = Issue.Status.ARCHIVED
        issue.save(update_fields=["status", "updated_at"])
        return Response(IssueDetailSerializer(issue).data)
