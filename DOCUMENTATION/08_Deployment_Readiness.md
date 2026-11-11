# Deployment readiness checklist

This repository has not been deployed. Complete and verify these steps in the target environment before describing it as production-ready.

## Required environment

- `DJANGO_DEBUG=False`
- Unique, long `DJANGO_SECRET_KEY` from the hosting secret manager; never use `.env.example` placeholder.
- `DJANGO_ALLOWED_HOSTS` set to exact backend hostnames.
- `DATABASE_URL` PostgreSQL URL with TLS; percent-encode special characters in username/password. Run migrations against this database.
- `CORS_ALLOWED_ORIGINS` set to the exact HTTPS frontend origin(s), without wildcard.
- HTTPS reverse proxy; set `TRUST_PROXY_SSL_HEADER=True` only when the trusted proxy overwrites `X-Forwarded-Proto`. `SECURE_SSL_REDIRECT` defaults on outside DEBUG.
- `DJANGO_MEDIA_ROOT` on a persistent writable volume or implement an object storage backend before using ephemeral hosts. Current uploaded media uses local filesystem storage.
- `VITE_API_BASE_URL` set to the Django API origin for separate frontend hosting. Build the frontend after setting it.
- `GEMINI_API_KEY` only when live AI is desired. Missing credentials preserve grievance submission but AI analysis returns unavailable.
- A shared cache/rate-limit store before running multiple Django workers. Current default local-memory cache is per process; limits do not aggregate across instances.
- Set `API_NUM_PROXIES` to the number of trusted reverse proxies in front of Django so DRF derives throttle client IPs from the expected end of the forwarded chain.

## Release commands

```powershell
python manage.py check --deploy
python manage.py migrate --noinput
python manage.py seed_departments
python manage.py collectstatic --noinput
python manage.py test
npm ci
npm run lint
npm run build
```

Configure the platform start command for Gunicorn using `config.wsgi:application`. Confirm static assets load through WhiteNoise, verify media survives process restart, verify the frontend origin/API URL, and walk through citizen submission → CMO review/assignment → officer update/report → CMO acceptance/resolution → citizen feedback/reopen in a clean session. Provision test CMO/officer accounts securely; do not use public registration for these roles. Verify missing/valid Gemini-key behavior separately.

## Manual deployment blockers

- Hosting provider, PostgreSQL instance, HTTPS domain, persistent media volume, and shared throttle cache have not been provisioned here.
- No real Gemini key is available for provider verification.
- Deployment and hosted end-to-end checks remain to be performed by the operator.
