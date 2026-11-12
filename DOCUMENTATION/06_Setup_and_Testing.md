# Setup, testing, and deployment

## Local development

### Backend (PowerShell)

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Set a unique local DJANGO_SECRET_KEY. GEMINI_API_KEY is optional.
python manage.py migrate
python manage.py seed_departments
python manage.py runserver
```

An empty `DATABASE_URL` selects local SQLite. In another terminal:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. For a separately hosted API, set `VITE_API_BASE_URL` to the API origin. Never put `GEMINI_API_KEY` in frontend config.

## Environment variables

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Required; production needs unique random 50+ characters. |
| `DJANGO_ENV`, `DJANGO_DEBUG` | Environment and debug mode; production requires `production` and false. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames without scheme/path. |
| `DATABASE_URL` | Blank for local SQLite; PostgreSQL URL in production. External production DB requires TLS. |
| `DJANGO_MEDIA_ROOT` | Writable media directory; must be absolute in production. |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | Exact HTTPS origins in production. |
| `TRUST_PROXY_SSL_HEADER`, `API_NUM_PROXIES` | Trusted proxy configuration. |
| `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS` | Token lifetimes; defaults 15 minutes and 1 day. |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Optional server-only Gemini settings. |
| `VITE_API_BASE_URL` | Frontend API origin; local examples use localhost:8000. |

Use `backend/.env.example` locally, Render environment settings when hosted, `frontend/.env.example` for Vite, and root `.env.example` only for Docker Compose. Examples are placeholders, never credentials.

## Staff test accounts

Public registration creates citizens only. After seeding departments, create staff accounts locally with operator-chosen passwords in `python manage.py shell`:

```python
from getpass import getpass
from apps.accounts.models import User
from apps.departments.models import Department
User.objects.create_user(email="cmo@example.test", password=getpass("CMO password: "), role=User.Role.CMO)
User.objects.create_user(email="officer@example.test", password=getpass("Officer password: "), role=User.Role.OFFICER, department=Department.objects.get(code="PWD"))
```

The usernames above are examples, not pre-created accounts. The README contains separate evaluator demo-account details supplied for this assessment; those shared accounts must remain isolated from real users and production administration.

To create the five non-PWD evaluator officers in a local or assessment database, run the command after `seed_departments` with `DEMO_OFFICER_PASSWORD` set to the evaluator password. In PowerShell:

```powershell
$env:DEMO_OFFICER_PASSWORD = 'Django@123'
python manage.py seed_demo_officers
Remove-Item Env:DEMO_OFFICER_PASSWORD
```

The command creates `officerhealth@gmail.com` (Health and Family Welfare), `officerlsgd@gmail.com` (Local Self Government), `officerwater@gmail.com` (Water Resources), `officereducation@gmail.com` (General Education), and `officerkseb@gmail.com` (Electricity Board). All use the evaluator password listed in the README. It excludes and does not modify PWD. It is idempotent and stops on a conflicting officer/account rather than creating duplicates. Do not run this demo seeder against production accounts or data.

## Checks

From `backend/`: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py test`. From `frontend/`: `npm run lint`, `npm run build`. Provider/hosted behavior is not established by mocked tests.

## Render + Neon + Vercel deployment

1. Create Neon PostgreSQL and use its TLS-enabled connection URL (`sslmode=require`).
2. Deploy with root `render.yaml`. Configure secret `DJANGO_SECRET_KEY`, exact `DJANGO_ALLOWED_HOSTS`, Neon `DATABASE_URL`, exact Vercel origins for both CORS and CSRF, and optional backend-only `GEMINI_API_KEY`. Blueprint configures production mode, `/tmp/whitematrix-media`, proxy awareness, cache table creation, Gunicorn, and `/health/`.
3. After first deployment, Render Shell: `python manage.py migrate --noinput`, `python manage.py seed_departments`, `python manage.py check --deploy`.
4. Deploy `frontend/` on Vercel with `npm run build`, output `dist`, and `VITE_API_BASE_URL=https://<actual-render-host>` (no trailing slash). Add the Vercel origin to both backend CORS/CSRF variables.
5. Provision CMO/officer accounts privately. Smoke-test registration, login, case submission/tracking, uploads, assignment, report review, resolution, feedback/reopen, and Gemini only when a real key is configured.

Render free web services may sleep while idle. Render local media is ephemeral; attachments can disappear after restart/redeploy. This configuration is temporary assessment storage, not durable production media. No live hosting or Gemini verification is claimed.

## Optional Docker Compose

Compose is a separate self-hosted setup with PostgreSQL and named database/media volumes. Copy root `.env.example` to ignored `.env.production`, replace placeholders, then run the exact commands below. Back up and test restoring both volumes. Compose has not been live-host validated here.

```powershell
docker compose --env-file .env.production config
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d database
docker compose --env-file .env.production run --rm api python manage.py migrate --noinput
docker compose --env-file .env.production run --rm api python manage.py createcachetable
docker compose --env-file .env.production run --rm api python manage.py seed_departments
docker compose --env-file .env.production up -d
```
