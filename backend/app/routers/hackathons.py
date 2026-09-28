from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas, security
from app.audit import log_event

router = APIRouter(prefix="/api/hackathons", tags=["hackathons"])


@router.get("", response_model=List[schemas.HackathonOut])
def list_hackathons(db: Session = Depends(get_db)):
    return db.query(models.Hackathon).order_by(models.Hackathon.created_at.desc()).all()


@router.get("/{hackathon_id}", response_model=schemas.HackathonOut)
def get_hackathon(hackathon_id: str, db: Session = Depends(get_db)):
    h = db.query(models.Hackathon).filter(models.Hackathon.id == hackathon_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    return h


@router.post("", response_model=schemas.HackathonOut)
def create_hackathon(payload: schemas.HackathonCreate, db: Session = Depends(get_db),
                      user: models.User = Depends(security.require_roles("organizer"))):
    h = models.Hackathon(**payload.model_dump(), created_by=user.id)
    db.add(h)
    db.flush()
    log_event(db, user, "hackathon.create", "hackathon", h.id, {"name": h.name}, hackathon_id=h.id)
    db.commit()
    db.refresh(h)
    return h


@router.patch("/{hackathon_id}", response_model=schemas.HackathonOut)
def update_hackathon(hackathon_id: str, payload: schemas.HackathonUpdate, db: Session = Depends(get_db),
                      user: models.User = Depends(security.require_roles("organizer"))):
    h = db.query(models.Hackathon).filter(models.Hackathon.id == hackathon_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    data = payload.model_dump(exclude_unset=True)
    if "status" in data:
        h.status = models.HackathonStatus(data.pop("status"))
    for k, v in data.items():
        setattr(h, k, v)
    log_event(db, user, "hackathon.update", "hackathon", h.id, {"fields": list(data.keys())}, hackathon_id=h.id)
    db.commit()
    db.refresh(h)
    return h
