from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas, security
from app.audit import log_event

router = APIRouter(prefix="/api/community", tags=["community"])


@router.post("/projects/{project_id}/vote")
def cast_vote(project_id: str, db: Session = Depends(get_db),
              user: models.User = Depends(security.get_current_user)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    existing = db.query(models.Vote).filter(
        models.Vote.project_id == project_id, models.Vote.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already voted for this project")
    v = models.Vote(project_id=project_id, user_id=user.id)
    db.add(v)
    log_event(db, user, "vote.cast", "project", project_id, {}, hackathon_id=project.hackathon_id)
    db.commit()
    count = db.query(models.Vote).filter(models.Vote.project_id == project_id).count()
    return {"ok": True, "vote_count": count}


@router.get("/projects/{project_id}/votes")
def vote_count(project_id: str, db: Session = Depends(get_db)):
    count = db.query(models.Vote).filter(models.Vote.project_id == project_id).count()
    return {"project_id": project_id, "vote_count": count}


@router.post("/projects/{project_id}/comments")
def add_comment(project_id: str, content: str, db: Session = Depends(get_db),
                 user: models.User = Depends(security.get_current_user)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    c = models.Comment(project_id=project_id, user_id=user.id, content=content)
    db.add(c)
    log_event(db, user, "comment.add", "project", project_id, {}, hackathon_id=project.hackathon_id)
    db.commit()
    db.refresh(c)
    return {"id": c.id, "content": c.content, "author": user.full_name, "created_at": c.created_at.isoformat()}


@router.get("/projects/{project_id}/comments")
def list_comments(project_id: str, db: Session = Depends(get_db)):
    rows = db.query(models.Comment).filter(models.Comment.project_id == project_id).order_by(
        models.Comment.created_at
    ).all()
    return [
        {"id": c.id, "content": c.content, "author": c.user.full_name, "created_at": c.created_at.isoformat()}
        for c in rows
    ]
