# SkillForge

**Build the right team. Prove what you built.**

SkillForge is a self-hosted hackathon platform that connects skill-based
team formation to a claim-and-evidence project submission model and an
auditable, normalized judging engine.

```
SKILLS -> TEAM FORMATION -> PROJECT -> CLAIMS + EVIDENCE -> JUDGING
       -> NORMALIZATION -> RANKING -> AUDIT / REPLAY / RANKING LAB
```

This is a real, working full-stack application — not a UI prototype. Every
button in the frontend calls a real API endpoint, backed by a real SQLite
database, enforced by real server-side authorization. See
`ACCEPTANCE-REPORT.md` for a requirement-by-requirement account of what's
implemented and tested, and what isn't.

## Stack

- **Backend:** Python, FastAPI, SQLAlchemy, SQLite, Pydantic, JWT auth
- **Frontend:** React, Vite, TypeScript, Tailwind CSS
- No external/cloud services required. Runs fully offline once dependencies
  are installed.

## Running it locally

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m scripts.seed        # populates realistic demo data (drops any existing DB)
python -m uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000/api`, with interactive OpenAPI
docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app is now at `http://localhost:5173` (Vite proxies `/api` to the
backend on port 8000 — see `vite.config.ts`).

### Running the test suite

```bash
cd backend
python -m pytest app/tests -q
```

## Demo accounts

After running the seed script, all accounts use the password
`DemoPass123!`:

| Role | Email |
|---|---|
| Organizer | organizer@skillforge.demo |
| Judge (harsh grader) | judge.harsh@skillforge.demo |
| Judge (generous grader) | judge.generous@skillforge.demo |
| Judge (moderate grader) | judge.moderate@skillforge.demo |
| Participant | aarav.mehta@skillforge.demo (and 9 others — see `scripts/seed.py`) |

The seed script deliberately gives the three judges different scoring
habits and constructs a scenario where the official z-score-normalized
ranking actually differs from a simple raw-average ranking (see
`WRITE-UP.md` for the worked numbers) — so the normalization system's
effect is demonstrable, not just theoretical.

## Documentation

- `docs/ARCHITECTURE.md` — system design, request flow, why FastAPI/SQLite/React
- `docs/DATA-MODEL.md` — full schema and entity relationships
- `docs/JUDGING.md` — the judging engine: assignment, blind judging, conflicts,
  rubrics, locking, normalization, ranking, simulation, replay
- `docs/THREAT-MODEL.md` — threats considered and how each is mitigated
- `docs/ACCEPTANCE-REPORT.md` — requirement -> implementation -> test -> result
- `WRITE-UP.md` — the engineering case study / Write-Up Quest submission

## What's deliberately not included

Per the project's own priority rule ("working core features > more
features"), a few things described in early planning were cut rather than
shipped half-working:

- **3D background / animated visuals** — no functional payoff, and the
  fastest way to spend a review budget on decoration instead of a working
  judging engine. The UI uses a plain wine/burgundy identity instead.
- **Docker Compose file** — not included in this pass; `pip install` +
  `npm install` covers local setup. Both services are plain
  Python/Node processes with no external service dependencies, so
  containerizing them is mechanical if needed later.
- Community voting/comments (`/api/community/...`) are wired into the
  project detail page (vote button + comment thread), but there's no
  separate leaderboard-by-votes view yet.
