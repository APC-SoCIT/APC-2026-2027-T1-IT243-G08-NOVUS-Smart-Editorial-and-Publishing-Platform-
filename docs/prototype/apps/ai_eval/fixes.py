"""
Quick fixes: exact line edits the assessment proposes for mechanical problems.

The model sees the article with its tags stripped but its HTML entities left
in place, so a quoted passage may read "&amp;" where the editor shows "&".
Every lookup therefore tries both forms, and only ever inside text — a match
that spans a tag is treated as not found, because replacing across markup
would corrupt the document.
"""
import html
import re

from django.conf import settings

TAG = re.compile(r"(<[^>]*>)")


def _forms(text):
    return {text, html.escape(html.unescape(text), quote=False)}


def _positions(body, original):
    """Every place the passage appears inside a single text node."""
    hits, offset = {}, 0
    for part in TAG.split(body or ""):
        if part and not part.startswith("<"):
            for t in _forms(original):
                start = 0
                while t:
                    i = part.find(t, start)
                    if i < 0:
                        break
                    hits[offset + i] = t
                    start = i + 1
        offset += len(part)
    return hits


def apply_fix(body, fix):
    """The body with the fix applied, or None if the passage is no longer
    there exactly once — edited away, or now ambiguous."""
    hits = _positions(body, fix["original"])
    if len(hits) != 1:
        return None
    (pos, matched), = hits.items()
    replacement = html.escape(html.unescape(fix["replacement"]), quote=False)
    return body[:pos] + replacement + body[pos + len(matched):]


def clean_fixes(raw, body):
    """Keep only fixes that can be applied as proposed: a real change, a
    passage short enough to be a line edit, and one found exactly once."""
    out, seen = [], set()
    for f in raw or []:
        if len(out) >= settings.AI_MAX_FIXES:
            break
        if not isinstance(f, dict):
            continue
        original = str(f.get("original", "")).strip()
        replacement = str(f.get("replacement", "")).strip()
        if (not original or not replacement or original == replacement
                or len(original) > 300 or len(replacement) > 400 or original in seen):
            continue
        if len(_positions(body, original)) != 1:
            continue
        seen.add(original)
        note_type = str(f.get("note_type", "GRAMMAR")).upper()
        out.append({
            "id": f"f{len(out) + 1}",
            "original": original,
            "replacement": replacement,
            "reason": str(f.get("reason", "")).strip()[:200],
            "note_type": note_type if note_type in ("GRAMMAR", "TONE") else "GRAMMAR",
        })
    return out


def band_for(score):
    if score >= settings.AI_PASSING_SCORE:
        return "PASS"
    if score < settings.AI_REWRITE_BELOW:
        return "REWRITE"
    return "REVISE"


def fix_states(evaluation):
    """fix id -> accepted | dismissed | stale | pending, against the copy as
    it stands now."""
    cached = getattr(evaluation, "_fix_states", None)
    if cached is not None:
        return cached
    decided = dict(evaluation.fix_decisions.values_list("fix_id", "action"))
    body = evaluation.article.body
    states = {}
    for f in evaluation.fixes or []:
        action = decided.get(f["id"])
        if action:
            states[f["id"]] = action.lower()
        elif len(_positions(body, f["original"])) != 1:
            states[f["id"]] = "stale"
        else:
            states[f["id"]] = "pending"
    evaluation._fix_states = states
    return states


def all_resolved(evaluation):
    """True once every fix has been accepted, dismissed or overtaken."""
    states = fix_states(evaluation)
    return bool(states) and "pending" not in states.values()
