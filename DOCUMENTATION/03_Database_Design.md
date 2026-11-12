# Database design

The custom user model uses email as its login identifier. Django migrations are the schema source of truth. Local development defaults to SQLite; a PostgreSQL URL selects PostgreSQL.

```mermaid
erDiagram
  USER ||--o{ GRIEVANCE : submits
  DEPARTMENT ||--o{ GRIEVANCE : classifies
  GRIEVANCE ||--o{ GRIEVANCE_HISTORY : records
  USER ||--o{ GRIEVANCE_HISTORY : responsible
  GRIEVANCE ||--o{ ATTACHMENT : includes
  GRIEVANCE ||--o{ DEPARTMENT_ASSIGNMENT : assignment_history
  DEPARTMENT ||--o{ DEPARTMENT_ASSIGNMENT : handles
  USER ||--o{ DEPARTMENT_ASSIGNMENT : officer
  USER ||--o{ DEPARTMENT_ASSIGNMENT : assigned_by
  GRIEVANCE ||--o{ ACTION_TAKEN_REPORT : receives
  USER ||--o{ ACTION_TAKEN_REPORT : writes
  GRIEVANCE ||--o{ CITIZEN_FEEDBACK : receives
  USER ||--o{ CITIZEN_FEEDBACK : submits
  GRIEVANCE ||--o| AI_RECOMMENDATION : has
  DEPARTMENT ||--o{ AI_RECOMMENDATION : suggested
  USER ||--o{ AI_RECOMMENDATION : reviews
  GRIEVANCE ||--o{ GRIEVANCE_ESCALATION : escalated
  USER ||--o{ GRIEVANCE_ESCALATION : raises

  USER {
    bigint id PK
    string email UK
    string role
    bigint department_id FK
  }
  DEPARTMENT {
    bigint id PK
    string code UK
    string name
    boolean is_active
  }
  GRIEVANCE {
    bigint id PK
    string reference_number UK
    bigint citizen_id FK
    bigint department_id FK
    string district
    string category
    string priority
    string status
  }
  GRIEVANCE_HISTORY {
    bigint id PK
    bigint grievance_id FK
    bigint responsible_user_id FK
    string previous_status
    string new_status
    boolean is_internal
    datetime created_at
  }
  ATTACHMENT {
    bigint id PK
    bigint grievance_id FK
    string file
    string original_name
    string content_type
  }
  DEPARTMENT_ASSIGNMENT {
    bigint id PK
    bigint grievance_id FK
    bigint department_id FK
    bigint officer_id FK
    bigint assigned_by_id FK
    boolean is_active
  }
  ACTION_TAKEN_REPORT {
    bigint id PK
    bigint grievance_id FK
    bigint officer_id FK
    string review_status
    text report
  }
  CITIZEN_FEEDBACK {
    bigint id PK
    bigint grievance_id FK
    bigint citizen_id FK
    int resolution_cycle
    int rating
  }
  AI_RECOMMENDATION {
    bigint id PK
    bigint grievance_id FK UK
    bigint department_id FK
    string category
    string priority
    string decision
    bigint reviewed_by_id FK
  }
  GRIEVANCE_ESCALATION {
    bigint id PK
    bigint grievance_id FK
    bigint raised_by_id FK
    text reason
    datetime created_at
  }
```

`ContactEnquiry` stores public prototype contact form entries and is independent of grievances. A `DepartmentAssignment` record is retained when reassigned; only the current record has `is_active=True`. `GrievanceHistory.is_internal` separates staff-only remarks from citizen-visible status changes/updates. Feedback rating is database constrained to 1–5; a uniqueness constraint permits one feedback per grievance resolution cycle. Production uses PostgreSQL for both application data and the shared Django throttle cache table.
