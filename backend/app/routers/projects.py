from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app import models, schemas, security
from app.audit import log_event
from app.deadlines import assert_before_submission_deadline

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _require_team_member(db: Session, team_id: str, user: models.User):
    if user.role == models.Role.admin:
        return
    m = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team_id, models.TeamMember.user_id == user.id
    ).first()
    if not m:
        raise HTTPException(status_code=403, detail="Only members of this project's team can do that")


def _get_project_or_404(db: Session, project_id: str) -> models.Project:
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")
    return p


@router.get("", response_model=List[schemas.ProjectOut])
def list_projects(hackathon_id: Optional[str] = None, q: Optional[str] = None, db: Session = Depends(get_db)):
    """Public gallery listing — submitted/locked projects only. There is no
    status_filter override here: draft projects are never visible to anyone
    outside their own team (see /projects/by-team/{team_id} for that)."""
    query = db.query(models.Project).filter(
        models.Project.status.in_([models.ProjectStatus.submitted, models.ProjectStatus.locked])
    )
    if hackathon_id:
        query = query.filter(models.Project.hackathon_id == hackathon_id)
    if q:
        query = query.filter(models.Project.name.ilike(f"%{q}%"))
    return query.order_by(models.Project.created_at.desc()).all()


@router.get("/by-team/{team_id}", response_model=Optional[schemas.ProjectOut])
def get_project_by_team(team_id: str, db: Session = Depends(get_db),
                         user: models.User = Depends(security.get_current_user)):
    """Lets a team see its own project regardless of status (including
    drafts). Only team members and organizers/admins may call this --
    unlike the public gallery, which never exposes drafts."""
    _require_team_member(db, team_id, user)
    return db.query(models.Project).filter(models.Project.team_id == team_id).first()


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return _get_project_or_404(db, project_id)


@router.post("", response_model=schemas.ProjectOut)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db),
                    user: models.User = Depends(security.require_roles("participant"))):
    _require_team_member(db, payload.team_id, user)
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == payload.hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    existing = db.query(models.Project).filter(models.Project.team_id == payload.team_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="This team already has a project")
    p = models.Project(**payload.model_dump())
    db.add(p)
    db.flush()
    log_event(db, user, "project.create_draft", "project", p.id, {"name": p.name}, hackathon_id=p.hackathon_id)
    db.commit()
    db.refresh(p)
    return p


@router.patch("/{project_id}", response_model=schemas.ProjectOut)
def update_project(project_id: str, payload: schemas.ProjectUpdate, db: Session = Depends(get_db),
                    user: models.User = Depends(security.get_current_user)):
    p = _get_project_or_404(db, project_id)
    _require_team_member(db, p.team_id, user)
    if p.status == models.ProjectStatus.locked:
        raise HTTPException(status_code=403, detail="Project is locked and can no longer be edited")
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == p.hackathon_id).first()
    assert_before_submission_deadline(hackathon)

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(p, k, v)
    log_event(db, user, "project.edit_draft", "project", p.id, {"fields": list(data.keys())}, hackathon_id=p.hackathon_id)
    db.commit()
    db.refresh(p)
    return p


@router.post("/{project_id}/submit", response_model=schemas.ProjectOut)
def submit_project(project_id: str, db: Session = Depends(get_db),
                    user: models.User = Depends(security.get_current_user)):
    p = _get_project_or_404(db, project_id)
    _require_team_member(db, p.team_id, user)
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == p.hackathon_id).first()
    assert_before_submission_deadline(hackathon)
    if p.status == models.ProjectStatus.locked:
        raise HTTPException(status_code=403, detail="Project is already locked")

    p.status = models.ProjectStatus.submitted
    p.submitted_at = datetime.utcnow()
    log_event(db, user, "project.submit", "project", p.id, {}, hackathon_id=p.hackathon_id)
    db.commit()
    db.refresh(p)
    return p


def lock_expired_submissions(db: Session, hackathon: models.Hackathon):
    """Called by the deadline sweep / organizer views: once a submission
    deadline has passed, submitted projects transition to LOCKED so no
    further edits are possible even if a client races the deadline check."""
    if datetime.utcnow() <= hackathon.submission_deadline:
        return
    projects = db.query(models.Project).filter(
        models.Project.hackathon_id == hackathon.id,
        models.Project.status == models.ProjectStatus.submitted,
    ).all()
    for p in projects:
        p.status = models.ProjectStatus.locked
        log_event(db, None, "project.auto_lock", "project", p.id, {"reason": "deadline_passed"},
                   hackathon_id=hackathon.id)


# ---------- Claims ----------
@router.post("/{project_id}/claims", response_model=schemas.ClaimOut)
def add_claim(project_id: str, payload: schemas.ClaimCreate, db: Session = Depends(get_db),
              user: models.User = Depends(security.get_current_user)):
    p = _get_project_or_404(db, project_id)
    _require_team_member(db, p.team_id, user)
    if p.status == models.ProjectStatus.locked:
        raise HTTPException(status_code=403, detail="Project is locked")
    claim = models.ProjectClaim(project_id=project_id, title=payload.title, description=payload.description)
    db.add(claim)
    log_event(db, user, "claim.create", "claim", claim.id, {"title": payload.title}, hackathon_id=p.hackathon_id)
    db.commit()
    db.refresh(claim)
    return claim


@router.delete("/{project_id}/claims/{claim_id}")
def delete_claim(project_id: str, claim_id: str, db: Session = Depends(get_db),
                  user: models.User = Depends(security.get_current_user)):
    p = _get_project_or_404(db, project_id)
    _require_team_member(db, p.team_id, user)
    if p.status == models.ProjectStatus.locked:
        raise HTTPException(status_code=403, detail="Project is locked")
    claim = db.query(models.ProjectClaim).filter(
        models.ProjectClaim.id == claim_id, models.ProjectClaim.project_id == project_id
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    db.delete(claim)
    log_event(db, user, "claim.delete", "claim", claim_id, {}, hackathon_id=p.hackathon_id)
    db.commit()
    return {"ok": True}


# ---------- Evidence ----------
@router.post("/{project_id}/claims/{claim_id}/evidence", response_model=schemas.EvidenceOut)
def add_evidence(project_id: str, claim_id: str, payload: schemas.EvidenceIn, db: Session = Depends(get_db),
                  user: models.User = Depends(security.get_current_user)):
    p = _get_project_or_404(db, project_id)
    _require_team_member(db, p.team_id, user)
    if p.status == models.ProjectStatus.locked:
        raise HTTPException(status_code=403, detail="Project is locked")
    claim = db.query(models.ProjectClaim).filter(
        models.ProjectClaim.id == claim_id, models.ProjectClaim.project_id == project_id
    ).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    ev = models.ClaimEvidence(claim_id=claim_id, type=models.EvidenceType(payload.type), content=payload.content)
    db.add(ev)
    log_event(db, user, "evidence.add", "evidence", ev.id, {"type": payload.type}, hackathon_id=p.hackathon_id)
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/{project_id}/claims/{claim_id}/evidence/{evidence_id}")
def delete_evidence(project_id: str, claim_id: str, evidence_id: str, db: Session = Depends(get_db),
                     user: models.User = Depends(security.get_current_user)):
    p = _get_project_or_404(db, project_id)
    _require_team_member(db, p.team_id, user)
    if p.status == models.ProjectStatus.locked:
        raise HTTPException(status_code=403, detail="Project is locked")
    ev = db.query(models.ClaimEvidence).filter(
        models.ClaimEvidence.id == evidence_id, models.ClaimEvidence.claim_id == claim_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence not found")
    db.delete(ev)
    log_event(db, user, "evidence.delete", "evidence", evidence_id, {}, hackathon_id=p.hackathon_id)
    db.commit()
    return {"ok": True}
