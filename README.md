# People’s Desk

**A grievance workflow prototype for the WhiteMatrix AI Full Stack Engineer machine test.** This fictional assessment project is not an official Government of Kerala or Chief Minister’s Office service. Use fictional data only.

## What it does

Citizens submit and track cases; CMO administrators review and route them; department officers investigate and report action; the CMO reviews the report and records an outcome. Status and assignment history are persisted. AI is advisory and cannot make an official decision.

## Technology

| Layer | Technology |
|---|---|
| Frontend | React + Vite, plain CSS |
| API | Django + Django REST Framework, Gunicorn in deployment |
| Authentication | SimpleJWT access and rotating refresh tokens; browser tokens are stored per tab in `sessionStorage` |
| Database | SQLite for local development; PostgreSQL on Neon for the assessment deployment |
| Hosting | Vercel frontend; Render backend |
| AI | Google Gemini server-side through the Google Gen AI SDK |
| Static/media | WhiteNoise serves collected static files; Django stores uploaded files on local filesystem |

## Workflow

`Citizen → CMO review → department/officer assignment → officer updates and action report → CMO review → resolution or citizen reopening`

Officers access active assignments for their department. Resolution requires an accepted report from the currently assigned officer. See [overview](DOCUMENTATION/01_Project_Overview.md) and [user guide](DOCUMENTATION/07_User_Guide.md).

## Hosted application

No verified hosted application URL is recorded in this repository. Do not treat example hostnames as live services. Deployment instructions describe the intended Render + Neon + Vercel configuration; operators must verify the resulting URLs and full workflow.

## Start locally

1. Follow [local setup and tests](DOCUMENTATION/06_Setup_and_Testing.md).
2. Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env.local`; set a local secret key.
3. Migrate and seed departments, then run Django on port 8000 and Vite on port 5173 in separate terminals.

Public registration creates citizen accounts only. For local development, create CMO/officer users using the interactive instructions in the setup guide.

## Evaluator demo accounts

Use these accounts to exercise the staff workflows in the evaluation environment:

| Role | Email | Password |
|---|---|---|
| CMO administrator | `cmo1@gmail.com` | `Django@123` |
| Department officer | `officerpwd@gmail.com` | `Django@123` |
| Health and Family Welfare officer | `officerhealth@gmail.com` | `Django@123` |
| Local Self Government officer | `officerlsgd@gmail.com` | `Django@123` |
| Water Resources officer | `officerwater@gmail.com` | `Django@123` |
| General Education officer | `officereducation@gmail.com` | `Django@123` |
| Electricity Board officer | `officerkseb@gmail.com` | `Django@123` |

Citizens should register through the application with their own test details. These shared credentials are for evaluator testing only; do not reuse them for real accounts or production administration.

The five non-PWD officer accounts can be created after `seed_departments` by running `python manage.py seed_demo_officers` with `DEMO_OFFICER_PASSWORD` set to the listed test password. The command skips already-correct accounts, refuses conflicting department assignments, and leaves the existing PWD account unchanged. Do not run this demo-account seeder on a production system that contains real users.

## Documentation

- [Project overview](DOCUMENTATION/01_Project_Overview.md)
- [System architecture](DOCUMENTATION/02_System_Architecture.md) · [architecture diagram](DOCUMENTATION/diagrams/system_architecture.png)
- [Database design](DOCUMENTATION/03_Database_Design.md) · [ER diagram](DOCUMENTATION/diagrams/database_er_diagram.png)
- [API reference](DOCUMENTATION/04_API_Documentation.md)
- [AI integration](DOCUMENTATION/05_AI_Integration.md)
- [Setup, testing, and deployment](DOCUMENTATION/06_Setup_and_Testing.md)
- [User guide](DOCUMENTATION/07_User_Guide.md)

## Configuration safety

Examples use placeholders only. Keep real Django secrets, Neon URLs/passwords, and Gemini keys in ignored local environment files or the hosting provider’s secret settings. Never put `GEMINI_API_KEY` in Vercel. The root `.env.example` is for Docker Compose only; use the backend and frontend examples for local setup.
