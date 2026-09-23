"""
UC-1.5 Generate Article Evaluation — the only place that talks to the Anthropic
API. Returns both a numeric assessment and a narrative editorial brief, per the
system context diagram. Keeping it isolated here means swapping models, prompts,
or providers never touches the editorial workflow code.
"""
import json

import anthropic
from django.conf import settings
from django.utils.html import strip_tags

from .fixes import clean_fixes

NOTE_TYPES = {"GRAMMAR", "TONE", "STRUCTURE", "FACTUAL"}
PRIORITIES = {"LOW", "MEDIUM", "HIGH"}

EVAL_SYSTEM_PROMPT = """You are an editorial quality evaluator for BOSS \
Magazine PH, a Filipino lifestyle publication covering fashion, culture, \
modern trends, business, and society.

Assess the submitted article draft and return a numeric assessment, \
actionable editorial feedback, and quick fixes.

Scoring: grammar and readability 0-100 each, plus an overall score 0-100. \
Recommend REJECT only for serious grammar or readability problems, not for \
editorial taste.

Feedback: write a 2-3 sentence summary of the piece's strengths and \
weaknesses, then list 0-5 concrete suggestions. Each suggestion names the \
section it applies to, its type, a specific instruction the writer can act \
on, and a priority. Do not invent problems; return an empty list if the \
draft is clean.

Quick fixes: for purely mechanical problems only - spelling, grammar, \
agreement, punctuation, or a single unclear sentence - propose up to 8 exact \
edits. "original" must be copied character for character from the article, \
be at most one sentence, and appear only once in it. "replacement" changes \
only what is needed. Never propose fixes that change the argument, the \
structure, facts, figures, names, quotations or the writer's voice; those \
belong in suggestions. Return an empty list if the draft is clean or needs \
rewriting rather than line edits.

note_type must be one of: GRAMMAR, TONE, STRUCTURE, FACTUAL
priority must be one of: LOW, MEDIUM, HIGH
fix note_type must be one of: GRAMMAR, TONE

Respond with ONLY a JSON object, no other text, no markdown fences:
{"grammar_score": <int>, "readability_score": <int>, "overall_score": <int>,
 "recommendation": "APPROVE" | "REJECT",
 "summary": "<2-3 sentences>",
 "suggestions": [
   {"section": "<section name>", "note_type": "<type>",
    "instruction": "<specific, actionable>", "priority": "<priority>"}
 ],
 "fixes": [
   {"original": "<exact text>", "replacement": "<corrected text>",
    "reason": "<one short sentence>", "note_type": "GRAMMAR" | "TONE"}
 ]}"""


class EvaluationError(Exception):
    """Raised when Claude's response can't be parsed into a valid verdict."""


class EvaluationUnavailable(EvaluationError):
    """No assessment can be obtained. The gate treats this as an absence, not
    a score of zero: the article goes to review with the absence stated."""


def _clean_suggestions(raw):
    """Keep only well-formed suggestions. A malformed entry is dropped rather
    than failing the whole evaluation — a partial brief is more useful to an
    Editor than none."""
    out = []
    for s in (raw or [])[:5]:
        if not isinstance(s, dict):
            continue
        instruction = str(s.get("instruction", "")).strip()
        if not instruction:
            continue
        note_type = str(s.get("note_type", "")).upper()
        priority = str(s.get("priority", "")).upper()
        out.append({
            "section": str(s.get("section", "")).strip()[:100],
            "note_type": note_type if note_type in NOTE_TYPES else "STRUCTURE",
            "instruction": instruction[:500],
            "priority": priority if priority in PRIORITIES else "MEDIUM",
        })
    return out


def evaluate_article(article) -> dict:
    """Returns a dict matching ArticleEvaluation's evaluated fields, ready to
    unpack into ArticleEvaluation.objects.create(article=article, **result)."""

    # With no credential there is no assessment to give. Returning a zero
    # would fail every draft at the gate; raising lets submission route it
    # to review with the absence stated instead.
    if not settings.ANTHROPIC_API_KEY or "placeholder" in settings.ANTHROPIC_API_KEY:
        raise EvaluationUnavailable("No evaluation credential is configured.")

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model=settings.ANTHROPIC_EVAL_MODEL,
        max_tokens=2200,  # room for quick fixes
        system=EVAL_SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Title: {article.title}\n\n{strip_tags(article.body)}",
        }],
    )
    usage = getattr(message, "usage", None)
    text = message.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(text)
        return {
            "grammar_score": max(0, min(100, int(parsed["grammar_score"]))),
            "readability_score": max(0, min(100, int(parsed["readability_score"]))),
            "overall_score": max(0, min(100, int(parsed["overall_score"]))),
            "recommendation": parsed["recommendation"],
            "summary": str(parsed.get("summary", "")).strip(),
            "suggestions": _clean_suggestions(parsed.get("suggestions")),
            "fixes": clean_fixes(parsed.get("fixes"), article.body),
            "raw_response": parsed,
            "ai_model": settings.ANTHROPIC_EVAL_MODEL,
            # Recorded per assessment so the monthly cost is answerable from
            # the data rather than estimated from the call count.
            "input_tokens": getattr(usage, "input_tokens", 0) if usage else 0,
            "output_tokens": getattr(usage, "output_tokens", 0) if usage else 0,
        }
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        raise EvaluationError(f"Could not parse Claude's evaluation: {text!r}") from exc
