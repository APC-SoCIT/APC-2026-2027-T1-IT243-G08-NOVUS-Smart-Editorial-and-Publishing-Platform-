from django.db.models import Q
from rest_framework import permissions, viewsets

from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Message
from .serializers import MessageSerializer


class MessageViewSet(viewsets.ModelViewSet):
    """Article-scoped editorial correspondence."""

    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Message.objects.select_related("sender", "article")

        # A user sees messages on articles they are attached to, plus anything
        # addressed to them directly. Editors and Publishers see all threads.
        if user.role in (user.Role.EDITOR, user.Role.PUBLISHER, user.Role.ADMIN):
            pass
        else:
            qs = qs.filter(
                Q(article__writer=user) | Q(article__editor=user)
                | Q(sender=user) | Q(recipient=user)
            )

        article = self.request.query_params.get("article")
        return qs.filter(article_id=article) if article else qs

    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)

        targets = ([message.recipient] if message.recipient
                   else message.participants() - {message.sender})
        for person in targets:
            notify(person, Notification.Kind.MESSAGE,
                   f'{message.sender.get_full_name()} commented on '
                   f'"{message.article.title}".',
                   f"/editor/review/{message.article_id}")
