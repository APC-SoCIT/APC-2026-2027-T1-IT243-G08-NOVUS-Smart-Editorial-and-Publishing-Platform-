# NOVUS

Smart Editorial and Publishing Platform for **BOSS Magazine PH**.

Capstone project, Asia Pacific College, AY 2026–2027.
Rei Khalil S. Galido · Roman Rico B. Albania · Joshmar L. Clavero · Joshua Concepcion
Co-author: Carl Dominique Bueno

---

## What it does

NOVUS replaces a magazine's editorial workflow — currently spread across
Messenger, Viber and Gmail — with a single pipeline, and adds an automated
pre-screening step so editors review work that is already worth reading.

The system carries two brands. **NOVUS** is the internal workspace used by
writers, editors, publishers, designers and administrators. **BOSS Magazine
PH** is the public face: the reader portal, the issue archive, and the
subscriber edition.

### The pipeline

```
Editor assigns a topic, angle and deadline
        ↓
Writer drafts it  (rich text, hero image, inline photography)
        ↓
Writer submits  →  automated evaluation scores grammar and readability
        ↓
   ≥ 70  ────────────────→  Editor's review queue
   < 70  ──→ returned to the writer with the AI's notes attached
        ↓
Editor reviews: request revisions · override the verdict · approve
        ↓
Editor assigns the article to an issue
        ↓
Designer uploads a layout  →  Editor approves it
        ↓
Publisher releases the issue, or publishes a standalone article
        ↓
Readers read it
```

An article an editor writes themselves goes to the **publisher** for sign-off,
never back to the editor who wrote it. Nobody approves their own copy.

---

## Stack

| Layer | Choice |
|---|---|
| Frontend | Vue 3 · Vite · Pinia · Vue Router · TipTap · GSAP · ApexCharts |
| Backend | Django 5.2 · Django REST Framework · SimpleJWT |
| Database | PostgreSQL (Neon) |
| Evaluation | Anthropic Claude |
| Hosting | Render (API) · Vercel (frontend) |

---

## Running it locally

The backend lives in `docs/prototype`, the frontend in `frontend`.
Two terminals, one for each.

**Backend**

```bash
cd docs/prototype
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then fill it in — see below
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Open port **5173**. Django's administration interface is on port **8000** at
`/admin/`.

### `.env`

```
DJANGO_SECRET_KEY=<50+ characters; generate with the command below>
DJANGO_DEBUG=True
DATABASE_URL=postgresql://user:pass@host.neon.tech/db?sslmode=require
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_EVAL_MODEL=claude-haiku-4-5-20251001
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

`DATABASE_URL` may point at a local SQLite file for quick work —
`sqlite:///db.sqlite3` — but keep a Neon branch for anything shared.

### Demo data

```bash
python manage.py seed_demo --fresh
```

Creates a realistic spread of articles across every pipeline stage. **The
evaluation scores it writes are illustrative, not AI output** — the reports
label them as such, and you should too.

| Role | Email | Password |
|---|---|---|
| Writer | `writer@boss.ph` | `writer1234` |
| Editor | `editor@boss.ph` | `editor1234` |
| Publisher | `publisher@boss.ph` | `publish1234` |
| Designer | `designer@boss.ph` | `design1234` |
| Admin | `admin@boss.ph` | `admin1234` |

Staff sign in at `/staff/login` — deliberately unlinked from the public site.
The reader portal is at `/read` and needs no account.

### Tests

```bash
python -m pytest
```

---

## Environment quirks

These cost real time to find. Read them before debugging anything that looks
impossible.

**Python 3.14 breaks several pinned packages.** `psycopg` 3.2.3 has no wheel
for it; `Django` below 5.2 crashes in the admin. The pins in
`requirements.txt` are deliberately loose (`Django>=5.2,<6.0`,
`psycopg[binary]>=3.2.4`) for this reason. **Do not pin Django to 6.x** — it
removes `cc_delim_re`, which DRF 3.15 imports.

**`DATABASES` is written out longhand** in `config/settings/base.py` rather
than parsed from a URL. Both `django-environ`'s `env.db()` and
`dj_database_url.config()` silently returned empty dicts on Python 3.14,
producing a dummy backend and a baffling `ImproperlyConfigured: supply the
ENGINE value`. Do not "tidy" it back into a URL parser.

**Settings live at `config.settings.dev` and `config.settings.prod`**, not
`config.settings`. `manage.py` defaults to dev.

**Tests reuse the database.** `pytest.ini` sets `--reuse-db` because an
orphaned `test_neondb` on Neon otherwise makes pytest exit with
`SystemExit: 2`.

**Media URLs are returned relative** (`/media/…`) by a custom
`RelativeImageField`. DRF's default absolute URLs point at `localhost:8000`,
which the browser refuses as mixed content behind a Codespaces HTTPS origin.
The frontend prefixes them from `VITE_MEDIA_BASE` in production.

**The Vite proxy covers `/api` and `/media`.** Anything else served by Django
needs adding to `vite.config.js`.

---

## Deployment

### Render — the API

- **Root Directory**: `docs/prototype` (easy to miss; nothing works without it)cd ../docs/prototype && source .venv/bin/activate
grep -n -A6 "evaluation.save()" apps/editorial/views.py | head -12
- **Build Command**: `./build.sh`
- **Start Command**: `gunicorn config.wsgi:application`

| Variable | Value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
| `DJANGO_SECRET_KEY` | a fresh one, not the development key |
| `DATABASE_URL` | the Neon connection string |
| `ANTHROPIC_API_KEY` | |
| `PYTHON_VERSION` | `3.12.7` |
| `CORS_ALLOWED_ORIGINS` | the Vercel production URL |

Python is pinned to 3.12 in production to avoid the packaging failures
described above.

### Vercel — the frontend

- **Root Directory**: `frontend`

| Variable | Value |
|---|---|
| `VITE_API_BASE` | `https://<render-service>.onrender.com/api` |
| `VITE_MEDIA_BASE` | `https://<render-service>.onrender.com` |

Both are **Config**, not Secret — `VITE_` variables are compiled into the
browser bundle by design, so never put a real secret behind that prefix.

`vercel.json` rewrites every path to `index.html` so client-side routes
survive a hard refresh.

### Known limitations in production

**Render's free tier has an ephemeral disk.** Uploaded images and magazine
layouts are erased on every deploy. Cloudflare R2 is specified in the system
architecture for this reason and is scoped for Phase 2.

**Render's free tier sleeps after ~15 minutes idle.** The first request then
takes around 50 seconds. Warm it before a live demonstration.

---

## Repository layout

```
docs/prototype/          Django backend
  apps/
    accounts/            users, roles, reader profiles
    editorial/           articles, revisions, versions, images
    ai_eval/             the pre-screening gate
    issues/              issues and readiness
    design/              magazine layouts
    publishing/          publication services
    content/             public reader API
    notifications/       in-app notifications
    messaging/           article discussion
    reports/             aggregation endpoints
    platform/            settings and maintenance mode
    common/              shared models, permissions, seeding
  config/settings/       base · dev · prod

frontend/                Vue 3 application
  src/
    views/               pages
    components/          shared components
      ui/                design-system primitives
    stores/              Pinia state
    styles/tokens.css    design tokens for both brands
    content/legal.js     privacy, terms, cookies, refunds

docs/                    academic deliverables
```

---

## Scope

Built: the editorial pipeline end to end, issue publication, the paywall and
subscriber edition, reports, notifications, messaging, user administration,
and platform settings.

**Scoped for Phase 2**: payment processing (Module 9), Cloudflare R2 storage,
transactional email, and scheduled publication. Subscription entitlement is
enforced throughout; only the payment that grants it is absent, and an
administrator grants tiers manually in the meantime.

---

## Legal

The privacy policy, terms of service, cookie policy and refund policy in
`frontend/src/content/legal.js` were drafted against the Data Privacy Act of
2012 (RA 10173) and the Consumer Act (RA 7394). **They have not been reviewed
by counsel.** Before the platform processes real reader data or takes real
payment, BOSS Media Philippines Inc. should obtain professional review and
establish whether registration with the National Privacy Commission is
required.