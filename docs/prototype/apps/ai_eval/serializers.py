from rest_framework import serializers

from .fixes import fix_states
from .models import ArticleEvaluation


class ArticleEvaluationSerializer(serializers.ModelSerializer):
    overridden_by_name = serializers.CharField(source="overridden_by.get_full_name", read_only=True)
    fixes = serializers.SerializerMethodField()
    fix_summary = serializers.SerializerMethodField()

    class Meta:
        model = ArticleEvaluation
        fields = [
            "id", "article", "grammar_score", "readability_score", "overall_score",
            "recommendation", "verdict", "summary", "suggestions", "fixes", "fix_summary",
            "ai_model", "is_overridden", "override_reason",
            "overridden_by", "overridden_by_name", "overridden_at", "created_at",
        ]
        read_only_fields = fields

    def get_fixes(self, obj):
        states = fix_states(obj)
        return [{**f, "state": states.get(f["id"], "pending")} for f in (obj.fixes or [])]

    def get_fix_summary(self, obj):
        counts = {"accepted": 0, "dismissed": 0, "stale": 0, "pending": 0}
        for v in fix_states(obj).values():
            counts[v] += 1
        return counts
