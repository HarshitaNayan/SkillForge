import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app import models, security

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("")
def list_audit_log(hackathon_id: Optional[str] = None, action: Optional[str] = None,
                    limit: int = Query(200, le=1000), db: Session = Depends(get_db),
                    user: models.User = Depends(security.require_roles("organizer", "admin"))):
    q = db.query(models.AuditLog)
    if hackathon_id:
        q = q.filter(models.AuditLog.hackathon_id == hackathon_id)
    if action:
        q = q.filter(models.AuditLog.action == action)
    rows = q.order_by(models.AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {"id": r.id, "actor_id": r.actor_id, "actor_role": r.actor_role, "action": r.action,
         "resource_type": r.resource_type, "resource_id": r.resource_id,
         "metadata": json.loads(r.metadata_json or "{}"), "timestamp": r.timestamp.isoformat()}
        for r in rows
    ]
