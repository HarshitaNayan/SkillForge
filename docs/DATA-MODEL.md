# Data Model

All tables live in one SQLite database (`backend/skillforge.db`), defined
in `backend/app/models.py`. IDs are UUID strings. Timestamps are UTC.

## Entity relationship summary

```
User ──< UserSkill >── Skill
User ──< TeamMember >── Team ──< TeamSkillRequirement >── Skill
Team ──< Project ──< ProjectClaim ──< ClaimEvidence
Hackathon ──< Team, Project, Rubric, JudgeAssignment, JudgeConflict,
              Evaluation, NormalizedScore, Ranking, RankingSimulation,
              AuditLog
Rubric ──< RubricCriterion
JudgeAssignment ──1:1── Evaluation ──< EvaluationScore >── RubricCriterion
Project ──< Vote, Comment
```

## Tables

**users** — `id, email (unique), password_hash, full_name, role (enum:
participant/judge/organizer/admin), institution, is_demo, created_at`.
Role is a first-class column checked by `require_roles()` on every
protected endpoint — not inferred from anything client-supplied.

**skills** — `id, name (unique), category`. A shared, growable catalog;
any user or organizer action that references a new skill name creates
the row if it doesn't exist yet ("configurable rather than hardcoded",
per the spec).

**user_skills** — `id, user_id, skill_id, kind (have/want), proficiency
(0-100, only for kind=have)`. Unique on (user_id, skill_id, kind) — a
user can both "have" and "want" the same skill (rare but not forbidden)
without duplicate rows of the same kind.

**hackathons** — `id, name, tagline, description, rules,
registration_deadline, start_date, end_date, submission_deadline
(required), min_team_size, max_team_size, blind_judging, status (enum),
created_by`. `submission_deadline` is the one field every deadline check
in the codebase reads from — there is exactly one source of truth for
"is it too late."

**teams** — `id, hackathon_id, name, created_by`. A user can belong to
at most one team per hackathon (enforced in `routers/teams.py`, not just
assumed).

**team_members** — `id, team_id, user_id, is_leader`. Unique on
(team_id, user_id).

**team_skill_requirements** — `id, team_id, skill_id` — the team's
declared "looking for" list, consumed by the matching engine.

**projects** — `id, team_id (unique — one project per team), hackathon_id,
name, short_description, detailed_description, technologies, repo_url,
demo_url, status (draft/submitted/locked), submitted_at`.

**project_claims** — `id, project_id, title, description`.

**claim_evidence** — `id, claim_id, type (enum: repository/demo/
documentation/architecture_diagram/screenshot/test_result/explanation),
content`. Evidence existing does not imply a claim is judged true — that
distinction is enforced by never auto-deriving a claim's truth value
anywhere in the codebase; only a judge's rubric scores and comments
represent an evaluation.

**judge_assignments** — `id, hackathon_id, judge_id, project_id,
assigned_by`. Unique on (judge_id, project_id). Creating an assignment is
blocked server-side if a `judge_conflicts` row already exists for that
pair.

**judge_conflicts** — `id, hackathon_id, judge_id, project_id, reason,
declared_by`. Unique on (judge_id, project_id). Declaring a conflict
deletes any existing assignment for that pair in the same transaction —
conflict declaration is destructive to the assignment by design, not
just advisory.

**rubrics** / **rubric_criteria** — `rubrics: id, hackathon_id, name,
is_active`. `rubric_criteria: id, rubric_id, name, weight_percent,
order_index`. Creating a rubric deactivates any previous active rubric
for that hackathon in the same call (only one active rubric at a time).
Weights are validated to sum to 100 in the Pydantic schema
(`schemas.py::RubricCreate`) before anything touches the database.

**evaluations** — `id, hackathon_id, assignment_id (unique — one
evaluation per assignment), judge_id, project_id, rubric_id,
overall_comment, submitted_at, locked`. `locked=True` is the only state
that makes an evaluation immutable and countable toward scoring.

**evaluation_scores** — `id, evaluation_id, criterion_id, score (0-10),
comment`. Unique on (evaluation_id, criterion_id).

**normalized_scores** — `id, hackathon_id, project_id, run_id, raw_score,
normalized_score, final_score, num_evaluations, method, computed_at`.
Every normalization run gets a fresh `run_id` (UUID); rows are never
overwritten, so past runs remain inspectable.

**rankings** — `id, hackathon_id, run_id, project_id, rank, final_score,
is_official, published, computed_at`. A ranking row is tied to the
`run_id` that produced it. Only rows created with `publish=true` on
`/api/scoring/rank/{run_id}` get `is_official=True` — every other
ranking computation (including every Ranking Lab simulation) never
writes to this table at all; simulations are computed in-memory and
persisted separately in `ranking_simulations`.

**ranking_simulations** — `id, hackathon_id, name, config_json,
result_json, diff_summary, created_by, created_at`. Stores the exact
input configuration and output of every what-if run, so a simulation is
reproducible and auditable after the fact, not just a transient UI state.

**audit_logs** — `id, actor_id, actor_role, action, resource_type,
resource_id, metadata_json, hackathon_id, timestamp`. Append-only: no
route in the entire API updates or deletes an `AuditLog` row.

**votes** — `id, project_id, user_id`. Unique on (project_id, user_id) —
the database itself, not just application logic, prevents duplicate
voting.

**comments** — `id, project_id, user_id, content, created_at`.

## Constraints doing real work

- `UniqueConstraint` on (team_id, user_id), (judge_id, project_id) [both
  assignments and conflicts], (evaluation_id, criterion_id), (project_id,
  user_id) [votes] — these aren't decorative; several of the security
  tests rely on the database itself rejecting a duplicate, not just the
  application layer remembering to check.
- Every foreign key models a real ownership or containment relationship
  used by an authorization check somewhere in `routers/` (e.g. "is this
  user a member of this project's team" walks `team_members` by
  `project.team_id`).
