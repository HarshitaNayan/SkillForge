# From Claims to Evidence: Building a Reproducible Hackathon Judging System

## 1. Problem

Hackathon judging usually collapses two different questions into one:
"what does this team say they built?" and "how good is it?" A three-
minute demo and a paragraph description are not enough evidence to
answer the first question reliably, which means the second question gets
answered on vibes and stage presence more than on substance. Separately,
judges disagree — not just about quality, but about what a "7" even
means — and naively averaging their raw scores silently favors whichever
teams happened to draw the more generous graders.

## 2. Motivation

SkillForge exists to make both of those problems structural rather than
incidental: force teams to state claims explicitly and attach evidence
per claim (so a judge is evaluating a specific, falsifiable statement,
not a vibe), and correct for judge-to-judge scoring habits mathematically
before ranking, with the correction method itself open to inspection.

## 3. Concept

```
SKILLS -> TEAM FORMATION -> PROJECT -> CLAIMS + EVIDENCE -> JUDGING
       -> NORMALIZATION -> RANKING -> AUDIT / REPLAY / RANKING LAB
```

Team formation and judging are usually treated as unrelated hackathon
features. SkillForge treats them as one pipeline: the same skill data a
participant enters to find teammates is the same kind of structured,
inspectable information a judge later relies on (via claims/evidence)
to evaluate the team's output — and the same principle (show your work,
don't just assert it) runs through both halves.

## 4. Skill-based team formation

Matching is a deterministic calculation over declared skill proficiency
and declared gaps ("looking for X"), not a black box. For a candidate and
a team, the score is `average proficiency of covered gap-skills × (gap
skills covered / total gap skills)` — rewarding both breadth (covering
more of what's missing) and depth (being good at what's covered). The
API returns the matched skills, the still-missing skills, and a plain-
language reason ("Covers 2 of 3 needed skills... at an average
proficiency of 82%") alongside the number, specifically so it's never a
"mysterious percentage."

## 5. Claim/evidence architecture

A project doesn't have a monolithic description — it has a list of
discrete claims ("REST API", "Real-time sync"), each with zero or more
pieces of evidence (a repo link, a demo link, a written explanation).
Deliberately, the system never marks a claim "verified" just because
evidence exists — `ProjectClaim` and `ClaimEvidence` are separate tables
with no `verified` boolean anywhere; a judge's rubric score and comment
are the only place a truth judgment is recorded. This was a specific
design decision to resist the temptation to auto-score based on evidence
presence, which would just move the "vibes" problem one level down.

## 6. Judging engine

See `docs/JUDGING.md` for the full pipeline. The core engineering
decision: assignment, blind judging, conflict-of-interest, and locking
are each enforced at more than one layer (schema validation, ownership
check, database constraint) so that no single missed check anywhere in
the codebase silently breaks an integrity guarantee.

## 7. Weighted scoring

Each evaluation's per-criterion scores (0-10) combine into one weighted
score using the active rubric's `weight_percent` values, which are
schema-validated to sum to 100 before the rubric can even be saved. This
keeps "40% technical, 20% innovation..." an organizer-configured fact,
not a hardcoded assumption anywhere in the scoring code.

## 8. Score normalization

Full method and edge-case handling: `docs/JUDGING.md`. The short version:
z-score each judge against their own mean/stdev, average the z-scores
per project, map back to a 0-10 scale via a fixed, documented constant.

## 9. Ranking

Sorted, dense-ranked by final score, tied to the specific normalization
`run_id` that produced it. Publishing a ranking as official is a distinct
organizer action from computing one — you can compute and inspect a
ranking before deciding to publish it.

## 10. Ranking Lab

The signature feature, and the one most likely to be dismissed as
decorative if it weren't demonstrably real. It shares its scoring
function with the actual normalization run (see `services/scoring.py`),
so "run a simulation" cannot silently use different math than "run the
real thing." It's verified never to write to the official ranking table
(`test_official_ranking_never_mutated_by_simulation`).

## 11. Ranking Replay

Rather than script an animation of "what a judging pipeline looks like,"
Replay queries the real, timestamped `audit_logs` table for the specific
hackathon and returns the actual sequence of events that occurred. If a
hackathon's evaluations were locked out of the "expected" order (say, a
late-added judge assignment after some evaluations were already in), the
replay would show that — it isn't a canned diagram.

## 12. Auditability

Every mutating endpoint writes an `AuditLog` row in the same database
transaction as the action itself — meaning there is no code path where an
action succeeds but its audit record is lost to a crash between two
separate commits. No route in the API updates or deletes an audit row.

## 13. Security

See `docs/THREAT-MODEL.md`. The recurring pattern: never trust a
client-supplied ID to imply permission; re-derive the actor's real
relationship to the resource from the database on every mutating call.

## 14. Threat model

Ten named threats, mitigations, and residual risks, cross-referenced to
the specific automated test that verifies each: `docs/THREAT-MODEL.md`.

## 15. Offline architecture

No mandatory external service. SQLite for storage, JWT for stateless
auth (no session store), FastAPI + Uvicorn as the only server process.
Once `pip install` and `npm install` have run, the system needs no
internet access to operate.

## 16. Database design

Full schema and the reasoning behind each unique constraint:
`docs/DATA-MODEL.md`.

## 17. API design

REST, one router module per resource area, 57 routes, Pydantic-validated
request/response contracts, auto-generated OpenAPI docs at `/docs`. No
endpoint exists that the frontend doesn't call, and no button in the
frontend calls an endpoint that doesn't exist — verified by manual
cross-reference during development, not just asserted.

## 18. Testing

16 backend pytest tests targeting the security-critical paths named in
the spec (RBAC isolation, COI, locking, deadlines, rubric validation,
ownership), plus a seed script that is itself a full end-to-end
integration test of the real pipeline over the real HTTP API. See
`docs/ACCEPTANCE-REPORT.md` for the full list and what's explicitly not
covered (frontend automated tests, load/concurrency testing).

## 19. Experiments

**Experiment: does normalization actually change the outcome, or is it
theoretical?**

Setup: three judges scored the same four projects. Judge A ("harsh")
scored in the 3.7-6.9 range; Judge B ("generous") scored in the 7.7-9.4
range; Judge C ("moderate", recused from one project via a declared
conflict) scored in the 6.4-7.9 range. Critically, the judges' *relative*
opinions of the four projects were constructed to disagree with each
other, not just their absolute generosity.

Raw-average ranking (normalization method = `none`):
```
1. Vantage Vision   — 7.25
2. Ember Marketplace — 7.03
3. Quartz Tracker    — 7.00
4. Nimbus Notes      — 6.70
```

Z-score-normalized ranking (method = `z_score`, the published official):
```
1. Ember Marketplace — final score 5.449
2. Vantage Vision    — final score 5.396
3. Nimbus Notes      — final score 4.970
4. Quartz Tracker    — final score 4.318
```

**Result: all four positions changed.** Ember Marketplace — ranked 2nd on
raw averages — moves to 1st once each judge's score is measured against
their own baseline instead of an absolute scale; Quartz Tracker, close to
1st on raw score, drops to last once you account for the fact that its
relatively strong raw numbers came disproportionately from the judge who
scored everything highly. This is the concrete evidence that the z-score
method is doing real, outcome-changing work in this dataset — not merely
present in the code.

**Experiment: removing a judge (Ranking Lab).** Running the "exclude
generous judge" simulation changes 3 of 4 ranking positions relative to
the official ranking, showing the system is meaningfully sensitive to
which judges participate — an organizer using Ranking Lab could use this
to check whether a single judge's absence (illness, late withdrawal) would
have changed the outcome enough to warrant re-review.

## 20. Results

A working, tested, end-to-end platform: 4 roles, 57 API routes, 16
passing security/logic tests, one seed script that exercises the entire
pipeline over real HTTP and fails loudly on any regression, and a
normalization system with a documented method and a demonstrated,
non-trivial effect on real (seeded) data.

## 21. Limitations

- Single active rubric per hackathon at a time — no support for
  versioned rubrics with historical re-scoring.
- No file/image upload for evidence — URLs and text only.
- No rate limiting at the application layer.
- No Docker Compose file or CI pipeline in this pass.
- Frontend has no automated test suite (verified by build + manual
  contract review instead).

## 22. Future improvements

- Background scheduler for deadline-driven auto-locking, rather than the
  current lazy sweep-on-view approach (functionally equivalent for
  enforcement, since every write path checks the deadline directly, but
  a scheduler would keep `Project.status` visually current between
  organizer page loads too).
- Hash-chained audit log for tamper-evidence beyond "no API route can
  modify it."
- Multi-rubric versioning with historical evaluation reconciliation.
- File upload support for evidence (screenshots, architecture diagrams)
  instead of URL/text-only.

## 23. Lessons learned

The most valuable design decision was making the Ranking Lab simulation
share its scoring function with the real normalization run: it removed
an entire category of bug (demo path silently diverging from production
logic) by construction rather than by discipline. The second most
valuable decision was writing the seed script against the real HTTP API
instead of the ORM directly — it caught several integration bugs (a
rubric-criterion mismatch, a role-registration validation error) that
unit tests alone would have missed, simply because seeding a realistic
scenario forced every layer of the stack to actually cooperate.
