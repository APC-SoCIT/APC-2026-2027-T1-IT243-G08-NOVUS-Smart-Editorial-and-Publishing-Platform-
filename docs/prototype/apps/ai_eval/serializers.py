from rest_framework import serializers

from .fixes import fix_states
from .models import ArticleEvaluation


class ArticleEvaluationSerializer(serializers.ModelSerializer):
    overridden_by_name = serializers.CharField(source="overridden_by.get_full_name", read_only=True)
    fixes = serializers.SerializerMethodField()
    fix_summary = serializers.SerializerMethodField()
    accepted_history = serializers.SerializerMethodField()

    class Meta:
        model = ArticleEvaluation
        fields = [
            "id", "article", "grammar_score", "readability_score", "overall_score",
            "recommendation", "verdict", "summary", "suggestions", "fixes", "fix_summary", "accepted_history",
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

    def get_accepted_history(self, obj):
        """Every AI fix the writer accepted on this article, across all of its
        assessments, oldest first. A resubmission creates a new assessment
        with no fixes of its own, so reading only the latest one would hide
        what the machine changed from the editor who approves the copy."""
        from .models import FixDecision
        out = []
        for ev in obj.article.evaluations.order_by("created_at").prefetch_related("fix_decisions"):
            taken = {d.fix_id for d in ev.fix_decisions.all()
                     if d.action == FixDecision.Action.ACCEPTED}
            out += [{"id": f"{ev.id}-{f['id']}", "original": f["original"],
                     "replacement": f["replacement"]}
                    for f in (ev.fixes or []) if f.get("id") in taken]
        return out
