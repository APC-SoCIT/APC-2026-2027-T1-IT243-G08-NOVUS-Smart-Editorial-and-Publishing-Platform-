from rest_framework import permissions, viewsets

from .models import ArticleEvaluation
from .serializers import ArticleEvaluationSerializer


class ArticleEvaluationViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only browse of AI verdicts — the override/approve actions
    themselves live on ArticleViewSet (apps.editorial) since they mutate
    Article.status, not just the evaluation row."""

    serializer_class = ArticleEvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = ArticleEvaluation.objects.select_related("article")
        if user.role == user.Role.WRITER:
            return qs.filter(article__writer=user)
        return qs
