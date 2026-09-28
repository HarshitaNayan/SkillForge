# Threat Model

Scope: a self-hosted SkillForge deployment running one hackathon, with
participants, judges, organizers, and an admin as the trust boundary
between roles, plus the general public accessing the read-only gallery.

For each threat: what could go wrong, what mitigates it in this codebase,
and what's explicitly out of scope.

## 1. Unauthorized judging (a non-judge or wrong judge submitting scores)

- **Mitigation:** `require_roles("judge")` on `/api/judging/evaluations`
  rejects any non-judge with 403 before the handler runs. Within judges,
  `_assert_can_judge` checks a real `JudgeAssignment` row exists for the
  (judge, project) pair — a judge cannot score a project they were never
  assigned, even if they know its ID.
- **Tested by:** `test_judge_cannot_evaluate_unassigned_project`.
- **Out of scope:** compromise of a judge's own credentials (see #8).

## 2. Role escalation

- **Mitigation:** the registration schema (`schemas.py::UserRegister`)
  only accepts `role in {participant, judge}` — a Pydantic validator
  rejects `organizer`/`admin` at the request-parsing stage, before any
  handler code runs. There is no API endpoint anywhere that lets a user
  change their own role. Organizer/admin accounts must be provisioned by
  a direct database write (documented in the seed script and tests as
  the intended bootstrap path for a first admin).
- **Tested by:** `test_cannot_self_register_as_organizer_or_admin`.
- **Residual risk:** whoever has direct database or shell access to a
  deployment can grant themselves any role — this is standard for a
  self-hosted single-tenant app and is a deployment/hosting concern, not
  an application-layer one.

## 3. Manipulation of scores

- **Mitigation:** scores are validated to be in [0, 10] at the schema
  layer; the set of criterion IDs submitted must exactly match the active
  rubric's criteria (rejects scoring against a stale/wrong/partial
  rubric); once `locked=True`, an evaluation cannot be resubmitted or
  edited by anyone, including the judge who wrote it, via any endpoint —
  there is no PATCH or PUT route for evaluations, only the guarded
  create-or-update-until-locked flow in `submit_evaluation`.
- **Tested by:** `test_locked_evaluation_cannot_be_modified`.

## 4. Duplicate voting

- **Mitigation:** enforced at two levels — the application checks for an
  existing `Vote` row before inserting, and the database itself has a
  `UniqueConstraint` on (project_id, user_id), so even a race condition
  between two concurrent requests from the same user can't produce two
  votes (the second insert fails at the DB layer).

## 5. Deadline manipulation

- **Mitigation:** every project-mutating endpoint (`update_project`,
  `submit_project`, claim/evidence create-or-delete) independently calls
  `assert_before_submission_deadline`, which compares the *server's*
  current time against the *stored* `submission_deadline` value on every
  single call — there is no reliance on a client-supplied timestamp, a
  cached "is it locked" flag, or the frontend disabling a button. The
  frontend disabling controls after a deadline is a UX courtesy only.
- **Tested by:** `test_project_edit_rejected_after_submission_deadline`.
- **Residual risk:** server clock accuracy. A deployment with a
  significantly wrong system clock could mis-enforce deadlines; this is
  an infrastructure concern (NTP), not something the application can fix
  from inside itself.

## 6. Unauthorized submission changes

- **Mitigation:** `_require_team_member` on every project-mutating
  endpoint walks the real `team_members` table for the project's
  `team_id` — an outsider (even an authenticated participant on a
  different team) gets 403. Admin is exempt by design (support/
  moderation access), everyone else is checked.
- **Tested by:** `test_only_team_member_can_edit_project`.

## 7. Judge conflicts of interest

- Covered in detail in `JUDGING.md`. Three independent enforcement
  points (block new assignment, revoke existing assignment on conflict
  declaration, re-check at evaluation-submit time) rather than one,
  specifically so a race between two requests can't slip a conflicted
  score through.
- **Tested by:** `test_conflicted_judge_cannot_evaluate`.

## 8. Unauthorized access to private data

- **Mitigation:** JWT-based auth on every non-public endpoint
  (`get_current_user` raises 401 with no token or an invalid one); blind
  judging strips team identity from a judge's queue at the server before
  the response is ever built (see `JUDGING.md`); the audit log itself is
  readable only by organizer/admin.
- **Tested by:** `test_unauthenticated_cannot_access_protected_resource`,
  `test_participant_cannot_access_organizer_apis`,
  `test_participant_cannot_access_judge_apis`.
- **Out of scope / residual risk:** this deployment uses a fixed
  `SECRET_KEY` fallback for local/demo use
  (`security.py::SECRET_KEY`, overridable via the `SKILLFORGE_SECRET_KEY`
  environment variable) — a production deployment MUST set that
  environment variable to a real secret; the fallback exists only so the
  seed script and local dev work out of the box. Token expiry is 7 days;
  there is no token revocation list, so a stolen token remains valid
  until it expires. HTTPS/TLS termination is assumed to be handled by
  whatever reverse proxy fronts the deployment — the app itself speaks
  plain HTTP, as is normal for an app-server process behind a proxy.

## 9. Rate abuse / repeated requests

- **Out of scope for this pass.** No rate limiting is implemented at the
  application layer. In a real deployment this belongs at the reverse
  proxy / API gateway layer (e.g. nginx `limit_req`), not duplicated
  inside the app. Noted here rather than silently omitted.

## 10. Ownership validation generally

- The pattern used throughout (`_require_team_member`,
  `_assert_can_judge`, rubric-criterion-set matching, locked-state checks)
  is: **never trust an ID in the request body to imply permission** —
  every mutating handler re-derives "does this actor have a real,
  currently-valid relationship to this resource" from the database on
  every call, rather than trusting anything the client asserts.

## Summary table

| Threat | Primary mitigation | Test |
|---|---|---|
| Unauthorized judging | assignment check | `test_judge_cannot_evaluate_unassigned_project` |
| Role escalation | registration schema validator | `test_cannot_self_register_as_organizer_or_admin` |
| Score manipulation | range validation + immutable lock | `test_locked_evaluation_cannot_be_modified` |
| Duplicate voting | DB unique constraint | (schema-level, exercised in `community.py`) |
| Deadline manipulation | server-side time check on every write | `test_project_edit_rejected_after_submission_deadline` |
| Unauthorized submission edits | team-membership check | `test_only_team_member_can_edit_project` |
| Judge conflicts of interest | 3-point enforcement | `test_conflicted_judge_cannot_evaluate` |
| Unauthorized data access | JWT + RBAC + blind-judging redaction | `test_unauthenticated_cannot_access_protected_resource`, `test_participant_cannot_access_organizer_apis` |
| Simulation corrupting official results | separate storage, no write path | `test_official_ranking_never_mutated_by_simulation` |

## Remaining limitations

- No rate limiting (see #9) — recommended at the infrastructure layer.
- No secret rotation / token revocation.
- No audit log integrity protection beyond "no API route can modify it"
  — someone with direct DB access could still edit rows. Cryptographic
  tamper-evidence (e.g. hash chaining) was judged out of scope for this
  pass; noted as a real future improvement in `WRITE-UP.md`.
