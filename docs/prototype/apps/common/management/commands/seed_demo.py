"""
Populates a realistic editorial operation for demonstration.

    python manage.py seed_demo           # add to what exists
    python manage.py seed_demo --fresh   # clear editorial data first

What this creates and why it looks the way it does:

A magazine that has been running for months, not one that started yesterday.
Articles are spread across five months so the archive has shape and the
calendar has history. Four writers rather than one, because a workload chart
with a single bar tells you nothing. Issues at every stage — two published,
one nearly ready, one just opened — so each dashboard has something true to
show.

Evaluation scores here are written by this command, not produced by the
model. Every seeded evaluation records ai_model='seed-demo' so the reports can
identify them, and so nobody mistakes them for live output.
"""
import io
import random
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import ReaderProfile, User
from apps.ai_eval.models import ArticleEvaluation
from apps.design.models import MagazineDesign
from apps.editorial.models import (
    Article, ArticleImage, ArticleVersion, RevisionNote,
)
from apps.issues.models import Issue
from apps.messaging.models import Message
from apps.notifications.models import Notification

# --------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------

WRITERS = [
    ("maria@boss.ph", "Maria", "Santos"),
    ("teo@boss.ph", "Teodoro", "Lim"),
    ("bea@boss.ph", "Beatriz", "Ocampo"),
    ("rafa@boss.ph", "Rafael", "Mendoza"),
]

# --------------------------------------------------------------------------
# Copy
#
# Written to read like a business and lifestyle magazine rather than filler:
# each has a headline that could run, a standfirst that says something, and
# body copy with an argument in it. Short, but not lorem ipsum.
# --------------------------------------------------------------------------

STORIES = [
    ("The Quiet Rise of Filipino Design Studios", "Business",
     "A decade ago most Filipino creative talent was exported. Today the studios are staying home.",
     ["Manila studios are taking brand work for clients in Singapore, Sydney and London, and doing it without opening an office abroad.",
      "The shift was not talent but infrastructure: connectivity, payment rails, and a generation who grew up presenting over video.",
      "What remains scarce is not skill but the confidence to price like a global agency. Several founders described quoting in pesos and watching a client visibly relax."]),

    ("Why Local Startups Are Betting on Sustainability", "Tech",
     "Environmental impact has moved from a marketing line to a funding requirement.",
     ["Investors now ask about impact in the first meeting rather than the last, and founders have adjusted their decks accordingly.",
      "Some concede the metrics are still being invented. One founder admitted his impact figures were 'directionally honest' and nothing more.",
      "The risk is a market where everyone reports well and nobody measures carefully."]),

    ("What Remote Work Did to Filipino Management Culture", "Leadership",
     "Three years of distributed teams quietly rewrote how Filipino managers lead.",
     ["The traditional emphasis on presence gave way, unevenly, to an emphasis on output.",
      "Middle managers absorbed most of the change and most of the strain. Several described learning to trust work they could not watch being done.",
      "Where it worked, it worked because someone wrote things down. Where it failed, it failed for the same reason."]),

    ("The Return of the Manila Coffee Bar", "Life",
     "Specialty coffee has entered a second wave, and this one is less about imported beans.",
     ["Growers in Benguet and Sultan Kudarat now supply roasters who once looked only to Ethiopia and Colombia.",
      "The result is a cup that tastes like somewhere rather than anywhere.",
      "Margins remain thin. The romance of provenance does not pay rent on Legazpi Street."]),

    ("Fintech Adoption Beyond Metro Manila", "Innovation",
     "Digital wallets are growing fast in the provinces, but the numbers hide a retention problem.",
     ["Many users open an account and never transact again after the first incentive expires.",
      "Agents, not apps, remain the trusted interface in much of the country — a person you can find if something goes wrong.",
      "The companies winning are the ones who understood that early and built around it rather than against it."]),

    ("The Landlords Rethinking Retail Space", "Business",
     "Mall vacancies forced a reckoning that online shopping alone does not explain.",
     ["Anchor tenants are shrinking footprints while independents take the space they leave.",
      "Leasing terms have become negotiable in ways that would have been unthinkable five years ago.",
      "One developer described it as learning to be a curator rather than a collector of rent."]),

    ("Inside the Philippine Game Studios Going Global", "Tech",
     "A small cluster of studios is shipping to Steam without leaving Quezon City.",
     ["Publishing deals that once required relocation now close over email and a shared build.",
      "The bottleneck is no longer distribution but discoverability — getting seen among thousands of releases.",
      "Two studios have started funding each other's marketing, which says something about how little else is available."]),

    ("The New Rules of Filipino Hospitality", "Life",
     "Boutique hotels are trading grandeur for specificity.",
     ["Guests increasingly book a point of view rather than a star rating.",
      "Owners describe the shift as a return to how they always wanted to host, before the category demanded marble.",
      "It scales badly, which may be the point."]),

    ("Succession Planning in Family Businesses", "Leadership",
     "The second generation is arriving with different assumptions.",
     ["Founders built on relationships; successors build on systems. Neither is wrong and both are incomplete.",
      "The handover works when both are treated as legitimate rather than one as a correction of the other.",
      "It fails, reliably, when the founder keeps the relationships and hands over only the org chart."]),

    ("Cold Chains and the Fight Against Food Waste", "Innovation",
     "A logistics problem is quietly reshaping Philippine agriculture.",
     ["Post-harvest losses remain among the highest in the region, and most of them happen in the first day.",
      "Refrigeration investment is finally following the produce rather than the retail, which is a reversal.",
      "Farmers who can hold stock for a week negotiate differently. That is the whole argument."]),

    ("The Designers Reviving Philippine Textiles", "Life",
     "Weaving traditions are finding a market that pays properly for them.",
     ["Collaboration replaced extraction, though where the line sits is still contested and probably should be.",
      "Provenance now sells as strongly as pattern, which has changed what designers are willing to disclose.",
      "The weavers, asked directly, mostly want consistent orders rather than recognition."]),

    ("What the Peso's Slide Means for Importers", "Business",
     "Currency pressure is reshaping procurement decisions across the sector.",
     ["Some firms hedged early. Most did not, and are now discovering what their margins were actually made of.",
      "The adjustment has been passed to consumers unevenly, which tells you who has pricing power.",
      "Several importers have started sourcing domestically for the first time in a decade."]),

    ("The Case for Four-Day Weeks in BPO", "Leadership",
     "A handful of firms are testing compressed schedules in an industry built on coverage.",
     ["Early results suggest retention gains outweigh the scheduling friction, though the sample is small.",
      "Clients, predictably, needed the most convincing — and were convinced by attrition numbers rather than argument.",
      "Nobody involved claims it generalises. Several think it might anyway."]),

    ("Solar's Slow Arrival on Philippine Rooftops", "Innovation",
     "Net metering rules and financing gaps explain more than sunlight ever did.",
     ["Installation costs have fallen faster than approval times, which is now the binding constraint.",
      "Households that persevered report payback inside six years and a marked drop in argument about air conditioning.",
      "The industry's problem is not demand. It is the eleven weeks between wanting one and having one."]),

    ("The Bookstores That Refused to Close", "Life",
     "Independent shops found a model that chain retail could not copy.",
     ["Curation and community events replaced volume as the business case, which required accepting a smaller business.",
      "Several now publish as well as sell, mostly poetry, mostly at a loss they describe as deliberate.",
      "The ones that survived had landlords who were also customers. That is not a strategy anyone can adopt."]),

    ("How Philippine Coffee Farmers Are Reclaiming Value", "Business",
     "Direct trade is shifting margin back up the chain, slowly.",
     ["Cooperatives that once sold green beans at commodity prices now roast and brand their own.",
      "The capital required is modest; the expertise is not, and most of it had to be learned from scratch.",
      "Buyers report better consistency than three years ago, which is the only endorsement that matters."]),

    ("The Architects Building for Flooding", "Innovation",
     "Design is adapting to a climate reality that planning regulation has not caught up with.",
     ["Elevated ground floors and permeable surfaces are becoming standard in new residential work.",
      "Retrofitting existing stock is where the real problem sits, and where almost no funding exists.",
      "One architect described her job as 'arguing with 1970s assumptions in 2026 buildings'."]),

    ("Why Filipino Podcasts Found Their Audience", "Tech",
     "A medium that struggled for years is suddenly working.",
     ["Cheaper data and longer commutes did more for the format than any production investment.",
      "Advertisers arrived late and are still working out what they are buying.",
      "The most listened-to shows are conversational rather than produced, which surprised everyone except the hosts."]),
]

REVISION_NOTES = [
    ("Introduction", "STRUCTURE",
     "The main claim is buried in the third paragraph. Lead with it.", "HIGH"),
    ("Body", "FACTUAL",
     "The adoption figure needs a source or it should come out.", "HIGH"),
    ("Body", "TONE",
     "This section reads as advocacy rather than reporting.", "MEDIUM"),
    ("Conclusion", "STRUCTURE",
     "The ending stops rather than concludes. Give the reader a takeaway.", "MEDIUM"),
    ("Throughout", "GRAMMAR",
     "Several subject-verb agreement errors, particularly with collective nouns.", "HIGH"),
    ("Second section", "STRUCTURE",
     "Two ideas are competing here. Split them or cut one.", "MEDIUM"),
]

SUMMARIES_PASS = [
    "Clear structure and a strong opening. The argument holds through to the end.",
    "Well sourced and readable. Minor tightening would help the middle section.",
    "Confident reporting with a distinct voice. Ready for an editor.",
    "The lead does its job and the piece earns its length.",
]

SUMMARIES_FAIL = [
    "The reporting is promising but the draft needs structural work before review.",
    "Several factual claims are unsupported and the argument loses shape after the opening.",
    "Readable, but the piece does not decide what it is about until too late.",
]

MESSAGES = [
    ("Can we get a second source on the figure in paragraph three?", "editor"),
    ("Chasing it now — the cooperative said they'd send the numbers today.", "writer"),
    ("No rush. Happy with the rest of it.", "editor"),
    ("Should this run before or after the issue ships?", "writer"),
    ("Let's hold it for the issue. It reads better alongside the cover story.", "editor"),
]


def tiny_image(colour="white", size=(1200, 800)):
    """A real image. ImageField validates with Pillow, so a fabricated header
    is rejected as a corrupt file."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", size, colour).save(buf, format="JPEG", quality=70)
    return ContentFile(buf.getvalue())


COVER_COLOURS = ["#1a2744", "#7b4b94", "#1c6b45", "#8a5a12", "#9e2f2f"]


def placeholder_pdf(title, pages=4):
    """A structurally valid multi-page PDF.

    The previous placeholder was a header and nothing else, which satisfied
    the upload validator but could not be parsed by the reader — so a seeded
    issue looked publishable and then failed when someone opened it.

    Written by hand rather than with a library: a PDF is a small set of
    numbered objects and a cross-reference table, and generating one here
    avoids a dependency for something only the demo data needs.
    """
    objects = []

    # 1: catalogue, 2: page tree, 3: font. Pages follow.
    kids = " ".join(f"{4 + i * 2} 0 R" for i in range(pages))
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for i in range(pages):
        content = (
            f"BT /F1 28 Tf 72 700 Td ({title}) Tj ET\n"
            f"BT /F1 14 Tf 72 660 Td (Placeholder layout - page {i + 1} of {pages}) Tj ET\n"
            f"BT /F1 10 Tf 72 100 Td (Generated by seed_demo. Not a real magazine layout.) Tj ET"
        )
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> "
            f"/Contents {5 + i * 2} 0 R >>")
        objects.append(
            f"<< /Length {len(content)} >>\nstream\n{content}\nendstream")

    out = "%PDF-1.4\n"
    offsets = []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n{body}\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n"
    out += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_at}\n%%EOF\n")

    return ContentFile(out.encode("latin-1"))


class Command(BaseCommand):
    help = "Create a realistic editorial operation for demonstration."

    def add_arguments(self, parser):
        parser.add_argument("--fresh", action="store_true",
                            help="Clear editorial data before seeding.")
        parser.add_argument("--images", action="store_true",
                            help="Generate placeholder hero images. Slower.")

    # ----------------------------------------------------------------------

    def handle(self, *args, **opts):
        self.stdout.write("Seeding…")

        editor = User.objects.filter(role=User.Role.EDITOR).first()
        publisher = User.objects.filter(role=User.Role.PUBLISHER).first()
        designer = User.objects.filter(role=User.Role.GRAPHIC_DESIGNER).first()

        if not (editor and publisher and designer):
            self.stderr.write(self.style.ERROR(
                "Need an editor, a publisher and a designer. "
                "Create the staff accounts first."))
            return

        if opts["fresh"]:
            self._clear()

        writers = self._writers()
        issues = self._issues(publisher)
        self._articles(writers, editor, publisher, issues, opts["images"])
        self._designs(designer, editor, issues)
        self._readers()

        self.stdout.write(self.style.SUCCESS("\nDone."))
        self._summary()
        self.stdout.write(self.style.WARNING(
            "\nEvaluation scores here were written by this command, not "
            "produced by the model. They are marked ai_model='seed-demo'."))

    # ----------------------------------------------------------------------

    def _clear(self):
        # Children before parents: the foreign keys are PROTECT in places.
        Message.objects.all().delete()
        ArticleEvaluation.objects.all().delete()
        RevisionNote.objects.all().delete()
        ArticleVersion.objects.all().delete()
        ArticleImage.objects.all().delete()
        Article.objects.all().delete()
        MagazineDesign.objects.all().delete()
        Issue.objects.all().delete()
        Notification.objects.all().delete()
        self.stdout.write("  cleared existing editorial data")

    def _writers(self):
        made = []
        for email, first, last in WRITERS:
            u, created = User.objects.get_or_create(
                email=email,
                defaults={"first_name": first, "last_name": last,
                          "role": User.Role.WRITER},
            )
            if created:
                u.set_password("writer1234")
                u.save()
            made.append(u)
        self.stdout.write(f"  {len(made)} writers")
        return made

    def _issues(self, publisher):
        today = date.today()
        plan = [
            # number, title, months ago, status, minimum
            (11, "The Resilience Issue", 4, Issue.Status.PUBLISHED, 4),
            (12, "The Design Issue", 2, Issue.Status.PUBLISHED, 4),
            (13, "The Innovation Issue", 0, Issue.Status.PLANNING, 5),
            (14, "The Leadership Issue", -2, Issue.Status.PLANNING, 5),
        ]
        made = {}
        for number, title, ago, status, minimum in plan:
            target = today - timedelta(days=30 * ago)
            issue, _ = Issue.objects.get_or_create(
                number=number,
                defaults={
                    "title": title,
                    "minimum_articles": minimum,
                    "target_release_date": target,
                    "status": status,
                    "created_by": publisher,
                    "published_by": publisher if status == Issue.Status.PUBLISHED else None,
                    "published_at": (timezone.now() - timedelta(days=30 * ago))
                                    if status == Issue.Status.PUBLISHED else None,
                },
            )
            made[number] = issue
        self.stdout.write(f"  {len(made)} issues")
        return made

    # ----------------------------------------------------------------------

    def _articles(self, writers, editor, publisher, issues, with_images):
        """Distribution chosen so every screen has something true to show:
        a back catalogue with depth, a review queue that is not empty, work
        in progress at each stage, and two things genuinely overdue."""
        today = date.today()
        now = timezone.now()
        plan = [
            # status, count, issue number or None, months ago
            (Article.Status.PUBLISHED, 4, 11, 4),
            (Article.Status.PUBLISHED, 4, 12, 2),
            (Article.Status.PUBLISHED, 2, None, 1),
            (Article.Status.APPROVED, 2, 13, 0),
            (Article.Status.UNDER_REVIEW, 3, None, 0),
            (Article.Status.REVISION_REQUESTED, 2, None, 0),
            (Article.Status.DRAFTING, 2, None, 0),
            (Article.Status.ASSIGNED, 1, None, 0),
        ]

        i = 0
        made = 0
        for status, count, issue_no, ago in plan:
            for _ in range(count):
                if i >= len(STORIES):
                    break
                title, category, excerpt, paras = STORIES[i]
                i += 1

                writer = writers[i % len(writers)]
                issue = issues.get(issue_no) if issue_no else None

                # Two overdue, the rest comfortable — enough to show the
                # deadline machinery without the dashboard looking like a
                # disaster.
                if status in (Article.Status.DRAFTING, Article.Status.ASSIGNED) and made % 5 == 0:
                    deadline = today - timedelta(days=random.randint(2, 6))
                else:
                    deadline = today + timedelta(days=random.randint(3, 24))

                created = now - timedelta(days=30 * ago + random.randint(1, 20))

                article = Article.objects.create(
                    title=title, category=category, excerpt=excerpt,
                    body="".join(f"<p>{p}</p>" for p in paras),
                    writer=writer,
                    editor=editor if status not in (
                        Article.Status.ASSIGNED, Article.Status.DRAFTING) else None,
                    assigned_by=editor,
                    brief=f"Cover the {category.lower()} angle. Speak to at "
                          f"least two sources and get numbers where you can.",
                    deadline=deadline,
                    status=status,
                    issue=issue,
                    is_premium=bool(issue),
                )
                Article.objects.filter(pk=article.pk).update(created_at=created)

                if with_images and status == Article.Status.PUBLISHED:
                    article.hero_image.save(
                        f"hero-{article.pk}.jpg",
                        tiny_image(random.choice(COVER_COLOURS)), save=True)
                    article.hero_caption = "Photograph by the BOSS picture desk"
                    article.save(update_fields=["hero_caption"])

                self._history(article, writer, editor, status, created)

                if status == Article.Status.PUBLISHED:
                    Article.objects.filter(pk=article.pk).update(
                        published_at=created + timedelta(days=random.randint(3, 10)))

                made += 1

        lead = Article.objects.filter(status=Article.Status.PUBLISHED).first()
        if lead:
            lead.is_featured = True
            lead.is_premium = False   # the shop window should be readable
            lead.save(update_fields=["is_featured", "is_premium"])

        self.stdout.write(f"  {made} articles")

    def _history(self, article, writer, editor, status, created):
        """Versions, evaluations, notes and discussion — the trail that makes
        an article look worked on rather than inserted."""
        submitted = status not in (Article.Status.ASSIGNED, Article.Status.DRAFTING)
        if not submitted:
            return

        ArticleVersion.objects.create(
            article=article, number=1, title=article.title,
            body=article.body, excerpt=article.excerpt, submitted_by=writer)

        failing = status == Article.Status.REVISION_REQUESTED
        overall = random.randint(48, 66) if failing else random.randint(74, 94)

        suggestions = [
            {"section": s, "note_type": t, "instruction": ins, "priority": p}
            for s, t, ins, p in random.sample(REVISION_NOTES, 2 if failing else 0)
        ]

        ArticleEvaluation.objects.create(
            article=article,
            grammar_score=max(0, min(100, overall + random.randint(-6, 6))),
            readability_score=max(0, min(100, overall + random.randint(-6, 6))),
            overall_score=overall,
            recommendation="REJECT" if failing else "APPROVE",
            summary=random.choice(SUMMARIES_FAIL if failing else SUMMARIES_PASS),
            suggestions=suggestions,
            ai_model="seed-demo",
            raw_response={"seeded": True},
        )

        if failing:
            article.returned_by_ai = True
            article.save(update_fields=["returned_by_ai"])
            for s in suggestions:
                RevisionNote.objects.create(
                    article=article, editor=None, section=s["section"],
                    note_type=s["note_type"], instruction=s["instruction"],
                    priority=s["priority"])

        # A conversation on roughly every third article.
        if article.pk % 3 == 0:
            for body, who in MESSAGES[:random.randint(2, 5)]:
                Message.objects.create(
                    article=article,
                    sender=editor if who == "editor" else writer,
                    body=body)

    def _designs(self, designer, editor, issues):
        made = 0
        for number, issue in issues.items():
            if issue.status != Issue.Status.PUBLISHED and number != 13:
                continue
            approved = issue.status == Issue.Status.PUBLISHED
            d = MagazineDesign.objects.create(
                issue=issue, version="v1.0", designer=designer,
                notes_to_editor="Cover treatment follows the house grid. "
                                "Type is set in Canela for the display.",
                status=(MagazineDesign.Status.APPROVED if approved
                        else MagazineDesign.Status.PENDING_REVIEW),
                reviewed_by=editor if approved else None,
                reviewed_at=timezone.now() if approved else None,
            )
            d.file.save(f"issue-{number}-layout.pdf",
                        placeholder_pdf(f"BOSS Magazine - Issue {number}"),
                        save=False)
            d.cover_image.save(f"issue-{number}-cover.jpg",
                               tiny_image(COVER_COLOURS[number % len(COVER_COLOURS)],
                                          (900, 1200)), save=True)
            made += 1
        self.stdout.write(f"  {made} layouts")

    def _readers(self):
        people = [
            ("reader@boss.ph", "Ana", "Villanueva", ReaderProfile.Tier.FREE),
            ("subscriber@boss.ph", "Paolo", "Reyes", ReaderProfile.Tier.SUBSCRIBER),
        ]
        for email, first, last, tier in people:
            u, created = User.objects.get_or_create(
                email=email,
                defaults={"first_name": first, "last_name": last,
                          "role": User.Role.READER},
            )
            if created:
                u.set_password("reader1234")
                u.save()
            profile, _ = ReaderProfile.objects.get_or_create(user=u)
            profile.tier = tier
            if tier == ReaderProfile.Tier.SUBSCRIBER:
                profile.subscription_started_at = timezone.now() - timedelta(days=60)
            profile.save()
        self.stdout.write("  2 readers (1 free, 1 subscriber)")

    def _summary(self):
        from django.db.models import Count
        self.stdout.write("")
        for row in (Article.objects.values("status")
                    .annotate(n=Count("id")).order_by("-n")):
            label = row["status"].replace("_", " ").title()
            self.stdout.write(f"  {row['n']:>3}  {label}")
        self.stdout.write(f"  {Issue.objects.count():>3}  Issues")
        self.stdout.write(f"  {MagazineDesign.objects.count():>3}  Layouts")
        self.stdout.write(f"  {Message.objects.count():>3}  Messages")
