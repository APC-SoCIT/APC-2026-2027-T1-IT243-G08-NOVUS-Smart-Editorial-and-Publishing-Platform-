"""
UC-1.11 Generate Article Evaluation — the only place in the codebase that
talks to the Anthropic API. Keeping it isolated here (rather than inline in
apps/editorial/views.py) means swapping models, prompts, or providers later
never touches the editorial workflow code.
"""
import json

import anthropic
from django.conf import settings

EVAL_SYSTEM_PROMPT = """You are an editorial quality evaluator for BOSS \
Magazine PH, a Filipino lifestyle publication. Score the submitted article \
draft on grammar and readability (0-100 each), give an overall score \
(0-100), and a recommendation of APPROVE or REJECT (REJECT only for \
serious grammar/readability problems, not editorial taste).

Respond with ONLY a JSON object, no other text, no markdown fences:
{"grammar_score": <int>, "readability_score": <int>, "overall_score": <int>, \
"recommendation": "APPROVE" | "REJECT"}"""


class EvaluationError(Exception):
    """Raised when Claude's response can't be parsed as a valid verdict."""


def evaluate_article(article) -> dict:
    """Returns a dict matching ArticleEvaluation's evaluated fields, ready
    to unpack into ArticleEvaluation.objects.create(article=article, **result)."""
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.ANTHROPIC_EVAL_MODEL,
        max_tokens=300,
        system=EVAL_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Title: {article.title}\n\n{article.body}"}],
    )
    text = message.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(text)
        return {
            "grammar_score": int(parsed["grammar_score"]),
            "readability_score": int(parsed["readability_score"]),
            "overall_score": int(parsed["overall_score"]),
            "recommendation": parsed["recommendation"],
            "raw_response": parsed,
            "ai_model": settings.ANTHROPIC_EVAL_MODEL,
        }
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        raise EvaluationError(f"Could not parse Claude's evaluation: {text!r}") from exc
