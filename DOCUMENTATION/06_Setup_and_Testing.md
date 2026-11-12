# Setup and testing

## Local backend

From `backend/` in PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Replace DJANGO_SECRET_KEY in .env with a unique local random value.
python manage.py migrate
python manage.py seed_departments
python manage.py runserver
```

When `DATABASE_URL` is empty, Django uses local SQLite. The example enables DEBUG for local work; Django itself defaults DEBUG to false and requires a configured secret.

## Local frontend

From `frontend/`:

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8000`. The frontend uses real API responses; no mock backend is required.

## Local test roles

Register a citizen through the UI or API. Public registration cannot create elevated roles. To create local CMO/officer accounts, use Django shell and choose private test passwords interactively:

```python
from getpass import getpass
from apps.accounts.models import User
from apps.departments.models import Department

User.objects.create_user(email="demo.cmo@example.test", password=getpass("CMO test password: "), role=User.Role.CMO)
User.objects.create_user(email="demo.officer@example.test", password=getpass("Officer test password: "), role=User.Role.OFFICER, department=Department.objects.get(code="PWD"))
```

The email addresses above are the local test usernames. The operator-selected passwords are the corresponding credentials; no shared demo password is stored in source control. Set up at least one grievance and assignment before signing in as the officer.

## Verification commands

```powershell
# backend, with DJANGO_SECRET_KEY configured
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
# frontend
npm run lint
npm run build
```

Tests use a temporary test database and mock Gemini provider calls. A live Gemini request requires a valid secret and network/provider access.

## Production deployment

Use the Compose stack and operator checklist in [the deployment runbook](08_Deployment_Readiness.md). Configure `.env.production` outside Git, run PostgreSQL migrations and create the shared throttle cache table before starting the application. Do not deploy using local demo data or development secrets.
