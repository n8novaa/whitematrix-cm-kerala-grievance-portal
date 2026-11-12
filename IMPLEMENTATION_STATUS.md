# Implementation status

Last updated: 12 November 2026

## Verified

- Backend regression suite: 62 tests passed, including lifecycle, authorization, current-cycle report, attachment, AI error/throttle, registration, and health endpoint coverage.
- Django system checks and migration drift checks passed.
- Static assets collected successfully (408 post-processed).
- Frontend ESLint and production build passed.
- Deployment-shaped Django `check --deploy` completed with two HSTS advisories about subdomain coverage and browser preload; values remain opt-in pending domain policy confirmation.
- Docker Compose could not be validated or built because Docker is not installed in this workspace.

## Deployment preparation

- Production settings require a strong secret, `DEBUG=False`, exact hosts/origins, PostgreSQL, and absolute persistent media path.
- Compose defines PostgreSQL, Django/Gunicorn, and Nginx/Vite services, with persistent DB/media volumes, shared DB cache, migrations/cache-table instructions, and health endpoint.
- Backend and frontend environment examples use safe placeholders; local `.env` files are ignored. No real Gemini key or production secret is included.
- Feedback is unique per resolution cycle. Reopened cases require a fresh accepted report from the currently assigned officer.

## Remaining before public launch

- Configure provider/domain/DNS/TLS, real production secrets, PostgreSQL and persistent storage; build and run Compose on a Docker host.
- Verify backups/restores and perform hosted citizen → CMO → officer → CMO → citizen and authorized attachment workflows.
- Verify live Gemini using an operator-provided key if needed; provider tests in this workspace are mocked.
- JWT tokens are isolated per tab in sessionStorage; XSS hardening remains necessary before processing real user data.
