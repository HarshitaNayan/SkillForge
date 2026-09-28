# Judging Engine

This document explains the full judging pipeline and, specifically, the
normalization method — the part of the system most likely to be
scrutinized, and the one the spec explicitly asks to be "documented" and
"defensible."

## Pipeline

```
1. Organizer configures a weighted rubric (criteria + weight_percent, sum=100)
2. Organizer assigns judges to projects
3. Judges may declare conflicts of interest -> assignment auto-revoked
4. Judges submit scores per criterion (0-10) against the active rubric
5. Judge locks the evaluation (submit_final=true) -> immutable from here
6. Organizer runs normalization -> raw + normalized + final score per project
7. Organizer generates a ranking from a normalization run
8. Organizer publishes that ranking as official (only one official ranking
   per hackathon at a time)
9. Ranking Lab: organizer can simulate alternate scenarios without ever
   touching the official ranking
10. Ranking Replay reconstructs the actual audit-log sequence that produced
    the current official ranking
```

## Blind judging

When a hackathon has `blind_judging=True` (the default), the judge's
queue endpoint (`GET /api/judging/my-projects`) never includes the
`team_name` or `team_members` fields in its response — the backend
simply doesn't put them in the payload, so there's nothing for the
frontend to accidentally leak. This is enforced once, server-side, for
every client that ever calls that endpoint (a hostile or modified
frontend gains nothing).

## Conflict of interest enforcement

Two independent points of enforcement, not one:
1. `POST /api/judging/assignments` refuses to create an assignment if a
   `JudgeConflict` row already exists for that (judge, project) pair.
2. Declaring a conflict (`POST /api/judging/conflicts`) deletes any
   existing assignment for that pair in the same transaction.
3. As defense in depth, `submit_evaluation` independently re-checks for a
   conflict before accepting any score — so even a race between "declare
   conflict" and "submit evaluation" in two different requests can't let
   a conflicted judge's score through.

## Score locking

An evaluation is mutable (can be saved as a draft, re-submitted, edited)
until `submit_final=true` sets `locked=True`. From that point:
- Re-submitting is rejected with 403.
- The organizer cannot delete the judge's assignment (`DELETE
  /api/judging/assignments/{id}` checks for a locked evaluation first).
- The score becomes eligible for normalization (`collect_locked_evaluations`
  only ever reads `locked=True` rows).

## Normalization method: judge-relative z-score

**Problem.** Judges differ in scoring habits. A judge who scores
everything 8-9 and one who spreads scores 4-9 aren't directly comparable;
naively averaging raw scores across judges biases outcomes toward
whichever judges happened to grade the "easier" way, not toward which
projects were actually better.

**Method** (`app/services/scoring.py::compute_project_scores`):
1. For each judge, collect their locked weighted-rubric scores (each a
   single 0-10 number combining that evaluation's criterion scores per
   the active rubric's weights) across every project they evaluated.
2. Compute that judge's mean (`mu_j`) and population standard deviation
   (`sigma_j`) over their own scores only.
3. For each evaluation, `z = (score - mu_j) / sigma_j` — how far above or
   below *that judge's own average* this project scored, independent of
   the judge's overall generosity or harshness.
4. A project's normalized score is the mean of its z-scores across every
   judge who evaluated it.
5. For readability, normalized scores are mapped back onto a 0-10 scale:
   `final = clamp(5 + z_mean * 2, 0, 10)`. This is a fixed, documented
   choice (roughly ±2.5 standard deviations spans the full range,
   centered at 5) — not a parameter fitted to make any particular
   ranking come out a certain way.

**Edge cases, and why they're handled this way:**
- **Zero variance** (`sigma_j == 0`): the judge gave identical scores to
  everything they evaluated, so their scores carry no information about
  which project was better. Rather than divide by zero, their z-score is
  defined as `0` (neutral) for every project.
- **A judge with exactly one locked evaluation**: population stdev of a
  single point is `0` by construction, so the same zero-variance rule
  applies automatically — no special-casing needed.
- **A project with zero locked evaluations**: excluded from the
  normalization/ranking output entirely (never assigned a fabricated
  score), because there's nothing to compute from.
- **Insufficient evaluators generally**: the API always returns
  `num_evaluations` alongside every score, so a project ranked on one
  evaluation is visibly distinguishable from one ranked on five — the
  organizer isn't given a number without its evidentiary weight.

**Alternative methods**, selectable per-run:
- `min_max`: rescales each judge's own scores to [0,10] using their
  observed min/max. If a judge's min equals their max (no spread), every
  one of their scores maps to the scale's midpoint, 5.0, instead of
  dividing by zero.
- `none`: skips normalization entirely (`final == raw`). This exists
  specifically so an organizer can run it side-by-side with `z_score` in
  the Ranking Lab and see, in the actual seeded data, exactly how much
  normalization changes the outcome (see `WRITE-UP.md` for the numbers —
  in the seeded scenario, normalization changes all four ranking
  positions).

## Ranking

`build_ranking` sorts a normalization run's `final_score` descending and
assigns dense ranks 1..N. A ranking is only written to the `rankings`
table as official when an organizer explicitly calls `POST
/api/scoring/rank/{run_id}?publish=true`; publishing one run
automatically un-officializes any previously published ranking for that
hackathon (only one official ranking exists at a time).

## Ranking Lab (what-if simulation)

`POST /api/scoring/simulate` accepts:
- `exclude_judge_ids` — recompute as if these judges never evaluated anything
- `exclude_evaluation_ids` — drop specific evaluations
- `weight_overrides` — recompute with different rubric criterion weights
- `method` — try a different normalization method

Critically, the simulation calls the exact same `compute_project_scores`
function the real normalization run uses — there is no separate,
possibly-diverging "demo" code path. It returns both the current official
ranking and the simulated one side by side with a diff summary ("N
ranking position(s) changed"), and **never writes to the `rankings`
table** — verified by `test_official_ranking_never_mutated_by_simulation`
in the test suite, which runs a simulation and asserts the official
ranking is byte-for-byte identical before and after.

## Ranking Replay

`GET /api/scoring/replay` queries the real `audit_logs` table, filtered
to the actions that actually constitute the judging pipeline
(`project.submit`, `judge.assign`, `evaluation.lock`, `rubric.create`,
`normalization.run`, `ranking.generate`, `ranking.publish`, etc.), ordered
by timestamp. This is not an animation or a scripted sequence — it is a
direct read of what actually happened, in the order it actually happened,
for this specific hackathon.

## Judging Observatory

`GET /api/scoring/observatory` computes every number it returns (total
submissions, assignment coverage, per-judge score distributions,
normalization status) from live queries against the current database
state at request time — nothing is cached or pre-computed at write time,
so the dashboard can never show stale numbers.
