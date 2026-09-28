from datetime import datetime, timedelta
from app.tests.conftest import register_and_login, promote_role, auth


def make_hackathon(client, org_token, submission_deadline=None):
    submission_deadline = submission_deadline or (datetime.utcnow() + timedelta(days=7)).isoformat()
    r = client.post("/api/hackathons", json={
        "name": "Test Hack", "submission_deadline": submission_deadline,
        "min_team_size": 1, "max_team_size": 4, "blind_judging": True,
    }, headers=auth(org_token))
    assert r.status_code == 200, r.text
    return r.json()


def test_unauthenticated_cannot_access_protected_resource(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_participant_cannot_access_organizer_apis(client):
    p_token, _ = register_and_login(client, "p1@test.com", "pass1234", "P One", "participant")
    r = client.post("/api/hackathons", json={
        "name": "Hack", "submission_deadline": (datetime.utcnow() + timedelta(days=1)).isoformat(),
    }, headers=auth(p_token))
    assert r.status_code == 403


def test_participant_cannot_access_judge_apis(client):
    p_token, _ = register_and_login(client, "p2@test.com", "pass1234", "P Two", "participant")
    r = client.get("/api/judging/my-projects?hackathon_id=x", headers=auth(p_token))
    assert r.status_code == 403


def test_cannot_self_register_as_organizer_or_admin(client):
    r = client.post("/api/auth/register", json={
        "email": "sneaky@test.com", "password": "pass1234", "full_name": "Sneaky", "role": "organizer",
    })
    assert r.status_code == 422
    r = client.post("/api/auth/register", json={
        "email": "sneaky2@test.com", "password": "pass1234", "full_name": "Sneaky2", "role": "admin",
    })
    assert r.status_code == 422


def test_judge_cannot_evaluate_unassigned_project(client):
    org_token, org_id = register_and_login(client, "org1@test.com", "pass1234", "Org One")
    promote_role(org_id, "organizer")

    judge_token, judge_id = register_and_login(client, "judge1@test.com", "pass1234", "Judge One", "judge")
    leader_token, leader_id = register_and_login(client, "lead1@test.com", "pass1234", "Leader One")

    h = make_hackathon(client, org_token)
    r = client.post("/api/teams", json={"hackathon_id": h["id"], "name": "T1", "looking_for_skill_names": []},
                     headers=auth(leader_token))
    team = r.json()
    r = client.post("/api/projects", json={
        "team_id": team["id"], "hackathon_id": h["id"], "name": "Proj1",
    }, headers=auth(leader_token))
    project = r.json()

    r = client.post("/api/judging/rubrics", json={
        "hackathon_id": h["id"], "criteria": [{"name": "Quality", "weight_percent": 100}],
    }, headers=auth(org_token))
    rubric = r.json()
    crit_id = rubric["criteria"][0]["id"]

    # Judge was never assigned -- must be rejected
    r = client.post("/api/judging/evaluations", json={
        "project_id": project["id"], "scores": [{"criterion_id": crit_id, "score": 8}], "submit_final": True,
    }, headers=auth(judge_token))
    assert r.status_code == 403


def test_conflicted_judge_cannot_evaluate(client):
    org_token, org_id = register_and_login(client, "org2@test.com", "pass1234", "Org Two")
    promote_role(org_id, "organizer")
    judge_token, judge_id = register_and_login(client, "judge2@test.com", "pass1234", "Judge Two", "judge")
    leader_token, leader_id = register_and_login(client, "lead2@test.com", "pass1234", "Leader Two")

    h = make_hackathon(client, org_token)
    team = client.post("/api/teams", json={"hackathon_id": h["id"], "name": "T2", "looking_for_skill_names": []},
                        headers=auth(leader_token)).json()
    project = client.post("/api/projects", json={
        "team_id": team["id"], "hackathon_id": h["id"], "name": "Proj2",
    }, headers=auth(leader_token)).json()

    r = client.post("/api/judging/assignments", json={
        "hackathon_id": h["id"], "judge_id": judge_id, "project_id": project["id"],
    }, headers=auth(org_token))
    assert r.status_code == 200

    # Declare a conflict -- this must remove the assignment
    r = client.post("/api/judging/conflicts", json={
        "hackathon_id": h["id"], "judge_id": judge_id, "project_id": project["id"], "reason": "bias",
    }, headers=auth(org_token))
    assert r.status_code == 200

    rubric = client.post("/api/judging/rubrics", json={
        "hackathon_id": h["id"], "criteria": [{"name": "Quality", "weight_percent": 100}],
    }, headers=auth(org_token)).json()
    crit_id = rubric["criteria"][0]["id"]

    r = client.post("/api/judging/evaluations", json={
        "project_id": project["id"], "scores": [{"criterion_id": crit_id, "score": 9}], "submit_final": True,
    }, headers=auth(judge_token))
    assert r.status_code == 403


def test_locked_evaluation_cannot_be_modified(client):
    org_token, org_id = register_and_login(client, "org3@test.com", "pass1234", "Org Three")
    promote_role(org_id, "organizer")
    judge_token, judge_id = register_and_login(client, "judge3@test.com", "pass1234", "Judge Three", "judge")
    leader_token, leader_id = register_and_login(client, "lead3@test.com", "pass1234", "Leader Three")

    h = make_hackathon(client, org_token)
    team = client.post("/api/teams", json={"hackathon_id": h["id"], "name": "T3", "looking_for_skill_names": []},
                        headers=auth(leader_token)).json()
    project = client.post("/api/projects", json={
        "team_id": team["id"], "hackathon_id": h["id"], "name": "Proj3",
    }, headers=auth(leader_token)).json()
    client.post("/api/judging/assignments", json={
        "hackathon_id": h["id"], "judge_id": judge_id, "project_id": project["id"],
    }, headers=auth(org_token))
    rubric = client.post("/api/judging/rubrics", json={
        "hackathon_id": h["id"], "criteria": [{"name": "Quality", "weight_percent": 100}],
    }, headers=auth(org_token)).json()
    crit_id = rubric["criteria"][0]["id"]

    r = client.post("/api/judging/evaluations", json={
        "project_id": project["id"], "scores": [{"criterion_id": crit_id, "score": 7}], "submit_final": True,
    }, headers=auth(judge_token))
    assert r.status_code == 200
    assert r.json()["locked"] is True

    # Second attempt to submit for the same assignment must be rejected
    r = client.post("/api/judging/evaluations", json={
        "project_id": project["id"], "scores": [{"criterion_id": crit_id, "score": 2}], "submit_final": True,
    }, headers=auth(judge_token))
    assert r.status_code == 403


def test_participant_cannot_edit_locked_project(client):
    org_token, org_id = register_and_login(client, "org4@test.com", "pass1234", "Org Four")
    promote_role(org_id, "organizer")
    leader_token, leader_id = register_and_login(client, "lead4@test.com", "pass1234", "Leader Four")

    h = make_hackathon(client, org_token)
    team = client.post("/api/teams", json={"hackathon_id": h["id"], "name": "T4", "looking_for_skill_names": []},
                        headers=auth(leader_token)).json()
    project = client.post("/api/projects", json={
        "team_id": team["id"], "hackathon_id": h["id"], "name": "Proj4",
    }, headers=auth(leader_token)).json()
    client.post(f"/api/projects/{project['id']}/submit", headers=auth(leader_token))

    # Manually flip to locked as the deadline sweep would
    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    p = db.query(models.Project).filter(models.Project.id == project["id"]).first()
    p.status = models.ProjectStatus.locked
    db.commit()
    db.close()

    r = client.patch(f"/api/projects/{project['id']}", json={"name": "Hacked Name"}, headers=auth(leader_token))
    assert r.status_code == 403


def test_project_edit_rejected_after_submission_deadline(client):
    org_token, org_id = register_and_login(client, "org5@test.com", "pass1234", "Org Five")
    promote_role(org_id, "organizer")
    leader_token, leader_id = register_and_login(client, "lead5@test.com", "pass1234", "Leader Five")

    past_deadline = (datetime.utcnow() - timedelta(days=1)).isoformat()
    h = make_hackathon(client, org_token, submission_deadline=past_deadline)
    team = client.post("/api/teams", json={"hackathon_id": h["id"], "name": "T5", "looking_for_skill_names": []},
                        headers=auth(leader_token)).json()
    project = client.post("/api/projects", json={
        "team_id": team["id"], "hackathon_id": h["id"], "name": "Proj5",
    }, headers=auth(leader_token)).json()

    r = client.patch(f"/api/projects/{project['id']}", json={"name": "New Name"}, headers=auth(leader_token))
    assert r.status_code == 403
    r = client.post(f"/api/projects/{project['id']}/submit", headers=auth(leader_token))
    assert r.status_code == 403


def test_rubric_weights_must_sum_to_100(client):
    org_token, org_id = register_and_login(client, "org6@test.com", "pass1234", "Org Six")
    promote_role(org_id, "organizer")
    h = make_hackathon(client, org_token)
    r = client.post("/api/judging/rubrics", json={
        "hackathon_id": h["id"],
        "criteria": [{"name": "A", "weight_percent": 60}, {"name": "B", "weight_percent": 30}],
    }, headers=auth(org_token))
    assert r.status_code == 422


def test_only_team_member_can_edit_project(client):
    org_token, org_id = register_and_login(client, "org7@test.com", "pass1234", "Org Seven")
    promote_role(org_id, "organizer")
    leader_token, leader_id = register_and_login(client, "lead7@test.com", "pass1234", "Leader Seven")
    outsider_token, outsider_id = register_and_login(client, "outsider7@test.com", "pass1234", "Outsider Seven")

    h = make_hackathon(client, org_token)
    team = client.post("/api/teams", json={"hackathon_id": h["id"], "name": "T7", "looking_for_skill_names": []},
                        headers=auth(leader_token)).json()
    project = client.post("/api/projects", json={
        "team_id": team["id"], "hackathon_id": h["id"], "name": "Proj7",
    }, headers=auth(leader_token)).json()

    r = client.patch(f"/api/projects/{project['id']}", json={"name": "Stolen"}, headers=auth(outsider_token))
    assert r.status_code == 403


def test_official_ranking_never_mutated_by_simulation(client):
    org_token, org_id = register_and_login(client, "org8@test.com", "pass1234", "Org Eight")
    promote_role(org_id, "organizer")
    judge_token, judge_id = register_and_login(client, "judge8@test.com", "pass1234", "Judge Eight", "judge")
    leader_token, leader_id = register_and_login(client, "lead8@test.com", "pass1234", "Leader Eight")

    h = make_hackathon(client, org_token)
    team = client.post("/api/teams", json={"hackathon_id": h["id"], "name": "T8", "looking_for_skill_names": []},
                        headers=auth(leader_token)).json()
    project = client.post("/api/projects", json={
        "team_id": team["id"], "hackathon_id": h["id"], "name": "Proj8",
    }, headers=auth(leader_token)).json()
    client.post(f"/api/projects/{project['id']}/submit", headers=auth(leader_token))
    client.post("/api/judging/assignments", json={
        "hackathon_id": h["id"], "judge_id": judge_id, "project_id": project["id"],
    }, headers=auth(org_token))
    rubric = client.post("/api/judging/rubrics", json={
        "hackathon_id": h["id"], "criteria": [{"name": "Quality", "weight_percent": 100}],
    }, headers=auth(org_token)).json()
    crit_id = rubric["criteria"][0]["id"]
    client.post("/api/judging/evaluations", json={
        "project_id": project["id"], "scores": [{"criterion_id": crit_id, "score": 8}], "submit_final": True,
    }, headers=auth(judge_token))

    run = client.post("/api/scoring/normalize", json={"hackathon_id": h["id"], "method": "none"},
                       headers=auth(org_token)).json()
    client.post(f"/api/scoring/rank/{run['run_id']}?hackathon_id={h['id']}&publish=true", headers=auth(org_token))
    official_before = client.get(f"/api/scoring/rank/official?hackathon_id={h['id']}").json()

    client.post("/api/scoring/simulate", json={
        "hackathon_id": h["id"], "name": "sim", "exclude_judge_ids": [judge_id],
    }, headers=auth(org_token))

    official_after = client.get(f"/api/scoring/rank/official?hackathon_id={h['id']}").json()
    assert official_before == official_after


def test_draft_projects_are_never_publicly_listed(client):
    """Regression test: the public gallery must never expose another
    team's unsubmitted draft, regardless of query params passed to it."""
    org_token, org_id = register_and_login(client, "org9@test.com", "pass1234", "Org Nine")
    promote_role(org_id, "organizer")
    leader_token, leader_id = register_and_login(client, "lead9@test.com", "pass1234", "Leader Nine")
    outsider_token, _ = register_and_login(client, "outsider9@test.com", "pass1234", "Outsider Nine")

    h = make_hackathon(client, org_token)
    team = client.post("/api/teams", json={"hackathon_id": h["id"], "name": "T9", "looking_for_skill_names": []},
                        headers=auth(leader_token)).json()
    project = client.post("/api/projects", json={
        "team_id": team["id"], "hackathon_id": h["id"], "name": "SecretDraft9",
    }, headers=auth(leader_token)).json()

    # Public/anonymous listing must never show it, no matter what's passed
    r = client.get(f"/api/projects?hackathon_id={h['id']}&status_filter=draft")
    assert r.status_code in (200, 422)  # if the param is accepted it must be ignored, not honored
    if r.status_code == 200:
        assert all(p["name"] != "SecretDraft9" for p in r.json())

    r = client.get("/api/projects")
    assert all(p["name"] != "SecretDraft9" for p in r.json())

    # A non-team-member cannot fetch it via the team-scoped endpoint either
    r = client.get(f"/api/projects/by-team/{team['id']}", headers=auth(outsider_token))
    assert r.status_code == 403

    # The team's own leader can
    r = client.get(f"/api/projects/by-team/{team['id']}", headers=auth(leader_token))
    assert r.status_code == 200
    assert r.json()["name"] == "SecretDraft9"
