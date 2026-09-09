from rest_framework import serializers

from .models import ArticleEvaluation


class ArticleEvaluationSerializer(serializers.ModelSerializer):
    overridden_by_name = serializers.CharField(source="overridden_by.get_full_name", read_only=True)

    class Meta:
        model = ArticleEvaluation
        fields = [
            "id", "article", "grammar_score", "readability_score", "overall_score",
            "recommendation", "ai_model", "is_overridden", "override_reason",
            "overridden_by", "overridden_by_name", "overridden_at", "created_at",
        ]
        read_only_fields = fields
