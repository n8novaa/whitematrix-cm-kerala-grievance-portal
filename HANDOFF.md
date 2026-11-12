# Handoff

## Current checkpoint

The implementation and deployment configuration are updated in the working tree and remain uncommitted. The existing `AGENTS.md` deletion and ZIP artifacts are preserved. No commit was amended and nothing was pushed.

The app supports citizen, CMO, and officer workflows, including reopened grievance cycles, current-assignment action reports, feedback per resolution, role-restricted attachment downloads, and internal/public note separation. Production configuration is provided through Docker Compose with PostgreSQL, Django/Gunicorn, Nginx/Vite, a shared database throttle cache, health check, and persistent database/media volumes.

## Verification

- Backend suite: 62 tests passed.
- Django `check`: passed.
- `makemigrations --check --dry-run`: no model changes missing migrations.
- `collectstatic --noinput`: passed; 408 assets post-processed.
- Production `check --deploy`: completed with only the HSTS include-subdomains and preload advisories. These are intentionally not forced because they require confirming every applicable subdomain uses HTTPS and opting into browser preload.
- Frontend lint and Vite production build: passed.
- `git diff --check`: passed.
- Synthetic configuration checks do not verify real hosting, database, or Gemini connectivity.

## Still required before public production use

- Install/use Docker Compose and validate/build the stack on the deployment host; Docker was unavailable in this workspace.
- Configure a domain, TLS-terminating trusted reverse proxy, DNS, firewall, persistent storage, and production PostgreSQL credentials. Back up and test restoring both volumes.
- Supply real secrets and exact host/CORS/CSRF origins using a secret manager or ignored `.env.production`.
- Test the full HTTPS deployment and attachment persistence. Provision CMO/officer accounts through a trusted administrative process.
- Supply a Gemini key and verify a live provider request if AI is required; local tests mock provider responses.
- JWT tokens are stored in per-tab sessionStorage to isolate tab sessions. Review the XSS/token-storage threat model before handling real user data.
