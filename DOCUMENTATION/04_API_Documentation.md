# API documentation

Base path: `/api/v1/`. Unless marked public, requests require `Authorization: Bearer <access-token>`. JSON endpoints use `Content-Type: application/json`; grievance creation can use multipart form data with repeated `attachments` fields. Timestamps are ISO 8601.

`GET /health/` is a deployment health endpoint. It returns 200 only when Django can reach its database and configured cache.

## Authentication

| Method and path | Access | Purpose |
|---|---|---|
| `POST /auth/register/` | Public, throttled | Creates citizen account; role is not client-selectable. |
| `POST /auth/login/` | Public, throttled | Email/password to access and refresh JWT. |
| `POST /auth/refresh/` | Public, throttled | Rotates refresh token and returns access token. |
| `POST /auth/logout/` | Authenticated | Blacklists the caller’s refresh token. |
| `GET/PATCH /auth/profile/` | Authenticated | Read/update caller profile fields. |

Registration requires `email`, `password`, `confirm_password`, `first_name`, `last_name`, and `mobile_number`. The server validates mobile number format and matching passwords; registration always creates a citizen account.

## Departments and AI

- `GET /departments/`, `GET /departments/{id}/`: active department directory (public).
- `GET /departments/{id}/officers/`: CMO-only officer list.
- `POST /ai/analyze/`: citizen-only and throttled. Body: `{ "description": "..." }`. Returns advisory department code, category, priority, summary, model name, and a short-lived signed recommendation token. AI failures return a generic 502; missing key returns 503.

## Grievances

- `POST /grievances/`: citizen create; district, category, subject, description, optional safe attachments. Optional `ai_recommendation_token` must be valid, unexpired, and bound to the exact description. Returns the generated `CMK-YYYY-{32 hex}` reference.
- `GET /grievances/`, `GET /grievances/{id}/`: owner-only citizen records.
- `GET /grievances/track/{reference}/`: public and throttled; shows status and public history only.
- `GET /grievances/{id}/attachments/{attachment_id}/`: owner, active assigned officer, or CMO only.
- `POST /grievances/{id}/reopen/`: owning citizen; `{ "remarks": "..." }`; resolved cases only.
- `POST /grievances/{id}/feedback/`: owning citizen; resolved case only; `{ "rating": 1..5, "comments": "..." }`; one per resolution cycle (cycle increments on each resolution).

## CMO operations

- `GET /grievances/cmo/queue/`: CMO-only. Optional query parameters: `status`, `department`, `district`, `category`, `priority`, `search`.
- `POST /grievances/{id}/cmo/review/`: move valid case to `UNDER_REVIEW`; optional internal `remarks`.
- `POST /grievances/{id}/assign/`: `{ "department_id": 1, "officer_id": 2, "remarks": "internal note" }`; CMO review is required first. It changes the active assignment and advances reviewed new/reopened cases to progress.
- `POST /grievances/{id}/ai-recommendation/decision/`: `{ "decision": "ACCEPTED" }` or `{ "decision": "OVERRIDDEN", "department_id": 1, "category": "Roads", "priority": "HIGH" }`.
- `POST /grievances/{id}/escalations/`, `GET /grievances/{id}/escalations/`: CMO-only; create with `{ "reason": "at least 10 characters" }`, list audit records.
- `POST /grievances/action-reports/{report_id}/review/`: `{ "decision": "ACCEPTED"|"RETURNED", "remarks": "..." }`.
- `POST /grievances/{id}/resolve/`: CMO-only; requires an accepted action report; `{ "remarks": "citizen-visible resolution note" }`.
- `GET /dashboard/cmo/statistics/`: counts by status, department, and district, plus total, pending, resolved, overdue.

## Officer operations

- `GET /grievances/officer/queue/`: only currently assigned cases.
- `POST /grievances/{id}/updates/`: assigned officer or CMO; `{ "remarks": "...", "is_public": false }`. Defaults to internal. Set `is_public: true` for citizen-visible content.
- `POST /grievances/{id}/action-reports/`: active assigned officer; `{ "report": "at least 10 characters" }`; creates a pending CMO review report.

CMO and officer serializers contain internal information according to their role. Citizen and tracking serializers omit internal notes, assignments, AI review fields, action reports and feedback belonging to other citizens. Errors use standard DRF response bodies. See tests for executable examples and authorization details.
