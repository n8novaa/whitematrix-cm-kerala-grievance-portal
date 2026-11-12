# Project overview

## The assignment

The WhiteMatrix machine-test brief asks for a prototype that lets citizens submit and track grievances, lets a CMO administrator route cases, and lets department officers report action. It also specifies public pages, statistics, attachments, AI suggestions, role-based access, documentation, and an end-to-end demo. The assignment PDF was supplied separately and is not stored in this repository.

People’s Desk is a fictional recruitment demonstration built for this scenario. It is not an official Government of Kerala or Chief Minister’s Office service. Use fictional data only.

## Objectives and scope

- Give citizens a clear way to register, submit a case, receive a reference, track public progress, and provide post-resolution feedback or reopen a case.
- Give CMO administrators a central queue to review, route, monitor, and record decisions.
- Give department officers a department-scoped work queue and a way to report investigation results to the CMO.
- Demonstrate API-backed public information pages, department directory, contact enquiries, statistics, attachments, and advisory AI.

The implementation includes Home, About, How It Works, Departments, Contact, FAQ, citizen, CMO, and officer screens. Statistics and department content are sample/application-backed as implemented; the app must still be presented as an assessment prototype rather than an official service.

## What the prototype supports

### Citizen

- Register and sign in; public registration creates citizen accounts only.
- Submit a grievance with district, category, subject, description, optional attachments, and an optional advisory AI recommendation.
- Receive a generated reference, inspect own grievances and public updates, and track a case by reference.
- Leave feedback after resolution and reopen a resolved case.

### CMO administrator

- Review and filter the grievance queue; inspect attachments and statistics.
- Accept or override a stored AI suggestion, assign a department and selected officer, add internal remarks, publish public updates, and record escalations.
- Review/return action reports and resolve only when the current assigned officer’s latest report has been accepted.

### Department officer

- View active assignments for the officer’s department, inspect details and attachments, add internal or citizen-visible progress, and submit an action report for CMO review.
- Officers cannot resolve cases or access grievances assigned to another department.

## Lifecycle

`SUBMITTED → UNDER_REVIEW → IN_PROGRESS → RESOLVED → REOPENED → UNDER_REVIEW → IN_PROGRESS → RESOLVED`

The CMO starts review before assignment. Assignment advances a reviewed case to progress. Every status transition records an actor and time. Reopening requires a new report cycle; old accepted reports do not qualify for a later resolution.

## Technology

React + Vite frontend; Django + DRF backend; SimpleJWT authentication; PostgreSQL in deployment (Neon for the assessment topology), SQLite locally; Gemini backend integration; filesystem attachment storage. The assessment deployment target is Vercel for the frontend and Render for the API. Docker Compose is a separate self-hosted option.

## Limits and verification

Render’s temporary filesystem can lose attachments after restart/redeploy, and free web services can sleep when idle. Queue endpoints are currently unpaginated. Hosted deployment, real Neon connectivity, persistent production media, and live Gemini behavior must be verified by the operator; this repository does not claim those live checks.
