from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas, security
from app.audit import log_event

router = APIRouter(prefix="/api", tags=["skills"])


@router.get("/skills", response_model=List[schemas.SkillOut])
def list_skills(db: Session = Depends(get_db)):
    return db.query(models.Skill).order_by(models.Skill.name).all()


@router.post("/skills", response_model=schemas.SkillOut)
def create_skill(payload: schemas.SkillCreate, db: Session = Depends(get_db),
                  user: models.User = Depends(security.require_roles("organizer"))):
    existing = db.query(models.Skill).filter(models.Skill.name == payload.name).first()
    if existing:
        return existing
    skill = models.Skill(name=payload.name, category=payload.category)
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/users/me/skills", response_model=List[schemas.UserSkillOut])
def my_skills(db: Session = Depends(get_db), user: models.User = Depends(security.get_current_user)):
    rows = db.query(models.UserSkill).filter(models.UserSkill.user_id == user.id).all()
    return [
        schemas.UserSkillOut(skill_name=r.skill.name, kind=r.kind.value, proficiency=r.proficiency)
        for r in rows
    ]


@router.put("/users/me/skills", response_model=List[schemas.UserSkillOut])
def set_my_skills(payload: List[schemas.UserSkillIn], db: Session = Depends(get_db),
                   user: models.User = Depends(security.get_current_user)):
    """Replaces the caller's full skill profile (have + want) with the given list."""
    db.query(models.UserSkill).filter(models.UserSkill.user_id == user.id).delete()
    for item in payload:
        skill = db.query(models.Skill).filter(models.Skill.name == item.skill_name).first()
        if not skill:
            skill = models.Skill(name=item.skill_name)
            db.add(skill)
            db.flush()
        if item.kind == "have" and item.proficiency is None:
            raise HTTPException(status_code=422, detail=f"proficiency is required for skill '{item.skill_name}'")
        us = models.UserSkill(user_id=user.id, skill_id=skill.id, kind=models.SkillKind(item.kind),
                               proficiency=item.proficiency if item.kind == "have" else None)
        db.add(us)
    log_event(db, user, "skills.update", "user", user.id, {"count": len(payload)})
    db.commit()
    rows = db.query(models.UserSkill).filter(models.UserSkill.user_id == user.id).all()
    return [schemas.UserSkillOut(skill_name=r.skill.name, kind=r.kind.value, proficiency=r.proficiency) for r in rows]
