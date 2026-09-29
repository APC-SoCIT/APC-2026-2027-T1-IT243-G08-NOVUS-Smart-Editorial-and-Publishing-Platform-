"""
A showcase dataset: every screen and every demonstration step has a record in
exactly the state it needs, so nothing has to be staged live.

    python manage.py seed_showcase              # replace content, keep accounts
    python manage.py seed_showcase --no-images  # faster; no photographs or covers

Accounts are never removed or re-passworded. Only editorial content, issues,
layouts, messages, notifications and bookmarks are replaced.

Issues are closed through the application's own close action and published
through its own publishing service, so a seeded issue is in precisely the
state a real one would be. If either would refuse during a demonstration,
this command refuses too, and says why.

Evaluation scores are written by this command, not produced by the model.
Every one is marked ai_model='seed-demo'.
"""
from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import ReaderProfile, User
from apps.ai_eval.models import ArticleEvaluation, FixDecision
from apps.common.management.commands.seed_demo import (
    COVER_COLOURS, FLAWED_SENTENCE, SEED_FIXES, placeholder_pdf, tiny_image,
)
from apps.content.models import Bookmark
from apps.design.models import MagazineDesign
from apps.editorial.models import Article, ArticleImage, ArticleVersion, RevisionNote
from apps.issues.models import Issue
from apps.messaging.models import Message
from apps.notifications.models import Notification
from apps.notifications.services import article_link

S = Article.Status


def html(paras):
    return "".join(f"<p>{p}</p>" for p in paras)


# ---------------------------------------------------------------------------
# Copy. Written for BOSS Magazine's beats; each piece has an argument.
# ---------------------------------------------------------------------------

STORIES = {
    # ---- Issue 21: The Heritage Issue (published, then retired) ----------
    "jeepney": ("The Last Jeepney Painters of Sarao", "Life",
        "The artists who gave Manila's streets their colour are running out of vehicles to paint.",
        ["For seventy years the workshops of Las Piñas turned surplus army trucks into rolling murals. Modernisation rules now favour standard minibuses, and the painters' order books are thinning with every renewal cycle.",
         "The younger hands have moved to signage, tattoo work and brand murals, carrying the same airbrush discipline into walls rather than chassis.",
         "What survives is less a trade than a visual grammar: the chrome horses, the saints and the script lettering now appear on packaging, streetwear and hotel lobbies."]),
    "barong": ("The Barong Goes Back to Work", "Life",
        "A formal garment is finding a second life in the office, and designers are rethinking its fabric.",
        ["For decades the barong was reserved for weddings and state occasions. A new generation of tailors is cutting it looser, in cotton and linen blends meant for a Tuesday rather than a gala.",
         "Piña remains the prestige fibre, but its price and fragility have pushed makers towards blends that breathe without demanding a steamer.",
         "The result is a garment that signals heritage without costume, and it is selling to buyers who never owned a formal one."]),
    "familycorp": ("Three Generations, One Balance Sheet", "Leadership",
        "Filipino family firms are learning that succession is a governance question, not a sentimental one.",
        ["The founders built on relationships and memory. Their grandchildren arrive with board charters, audit committees and dashboards.",
         "Firms that managed the handover treated both approaches as legitimate, formalising what the founder knew instead of discarding it.",
         "Those that struggled kept the relationships with the patriarch and handed the heirs an organisation chart with nothing behind it."]),
    "heirloom": ("Heirloom Rice and the Price of Memory", "Business",
        "Cordillera farmers are finding premium buyers for grains that nearly disappeared.",
        ["Terraced varieties once grown only for household use now reach restaurants in Makati and specialty grocers abroad.",
         "Certification and cooperative branding did more than any single buyer, turning provenance into a price farmers can negotiate.",
         "The volumes remain small, and growers are wary of demand that could push them towards the yields that endangered the grain in the first place."]),

    # ---- Issue 22: The Makers Issue (current, published) -----------------
    "makers": ("Made Here: The New Filipino Makers", "Business",
        "A generation of independent brands is proving that local production can be a selling point.",
        ["From leather goods in Marikina to ceramics in Pampanga, small makers are building brands on transparency about where and how things are made.",
         "Social commerce gave them reach; what keeps customers is consistency, which most of them learned the hard way through returns and reviews.",
         "The constraint now is not demand but capital for the second production run, the point at which most small brands either scale or stall."]),
    "sneakers": ("Inside Manila's Sneaker Restoration Scene", "Life",
        "Repair shops have become the unlikely centre of a sustainability conversation.",
        ["Restorers in Cubao and Quezon City now rebuild soles, redye suede and replace worn heel counters on pairs their owners refuse to retire.",
         "Customers describe the service as cheaper than replacement and more satisfying than buying new.",
         "Several shops have started teaching weekend workshops, which earn less than repairs but build the loyalty that repairs alone do not."]),
    "loom": ("The Weavers Setting Their Own Prices", "Innovation",
        "Digital storefronts are shifting bargaining power towards the people who make the cloth.",
        ["Weaving communities in Ilocos and Mindanao are selling directly to designers through online catalogues rather than through a chain of middlemen.",
         "Direct orders arrive with clearer specifications, which has cut the waste of weaving to a guess.",
         "The weavers are careful about scale: consistent orders matter more to them than a viral moment that cannot be repeated."]),
    "coops": ("Why Cooperatives Are Having a Moment", "Leadership",
        "An old ownership model suits a generation wary of both corporations and gig platforms.",
        ["Worker and producer cooperatives are growing among designers, drivers and farmers who want a share of the value they create.",
         "Governance is the hard part. Members who join for fairness discover that fairness requires meetings, minutes and patience.",
         "The cooperatives that last write their rules down early and revisit them often."]),

    # ---- Issue 23: The Future of Work Issue (closed, layout approved) ----
    "hybrid": ("The Office Is Now a Place You Visit", "Leadership",
        "Philippine employers are redesigning offices around collaboration rather than attendance.",
        ["Firms that once measured presence now plan office days around workshops, onboarding and client meetings.",
         "The result is fewer desks and more rooms, and a commute that employees are willing to make because it has a purpose.",
         "Managers who adapted describe their job as designing reasons to meet rather than enforcing them."]),
    "upskill": ("Upskilling After Automation", "Innovation",
        "Contact centre workers are moving into quality, analytics and training roles.",
        ["As routine queries move to self-service, the remaining calls are harder, and so is the work of handling them well.",
         "Employers that invested early in training report lower attrition and a pipeline of team leads they no longer have to hire externally.",
         "The workers who moved up say the difference was time: paid hours to learn, not evenings after a night shift."]),
    "fourday": ("A Four-Day Week in a Twenty-Four-Hour Industry", "Business",
        "A small number of firms are testing compressed schedules without dropping coverage.",
        ["Early pilots rely on staggered teams rather than a shared day off, which protects clients from noticing any difference.",
         "Retention, not productivity, is the figure that persuaded management to continue.",
         "Nobody involved claims the model generalises, but several competitors have asked to see the rosters."]),
    "freelance": ("Freelancing Grows Up", "Business",
        "Independent professionals are building agencies, contracts and pensions around remote work.",
        ["The first wave of Filipino freelancers took whatever came through the platforms. The second negotiates retainers directly.",
         "Many now form small collectives to share clients and cover each other's leave.",
         "The missing piece is social protection, which most still arrange privately and inconsistently."]),

    # ---- Issue 24: The Food Issue (closed, awaiting layout) --------------
    "cacao": ("Davao Cacao Finds Its Voice", "Business",
        "Single-origin chocolate is giving Mindanao growers a reason to ferment carefully.",
        ["Bean-to-bar makers now pay premiums for properly fermented and dried cacao, and growers are adjusting their methods to match.",
         "The difference shows in the bar and in the price, which can be several times the commodity rate.",
         "The challenge is consistency across small farms, which cooperatives are addressing with shared fermentation centres."]),
    "carinderia": ("The Carinderia Goes Digital", "Innovation",
        "Neighbourhood eateries are using delivery apps without losing their regulars.",
        ["Owners describe the apps as a second counter rather than a replacement for the first.",
         "Commission rates remain the main complaint, and several now offer their own ordering through messaging for repeat customers.",
         "The dishes that travel well have quietly become the menu's backbone."]),
    "chefs": ("Young Chefs Rewriting the Filipino Menu", "Life",
        "A new generation is cooking regional dishes without apologising for them.",
        ["Restaurants in Manila and Cebu now name provinces rather than countries on their menus.",
         "Chefs are researching recipes with grandmothers and archivists, then plating them with confidence rather than fusion.",
         "Diners are responding, and so are the farmers who supply ingredients once dismissed as rustic."]),

    # ---- Issue 25: The Travel Issue (open) --------------------------------
    "siargao": ("After the Boom: Siargao's Second Act", "Business",
        "An island shaped by surf tourism is deciding what kind of growth it wants.",
        ["Local councils are weighing building limits against investors eager to replicate the resorts of Bali.",
         "Residents who opened homestays early are now organising to keep the island's scale human.",
         "The outcome will shape how other islands plan for sudden popularity."]),
    "slowtravel": ("The Case for Slow Travel at Home", "Life",
        "Filipino travellers are choosing longer stays in fewer places.",
        ["Remote work made week-long stays possible, and travellers discovered that one town explored properly beats five glimpsed.",
         "Guesthouses report longer bookings and guests who ask about markets rather than tours.",
         "For small towns, a guest who stays a week spends where a day-tripper does not."]),

    # ---- Standalone web pieces (free, published over past months) --------
    "podcast": ("Why Filipino Podcasts Finally Found an Audience", "Tech",
        "Cheaper data and longer commutes did more for the format than any studio.",
        ["Listening grew fastest among commuters and night-shift workers, who wanted company rather than news.",
         "The most popular shows are conversational, which surprised producers and pleased advertisers once they understood the loyalty.",
         "Monetisation lags behind listening, and most hosts still fund their shows from other work."]),
    "rooftop": ("Solar's Slow Climb onto Filipino Rooftops", "Innovation",
        "Approval times, not sunlight, now decide how fast households switch.",
        ["Panel prices have fallen faster than paperwork, which has become the binding constraint on adoption.",
         "Households that persevered report payback within six years.",
         "Installers say demand is not the problem; the eleven weeks between wanting a system and switching it on are."]),
    "bookshops": ("The Bookshops That Refused to Close", "Life",
        "Independent booksellers found a model the chains could not copy.",
        ["Curation, readings and small-press publishing replaced volume as the reason to visit.",
         "Several shops now publish poetry at a loss they describe as deliberate, because it brings readers through the door.",
         "The survivors share one advantage: landlords who were also customers."]),

    # ---- Demonstration pieces ---------------------------------------------
    "maria_draft": ("The Resale Economy Comes of Age", "Business",
        "Secondhand fashion is no longer a bargain hunt; it is a business with its own rules.",
        ["Five years ago, buying secondhand in Manila meant a weekend at the ukay-ukay and a willingness to dig. Today, curated resale shops on social media sell restored designer pieces with authentication, measurements and return policies.",
         "The shift began with shoppers who wanted quality at a lower price, but it has been sustained by sellers who treat resale as retail. They photograph carefully, grade condition honestly and answer questions quickly, and they have built loyal followings as a result.",
         "Brands have noticed. Several local labels now buy back their own pieces for resale, arguing that a jacket worn by three owners is a better advertisement than one worn once and discarded.",
         "The challenge ahead is trust at scale. As more sellers enter the market, authentication and fair grading will decide which shops last, and buyers are already learning to ask for both before they pay."]),
    "teo_returned": ("Night Markets and the New Street Economy", "Life",
        "Evening markets are becoming incubators for small food and craft businesses.",
        ["Across Metro Manila, night markets have grown from weekend novelties into regular fixtures that draw families, office workers and tourists.",
         "For vendors, the appeal is low rent and a crowd that arrives ready to spend, which lets a new business test its menu before committing to a lease.",
         "Organisers now curate their line-ups, balancing food with crafts and music so that visitors stay longer and return the following week."]),
    "teo_overdue": ("The Return of the Neighbourhood Tailor", "Life",
        "Alteration shops are busy again as shoppers keep clothes longer.",
        ["Tailors in older neighbourhoods report more repair and alteration work than at any time in the past decade."]),
    "bea_review": ("Coworking Beyond the Capital", "Business",
        "Shared offices are spreading to provincial cities, following remote workers home.",
        ["Operators in Iloilo, Bacolod and Cagayan de Oro report demand from professionals who kept their Manila jobs but moved back to their home provinces.",
         "The findings, gathered over three years, suggest that the industry is changing faster than expected, with smaller spaces and community events replacing the glass towers of the capital.",
         "Local owners say their members want reliable internet, a quiet room for calls and people to have lunch with, in that order."]),
    "bea_withdrawn": ("The Mall Food Hall Reinvented", "Business",
        "Food halls are replacing department store floors across Metro Manila.",
        ["Developers are converting anchor spaces into curated food halls that draw evening crowds."]),
    "rafa_rewrite": ("Crypto and the Filipino Saver", "Tech",
        "Digital assets attracted small savers. What happened next is still unfolding.",
        ["Many people bought crypto. Some made money and some did not. It was popular for a while.",
         "There are many reasons for this. Prices went up and down. People talked about it online a lot and some of them had good results.",
         "In conclusion crypto is a big topic and it will be interesting to see what happens in the future for everyone."]),
    "rafa_column": ("Letter to a City That Never Waits", "Life",
        "A personal essay on Manila traffic, patience, and the people who wait with you.",
        ["You learn the city from the back seat of a stalled bus. You learn it in fragments: the vendor who knows the light will not change, the student reading the same page for the fourth time, the driver who hums the same song every evening at the same corner.",
         "Waiting, here, is not the absence of life. It is where most of life happens.",
         "So this is a letter to the hours we lose and somehow keep, to the strangers who share them, and to a city that never waits for anyone, and asks us, every day, to wait for it."]),
    "editor_own": ("Editor's Letter: What Makers Teach Us", "Leadership",
        "The editor introduces an issue about people who build things by hand.",
        ["Every issue begins with a question. This time it was simple: who is still making things here, and what are they learning that the rest of us have forgotten?",
         "The answers took us to workshops, cooperatives and kitchens, and to makers who measure success in repeat customers rather than followers.",
         "We hope their patience is as instructive to you as it was to us."]),
}

PASS_SUMMARY = {
    "hybrid": "A clear argument with well-chosen examples. The ending lands.",
    "bea_review": "Well structured and readable. The opening establishes the trend quickly and the closing detail is memorable.",
    "editor_own": "Warm and concise, as an editor's letter should be. Ready for sign-off.",
}
DEFAULT_PASS_SUMMARY = "Clear structure and a confident voice. Ready for an editor."


class Command(BaseCommand):
    help = "Replace content with a showcase dataset. Accounts are kept."

    def add_arguments(self, parser):
        parser.add_argument("--no-images", action="store_true",
                            help="Skip photographs and covers. Faster.")

    # ------------------------------------------------------------------

    def handle(self, *args, **opts):
        self.images = not opts["no_images"]
        self.now = timezone.now()
        self.people()
        self.clear()

        self.stdout.write("Building issues through the application's own actions…")
        self.issue_21_retired()
        self.issue_22_published()
        self.issue_23_ready_to_publish()
        self.issue_24_awaiting_layout()
        self.issue_25_open()
        self.standalone_pieces()

        self.stdout.write("Building demonstration articles…")
        self.demo_articles()
        self.notifications_and_bookmarks()

        self.report()

    # ------------------------------------------------------------------ people

    def people(self):
        def one(role):
            u = User.objects.filter(role=role, is_active=True).order_by("id").first()
            if not u:
                raise CommandError(f"No active {role} account. Run: python manage.py seed_demo --users")
            return u
        self.editor = one(User.Role.EDITOR)
        self.publisher = one(User.Role.PUBLISHER)
        self.designer = one(User.Role.GRAPHIC_DESIGNER)
        w = {u.email: u for u in User.objects.filter(role=User.Role.WRITER)}
        missing = [e for e in ("maria@boss.ph", "teo@boss.ph", "bea@boss.ph", "rafa@boss.ph") if e not in w]
        if missing:
            raise CommandError(f"Missing writer accounts {missing}. Run: python manage.py seed_demo --users")
        self.maria, self.teo, self.bea, self.rafa = (w[e] for e in
            ("maria@boss.ph", "teo@boss.ph", "bea@boss.ph", "rafa@boss.ph"))
        self.writers = [self.maria, self.teo, self.bea, self.rafa]
        self.reader = User.objects.filter(email="reader@boss.ph").first()
        self.subscriber = User.objects.filter(email="subscriber@boss.ph").first()
        if self.subscriber:
            p, _ = ReaderProfile.objects.get_or_create(user=self.subscriber)
            p.tier = ReaderProfile.Tier.SUBSCRIBER
            p.subscription_started_at = p.subscription_started_at or self.now - timedelta(days=75)
            p.save()
        if self.reader:
            p, _ = ReaderProfile.objects.get_or_create(user=self.reader)
            p.tier = ReaderProfile.Tier.FREE
            p.save()

    def clear(self):
        # Content only. Accounts, reader profiles and preferences are kept.
        Bookmark.objects.all().delete()
        Notification.objects.all().delete()
        Message.objects.all().delete()
        FixDecision.objects.all().delete()
        ArticleEvaluation.objects.all().delete()
        RevisionNote.objects.all().delete()
        ArticleVersion.objects.all().delete()
        ArticleImage.objects.all().delete()
        Article.objects.all().delete()
        MagazineDesign.objects.all().delete()
        Issue.objects.all().delete()
        self.stdout.write("  Cleared content; accounts kept.")

    # ----------------------------------------------------------------- helpers

    def days_ago(self, d, hours=0):
        return self.now - timedelta(days=d, hours=hours)

    def article(self, key, writer, status, created, issue=None, order=0,
                deadline=None, premium=None, body=None, editor="default"):
        title, category, excerpt, paras = STORIES[key]
        a = Article.objects.create(
            title=title, category=category, excerpt=excerpt,
            body=body if body is not None else html(paras),
            writer=writer,
            editor=(self.editor if status not in (S.ASSIGNED, S.DRAFTING, S.PENDING_SIGNOFF)
                    else None) if editor == "default" else editor,
            assigned_by=self.editor if writer != self.editor else None,
            brief=f"{excerpt} Speak to at least two people doing this work, and "
                  f"get one figure you can source.",
            deadline=deadline or (created + timedelta(days=12)).date(),
            status=status, issue=issue, issue_order=order,
            is_premium=bool(issue) if premium is None else premium,
        )
        Article.objects.filter(pk=a.pk).update(created_at=created)
        if self.images and status in (S.APPROVED, S.PUBLISHED):
            a.hero_image.save(f"hero-{a.pk}.jpg",
                              tiny_image(COVER_COLOURS[a.pk % len(COVER_COLOURS)]), save=True)
            a.hero_caption = "Photograph by the BOSS picture desk"
            a.save(update_fields=["hero_caption"])
        return a

    def version(self, a, number, when, body=None):
        v = ArticleVersion.objects.create(article=a, number=number, title=a.title,
                                          body=body or a.body, excerpt=a.excerpt,
                                          submitted_by=a.writer)
        ArticleVersion.objects.filter(pk=v.pk).update(created_at=when)

    def evaluate(self, a, score, when, verdict=None, summary=None, suggestions=(),
                 fixes=(), grammar=None, readability=None, override=None):
        verdict = verdict or ("PASS" if score >= 70 else "REWRITE" if score < 40 else "REVISE")
        ev = ArticleEvaluation.objects.create(
            article=a,
            grammar_score=grammar if grammar is not None else max(0, min(100, score + 3)),
            readability_score=readability if readability is not None else max(0, min(100, score - 2)),
            overall_score=score,
            recommendation="APPROVE" if verdict == "PASS" else "REJECT",
            summary=summary or PASS_SUMMARY.get(self._key(a), DEFAULT_PASS_SUMMARY),
            suggestions=list(suggestions), fixes=[dict(f) for f in fixes],
            verdict=verdict, ai_model="seed-demo", raw_response={"seeded": True},
            input_tokens=1850, output_tokens=620 if not fixes else 910,
        )
        extra = {}
        if override:
            extra = dict(is_overridden=True, override_reason=override,
                         overridden_by=self.editor, overridden_at=when + timedelta(hours=5))
        ArticleEvaluation.objects.filter(pk=ev.pk).update(created_at=when, **extra)
        return ev

    def _key(self, a):
        return next((k for k, v in STORIES.items() if v[0] == a.title), "")

    def notes(self, a, items):
        for section, kind, text, prio in items:
            RevisionNote.objects.create(article=a, editor=None, section=section,
                                        note_type=kind, instruction=text, priority=prio)

    def design(self, issue, version, status, when, notes, revision_notes=""):
        d = MagazineDesign.objects.create(
            issue=issue, version=version, designer=self.designer,
            notes_to_editor=notes, status=status, revision_notes=revision_notes,
            reviewed_by=self.editor if status != MagazineDesign.Status.PENDING_REVIEW else None,
            reviewed_at=when + timedelta(days=1) if status != MagazineDesign.Status.PENDING_REVIEW else None,
        )
        d.file.save(f"issue-{issue.number}-{version}.pdf",
                    placeholder_pdf(f"BOSS Magazine - Issue {issue.number}: {issue.title}", pages=8),
                    save=False)
        if self.images:
            d.cover_image.save(f"issue-{issue.number}-{version}-cover.jpg",
                               tiny_image(COVER_COLOURS[issue.number % len(COVER_COLOURS)], (900, 1200)),
                               save=False)
        d.save()
        MagazineDesign.objects.filter(pk=d.pk).update(created_at=when)
        return d

    def make_issue(self, number, title, created, target, minimum):
        i = Issue.objects.create(number=number, title=title, minimum_articles=minimum,
                                 target_release_date=target, status=Issue.Status.PLANNING,
                                 created_by=self.publisher)
        Issue.objects.filter(pk=i.pk).update(created_at=created)
        return i

    def close(self, issue):
        """Through the application's own close action, as the publisher."""
        from rest_framework.test import APIRequestFactory, force_authenticate
        import apps.issues.views as views
        viewset = next(v for v in vars(views).values()
                       if isinstance(v, type) and hasattr(v, "close") and hasattr(v, "publish"))
        req = APIRequestFactory().post("/", {}, format="json", HTTP_HOST="localhost")
        force_authenticate(req, user=self.publisher)
        resp = viewset.as_view({"post": "close"})(req, pk=issue.pk)
        if resp.status_code >= 300:
            raise CommandError(f"Issue #{issue.number} could not be closed: {getattr(resp, 'data', resp)}")
        issue.refresh_from_db()

    def publish(self, issue, when):
        """Through the application's own publishing service."""
        from apps.publishing.services import NotReady, publish_issue
        try:
            publish_issue(issue, self.publisher)
        except NotReady as exc:
            raise CommandError(f"Issue #{issue.number} could not be published: {exc.reasons}")
        Issue.objects.filter(pk=issue.pk).update(published_at=when)
        for n, a in enumerate(Article.objects.filter(issue=issue).order_by("issue_order")):
            Article.objects.filter(pk=a.pk).update(published_at=when + timedelta(minutes=n))
        issue.refresh_from_db()

    def approved_in_issue(self, issue, keys, months_ago_days):
        made = []
        for n, key in enumerate(keys):
            writer = self.writers[n % 4]
            created = self.days_ago(months_ago_days + 14 - n)
            a = self.article(key, writer, S.APPROVED, created, issue=issue, order=n)
            self.version(a, 1, created + timedelta(days=5))
            self.evaluate(a, 76 + (n * 5) % 17, created + timedelta(days=5))
            made.append(a)
        return made

    # ------------------------------------------------------------------ issues

    def issue_21_retired(self):
        i = self.make_issue(21, "The Heritage Issue", self.days_ago(170), (self.now - timedelta(days=140)).date(), 4)
        self.approved_in_issue(i, ["jeepney", "barong", "familycorp", "heirloom"], 150)
        self.design(i, "v1.0", MagazineDesign.Status.APPROVED, self.days_ago(145),
                    "Cover uses the jeepney mural photographed at the Sarao works.")
        self.close(i)
        self.publish(i, self.days_ago(140))
        i.status = Issue.Status.ARCHIVED              # as the retire action does
        i.save(update_fields=["status", "updated_at"])
        self.stdout.write("  #21 The Heritage Issue — published, then retired")

    def issue_22_published(self):
        i = self.make_issue(22, "The Makers Issue", self.days_ago(70), (self.now - timedelta(days=30)).date(), 4)
        arts = self.approved_in_issue(i, ["makers", "sneakers", "loom", "coops"], 50)
        # The lead story is free, so the homepage shop window is readable.
        Article.objects.filter(pk=arts[0].pk).update(is_premium=False, is_featured=True)
        # One piece was overridden: the gate returned it, the editor disagreed.
        ArticleEvaluation.objects.filter(article=arts[3]).delete()
        self.evaluate(arts[3], 66, self.days_ago(45), verdict="REVISE",
                      summary="Readable, but the conclusion is abrupt and the governance section is thin.",
                      override="The abrupt ending is deliberate: the piece closes on the members' own words. "
                               "Governance is covered in the sidebar the designer is setting.")
        self.design(i, "v1.0", MagazineDesign.Status.SUPERSEDED, self.days_ago(40),
                    "First pass at the cover and opening spreads.",
                    revision_notes="Cover line competes with the photograph. Move it to the left third.")
        self.design(i, "v1.1", MagazineDesign.Status.APPROVED, self.days_ago(36),
                    "Cover line moved to the left third as requested.")
        self.close(i)
        self.publish(i, self.days_ago(30))
        self.stdout.write("  #22 The Makers Issue — published (current issue, flipbook ready)")

    def issue_23_ready_to_publish(self):
        i = self.make_issue(23, "The Future of Work Issue", self.days_ago(40), (self.now + timedelta(days=3)).date(), 4)
        self.approved_in_issue(i, ["hybrid", "upskill", "fourday", "freelance"], 15)
        self.design(i, "v1.0", MagazineDesign.Status.APPROVED, self.days_ago(4),
                    "Opening spread uses the office floor-plan illustration.")
        self.close(i)
        self.stdout.write("  #23 The Future of Work Issue — closed, layout approved: publish it live")

    def issue_24_awaiting_layout(self):
        i = self.make_issue(24, "The Food Issue", self.days_ago(25), (self.now + timedelta(days=21)).date(), 3)
        self.approved_in_issue(i, ["cacao", "carinderia", "chefs"], 5)
        self.close(i)
        self.stdout.write("  #24 The Food Issue — closed, awaiting the designer's layout")

    def issue_25_open(self):
        i = self.make_issue(25, "The Travel Issue", self.days_ago(8), (self.now + timedelta(days=50)).date(), 5)
        self.approved_in_issue(i, ["siargao", "slowtravel"], -5)
        self.issue_25 = i
        self.stdout.write("  #25 The Travel Issue — open, 2 of 5 planned articles")

    def standalone_pieces(self):
        for n, (key, ago) in enumerate([("podcast", 120), ("rooftop", 90), ("bookshops", 60)]):
            created = self.days_ago(ago + 10)
            a = self.article(key, self.writers[n], S.APPROVED, created, premium=False)
            self.version(a, 1, created + timedelta(days=4))
            self.evaluate(a, 80 + n * 4, created + timedelta(days=4))
            from apps.publishing.services import publish_article
            publish_article(a, self.publisher)
            Article.objects.filter(pk=a.pk).update(published_at=self.days_ago(ago))
        self.stdout.write("  3 standalone web pieces, free to read")

    # ------------------------------------------------------------ demo pieces

    def demo_articles(self):
        today = date.today()

        # Maria: a new commission, and a finished draft ready to submit live.
        self.article("maria_draft", self.maria, S.ASSIGNED, self.days_ago(1),
                     deadline=today + timedelta(days=9), body="")
        Article.objects.filter(title=STORIES["maria_draft"][0]).update(
            title="Pre-loved Luxury and the Filipino Shopper")
        self.maria_draft = self.article("maria_draft", self.maria, S.DRAFTING, self.days_ago(6),
                                        deadline=today + timedelta(days=4))

        # Teo: returned in the Revise band, with quick fixes to apply.
        t_body = STORIES["teo_returned"][3]
        body = html([t_body[0], FLAWED_SENTENCE, t_body[1], t_body[2]])
        a = self.article("teo_returned", self.teo, S.REVISION_REQUESTED, self.days_ago(5),
                         body=body, deadline=today + timedelta(days=3))
        Article.objects.filter(pk=a.pk).update(returned_by_ai=True)
        self.version(a, 1, self.days_ago(1, 3))
        sugg = [("Throughout", "GRAMMAR", "Several agreement errors; the quick fixes cover the mechanical ones.", "HIGH"),
                ("Conclusion", "STRUCTURE", "End on what the markets mean for the vendors, not on the organisers.", "MEDIUM")]
        self.evaluate(a, 58, self.days_ago(1, 3), grammar=49, readability=66,
                      summary="A timely subject with good reporting, let down by grammatical slips and a weak ending.",
                      suggestions=[dict(section=s, note_type=k, instruction=t, priority=p) for s, k, t, p in sugg],
                      fixes=SEED_FIXES)
        self.notes(a, sugg)
        self.teo_returned = a

        # Teo: overdue work, so the dashboard shows the alert.
        self.article("teo_overdue", self.teo, S.DRAFTING, self.days_ago(16),
                     deadline=today - timedelta(days=3))

        # Bea: passed after applying three of four fixes, waiting for the editor.
        flawed = html([STORIES["bea_review"][3][0], FLAWED_SENTENCE, STORIES["bea_review"][3][2]])
        a = self.article("bea_review", self.bea, S.UNDER_REVIEW, self.days_ago(9))
        self.version(a, 1, self.days_ago(4), body=flawed)
        ev1 = self.evaluate(a, 61, self.days_ago(4), grammar=52, readability=70,
                            summary="Strong reporting; several grammatical errors in the second paragraph.",
                            fixes=SEED_FIXES)
        for fid, act in (("f1", "ACCEPTED"), ("f2", "ACCEPTED"), ("f4", "ACCEPTED"), ("f3", "DISMISSED")):
            FixDecision.objects.create(evaluation=ev1, fix_id=fid, action=act, decided_by=self.bea)
        self.version(a, 2, self.days_ago(3, 20))
        self.evaluate(a, 84, self.days_ago(3, 20))
        Message.objects.create(article=a, sender=self.editor,
                               body="Good piece. Can you confirm the Iloilo operator's name before I approve?")
        Message.objects.create(article=a, sender=self.bea,
                               body="Confirmed with them this morning. Spelling is correct as written.")
        self.bea_review = a

        # Bea: withdrawn, with its reason recorded.
        a = self.article("bea_withdrawn", self.bea, S.WITHDRAWN, self.days_ago(20))
        Article.objects.filter(pk=a.pk).update(
            withdrawal_reason="The developer asked to delay the announcement; we will revisit next quarter.")

        # Rafa: returned for rework, below the rewrite mark.
        a = self.article("rafa_rewrite", self.rafa, S.REVISION_REQUESTED, self.days_ago(4))
        Article.objects.filter(pk=a.pk).update(returned_by_ai=True)
        self.version(a, 1, self.days_ago(2))
        sugg = [("Introduction", "STRUCTURE", "State what the piece is about in the first two sentences.", "HIGH"),
                ("Body", "FACTUAL", "Add figures and at least two named sources.", "HIGH"),
                ("Conclusion", "STRUCTURE", "Replace the general closing with a specific takeaway.", "MEDIUM")]
        self.evaluate(a, 34, self.days_ago(2), grammar=58, readability=41, verdict="REWRITE",
                      summary="The draft has no clear argument or evidence yet. It needs rework rather than line edits.",
                      suggestions=[dict(section=s, note_type=k, instruction=t, priority=p) for s, k, t, p in sugg])
        self.notes(a, sugg)
        self.rafa_rewrite = a

        # Rafa: a deliberate stylistic column the gate returned — the override demonstration.
        a = self.article("rafa_column", self.rafa, S.REVISION_REQUESTED, self.days_ago(3))
        Article.objects.filter(pk=a.pk).update(returned_by_ai=True, editor=self.editor)
        self.version(a, 1, self.days_ago(1, 6))
        sugg = [("Throughout", "TONE", "Second-person address and fragments read as informal for the publication.", "MEDIUM")]
        self.evaluate(a, 64, self.days_ago(1, 6), grammar=71, readability=58, verdict="REVISE",
                      summary="Evocative, but the second-person voice and sentence fragments lower the readability score.",
                      suggestions=[dict(section=s, note_type=k, instruction=t, priority=p) for s, k, t, p in sugg])
        self.notes(a, sugg)
        self.rafa_column = a

        # The editor's own letter, waiting for the publisher's sign-off.
        a = self.article("editor_own", self.editor, S.PENDING_SIGNOFF, self.days_ago(2), editor=None)
        self.version(a, 1, self.days_ago(1))
        self.evaluate(a, 81, self.days_ago(1))
        Message.objects.create(article=a, sender=self.editor,
                               body="Ramon, this is the letter for the Future of Work issue. Short on purpose.")
        self.editor_own = a

    # ------------------------------------------------- notifications, bookmarks

    def notify(self, who, kind, message, link):
        if who:
            Notification.objects.create(recipient=who, kind=kind, message=message, link=link)

    def notifications_and_bookmarks(self):
        K = Notification.Kind
        md = self.maria_draft
        self.notify(self.maria, K.ASSIGNED, f'{self.editor.get_full_name()} assigned you "{md.title}".',
                    article_link(self.maria, md))
        self.notify(self.teo, K.RETURNED_BY_AI,
                    f'"{self.teo_returned.title}" scored 58 and was returned for revision. 4 quick fixes suggested.',
                    article_link(self.teo, self.teo_returned))
        self.notify(self.teo, K.DEADLINE_PASSED, '"The Return of the Neighbourhood Tailor" is past its deadline.',
                    "/writer")
        self.notify(self.rafa, K.RETURNED_BY_AI,
                    f'"{self.rafa_rewrite.title}" scored 34 and needs rework rather than line edits.',
                    article_link(self.rafa, self.rafa_rewrite))
        self.notify(self.editor, K.SUBMITTED, f'"{self.bea_review.title}" passed pre-screening and awaits review.',
                    article_link(self.editor, self.bea_review))
        self.notify(self.editor, K.MESSAGE, f'{self.bea.get_full_name()} commented on "{self.bea_review.title}".',
                    article_link(self.editor, self.bea_review))
        self.notify(self.publisher, K.SUBMITTED,
                    f'"{self.editor_own.title}" by {self.editor.get_full_name()} awaits your sign-off.', "/publisher")
        self.notify(self.designer, K.DESIGN_APPROVED, "Your layout for Issue #23 was approved.", "/designer")
        if self.subscriber:
            latest = Article.objects.filter(status=S.PUBLISHED).order_by("-published_at")
            for a in latest[:3]:
                Bookmark.objects.get_or_create(reader=self.subscriber, article=a)
        if self.reader:
            free = Article.objects.filter(status=S.PUBLISHED, is_premium=False).first()
            if free:
                Bookmark.objects.get_or_create(reader=self.reader, article=free)

    # ------------------------------------------------------------------ report

    def report(self):
        from django.db.models import Count
        w = self.stdout.write
        w(self.style.SUCCESS("\nShowcase ready.\n"))
        w("Issues (checked against the application's own readiness rules):")
        for i in Issue.objects.order_by("number"):
            r = i.blocking_reasons
            reasons = (r() if callable(r) else r) if i.status not in (Issue.Status.PUBLISHED, Issue.Status.ARCHIVED) else []
            w(f"  #{i.number} {i.title:<28} {i.status:<10} closed={'yes' if i.is_closed else 'no ':<3} "
              f"layout={'yes' if i.approved_design else 'no ':<3} "
              + (f"blocking: {'; '.join(reasons)}" if reasons else "ready" if i.status not in ("PUBLISHED", "ARCHIVED") else ""))
        w("\nArticles:")
        for row in Article.objects.values("status").annotate(n=Count("id")).order_by("status"):
            w(f"  {row['n']:>3}  {row['status'].replace('_', ' ').title()}")
        w(f"\n  {ArticleEvaluation.objects.count()} assessments, "
          f"{ArticleEvaluation.objects.filter(is_overridden=True).count()} overridden · "
          f"{MagazineDesign.objects.count()} layout versions · {Message.objects.count()} messages · "
          f"{Notification.objects.count()} notifications · {Bookmark.objects.count()} bookmarks")
        w(self.style.MIGRATE_HEADING("\nWhere each demonstration step is:"))
        w("  Maria ...... a new commission, and a finished draft to submit live")
        w("  Teo ........ returned (58) with 4 quick fixes to apply; one overdue piece")
        w("  Bea ........ passed (84) after accepting 3 AI fixes; awaiting the editor")
        w("  Rafa ....... returned for rework (34); a column scored 64 to override")
        w("  Publisher .. the editor's letter to sign off; Issue #23 ready to publish")
        w("  Designer ... Issue #24 closed and awaiting a layout")
        w("  Editor ..... Issue #25 open for scheduling (2 of 5)")
        w("  Readers .... Issue #22 live: paywall, flipbook; #21 retired to the archive")
        w(self.style.WARNING("\nAll scores are seeded (ai_model='seed-demo'), not produced by the model."))
