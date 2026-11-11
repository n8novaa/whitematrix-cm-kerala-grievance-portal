# Project overview

People’s Desk is a fictional React/Vite and Django REST Framework prototype for submitting and processing grievances. It is a recruitment demonstration, is not an official Government of Kerala service, and must use fictional data only.

## Roles

- **Citizen:** register/sign in, submit and track grievances, upload supporting files, see public status history and updates, leave resolved-case feedback, and reopen a resolved case.
- **CMO administrator:** review the queue, move cases under review, inspect stored AI recommendations, explicitly accept or override a recommendation, assign an active department officer, publish citizen-visible updates, escalate with a recorded reason, review action reports, and resolve only after accepting an action report.
- **Department officer:** access only currently assigned cases, record internal or public progress updates, and submit action-taken reports for CMO review.

## Workflow

`SUBMITTED → UNDER_REVIEW → IN_PROGRESS → RESOLVED → REOPENED → UNDER_REVIEW or IN_PROGRESS`

The backend validates transitions and records each status change with its timestamp and responsible user. Assignment can move a new or reopened grievance directly to `IN_PROGRESS`. Officers cannot resolve cases. Resolution requires an accepted action report.

## Technology

- Frontend: React 19 and Vite, plain CSS, fetch-based API client.
- Backend: Django 6.1, Django REST Framework, SimpleJWT, PostgreSQL in deployment or SQLite for local development.
- AI: Google Gemini server-side integration; AI output is an advisory recommendation, stored separately, and requires CMO review before official category, priority, or department values change.

## Current limits

This is a prototype: queue endpoints are unpaginated, media uses local filesystem storage, and the default throttle cache is process-local. Use a persistent media mount and shared cache before multi-instance production. No hosted deployment is included in this repository checkpoint.
