"""Complementary-skill matching.

This is a deterministic, explainable calculation over real skill data —
not a machine-learning model and not described as "AI" anywhere in the
product. Given a team's declared "looking for" skill list, we score each
candidate participant by how much of that gap they cover, weighted by
their proficiency in each covered skill.
"""
from typing import List, Dict
from sqlalchemy.orm import Session
from app import models


def candidate_users_for_team(db: Session, team: models.Team, exclude_user_ids: set) -> List[models.User]:
    member_ids = {m.user_id for m in team.members} | exclude_user_ids
    return db.query(models.User).filter(
        models.User.role == models.Role.participant,
        ~models.User.id.in_(member_ids) if member_ids else True,
    ).all()


def score_candidate_for_team(db: Session, team: models.Team, candidate: models.User) -> Dict:
    looking_for = {req.skill.name for req in team.requirements}
    if not looking_for:
        return {
            "candidate_id": candidate.id,
            "candidate_name": candidate.full_name,
            "coverage_score": 0.0,
            "matched_skills": [],
            "still_missing": [],
            "reasoning": "This team has not declared any skill gaps yet, so there is nothing to match against.",
        }

    have_rows = [s for s in candidate.skills if s.kind == models.SkillKind.have]
    have_by_name = {r.skill.name: (r.proficiency or 0) for r in have_rows}

    matched = []
    total_weighted = 0.0
    for skill_name in looking_for:
        prof = have_by_name.get(skill_name)
        if prof is not None:
            matched.append(skill_name)
            total_weighted += prof

    still_missing = sorted(looking_for - set(matched))
    # Coverage score: average proficiency across covered gap-skills, scaled by
    # the fraction of the gap that's covered. This rewards both breadth
    # (covering more of the gap) and depth (higher proficiency in what's covered).
    if matched:
        avg_prof_of_matched = total_weighted / len(matched)
        breadth = len(matched) / len(looking_for)
        coverage_score = round(avg_prof_of_matched * breadth, 1)
    else:
        coverage_score = 0.0

    if not matched:
        reasoning = f"No overlap with what this team is looking for ({', '.join(sorted(looking_for))})."
    elif not still_missing:
        reasoning = (
            f"Covers every skill the team is looking for ({', '.join(sorted(matched))}) "
            f"at an average proficiency of {avg_prof_of_matched:.0f}%. Strong complementary skill coverage."
        )
    else:
        reasoning = (
            f"Covers {len(matched)} of {len(looking_for)} needed skills "
            f"({', '.join(sorted(matched))}) at an average proficiency of {avg_prof_of_matched:.0f}%; "
            f"still missing {', '.join(still_missing)}."
        )

    return {
        "candidate_id": candidate.id,
        "candidate_name": candidate.full_name,
        "coverage_score": coverage_score,
        "matched_skills": sorted(matched),
        "still_missing": still_missing,
        "reasoning": reasoning,
    }


def rank_candidates_for_team(db: Session, team: models.Team, limit: int = 20) -> List[Dict]:
    exclude = {m.user_id for m in team.members}
    candidates = candidate_users_for_team(db, team, exclude)
    scored = [score_candidate_for_team(db, team, c) for c in candidates]
    scored.sort(key=lambda x: x["coverage_score"], reverse=True)
    return scored[:limit]


def team_skill_coverage(team: models.Team) -> Dict:
    """Aggregate skill coverage across all current team members, plus the
    team's declared gaps ("looking for") that remain unmet.
    """
    covered = {}  # skill_name -> {"max_proficiency": int, "members": [names]}
    for member in team.members:
        for us in member.user.skills:
            if us.kind != models.SkillKind.have:
                continue
            name = us.skill.name
            entry = covered.setdefault(name, {"max_proficiency": 0, "members": []})
            entry["max_proficiency"] = max(entry["max_proficiency"], us.proficiency or 0)
            entry["members"].append({"name": member.user.full_name, "proficiency": us.proficiency})

    looking_for = [r.skill.name for r in team.requirements]
    missing = [s for s in looking_for if s not in covered]

    return {
        "covered": covered,
        "missing": missing,
    }
