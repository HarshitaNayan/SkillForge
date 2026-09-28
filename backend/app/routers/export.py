import csv
import io
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, security
from app.audit import log_event

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/rankings.csv")
def export_rankings_csv(hackathon_id: str, db: Session = Depends(get_db),
                         user: models.User = Depends(security.require_roles("organizer"))):
    rows = db.query(models.Ranking).filter(
        models.Ranking.hackathon_id == hackathon_id, models.Ranking.is_official == True  # noqa: E712
    ).order_by(models.Ranking.rank).all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["rank", "project_id", "project_name", "final_score", "raw_score", "normalized_score",
                      "num_evaluations", "method"])
    for r in rows:
        norm = db.query(models.NormalizedScore).filter(
            models.NormalizedScore.run_id == r.run_id, models.NormalizedScore.project_id == r.project_id
        ).first()
        project = db.query(models.Project).filter(models.Project.id == r.project_id).first()
        writer.writerow([
            r.rank, r.project_id, project.name if project else "", r.final_score,
            norm.raw_score if norm else "", norm.normalized_score if norm else "",
            norm.num_evaluations if norm else "", norm.method if norm else "",
        ])

    log_event(db, user, "export.rankings_csv", "hackathon", hackathon_id, {"rows": len(rows)}, hackathon_id=hackathon_id)
    db.commit()

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=skillforge_rankings_{hackathon_id[:8]}.csv"},
    )
