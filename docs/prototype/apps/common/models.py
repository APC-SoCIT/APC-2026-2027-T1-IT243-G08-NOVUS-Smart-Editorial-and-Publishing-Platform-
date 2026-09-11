from django.db import models


class TimeStampedModel(models.Model):
    """Shared audit columns. Not a table itself — every real table inherits this."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
