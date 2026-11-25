from rest_framework import viewsets

from apps.common.permissions import role_permission

from .models import ArticleEvaluation
from .serializers import ArticleEvaluationSerializer


class ArticleEvaluationViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only browse of AI verdicts — the override/approve actions
    themselves live on ArticleViewSet (apps.editorial) since they mutate
    Article.status, not just the evaluation row."""

    serializer_class = ArticleEvaluationSerializer
    def get_permissions(self):
        # Assessments are between a writer and the editors who decide.
        return [role_permission("WRITER", "EDITOR", "PUBLISHER")()]

    def get_queryset(self):
        user = self.request.user
        qs = ArticleEvaluation.objects.select_related("article").order_by("-created_at")
        if user.role == user.Role.WRITER:
            return qs.filter(article__writer=user)
        return qs
