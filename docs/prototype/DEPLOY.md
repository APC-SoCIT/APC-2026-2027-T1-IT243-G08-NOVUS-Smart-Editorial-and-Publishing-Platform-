# Deploying to Render (free web service)

1. Push this repo to GitHub.
2. Render dashboard → New → Web Service → connect the repo.
3. **Build command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
4. **Start command**: `gunicorn config.wsgi:application`
5. Environment variables (Render → Environment tab) — same names as `.env.example`:
   - `DJANGO_SECRET_KEY` (generate a new one, don't reuse dev)
   - `DJANGO_SETTINGS_MODULE=config.settings.prod`
   - `DJANGO_ALLOWED_HOSTS=your-service.onrender.com`
   - `DATABASE_URL` — your Neon connection string (same one locally, or a
     separate Neon branch for prod — either is fine for a capstone demo)
   - `CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app`
   - `ANTHROPIC_API_KEY`, `ANTHROPIC_EVAL_MODEL`
6. First deploy only: open the Render shell and run
   `python manage.py migrate && python manage.py createsuperuser`.

Free-tier Render web services spin down after ~15 minutes idle and take a
few seconds to wake up on the next request — expected and fine for a
capstone demo, just don't schedule your defense's live demo right after a
long idle gap without a warm-up request first.
