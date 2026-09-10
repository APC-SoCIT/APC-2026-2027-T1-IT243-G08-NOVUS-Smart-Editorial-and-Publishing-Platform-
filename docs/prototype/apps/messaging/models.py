from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Message(TimeStampedModel):
    """
    Editorial correspondence attached to an article.

    Distinct from RevisionNote: a revision note is a formal, sectioned
    instruction that changes the article's workflow state. A message is a
    conversation — clarifying a brief, flagging a source problem, agreeing a
    deadline extension. It changes nothing about the article.

    Scoped to an article on purpose. Free-form direct messaging between staff
    is out of scope; the point is that correspondence stays with the work it
    concerns rather than scattering across Messenger and Viber, which is the
    problem NOVUS exists to solve.
    """

    article = models.ForeignKey(
        "editorial.Article", on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="messages_sent",
    )
    body = models.TextField(max_length=2000)

    # Null means the thread is open to everyone working on the article.
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name="messages_received",
    )
    read_by = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message on {self.article_id} from {self.sender_id}"

    def participants(self):
        """Everyone attached to the article — who can see and receive it."""
        people = {self.article.writer, self.article.editor,
                  self.article.assigned_by}
        return {p for p in people if p}
