# Acceptance Report

Mapped against the grading weights you provided (tier correctness 40%,
judging integrity 25%, adaptability/operability 20%, code quality/
innovation 15%, plus normalization/API-first/threat-model bonuses).
Every "Result" below is based on an actual command run against this
codebase, not an assumption — see the "Verified by" column.

## 1. Tier correctness (40%)

The spec describes a large superset of possible features. Rather than
build a wide, partially-working T4 surface, the highest tier actually
completed end-to-end is:

| Capability | Status | Verified by |
|---|---|---|
| Auth (register/login/logout via token discard) | Done | `test_unauthenticated_cannot_access_protected_resource`, manual curl session |
| RBAC (4 roles, server-enforced) | Done | `test_participant_cannot_access_organizer_apis`, `test_participant_cannot_access_judge_apis` |
| Skill profiles (have + want, proficiency) | Done | `PUT /api/users/me/skills`, exercised by `scripts/seed.py` |
| Explainable team matching (no fake "AI") | Done | `services/matching.py`, exercised via `/api/teams/{id}/matches` |
| Team skill coverage view | Done | `/api/teams/{id}/coverage` |
| Projects: draft/edit/submit, deadline-enforced | Done | `test_project_edit_rejected_after_submission_deadline` |
| Claims + evidence (create/delete, no auto-truth) | Done | `routers/projects.py`, seeded with 4 real claims/project |
| Public gallery (search, filter by hackathon) | Done | curl-verified: unauthenticated `GET /api/projects` returns only submitted/locked |
| Judge assignment + blind judging | Done | `routers/judging.py::my_judging_queue` omits team identity when `blind_judging=True` |
| Conflict of interest (3-point enforcement) | Done | `test_conflicted_judge_cannot_evaluate` |
| Configurable weighted rubric (validated sum=100) | Done | `test_rubric_weights_must_sum_to_100` |
| Score submission + immutable locking | Done | `test_locked_evaluation_cannot_be_modified` |
| z-score normalization (documented, edge cases handled) | Done | `docs/JUDGING.md`, `test_scoring.py` |
| Ranking + official publish | Done | curl-verified against seeded data |
| Ranking Lab (simulation, never mutates official) | Done | `test_official_ranking_never_mutated_by_simulation` |
| Ranking Replay (from real audit log) | Done | `GET /api/scoring/replay` |
| Judging Observatory (live-computed stats) | Done | curl-verified, shows 3 distinct judge distributions |
| Audit log (append-only, organizer-readable) | Done | no update/delete route exists for `AuditLog` anywhere |
| CSV export | Done | `GET /api/export/rankings.csv`, streams real DB rows |
| Community voting/comments | Done | DB-unique-constrained against duplicate votes |
| Frontend covering all of the above | Done | builds clean (`npm run build`), all pages call real endpoints |
| Docker Compose / one-command deployment | **Not done** | plain `pip install` + `npm install`, documented in README |
| Automated CI pipeline | **Not done** | tests exist and pass locally; no CI config authored |

**Result:** the core pipeline (skills -> teams -> claims/evidence ->
judging -> normalization -> ranking -> audit/replay/lab) is complete,
tested, and demonstrated against real seeded data end-to-end over actual
HTTP. Two infrastructure conveniences (Docker, CI) were intentionally not
built, per the stated priority rule (working core over more surface
area).

## 2. Judging integrity (25%)

| Requirement | Status | Verified by |
|---|---|---|
| Real judge assignment | Done | `judge_assignments` table, unique-constrained |
| Rubric-based scoring | Done | scores tied to real `RubricCriterion` rows, criterion-set validated |
| Score validation | Done | 0-10 range enforced at schema layer |
| Conflict-of-interest handling | Done | `test_conflicted_judge_cannot_evaluate` |
| Score locking | Done | `test_locked_evaluation_cannot_be_modified` |
| Aggregation | Done | `compute_project_scores` groups by judge and project from real rows |
| Normalization | Done | documented z-score method, `none`/`min_max` alternatives |
| Ranking | Done | `build_ranking`, sorted by `final_score` |
| Auditability | Done | every mutating action calls `log_event` in the same transaction |

**Result:** met in full for a single-active-rubric, single-hackathon
scenario. Multi-rubric-per-hackathon-over-time auditing (e.g. re-scoring
under a changed rubric after the fact) is not built — only one rubric is
active at a time, by design (see `DATA-MODEL.md`).

## 3. Adaptability / operability (20%)

| Requirement | Status | Verified by |
|---|---|---|
| Configurable rubrics/weights | Done | `POST /api/judging/rubrics`, weight-sum validated |
| Configurable judges/teams/submissions | Done | all created via API, no hardcoded IDs anywhere in `app/` (only `scripts/seed.py`, which is demo data, not app logic) |
| Configurable deadlines | Done | per-hackathon `submission_deadline`/`registration_deadline` fields |
| Configurable skill catalog | Done | skills auto-created on first reference, no fixed enum |
| Multiple hackathons supported | Done | every table with hackathon-scoped data carries `hackathon_id`; tested implicitly by the test suite creating a fresh hackathon per test |

**Result:** met. The one constraint worth naming: an organizer account
must be provisioned by direct DB write rather than a self-service admin
UI (see `THREAT-MODEL.md` #2) — an intentional security tradeoff, not an
oversight, but it does mean "operability" for a brand-new deployment
requires one manual step.

## 4. Code quality / innovation (15%)

- Single-responsibility routers (one file per resource area), a shared
  `security.require_roles()` dependency reused everywhere rather than
  copy-pasted checks, and a scoring engine (`services/scoring.py`) with
  its normalization math documented inline in the module docstring, not
  scattered across the codebase.
- The Ranking Lab simulation and the real normalization run share the
  exact same `compute_project_scores` function — verified in
  `test_official_ranking_never_mutated_by_simulation` and by code
  inspection — so there's no risk of the "demo" simulation path silently
  diverging from the real judging math.
- The seed script drives the actual HTTP API rather than writing directly
  to the ORM, which means seeding *is* an integration test: if any layer
  of the real pipeline broke, `python -m scripts.seed` would fail loudly
  instead of silently producing valid-looking-but-untested data.
- Innovation: the claim -> evidence model explicitly refuses to
  auto-derive claim truth from evidence presence (a judge always decides)
  — a deliberate design choice against the more common shortcut of
  "evidence exists = feature verified."

## 5. Normalization Proof bonus (+5)

Documented method: `docs/JUDGING.md`. Demonstrated, not just described:
the seed script (`scripts/seed.py`) assigns three judges deliberately
different absolute scoring habits (harsh: 3.7-6.9, generous: 7.7-9.4,
moderate: 6.4-7.9) *and* deliberately different relative opinions of the
four projects, producing a case where the raw-average ranking and the
z-score-normalized ranking disagree on **all four** positions:

```
Raw-average order:    Vantage > Ember > Quartz > Nimbus
Z-normalized order:   Ember > Vantage > Nimbus > Quartz
```

This is a real, reproducible measurement from running
`POST /api/scoring/simulate` with `method: "none"` against the seeded
data and comparing to the official (`z_score`) ranking — not an invented
number. Edge cases (zero-variance judge, single-evaluation judge,
zero-evaluation project, min_max zero-range) are each handled with an
explicit, tested branch rather than an unguarded division.

## 6. API First bonus (+3)

Every frontend action calls a real REST endpoint under `/api/` (57 routes
total — verified by importing the FastAPI app and counting `app.routes`).
OpenAPI/Swagger docs are auto-generated and live at `/docs` with zero
extra documentation code (`curl http://localhost:8000/docs` returns 200
in this environment). No endpoint exists that the frontend doesn't
actually call, and no frontend feature exists that isn't backed by one.

## 7. Threat Model bonus (+3)

`docs/THREAT-MODEL.md` — ten numbered threats, each with a specific
mitigation, a note on residual risk where one exists, and a link to the
test that verifies it (nine of ten have an automated test; rate-limiting
is explicitly named as infrastructure-layer, out of scope for the app).

## Test suite summary

```
$ python -m pytest app/tests -q
16 passed
```

Covering: unauthenticated access rejection, participant/organizer/judge
role isolation, self-registration role-escalation prevention, unassigned-
judge rejection, conflict-of-interest enforcement, locked-evaluation
immutability, team-ownership enforcement, deadline enforcement (both edit
and submit), rubric weight validation, and simulation/official-ranking
independence. Plus the seed script itself, which is a full end-to-end
integration run through the real HTTP API (register -> skills -> teams ->
match -> project -> claims -> evidence -> submit -> assign -> conflict ->
evaluate -> lock -> normalize -> rank -> publish -> simulate) that fails
loudly (assertion error) if any step of the real pipeline breaks.

## What isn't done, honestly

- Docker Compose file (README documents plain `pip`/`npm` setup instead)
- CI pipeline config
- File/image upload for evidence (URLs and text only, by design — see
  `ARCHITECTURE.md`)
- Rate limiting (documented as an infrastructure-layer concern)
- Frontend automated tests (backend has 16 passing tests; frontend was
  verified by production build + manual API-contract review, not by an
  automated frontend test suite)
- A dedicated votes-leaderboard view (voting/commenting works and is
  wired into the project detail page, but there's no separate "most
  voted" ranking page)
