# CM Kerala Grievance Portal — delivery plan

## Outcome

Deliver by **12 November 2026, 8:00 PM IST** a hosted recruitment prototype that an evaluator can use to submit, route, update, and track a fictional grievance, inspect the AI assistant, and review the source and required documentation. The app must visibly identify itself as a prototype and must not imply Government of Kerala or CMO endorsement.

## What the assignment evaluates

| Area | Marks | Minimum evidence to demonstrate |
|---|---:|---|
| Frontend and UI/UX | 10 | Responsive public portal and clear citizen, CMO, and officer screens |
| Backend/business logic | 20 | Persistent records, role checks, reference IDs, workflow rules |
| Database design | 10 | Users, departments, grievances, history, assignments, attachments, feedback, enquiries |
| API development | 15 | Auth, submit/list/track/update, departments, statistics, AI analysis |
| AI implementation | 15 | Actual model/API analysis with suggestion review and explicit safeguards/fallback disclosure |
| Workflow functionality | 15 | Citizen → CMO → department → CMO review → citizen resolution/reopen path; timestamped actor history |
| Documentation | 10 | Seven requested guides, root README, env example, architecture and ER diagrams |
| Security/testing | 5 | Role-based access, secret hygiene, validation, focused end-to-end verification |

## Current repository baseline (11 Nov 2026)

- React 19 + Vite frontend is untouched starter content (`frontend/src/App.jsx`).
- Django 6.1 backend contains empty app models/views and only the default admin URL; there are no REST endpoints, migrations, or domain implementation.
- Settings still use a committed development secret, `DEBUG=True`, empty `ALLOWED_HOSTS`, SQLite, and no installed project apps/DRF/CORS configuration.
- `DOCUMENTATION/` exists but has no files. Root README and `.env.example` are missing. `PRD.md` was empty and is now this delivery plan.
- Git reports all project files as untracked and no commits yet. Preserve this starting state; make a baseline commit before substantial changes.

## Release strategy: build one vertical slice first

Use the existing React + Django REST Framework scaffold. Keep the data model and interfaces deliberately small, use PostgreSQL in deployment (SQLite for local/demo if needed), and implement the whole workflow before secondary public pages. Avoid adding a separate service or optional infrastructure unless the current host requires it.

### P0 — Establish a runnable, reviewable app (first)

1. Save a baseline commit; record the actual local setup and available deployment target.
2. Configure Django apps, DRF, CORS, environment-driven secret/debug/hosts/database/media settings, static/media handling, and a health endpoint.
3. Add models and migrations for departments, users/roles, grievances, status history, department assignment, attachments, feedback, and contact enquiries. Seed only clearly fictional departments/demo records.
4. Create root README, `.env.example` with placeholders only, and a quick local run path.

**Exit check:** fresh local setup migrates, seeds demo data, and serves API health without committed secrets.

### P1 — Score the workflow-heavy categories (highest value)

1. Citizen registration/login/logout and role-aware permissions.
2. Submit grievance with district/category/subject/description and optional safe file upload; return a unique reference ID.
3. Citizen dashboard and public/reference lookup with current status, department, remarks, and complete ordered history.
4. CMO queue: list/filter/detail, assign department/officer, add internal remarks, escalate, inspect report, review/resolve/reopen.
5. Officer queue: assigned cases, progress/remarks, action-taken report submitted back for CMO review.
6. Record every status change with timestamp and actor; enforce allowed transitions and permissions server-side.
7. Add summary statistics from stored records (total/pending/resolved/overdue and district/department breakdown).

**Exit check:** demonstrate the entire assignment’s mandatory lifecycle using one fictional grievance and three role-appropriate demo accounts.

### P2 — Frontend mapped to marks

1. Replace Vite starter screen with a coherent responsive Kerala grievance prototype: home, clear submit/track actions, sample stats, departments, footer and prototype disclaimer.
2. Add citizen registration/login, grievance form, AI suggestion review, dashboard, tracking, updates, and resolved-only feedback.
3. Add CMO and officer screens consuming the real APIs, including workflow actions and data-backed statistics.
4. Add About, How It Works, Departments, Contact, FAQ; persist contact enquiries through backend.
5. Ensure loading, empty, validation, and API error states are present; basic keyboard/label/mobile checks.

**Exit check:** no dead primary action or starter content; evaluator can complete the main workflow in browser.

### P3 — AI, evidence, and release (finish before deadline)

1. Integrate an actual LLM API for complaint summary, category/department suggestions, and Low/Medium/High priority. Read API key from environment, validate structured output, set a safe timeout/fallback, and let citizen/CMO review suggestions. Do not let AI assign, reject, or resolve cases.
2. If the model key/availability prevents live use, label the fallback in the UI and docs; be honest that fallback is not completed model integration (the rubric says keyword-only classification does not count).
3. Add the seven required `DOCUMENTATION/` files, architecture and ER diagrams, API examples, setup/testing guide, demo credentials (test-only), and AI/tools disclosure.
4. Run focused checks: migrations, backend checks/tests, frontend lint/build, and a browser walkthrough of registration → submit → CMO assignment → officer report → CMO resolution → citizen tracking/feedback.
5. Deploy early; configure environment variables and persistent database/media; verify the public URL in a clean session; record the 3–5 minute demo; submit hosted URL and repository before 8:00 PM IST.

## Time box and cut line

Work in this order: **runnable backend + schema → end-to-end workflow/API → usable role screens → live AI → documentation → deployment verification → demo polish**. Deploy a usable workflow as soon as P1 works, then improve it. If time contracts, defer elaborate charts, optional duplicate detection, animations, and extra visual polish; do not defer a public working URL, core lifecycle, role checks, AI disclosure, required docs, or demo evidence. Keep a time buffer for hosting/database configuration and cold-start checks.

## Release acceptance checklist

- [ ] Public app is reachable over HTTPS and clearly says recruitment prototype / not official government service.
- [ ] Fictional citizen can register/login, submit a grievance, receive a reference ID, and track it.
- [ ] CMO and officer demo accounts can only perform their permitted actions; complete lifecycle and timestamped history are visible.
- [ ] AI analysis calls a real model when configured; suggestions are reviewable, and limitations/fallback are disclosed.
- [ ] Required API operations and data-backed dashboard statistics work.
- [ ] Supporting file upload/retrieval and contact enquiry persistence work, or any scoped limitation is clearly called out.
- [ ] Seven documentation files, README, `.env.example`, architecture diagram and ER diagram are present.
- [ ] No real credentials/secrets or real citizen information are in the repository/demo data.
- [ ] Build/checks and browser walkthrough pass; demo video and submission links are ready before the deadline.

## Immediate unknowns to resolve while implementing

- Which deployment host/account and public repository are available? Do not delay local implementation for this; make host-agnostic settings first and deploy as soon as a target is identifiable.
- Can the selected host persist uploaded media and PostgreSQL? If not, choose supported object storage or explicitly constrain the demo upload path.
- Is a real AI provider key available? If not, implement the integration boundary and document what cannot be live-tested; never commit a key.
