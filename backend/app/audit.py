import json
from sqlalchemy.orm import Session
from app import models


def log_event(db: Session, actor, action: str, resource_type: str, resource_id: str = None,
              metadata: dict = None, hackathon_id: str = None):
    """Writes an immutable audit record. Called synchronously in the same
    transaction as the action it records, so an audit entry always exists
    if the underlying action committed.
    """
    entry = models.AuditLog(
        actor_id=getattr(actor, "id", None),
        actor_role=getattr(actor, "role", None).value if getattr(actor, "role", None) else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=json.dumps(metadata or {}, default=str),
        hackathon_id=hackathon_id,
    )
    db.add(entry)
    return entry
