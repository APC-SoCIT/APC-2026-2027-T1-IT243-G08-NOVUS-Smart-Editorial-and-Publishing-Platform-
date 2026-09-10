"""
Populates a realistic editorial pipeline for demonstration.

    python manage.py seed_demo          # add to what's there
    python manage.py seed_demo --fresh  # wipe articles/issues first

Scores here are illustrative, not produced by the AI. Anything created by this
command is marked in its evaluation payload so it can never be mistaken for a
live result.
"""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.ai_eval.models import ArticleEvaluation
from apps.editorial.models import Article, ArticleVersion, RevisionNote
from apps.issues.models import Issue

STORIES = [
    ("The Quiet Rise of Filipino Design Studios", "Business",
     "A decade ago most Filipino creative talent was exported. Today the studios are staying home.",
     ["Manila studios are taking brand work for clients in Singapore, Sydney and London.",
      "The shift was not talent but infrastructure: connectivity, payment rails, and a generation who grew up presenting over video.",
      "What remains scarce is not skill but the confidence to price like a global agency."]),
    ("Why Local Startups Are Betting on Sustainability", "Tech",
     "Environmental impact has moved from a marketing line to a funding requirement.",
     ["Investors now ask about impact in the first meeting rather than the last.",
      "Founders have adjusted, though some concede the metrics are still being invented."]),
    ("What Remote Work Did to Filipino Management Culture", "Leadership",
     "Three years of distributed teams quietly rewrote how Filipino managers lead.",
     ["The traditional emphasis on presence gave way, unevenly, to an emphasis on output.",
      "Middle managers absorbed most of the change, and most of the strain."]),
    ("The Return of the Manila Coffee Bar", "Life",
     "Specialty coffee has entered a second wave, and this one is less about imported beans.",
     ["Growers in Benguet and Sultan Kudarat now supply roasters who once looked only to Ethiopia.",
      "The result is a cup that tastes like somewhere rather than anywhere."]),
    ("Fintech Adoption Beyond Metro Manila", "Innovation",
     "Digital wallets are growing fast in the provinces, but the numbers hide a retention problem.",
     ["Many users open an account and never transact again after the first incentive.",
      "Agents, not apps, remain the trusted interface in much of the country."]),
    ("The Landlords Rethinking Retail Space", "Business",
     "Mall vacancies forced a reckoning that online shopping alone does not explain.",
     ["Anchor tenants are shrinking footprints while independents take the space.",
      "Leasing terms have become negotiable in ways unthinkable five years ago."]),
    ("Inside the Philippine Game Studios Going Global", "Tech",
     "A small cluster of studios is shipping to Steam without leaving Quezon City.",
     ["Publishing deals that once required relocation now close over email.",
      "The bottleneck is no longer distribution but discoverability."]),
    ("The New Rules of Filipino Hospitality", "Life",
     "Boutique hotels are trading grandeur for specificity.",
     ["Guests increasingly book a point of view rather than a star rating.",
      "Owners describe the shift as a return to how they always wanted to host."]),
    ("Succession Planning in Family Businesses", "Leadership",
     "The second generation is arriving with different assumptions.",
     ["Founders built on relationships; successors build on systems.",
      "The handover works when both are treated as legitimate."]),
    ("Cold Chains and the Fight Against Food Waste", "Innovation",
     "A logistics problem is quietly reshaping Philippine agriculture.",
     ["Post-harvest losses remain among the highest in the region.",
      "Refrigeration investment is finally following the produce rather than the retail."]),
    ("The Designers Reviving Philippine Textiles", "Life",
     "Weaving traditions are finding a market that pays properly for them.",
     ["Collaboration replaced extraction, though the line is still contested.",
      "Provenance now sells as strongly as pattern."]),
    ("What the Peso's Slide Means for Importers", "Business",
     "Currency pressure is reshaping procurement decisions across the sector.",
     ["Some firms hedged early; most did not.",
      "The adjustment has been passed to consumers unevenly."]),
    ("The Case for Four-Day Weeks in BPO", "Leadership",
     "A handful of firms are testing compressed schedules in an industry built on coverage.",
     ["Early results suggest retention gains outweigh scheduling friction.",
      "Clients, predictably, needed the most convincing."]),
    ("Solar's Slow Arrival on Philippine Rooftops", "Innovation",
     "Net metering rules and financing gaps explain more than sunlight ever did.",
     ["Installation costs have fallen faster than approval times.",
      "Households that persevered report payback inside six years."]),
    ("The Bookstores That Refused to Close", "Life",
     "Independent shops found a model that chain retail could not copy.",
     ["Curation and community events replaced volume as the business case.",
      "Several now publish as well as sell."]),
]

REVISION_NOTES = [
    ("Introduction", "STRUCTURE", "The main claim is buried in the third paragraph. Lead with it.", "HIGH"),
    ("Body", "FACTUAL", "The adoption figure needs a source or it should come out.", "HIGH"),
    ("Body", "TONE", "This section reads as advocacy rather than reporting.", "MEDIUM"),
    ("Conclusion", "STRUCTURE", "The ending stops rather than concludes. Give the reader a takeaway.", "MEDIUM"),
    ("Throughout", "GRAMMAR", "Several subject-verb agreement errors, particularly with collective nouns.", "HIGH"),
]


class Command(BaseCommand):
    help = "Create a realistic editorial pipeline for demonstration."

    def add_arguments(self, parser):
        parser.add_argument("--fresh", action="store_true",
                            help="Delete existing articles and issues first.")

    def handle(self, *args, **opts):
        writers = list(User.objects.filter(role=User.Role.WRITER, is_active=True))
        editor = User.objects.filter(role=User.Role.EDITOR).first()
        publisher = User.objects.filter(role=User.Role.PUBLISHER).first()

        if not writers or not editor or not publisher:
            self.stderr.write(self.style.ERROR(
                "Need at least one writer, editor and publisher. "
                "Create the demo accounts first."))
            return

        if opts["fresh"]:
            ArticleEvaluation.objects.all().delete()
            RevisionNote.objects.all().delete()
            ArticleVersion.objects.all().delete()
            Article.objects.all().delete()
            self.stdout.write("Cleared existing articles.")

        today = timezone.now().date()
        now = timezone.now()

        issue, _ = Issue.objects.get_or_create(
            number=13,
            defaults={"title": "The Innovation Issue",
                      "target_release_date": today + timedelta(days=21),
                      "created_by": publisher},
        )

        # A spread across the pipeline, weighted the way a real desk looks:
        # more work in progress than finished.
        plan = [
            ("PUBLISHED", 3), ("APPROVED", 2), ("UNDER_REVIEW", 3),
            ("REVISION_REQUESTED", 2), ("DRAFTING", 3), ("ASSIGNED", 2),
        ]

        made = 0
        i = 0
        for status, count in plan:
            for _ in range(count):
                if i >= len(STORIES):
                    break
                title, category, excerpt, paras = STORIES[i]
                i += 1

                writer = random.choice(writers)
                offset = random.randint(-6, 18)

                article = Article.objects.create(
                    title=title,
                    category=category,
                    excerpt=excerpt,
                    body="".join(f"<p>{p}</p>" for p in paras),
                    writer=writer,
                    editor=editor if status not in ("ASSIGNED", "DRAFTING") else None,
                    assigned_by=editor,
                    brief=f"Cover {category.lower()} angle. Speak to at least two sources.",
                    deadline=today + timedelta(days=offset),
                    status=status,
                    created_at=now - timedelta(days=random.randint(1, 30)),
                )

                if status in ("UNDER_REVIEW", "APPROVED", "PUBLISHED", "REVISION_REQUESTED"):
                    ArticleVersion.objects.create(
                        article=article, number=1, title=title,
                        body=article.body, excerpt=excerpt, submitted_by=writer)

                    failing = status == "REVISION_REQUESTED"
                    overall = random.randint(48, 66) if failing else random.randint(74, 94)
                    ev = ArticleEvaluation.objects.create(
                        article=article,
                        grammar_score=overall + random.randint(-5, 5),
                        readability_score=overall + random.randint(-5, 5),
                        overall_score=overall,
                        recommendation="REJECT" if failing else "APPROVE",
                        summary=("The reporting is promising but the draft needs "
                                 "structural work before review."
                                 if failing else
                                 "Clear structure and a strong opening. Reads cleanly."),
                        suggestions=[
                            {"section": s, "note_type": t, "instruction": ins, "priority": p}
                            for s, t, ins, p in random.sample(REVISION_NOTES, 2 if failing else 0)
                        ],
                        ai_model="seed-demo",
                        raw_response={"seeded": True},
                    )
                    if failing:
                        article.returned_by_ai = True
                        article.save(update_fields=["returned_by_ai"])
                        for s in ev.suggestions:
                            RevisionNote.objects.create(
                                article=article, editor=None, section=s["section"],
                                note_type=s["note_type"], instruction=s["instruction"],
                                priority=s["priority"])

                if status in ("APPROVED", "PUBLISHED"):
                    article.issue = issue
                    article.is_premium = True
                    article.save(update_fields=["issue", "is_premium"])

                if status == "PUBLISHED":
                    article.published_at = now - timedelta(days=random.randint(1, 14))
                    article.save(update_fields=["published_at"])

                made += 1

        # One featured piece for the homepage hero.
        lead = Article.objects.filter(status="PUBLISHED").first()
        if lead:
            lead.is_featured = True
            lead.is_premium = False   # the shop window should be readable
            lead.save(update_fields=["is_featured", "is_premium"])

        self.stdout.write(self.style.SUCCESS(
            f"Created {made} articles across the pipeline, plus {issue}."))
        self.stdout.write(self.style.WARNING(
            "Scores are illustrative, not AI-generated."))
