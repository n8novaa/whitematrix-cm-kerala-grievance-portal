# Codex Project Instructions

## Project

CM Kerala - Public Grievance Redressal Portal.

Read PRD.md before implementing any feature.

## Technology Stack

Frontend:

- React
- Vite
- JavaScript
- React Router
- Axios
- Recharts
- Lucide React
- Plain CSS

Backend:

- Django
- Django REST Framework
- Simple JWT

Database:

- PostgreSQL

AI:

- Google Gemini API

## Architecture

- Keep frontend and backend separate.
- Backend owns all business logic.
- Frontend communicates through REST APIs.
- API prefix: /api/v1/
- Follow the existing folder structure.
- Use modular and reusable code.

## Backend Rules

- Use Django ORM.
- Use serializers for validation.
- Use service functions for complex operations.
- Implement role-based permissions.
- Implement object-level permissions.
- Never trust frontend role information.
- Record every grievance status transition.
- Record department assignments.
- Use database transactions for workflow changes.
- Citizens access their own grievances only.
- Officers access their department's grievances only.
- Only CMO can resolve grievances.
- Never expose internal remarks to citizens.

## Frontend Rules

- Use reusable React components.
- Use React Router.
- Use Axios for API requests.
- Keep API calls in the services directory.
- Keep components separate from pages.
- Use plain CSS.
- Ensure responsive layouts.
- Implement loading and error states.

## Security

- Never hardcode credentials.
- Read secrets from environment variables.
- Never commit .env files.
- Validate uploaded files.
- Protect administrative endpoints.
- Never expose API keys to frontend.

## Development Rules

1. Inspect existing code before making changes.
2. Do not rewrite working code unnecessarily.
3. Do not introduce unnecessary dependencies.
4. Implement one milestone at a time.
5. Maintain consistent API contracts.
6. Run relevant checks after changes.
7. Report failures honestly.
8. Do not fabricate completed functionality.
9. Preserve existing Git history.
10. Prioritize working functionality over visual polish.

## Product Rules

- Support CITIZEN, CMO and OFFICER.
- Public registration creates CITIZEN accounts only.
- AI recommendations require human review.
- AI cannot independently resolve grievances.
- Use fictional demonstration data.
- Display recruitment prototype disclaimer.
