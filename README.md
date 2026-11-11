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
