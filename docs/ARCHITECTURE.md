# Architecture

## Overview

SkillForge is a conventional three-tier web app: a React SPA talks to a
FastAPI REST backend over JSON, which persists to a single SQLite file.
There is no queue, no cache layer, no microservices — for a single-event
hackathon platform running on one host, that complexity would cost more
than it buys. The design optimizes for correctness and auditability over
horizontal scale.

```
React (Vite, TS)  --HTTP/JSON-->  FastAPI  --SQLAlchemy ORM-->  SQLite file
     |                                |
     v                                v
 localStorage                  JWT (HS256), bcrypt password hashing
 (JWT token only)              RBAC enforced per-endpoint (server-side)
```

## Why this stack

- **FastAPI**: request/response validation comes free from Pydantic
  models, which matters a lot for a judging engine where a malformed
  score (out of range, wrong criterion set) must be rejected before it
  ever reaches the database. Auto-generated OpenAPI docs also satisfy
  the "API First" bonus requirement without extra documentation work
  that could drift from the real implementation.
- **SQLite**: the spec requires self-hosted/offline operation with no
  mandatory external services. SQLite is a single file, needs no server
  process, and is more than sufficient for a single-event hackathon's
  write volume (dozens of teams, hundreds of evaluations). SQLAlchemy is
  used as the ORM specifically so swapping to Postgres later (multi-event,
  concurrent-write scenarios) is a connection-string change, not a rewrite.
- **React + Vite + TypeScript**: TypeScript catches a class of bugs
  (wrong field names between frontend and backend contracts) that would
  otherwise only surface at runtime. Vite's dev server proxy makes local
  development match production request paths (`/api/...`) exactly.
- **JWT auth**: stateless tokens mean the backend needs no session store,
  which keeps the "no mandatory external service" property intact.

## Request flow (one representative example)

`POST /api/judging/evaluations` (a judge submitting a score):

1. **Frontend**: `JudgeEvaluate` page collects per-criterion scores via
   sliders bound to the *actual* active rubric's criteria (fetched from
   `GET /api/judging/rubrics/active`) — the UI cannot invent criteria
   that don't exist in the database.
2. **API layer**: `security.get_current_user` decodes the JWT and loads
   the real `User` row; `require_roles("judge")` rejects anyone else
   with 403 before the handler body even runs.
3. **Backend business logic** (`routers/judging.py::submit_evaluation`):
   - Confirms an assignment exists for this (judge, project) pair —
     otherwise 403.
   - Confirms no conflict-of-interest record exists for the pair —
     otherwise 403.
   - Confirms the submitted criterion IDs exactly match the hackathon's
     active rubric — otherwise 422 (prevents scoring against a stale or
     wrong rubric).
   - Confirms the evaluation isn't already locked — otherwise 403.
4. **Database**: scores are written as `EvaluationScore` rows tied to a
   real `RubricCriterion.id`; the evaluation is flagged `locked=True`
   only if the judge submitted a final (not draft) evaluation.
5. **Audit**: `log_event(...)` writes an `AuditLog` row in the *same*
   transaction, so an evaluation can never exist without a corresponding
   audit trail entry.
6. **Response**: the persisted evaluation (with its real ID and lock
   state) is returned.
7. **Frontend state update**: on success the UI shows "locked in" and
   routes back to the queue, which re-fetches from the server (no
   optimistic local-only state that could drift from the database).

Every other UI action (team join, project submit, rubric creation,
normalization run, simulation, CSV export) follows the same shape:
UI -> validated API call -> enforced backend logic -> real DB write ->
response -> UI re-fetch. `ACCEPTANCE-REPORT.md` maps this claim to
specific tests.

## Directory layout

```
backend/
  app/
    models.py        SQLAlchemy schema (see DATA-MODEL.md)
    schemas.py        Pydantic request/response contracts
    security.py        JWT + password hashing + RBAC dependency
    audit.py            log_event() helper used by every mutating endpoint
    deadlines.py        server-side deadline enforcement helpers
    services/
      matching.py        explainable skill-complementarity matching
      scoring.py          weighted scoring, normalization, ranking engine
    routers/            one module per resource area (auth, teams, projects,
                         judging, scoring, audit, export, community, users)
    tests/              pytest suite (security/RBAC + scoring edge cases)
  scripts/seed.py       drives the real API to populate demo data
frontend/
  src/
    api/client.ts        fetch wrapper (attaches JWT, parses errors)
    context/AuthContext.tsx
    components/          Layout (nav), Protected (route guard)
    pages/                one file per route area
docs/                    (this file and its siblings)
```

## Authorization model

RBAC is enforced with a single `require_roles(*roles)` FastAPI dependency
used on every mutating or role-scoped endpoint — never by hiding a
frontend button. `admin` is treated as a superset of every other role at
the dependency level. The frontend's `<Protected roles={...}>` wrapper
exists purely for UX (don't show a judge a broken organizer page); every
test in `test_security.py` calls the API directly, bypassing the frontend
entirely, to prove the backend enforces the same rule independently.

## Known limitations

- Single SQLite file means single-writer throughput; fine for one event,
  not for many concurrent large hackathons on one deployment.
- No background job runner: the "submission auto-lock at deadline" logic
  (`projects.py::lock_expired_submissions`) is invoked lazily rather than
  by a scheduled sweep — it runs whenever an organizer view that lists
  projects is loaded, and the *hard* enforcement (rejecting a submit/edit
  call after the deadline) does not depend on that sweep at all, since
  `deadlines.py` checks the actual current time against the actual
  deadline on every write, independent of whether any lock sweep has run.
- No file upload storage: evidence of type "screenshot" or "architecture
  diagram" is stored as a URL/text field, not a binary upload, keeping
  the app dependency-free (no object storage needed).
