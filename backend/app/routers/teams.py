from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas, security
from app.audit import log_event
from app.deadlines import assert_before_registration_deadline
from app.services import matching

router = APIRouter(prefix="/api/teams", tags=["teams"])


def _team_to_out(team: models.Team) -> schemas.TeamOut:
    return schemas.TeamOut(
        id=team.id,
        hackathon_id=team.hackathon_id,
        name=team.name,
        members=[
            schemas.TeamMemberOut(user_id=m.user_id, full_name=m.user.full_name, is_leader=m.is_leader)
            for m in team.members
        ],
        looking_for=[r.skill.name for r in team.requirements],
    )


@router.get("", response_model=List[schemas.TeamOut])
def list_teams(hackathon_id: str, db: Session = Depends(get_db)):
    teams = db.query(models.Team).filter(models.Team.hackathon_id == hackathon_id).all()
    return [_team_to_out(t) for t in teams]


@router.get("/{team_id}", response_model=schemas.TeamOut)
def get_team(team_id: str, db: Session = Depends(get_db)):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return _team_to_out(team)


@router.get("/{team_id}/coverage")
def get_team_coverage(team_id: str, db: Session = Depends(get_db)):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return matching.team_skill_coverage(team)


@router.get("/{team_id}/matches")
def get_team_matches(team_id: str, db: Session = Depends(get_db),
                      user: models.User = Depends(security.get_current_user)):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return matching.rank_candidates_for_team(db, team)


@router.post("", response_model=schemas.TeamOut)
def create_team(payload: schemas.TeamCreate, db: Session = Depends(get_db),
                 user: models.User = Depends(security.require_roles("participant"))):
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == payload.hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    assert_before_registration_deadline(hackathon)

    existing = db.query(models.TeamMember).join(models.Team).filter(
        models.Team.hackathon_id == payload.hackathon_id, models.TeamMember.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You are already on a team for this hackathon")

    team = models.Team(hackathon_id=payload.hackathon_id, name=payload.name, created_by=user.id)
    db.add(team)
    db.flush()
    db.add(models.TeamMember(team_id=team.id, user_id=user.id, is_leader=True))
    for skill_name in payload.looking_for_skill_names:
        skill = db.query(models.Skill).filter(models.Skill.name == skill_name).first()
        if not skill:
            skill = models.Skill(name=skill_name)
            db.add(skill)
            db.flush()
        db.add(models.TeamSkillRequirement(team_id=team.id, skill_id=skill.id))
    log_event(db, user, "team.create", "team", team.id, {"name": team.name}, hackathon_id=team.hackathon_id)
    db.commit()
    db.refresh(team)
    return _team_to_out(team)


@router.post("/{team_id}/join", response_model=schemas.TeamOut)
def join_team(team_id: str, db: Session = Depends(get_db),
              user: models.User = Depends(security.require_roles("participant"))):
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == team.hackathon_id).first()
    assert_before_registration_deadline(hackathon)

    already_on_team = db.query(models.TeamMember).join(models.Team).filter(
        models.Team.hackathon_id == team.hackathon_id, models.TeamMember.user_id == user.id
    ).first()
    if already_on_team:
        raise HTTPException(status_code=400, detail="You are already on a team for this hackathon")

    if len(team.members) >= hackathon.max_team_size:
        raise HTTPException(status_code=400, detail=f"Team is at its size limit ({hackathon.max_team_size})")

    db.add(models.TeamMember(team_id=team.id, user_id=user.id))
    log_event(db, user, "team.join", "team", team.id, {}, hackathon_id=team.hackathon_id)
    db.commit()
    db.refresh(team)
    return _team_to_out(team)


@router.post("/{team_id}/leave")
def leave_team(team_id: str, db: Session = Depends(get_db),
                user: models.User = Depends(security.get_current_user)):
    membership = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team_id, models.TeamMember.user_id == user.id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="You are not a member of this team")

    project_exists = db.query(models.Project).filter(
        models.Project.team_id == team_id, models.Project.status != models.ProjectStatus.draft
    ).first()
    if project_exists:
        raise HTTPException(status_code=403, detail="Cannot leave a team that has already submitted a project")

    team_id_val = membership.team_id
    db.delete(membership)
    log_event(db, user, "team.leave", "team", team_id_val, {})
    db.commit()
    return {"ok": True}
