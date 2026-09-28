from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app import models, schemas, security

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=List[schemas.UserOut])
def list_users(role: Optional[str] = None, db: Session = Depends(get_db),
               user: models.User = Depends(security.require_roles("organizer", "admin"))):
    q = db.query(models.User)
    if role:
        q = q.filter(models.User.role == models.Role(role))
    return q.order_by(models.User.full_name).all()
