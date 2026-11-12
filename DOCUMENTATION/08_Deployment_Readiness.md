# Deployment runbook

The repository includes a Docker Compose deployment with separate PostgreSQL, Django/Gunicorn API, and Nginx/Vite frontend services. This configuration is prepared for operator setup; it has not been deployed or validated with a real hosting provider.

## Configure environment

Copy `.env.production.example` to `.env.production` (never commit it), then set:

| Variable | Required value |
|---|---|
| `DJANGO_ENV` | `production` |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | Unique random value of at least 50 characters; generate with `python -c "import secrets; print(secrets.token_urlsafe(64))"` and store in a secret manager for hosted use. |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated exact public hostname(s) sent to the backend, without scheme or path. |
| `DATABASE_URL` | PostgreSQL URL; for this Compose file use service hostname `database`, the same database/user/password as `POSTGRES_*`, and `sslmode=disable` only on the private Compose network. For external PostgreSQL, require TLS with `sslmode=require` or stronger. URL-encode special characters in credentials. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Database initialization values; use a unique strong password and keep aligned with `DATABASE_URL`. |
| `DJANGO_MEDIA_ROOT` | `/app/media` in Compose; the named `grievance_media` volume persists uploaded files. |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | Exact frontend HTTPS origin(s), for example `https://portal.example.com`. |
| `TRUST_PROXY_SSL_HEADER` | `True` only behind the configured trusted TLS proxy, which must overwrite `X-Forwarded-Proto`. |
| `API_NUM_PROXIES` | Number of trusted proxies that append forwarded addresses; Compose defaults to 2 (external TLS proxy and internal Nginx). Adjust to actual topology. |
| `VITE_API_BASE_URL` | Leave empty for this same-origin Nginx `/api` proxy. If hosting the frontend separately, set the public API origin and rebuild; also configure exact CORS/CSRF origins. |
| `GEMINI_API_KEY` | Optional; keep server-side only. Set a valid provider key to enable live analysis; no key means graceful AI unavailability while grievance submission remains usable. |
| `GEMINI_MODEL` | Supported model identifier configured for the provider account. |
| `FRONTEND_PORT` | Optional host port, default `8080`; restrict direct access to the TLS reverse proxy. |

Examples in `.env.production.example` are placeholders, not credentials. Do not configure production secrets through the frontend build environment.

## Build and start (Docker Compose)

Install Docker Engine/Compose on the deployment host, place the environment file in the repository root, and configure a public DNS name plus TLS-terminating reverse proxy. The proxy should forward HTTPS traffic to the Compose frontend port and replace the forwarded protocol header. Restrict the frontend port to that proxy; do not expose PostgreSQL or the API directly.

```powershell
Copy-Item .env.production.example .env.production
# Edit .env.production and supply real deployment values using a secure editor/secret manager.
docker compose --env-file .env.production config
docker compose --env-file .env.production build
docker compose --env-file .env.production up -d database
docker compose --env-file .env.production run --rm api python manage.py migrate --noinput
docker compose --env-file .env.production run --rm api python manage.py createcachetable
docker compose --env-file .env.production run --rm api python manage.py seed_departments
docker compose --env-file .env.production up -d
docker compose --env-file .env.production ps
```

The API image runs `collectstatic` before starting Gunicorn; Nginx proxies `/static/` and `/admin/` to Django/WhiteNoise. Database records and uploaded files persist in named volumes `postgres_data` and `grievance_media`; back up both volumes and test restoring them. For a platform without persistent local volumes, configure durable object storage for uploads before accepting real users. Database cache provides shared throttling for all API workers and is created by the `createcachetable` step.

## Verify release

```powershell
docker compose --env-file .env.production exec api python manage.py check --deploy
docker compose --env-file .env.production exec api python manage.py showmigrations
Invoke-WebRequest http://localhost:8080/health/
```

Before public launch, exercise registration, citizen submission/tracking, authorized attachment upload/download, CMO review and assignment, officer updates/report, CMO return/accept/resolution, and citizen feedback/reopen on the HTTPS site. Provision CMO/officer users through a trusted administrator; public registration creates citizens only. Confirm media and database restoration and separately test real Gemini success and failure using the configured key.

## Current verification limits

- No Docker executable, hosting account, public domain, TLS proxy, PostgreSQL host, persistent volume, or production Gemini credential was available in this workspace. Compose images and hosted flows therefore remain unverified here.
- JWT tokens are stored in browser localStorage. Review and harden the browser token storage threat model before exposing real user data publicly.
- Live Gemini integration cannot be claimed successful until a provider request succeeds with the operator's credential.
