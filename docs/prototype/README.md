# NOVUS — Backend (Django / DRF)

Editorial & publishing platform for BOSS Magazine PH. This is the **Release 2
(MSYSADD) → Release 3 (MCSPROJ)** codebase — the requirements, use cases, C4
diagrams, and UI wireframes/storyboards were finalized in Release 1 (MNTSDEV).
Nothing here should contradict those artifacts; where this scaffold makes a
simplifying choice for the prototype, it's called out explicitly below.

## Stack (confirmed against the paper's Container/Component diagrams)

| Layer | Choice | Free tier used |
|---|---|---|
| Frontend | Vue 3 + Vite | Vercel |
| Backend | Django + Django REST Framework | Render (free web service) |
| Database | PostgreSQL | Neon (free tier) |
| File storage | Cloudflare R2 (S3-compatible) | Free tier, wired in Phase 2 |
| AI evaluation | Anthropic Claude API (Haiku) | Pay-as-you-go, cents per eval |
| Payments | PayMongo | Sandbox, wired in Phase 2 |
| Email | Resend | Free tier, wired in Phase 2 |
| Auth | `djangorestframework-simplejwt` | — |

## Why a custom User model on day one

UC-6.2 and the ERD both call for **one identity table** — Django's
`AUTH_USER_MODEL` can only be swapped *before* your first migration, so
`apps/accounts/models.py::User` is the first thing in this repo. Do not run
`migrate` before you've confirmed `AUTH_USER_MODEL = "accounts.User"` in
settings — swapping it later means dropping and recreating your database.

Reader/Subscriber-only attributes (billing, tier, renewal date) live in
`ReaderProfile`, a one-to-one extension — not a second identity table — per
the ERD's supertype/subtype pattern.

## App layout → Component Diagram mapping

The Django backend Component Diagram groups the system into three domains.
This maps 1:1 to the apps below:

| Component Diagram domain | Django app(s) | Status in this scaffold |
|---|---|---|
| Core Domain (Platform Settings) | `apps.platform` | stub (Phase 2, Module 4) |
| Editor & Publishing Domain | `apps.editorial`, `apps.ai_eval`, `apps.publishing` | **built** (editorial, ai_eval) / minimal (publishing) |
| Operations & Services Domain | `apps.reports`, `apps.notifications`, `apps.payments` | stub (Phase 2, Modules 3/9/10) |
| (cross-cutting) Auth Controller | `apps.accounts` | **built** |
| (cross-cutting) Content & Premium Access | `apps.content` | **built** (public reads only) |

"Stub" = the app exists with an `apps.py` so the folder/migration namespace is
reserved and won't cause churn later, but has no models yet. Build these out
module-by-module in the order given in "Build order" below.

## Deliberate MVP simplification: Article publish vs. Issue publish

The paper's UC-2.3 (Execute Live Publishing) publishes a whole **Issue**
bundle. For the first end-to-end demo we publish a single **Article**
directly (`POST /api/editorial/articles/{id}/publish/`) instead of building
Issue bundling first. This keeps the first sprint to the seven use cases
already scoped (UC-6.2, UC-1.2, UC-1.11, UC-1.5, UC-1.6, UC-2.3, UC-7.1)
without also requiring UC-1.1/UC-1.4(design)/UC-2.1/UC-2.2 to exist first.
Issue/Bundle modeling is the first thing to add in Phase 2 — see below — and
the `publish` action is intentionally isolated in `apps/publishing/services.py`
so swapping "publish an Article" for "publish an Issue" later doesn't touch
`apps.editorial`.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # fill in DATABASE_URL, ANTHROPIC_API_KEY, SECRET_KEY
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`DATABASE_URL` should point at your team's shared Neon branch, e.g.:
```
DATABASE_URL=postgresql://user:pass@ep-xxxx.neon.tech/novus?sslmode=require
```
Every teammate + Render use the **same env var name**, just different values
(local dev can point at a Neon dev branch instead of a local Postgres — no
need to install Postgres locally at all).

## Build order (matches your priority column in the test spec)

1. **Phase 1 — single flow (this scaffold)**: Login → Draft → Submit
   (auto-evaluates) → Editor Approve/Override/Request Revision → Publish →
   Public read. Covers UC-6.2, UC-1.2, UC-1.11, UC-1.5, UC-1.4, UC-1.6,
   UC-2.3 (simplified), UC-7.1.
2. **Phase 2 — High priority modules**: UC-1.1 Submit Bundle, UC-1.8 Upload
   Magazine Design (wire Cloudflare R2 here), UC-9.x Payments (wire PayMongo),
   UC-5.x User Privileges, UC-6.1/6.3 Register/Subscribe.
3. **Phase 3 — Medium/Low priority**: Reports (Module 3), Platform Settings
   (Module 4), remaining Content Interaction (Module 7/8) endpoints,
   Notifications (Module 10 addendum).

Cross-check new work against `NOVUS_Test_Case_.docx` — every endpoint you add
should make at least its `-BF` test case pass before moving to the next use
case; don't build alternate/exception flow handling until the basic flow
works end-to-end.

## Testing

```bash
pytest
```

`tests/test_editorial_flow.py` is a worked example that turns TC-1.2-BF and
TC-6.2-BF from the test spec into pytest — copy this pattern for new
use cases rather than inventing a new test style per app.
