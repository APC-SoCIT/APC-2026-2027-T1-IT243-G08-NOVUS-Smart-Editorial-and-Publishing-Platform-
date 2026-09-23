"""
Checks that run before an article reaches the evaluation service.

Every call to the service costs money and takes time, and a large share of
wasted calls are not borderline judgements — they are submissions nobody meant
to make. A draft with a placeholder still in it, a piece two paragraphs long, a
resubmission with nothing changed.

These checks are deliberately mechanical. They do not judge whether an article
is good; they establish whether it is finished enough to be worth asking. The
failures they produce read as the writer's own checklist rather than a refusal.
"""
import hashlib
import re
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

# A magazine publishes at many lengths. An editor's letter runs to 400
# words, a column to 600, but a front-of-book news item is 150 and a caption
# with commentary is under a hundred — all of them legitimate published work.
# The floor exists to catch the two-line accident, not to impose a house
# style, so it is set low and left configurable. BOSS can raise it once they
# have seen their own distribution.
MIN_WORDS = getattr(settings, "AI_MIN_WORDS", 120)
COOLDOWN = timedelta(minutes=5)
DAILY_LIMIT = 20

# TK is the journalism convention for "to come" and survives precisely because
# no English word contains the pair. The rest are the usual suspects.
PLACEHOLDERS = [
    (re.compile(r"\bTK\b"), "TK markers"),
    (re.compile(r"lorem ipsum", re.I), "placeholder text"),
    (re.compile(r"\b(TODO|FIXME|XXX)\b", re.I), "working notes"),
    (re.compile(r"\[(insert|add|check|source|quote)\b", re.I), "square-bracket notes"),
    (re.compile(r"\.\.\.\s*$", re.M), "trailing ellipses"),
]


class NotReady(Exception):
    """Carries the reasons, so the writer sees all of them at once rather
    than discovering them one resubmission at a time."""

    def __init__(self, reasons):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


def content_hash(article):
    """Identifies the copy, so an unchanged resubmission can reuse its
    assessment rather than buying the same answer twice."""
    body = re.sub(r"<[^>]+>", " ", article.body or "")
    body = re.sub(r"\s+", " ", body).strip().lower()
    subject = f"{(article.title or '').strip().lower()}|{body}"
    return hashlib.sha256(subject.encode("utf-8")).hexdigest()


def word_count(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    return len([w for w in text.split() if w.strip()])


def check(article, user):
    """Raise NotReady with everything that is wrong, or return quietly.

    Checks are ordered so the writer reads the substantial problems first.
    """
    reasons = []
    text = re.sub(r"<[^>]+>", " ", article.body or "")

    # ---- length -----------------------------------------------------------
    words = word_count(article.body)
    if words < MIN_WORDS:
        reasons.append(
            f"The draft runs to {words} words. Assessment begins at "
            f"{MIN_WORDS} words — an editor can change this for the "
            f"publication if your work runs shorter."
        )

    # ---- headline and standfirst ------------------------------------------
    if not (article.title or "").strip():
        reasons.append("The article has no headline.")

    if not (article.excerpt or "").strip():
        reasons.append(
            "The standfirst is empty. It is the sentence beneath the headline, "
            "and the reader portal needs one."
        )

    # ---- placeholders -----------------------------------------------------
    found = [label for pattern, label in PLACEHOLDERS if pattern.search(text)]
    if found:
        reasons.append(
            f"The copy still contains {', '.join(found)}. Resolve them before "
            f"submitting."
        )

    # ---- structure --------------------------------------------------------
    paragraphs = [p for p in re.split(r"</p>|<br\s*/?>", article.body or "")
                  if word_count(p) > 5]
    if words >= 400 and len(paragraphs) < 3:
        reasons.append(
            "The article is a single block of text. Break it into paragraphs "
            "so it can be read."
        )

    if words >= MIN_WORDS and not re.search(r"[.!?]", text):
        reasons.append("The copy contains no sentence endings.")

    # ---- unchanged resubmission -------------------------------------------
    last = article.evaluations.order_by("-created_at").first()
    if last and last.content_hash and last.content_hash == content_hash(article):
        reasons.append(
            "The copy has not changed since its last assessment. Revise it "
            "before submitting again — the previous result still stands."
        )

    # ---- cooldown ---------------------------------------------------------
    # Waived once every quick fix from that assessment has been dealt with:
    # accepting fixes and resubmitting straight away is the intended path,
    # and the daily ceiling still bounds it.
    from apps.ai_eval.fixes import all_resolved
    if last and timezone.now() - last.created_at < COOLDOWN and not all_resolved(last):
        wait = COOLDOWN - (timezone.now() - last.created_at)
        reasons.append(
            f"This article was assessed {int(wait.total_seconds() // 60) + 1} "
            f"minute(s) ago. Assessment is rate-limited; use the time to read "
            f"the notes."
        )

    # ---- daily ceiling ----------------------------------------------------
    from apps.ai_eval.models import ArticleEvaluation

    today = ArticleEvaluation.objects.filter(
        article__writer=user,
        created_at__gte=timezone.now() - timedelta(days=1),
    ).count()
    if today >= DAILY_LIMIT:
        reasons.append(
            f"You have reached the daily assessment limit of {DAILY_LIMIT}. "
            f"An editor can review the article without one."
        )

    if reasons:
        raise NotReady(reasons)
