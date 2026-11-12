# People’s Desk — Grievance Portal Prototype

This repository contains a fictional recruitment prototype for a grievance submission and follow-up workflow. It is not an official Government of Kerala service. Use only fictional data.

## Local setup

### Backend

From `backend/`, create and activate a Python virtual environment, then install dependencies:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_departments
python manage.py runserver
```

The copied `.env` file is loaded by Django. The local SQLite database is used while `DATABASE_URL` is empty. Set `DJANGO_SECRET_KEY` to a random value outside development. Set `GEMINI_API_KEY` to enable real AI suggestions; without it, the endpoint returns an explicit unavailable response and grievance submission still works.

Public registration creates citizen accounts only. See [the local role setup](DOCUMENTATION/06_Setup_and_Testing.md#local-test-roles) for secure CMO/officer account creation with operator-chosen test passwords.

## Production deployment

### Render backend + Neon PostgreSQL + Vercel frontend

1. **Create the Neon database.** In Neon Console, create a project and database. Copy the direct PostgreSQL connection string, keep the password private, and ensure the URL includes `sslmode=require` ([Neon connection guide](https://neon.com/docs/connect/connect-from-any-app)). The backend rejects external production PostgreSQL URLs that do not require TLS.
2. **Create the Vercel project** from this repository with project root `frontend`, build command `npm run build`, and output directory `dist`. Set `VITE_API_BASE_URL` to the expected Render hostname `https://whitematrix-grievance-api.onrender.com`; if Render assigns a different hostname, update this value and redeploy later. Note the exact Vercel production origin for CORS. The rewrite in `frontend/vercel.json` preserves client-side deep links.
3. **Create the Render service.** Connect this repository to Render as a Blueprint using the root `render.yaml`, or create a Python web service manually with root directory `backend` ([Render Django deployment guide](https://render.com/docs/deploy-django)). The Blueprint sets the build command (`pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py createcachetable`), Gunicorn start command, and `/health/` check. No persistent disk is configured. Set `DJANGO_ALLOWED_HOSTS` to the actual Render hostname, for example `whitematrix-grievance-api.onrender.com`, and set `DATABASE_URL` to the Neon direct URL. The exact Vercel CORS and CSRF origins must be configured before the first Render build because production settings validate them while collecting static files.
4. **Set Render environment values** (Render Dashboard → service → Environment). The required values are listed below. Use a generated Django key; never use an example placeholder. Enter the exact Vercel origin in both CORS variables.

| Render variable | Value |
|---|---|
| `DJANGO_ENV` | `production` |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | Unique output of `python -c "import secrets; print(secrets.token_urlsafe(64))"` (86 characters). |
| `DJANGO_ALLOWED_HOSTS` | Exact Render backend hostname, no scheme or path. |
| `DATABASE_URL` | Neon PostgreSQL direct connection string with `sslmode=require`. |
| `DJANGO_MEDIA_ROOT` | `/tmp/whitematrix-media` (writable, ephemeral Render filesystem). |
| `CORS_ALLOWED_ORIGINS` | Exact Vercel site origin, e.g. `https://your-project.vercel.app`. |
| `CSRF_TRUSTED_ORIGINS` | Same exact HTTPS Vercel origin. |
| `TRUST_PROXY_SSL_HEADER` | `True` (Render terminates HTTPS and forwards the original scheme). |
| `API_NUM_PROXIES` | `1` for Render's single trusted proxy. |
| `GEMINI_API_KEY` | Optional; add only in Render's secret environment settings to enable live AI. Never set it in Vercel. |
| `GEMINI_MODEL` | Optional; defaults to `gemini-3.5-flash-lite`. |

5. **Deploy and initialize the database.** After the first Render deploy is healthy, open the service Shell and run:

   ```sh
   python manage.py migrate --noinput
   python manage.py seed_departments
   python manage.py check --deploy
   ```

   The Render build command creates the shared database throttle-cache table. It requires `DATABASE_URL` to be present during the build. Confirm the health check at `https://<backend-host>/health/`.
6. **Create privileged accounts** in the Render Shell with `python manage.py shell`, then enter private, unique passwords when prompted:

   ```python
   from getpass import getpass
   from apps.accounts.models import User
   from apps.departments.models import Department

   User.objects.create_user(email="cmo@example.test", password=getpass("CMO password: "), role=User.Role.CMO)
   User.objects.create_user(email="officer@example.test", password=getpass("Officer password: "), role=User.Role.OFFICER, department=Department.objects.get(code="PWD"))
   ```

7. **Set the final Vercel API URL.** In Vercel, set `VITE_API_BASE_URL` to the actual Render backend origin (e.g. `https://whitematrix-grievance-api.onrender.com`, no trailing slash) for the Production environment. Add the same variable for Preview/Development only if those deployments should call production. `frontend/vercel.json` handles client-side route fallback using Vercel's [rewrite configuration](https://vercel.com/docs/project-configuration/vercel-json). Redeploy after changing this variable because Vite embeds it at build time.
8. **Confirm CORS/CSRF configuration.** Ensure the exact deployed Vercel origin (scheme and host only, no trailing path) is set in both Render variables `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS`, then redeploy Render. If using a Vercel custom domain, add that origin too.
9. **Smoke-test the deployment:** register/sign in, submit and track a grievance, upload and download an attachment, run AI analysis with a real Gemini key, and walk the complete citizen → CMO review/assignment → officer report → CMO acceptance/resolution → citizen feedback/reopen lifecycle. Use fictional data only.

**Render media is ephemeral.** The configured filesystem path is writable for this temporary assessment deployment, but attachments can disappear after a restart or redeploy. Do not use this storage mode for production records; configure durable object storage or a suitable persistent disk before real use. The database remains in Neon. Render/Vercel hosting and a live Gemini request have not been configured or verified here.

### Docker Compose option

The existing Compose setup remains available for local/self-managed deployment; see [the deployment runbook](DOCUMENTATION/08_Deployment_Readiness.md). The root `.env.production.example` is for that Compose topology and is not the Render environment template.

### Frontend

From `frontend/`:

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000` during local development. For separate frontend/backend hosting, set `VITE_API_BASE_URL` to the Django API origin and configure Django CORS to allow the deployed frontend origin.

## Main API areas

- `/api/v1/auth/` — registration, JWT login, refresh, logout, and profile
- `/api/v1/departments/` — public department directory and CMO officer lookup
- `/api/v1/grievances/` — citizen cases, public tracking, CMO queue/assignment, officer updates/reports, feedback, attachments, and enquiries
- `/api/v1/ai/analyze/` — advisory AI analysis; it never routes or resolves a grievance
- `/api/v1/dashboard/cmo/statistics/` — CMO case counts

## Documentation

The [documentation index](DOCUMENTATION/01_Project_Overview.md) links to project overview, architecture, database/ER diagram, API reference, AI integration, setup/testing, and role guides. [Deployment readiness](DOCUMENTATION/08_Deployment_Readiness.md) lists configuration and manual checks still needed; this repository has not been deployed.

See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for the current phase checkpoint and [HANDOFF.md](HANDOFF.md) for repository history and demo verification.
