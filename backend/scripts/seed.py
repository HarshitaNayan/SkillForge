"""Seeds realistic demo data by calling the real HTTP API end-to-end
(not by writing directly to the ORM), so seeding also proves the whole
pipeline actually works: auth -> skills -> teams -> projects -> claims ->
evidence -> judge assignment -> evaluation -> normalization -> ranking.

Run with: python -m scripts.seed
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force a fresh database file for a clean, reproducible seed.
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skillforge.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
os.environ["SKILLFORGE_DB"] = DB_PATH

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def register(email, password, full_name, role, institution=None):
    r = client.post("/api/auth/register", json={
        "email": email, "password": password, "full_name": full_name,
        "role": role, "institution": institution,
    })
    assert r.status_code == 200, r.text
    return r.json()


def login(email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    print("Seeding SkillForge demo data...")

    # --- Organizer ---
    # Organizer/admin roles are intentionally NOT self-registerable via the
    # public API (only participant/judge are) -- that's an RBAC decision,
    # not an oversight. For demo seeding we register as participant and
    # then promote via a direct one-time DB write, exactly as a real
    # deployment's admin bootstrap script would.
    org = register("organizer@skillforge.demo", "DemoPass123!", "Priya Sharma (Organizer)", "participant",
                    "SkillForge HQ")
    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    u = db.query(models.User).filter(models.User.email == "organizer@skillforge.demo").first()
    u.role = models.Role.organizer
    u.is_demo = True
    db.commit()
    db.close()
    org = login("organizer@skillforge.demo", "DemoPass123!")
    org_headers = auth_headers(org["access_token"])

    # --- Judges (3, deliberately different scoring habits) ---
    judges = []
    for email, name in [
        ("judge.harsh@skillforge.demo", "Dr. Anil Verma (Judge)"),
        ("judge.generous@skillforge.demo", "Dr. Fatima Noor (Judge)"),
        ("judge.moderate@skillforge.demo", "Rakesh Iyer (Judge)"),
    ]:
        u = register(email, "DemoPass123!", name, "judge", "Industry Panel")
        db = SessionLocal()
        row = db.query(models.User).filter(models.User.email == email).first()
        row.is_demo = True
        db.commit()
        db.close()
        tok = login(email, "DemoPass123!")
        judges.append({"email": email, "name": name, "id": u["user"]["id"], "headers": auth_headers(tok["access_token"])})

    # --- Participants (10) ---
    participant_specs = [
        ("Aarav Mehta", {"Frontend": 90, "UI/UX": 80}, ["Backend", "DevOps"]),
        ("Diya Kapoor", {"Backend": 90, "Database": 85, "DevOps": 75}, ["Frontend"]),
        ("Kabir Rao", {"AI/ML": 85, "Python": 90}, ["Frontend", "Database"]),
        ("Ananya Singh", {"Frontend": 85, "AI/ML": 70}, ["Backend", "DevOps"]),
        ("Vivaan Joshi", {"Backend": 80, "DevOps": 85}, ["Frontend", "AI/ML"]),
        ("Ishaan Gupta", {"Database": 90, "Backend": 70}, ["Frontend", "UI/UX"]),
        ("Myra Patel", {"UI/UX": 90, "Frontend": 75}, ["Backend"]),
        ("Reyansh Nair", {"AI/ML": 90, "Backend": 60}, ["Frontend", "DevOps"]),
        ("Saanvi Reddy", {"Frontend": 70, "Backend": 70, "DevOps": 60}, []),
        ("Arjun Malhotra", {"DevOps": 90, "Backend": 75}, ["Frontend", "AI/ML"]),
    ]
    participants = []
    for name, have, want in participant_specs:
        email = name.lower().replace(" ", ".") + "@skillforge.demo"
        u = register(email, "DemoPass123!", name, "participant", "Arcade Business College")
        tok = login(email, "DemoPass123!")
        headers = auth_headers(tok["access_token"])
        skills_payload = [{"skill_name": s, "kind": "have", "proficiency": p} for s, p in have.items()]
        skills_payload += [{"skill_name": s, "kind": "want", "proficiency": None} for s in want]
        r = client.put("/api/users/me/skills", json=skills_payload, headers=headers)
        assert r.status_code == 200, r.text
        participants.append({"name": name, "email": email, "id": u["user"]["id"], "headers": headers})

    # --- Hackathon ---
    submission_deadline = (datetime.utcnow() + timedelta(days=30)).isoformat()
    r = client.post("/api/hackathons", json={
        "name": "SkillForge Demo Hackathon 2026",
        "tagline": "Build the right team. Prove what you built.",
        "description": "A self-hosted hackathon platform demo: skill-based team formation, "
                        "claim-and-evidence submissions, and auditable, normalized judging.",
        "rules": "Teams of 2-4. Original work only. Submit before the deadline.",
        "submission_deadline": submission_deadline,
        "min_team_size": 2,
        "max_team_size": 4,
        "blind_judging": True,
    }, headers=org_headers)
    assert r.status_code == 200, r.text
    hackathon = r.json()
    hid = hackathon["id"]
    print(f"Created hackathon {hid}")

    # --- Teams ---
    team_defs = [
        ("Team Nimbus", [0, 1, 2], ["DevOps"]),         # Aarav(FE), Diya(BE), Kabir(AI/ML) -> needs DevOps
        ("Team Ember", [3, 4, 5], ["UI/UX"]),            # Ananya, Vivaan, Ishaan
        ("Team Quartz", [6, 7], ["Backend", "DevOps"]),  # Myra, Reyansh
        ("Team Vantage", [8, 9], ["AI/ML"]),             # Saanvi, Arjun
    ]
    teams = []
    for name, member_idxs, looking_for in team_defs:
        leader = participants[member_idxs[0]]
        r = client.post("/api/teams", json={
            "hackathon_id": hid, "name": name, "looking_for_skill_names": looking_for,
        }, headers=leader["headers"])
        assert r.status_code == 200, r.text
        team = r.json()
        for idx in member_idxs[1:]:
            member = participants[idx]
            r = client.post(f"/api/teams/{team['id']}/join", headers=member["headers"])
            assert r.status_code == 200, r.text
        teams.append({"id": team["id"], "name": name, "members": [participants[i] for i in member_idxs]})
        print(f"Created team {name} with {len(member_idxs)} members")

    # Sanity-check the matching engine for Team Nimbus (looking for DevOps)
    r = client.get(f"/api/teams/{teams[0]['id']}/matches", headers=teams[0]["members"][0]["headers"])
    assert r.status_code == 200, r.text

    # --- Rubric ---
    r = client.post("/api/judging/rubrics", json={
        "hackathon_id": hid, "name": "Standard Rubric",
        "criteria": [
            {"name": "Technical correctness", "weight_percent": 40},
            {"name": "Innovation", "weight_percent": 20},
            {"name": "Usability", "weight_percent": 15},
            {"name": "Architecture", "weight_percent": 15},
            {"name": "Documentation", "weight_percent": 10},
        ],
    }, headers=org_headers)
    assert r.status_code == 200, r.text
    rubric = r.json()
    criteria_ids = {c["name"]: c["id"] for c in rubric["criteria"]}
    print("Created rubric with 5 weighted criteria")

    # --- Projects with claims + evidence ---
    project_defs = [
        (0, "Nimbus Notes", "Realtime collaborative note-taking app",
         ["REST API", "Authentication", "Real-time sync", "Database"]),
        (1, "Ember Marketplace", "Local artisan marketplace with recommendations",
         ["REST API", "Authentication", "AI/ML model", "Deployment"]),
        (2, "Quartz Tracker", "Personal finance tracker with insights dashboard",
         ["REST API", "Database", "Dashboard/analytics"]),
        (3, "Vantage Vision", "Computer-vision based accessibility assistant",
         ["AI/ML model", "REST API", "Real-time processing"]),
    ]
    projects = []
    for team_idx, name, desc, claim_titles in project_defs:
        team = teams[team_idx]
        leader = team["members"][0]
        r = client.post("/api/projects", json={
            "team_id": team["id"], "hackathon_id": hid, "name": name,
            "short_description": desc, "detailed_description": desc + ". Built during the hackathon.",
            "technologies": "React, FastAPI, SQLite", "repo_url": f"https://github.com/demo/{name.lower().replace(' ', '-')}",
            "demo_url": f"https://demo.skillforge.dev/{name.lower().replace(' ', '-')}",
        }, headers=leader["headers"])
        assert r.status_code == 200, r.text
        project = r.json()
        for title in claim_titles:
            r = client.post(f"/api/projects/{project['id']}/claims", json={
                "title": title, "description": f"We implemented {title.lower()}.",
            }, headers=leader["headers"])
            assert r.status_code == 200, r.text
            claim = r.json()
            r = client.post(f"/api/projects/{project['id']}/claims/{claim['id']}/evidence", json={
                "type": "repository", "content": project["repo_url"],
            }, headers=leader["headers"])
            assert r.status_code == 200, r.text
        r = client.post(f"/api/projects/{project['id']}/submit", headers=leader["headers"])
        assert r.status_code == 200, r.text
        projects.append(project)
        print(f"Submitted project {name} with {len(claim_titles)} claims")

    # --- Judge assignments (each judge sees every project except any COI) ---
    for j in judges:
        for p in projects:
            r = client.post("/api/judging/assignments", json={
                "hackathon_id": hid, "judge_id": j["id"], "project_id": p["id"],
            }, headers=org_headers)
            assert r.status_code == 200, r.text

    # Declare one conflict of interest for realism: the "moderate" judge
    # recuses from Vantage Vision (project index 3).
    moderate_judge = judges[2]
    r = client.post("/api/judging/conflicts", json={
        "hackathon_id": hid, "judge_id": moderate_judge["id"], "project_id": projects[3]["id"],
        "reason": "Judge previously mentored this team.",
    }, headers=org_headers)
    assert r.status_code == 200, r.text
    print("Declared 1 conflict of interest (auto-removed the matching assignment)")

    # --- Evaluations: three judges with deliberately different distributions ---
    # These specific numbers are chosen (not arbitrary) to make the effect of
    # normalization visible and provable: the harsh judge's absolute scores
    # are low across the board but internally consistent, the generous
    # judge's are high across the board, and their *relative* opinions of
    # the four projects disagree enough that the raw-average ranking and
    # the z-score-normalized ranking actually differ. See WRITE-UP.md for
    # the worked comparison this produces.
    # projects list order: [Nimbus Notes, Ember Marketplace, Quartz Tracker, Vantage Vision]
    per_project_scores = {
        judges[0]["id"]: [3.7, 5.0, 6.9, 6.1],   # harsh — relatively prefers Quartz
        judges[1]["id"]: [8.5, 9.4, 7.7, 8.4],   # generous — relatively prefers Ember
        judges[2]["id"]: [7.9, 6.7, 6.4, None],  # moderate — COI on Vantage, prefers Nimbus
    }
    criterion_names = ["Technical correctness", "Innovation", "Usability", "Architecture", "Documentation"]
    for j in judges:
        plan = per_project_scores[j["id"]]
        for p, overall in zip(projects, plan):
            if overall is None:
                continue  # COI-excluded project for this judge
            # Same value on every criterion keeps the weighted score equal to
            # `overall` exactly, so the numbers above are the actual weighted scores.
            score_list = [{"criterion_id": criteria_ids[name], "score": overall, "comment": None}
                          for name in criterion_names]
            r = client.post("/api/judging/evaluations", json={
                "project_id": p["id"], "scores": score_list,
                "overall_comment": "Evaluated against the standard rubric.", "submit_final": True,
            }, headers=j["headers"])
            assert r.status_code == 200, r.text
    print("Submitted and locked all evaluations (with 3 distinct judge scoring distributions)")

    # --- Normalization + ranking ---
    r = client.post("/api/scoring/normalize", json={"hackathon_id": hid, "method": "z_score"}, headers=org_headers)
    assert r.status_code == 200, r.text
    run_id = r.json()["run_id"]
    r = client.post(f"/api/scoring/rank/{run_id}?hackathon_id={hid}&publish=true", headers=org_headers)
    assert r.status_code == 200, r.text
    print("Ran z-score normalization and published official ranking:")
    for row in r.json():
        print(f"  #{row['rank']} {row['project_name']} — final score {row['final_score']}")

    # --- Ranking Lab: demonstrate normalization's effect by comparing raw vs normalized ---
    r = client.post("/api/scoring/simulate", json={
        "hackathon_id": hid, "name": "Raw scores only (no normalization)", "method": "none",
    }, headers=org_headers)
    assert r.status_code == 200, r.text
    print(f"Ranking Lab simulation (raw vs normalized): {r.json()['diff_summary']}")

    r = client.post("/api/scoring/simulate", json={
        "hackathon_id": hid, "name": "Exclude generous judge", "exclude_judge_ids": [judges[1]["id"]],
    }, headers=org_headers)
    assert r.status_code == 200, r.text
    print(f"Ranking Lab simulation (excluding generous judge): {r.json()['diff_summary']}")

    print("\nSeed complete.")
    print("Demo accounts (all password: DemoPass123!):")
    print("  Organizer: organizer@skillforge.demo")
    for j in judges:
        print(f"  Judge: {j['email']}")
    for p in participants[:3]:
        print(f"  Participant: {p['email']}")
    print(f"Hackathon ID: {hid}")


if __name__ == "__main__":
    main()
