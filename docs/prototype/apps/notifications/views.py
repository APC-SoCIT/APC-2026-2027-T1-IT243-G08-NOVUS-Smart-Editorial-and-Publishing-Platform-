import io

from rest_framework import permissions, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Notification, NotificationPreference
from .serializers import NotificationPreferenceSerializer, NotificationSerializer


class DeadlineCheckView(APIView):
    """Runs the deadline sweep.

    The management command exists but nothing invoked it, so the one
    notification type that addresses missed deadlines only fired if somebody
    ran it by hand. Exposing it as an endpoint lets an external scheduler
    trigger it daily — the same service already keeping the API warm.

    Guarded by a shared secret rather than a session, because a scheduler
    cannot hold one. The sweep is idempotent within a day: it only notifies
    about articles whose deadline falls in the window, so a duplicate call
    produces duplicate notifications rather than incorrect ones. Callers
    should schedule it once daily.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        from django.conf import settings
        from django.core.management import call_command

        expected = getattr(settings, "SCHEDULER_TOKEN", "")
        supplied = request.headers.get("X-Scheduler-Token", "")

        if not expected or supplied != expected:
            return Response({"detail": "Not authorised."}, status=403)

        out = io.StringIO()
        call_command("check_deadlines", stdout=out)
        return Response({"ran": True, "output": out.getvalue().strip()})


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """UC-10.1 View, UC-10.2 Mark as Read, UC-10.3 Preferences."""

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        count = self.get_queryset().filter(is_read=False).count()
        return Response({"unread": count})

    @action(detail=True, methods=["post"], url_path="read")
    def mark_read(self, request, pk=None):
        n = self.get_object()
        n.is_read = True
        n.save(update_fields=["is_read", "updated_at"])
        return Response(NotificationSerializer(n).data)

    @action(detail=False, methods=["post"], url_path="read-all")
    def mark_all_read(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({"marked": updated})

    @action(detail=False, methods=["get", "patch"])
    def preferences(self, request):
        pref, _ = NotificationPreference.objects.get_or_create(user=request.user)
        if request.method == "PATCH":
            serializer = NotificationPreferenceSerializer(
                pref, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(NotificationPreferenceSerializer(pref).data)
