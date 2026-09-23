from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.editorial.models import Article


class ArticleEvaluation(TimeStampedModel):
    """UC-1.11 Generate Article Evaluation. One row per evaluation run — an
    article can be evaluated more than once (each resubmission after a
    revision creates a new row), so `article.evaluations.order_by("-created_at")
    .first()` is always 'the current verdict', matching the Editor Dashboard's
    'Overall Score' widget."""

    class Recommendation(models.TextChoices):
        APPROVE = "APPROVE", "Approve"
        REJECT = "REJECT", "Reject"

    class Verdict(models.TextChoices):
        PASS = "PASS", "Passed"
        REVISE = "REVISE", "Revise"
        REWRITE = "REWRITE", "Rewrite"

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="evaluations")

    grammar_score = models.PositiveSmallIntegerField()
    readability_score = models.PositiveSmallIntegerField()
    overall_score = models.PositiveSmallIntegerField()
    recommendation = models.CharField(max_length=10, choices=Recommendation.choices)

    # UC-1.5: the AI returns a narrative brief alongside the scores, per the
    # system context diagram ("scores submissions and generates narrative
    # editorial briefs"). `suggestions` is shaped to map 1:1 onto RevisionNote
    # so the Editor's composer can prefill from it (UC-1.7), and degrades to an
    # empty list when unavailable (UC-1.7 alternate flow "No AI Feedback").
    summary = models.TextField(blank=True)
    suggestions = models.JSONField(default=list, blank=True)

    # Decided from the score by the submission gate, not by the model, so the
    # bands mean the same whichever model produced the number.
    verdict = models.CharField(max_length=10, choices=Verdict.choices, blank=True)

    # Quick fixes: exact line edits for mechanical problems only. Each is
    # {id, original, replacement, reason, note_type}; kept only when its
    # passage appears exactly once in the copy that was assessed.
    fixes = models.JSONField(default=list, blank=True)

    raw_response = models.JSONField(default=dict, blank=True)
    ai_model = models.CharField(max_length=50, default="claude-haiku-4-5-20251001")

    content_hash = models.CharField(
        max_length=64, blank=True, db_index=True,
        help_text="Identifies the copy assessed, so an unchanged resubmission "
                  "reuses this result rather than buying the same answer twice.",
    )
    input_tokens = models.PositiveIntegerField(
        default=0, help_text="Recorded so the monthly cost is answerable "
                             "without estimating it.")
    output_tokens = models.PositiveIntegerField(default=0)

    # UC-1.5 Verify Override AI
    is_overridden = models.BooleanField(default=False)
    override_reason = models.CharField(max_length=500, blank=True)
    overridden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ai_overrides",
    )
    overridden_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Evaluation<article={self.article_id}> {self.overall_score} ({self.recommendation})"


class FixDecision(TimeStampedModel):
    """A writer's decision on one quick fix.

    Recorded so an editor can see which words came from the machine, and so
    a fix is decided once. The unique constraint is what stops a double
    click applying the same edit twice.
    """

    class Action(models.TextChoices):
        ACCEPTED = "ACCEPTED", "Accepted"
        DISMISSED = "DISMISSED", "Dismissed"

    evaluation = models.ForeignKey(ArticleEvaluation, on_delete=models.CASCADE,
                                   related_name="fix_decisions")
    fix_id = models.CharField(max_length=8)
    action = models.CharField(max_length=10, choices=Action.choices)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name="fix_decisions")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["evaluation", "fix_id"],
                                               name="one_decision_per_fix")]

    def __str__(self):
        return f"{self.fix_id} {self.action} on evaluation {self.evaluation_id}"
