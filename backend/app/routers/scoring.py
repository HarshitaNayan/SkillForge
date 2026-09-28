import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app import models, schemas, security
from app.audit import log_event
from app.services import scoring

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


@router.post("/normalize")
def run_normalization(payload: schemas.NormalizationRunRequest, db: Session = Depends(get_db),
                       user: models.User = Depends(security.require_roles("organizer"))):
    evals = scoring.collect_locked_evaluations(db, payload.hackathon_id)
    if not evals:
        raise HTTPException(status_code=400, detail="No locked evaluations exist yet for this hackathon")
    run_id = scoring.run_normalization(db, payload.hackathon_id, method=payload.method)
    log_event(db, user, "normalization.run", "hackathon", payload.hackathon_id,
              {"run_id": run_id, "method": payload.method, "num_evaluations": len(evals)},
              hackathon_id=payload.hackathon_id)
    db.commit()
    rows = db.query(models.NormalizedScore).filter(models.NormalizedScore.run_id == run_id).all()
    return {
        "run_id": run_id,
        "method": payload.method,
        "scores": [
            {"project_id": r.project_id, "raw_score": r.raw_score, "normalized_score": r.normalized_score,
             "final_score": r.final_score, "num_evaluations": r.num_evaluations}
            for r in rows
        ],
    }


@router.post("/rank/{run_id}")
def compute_ranking(run_id: str, hackathon_id: str, publish: bool = False, db: Session = Depends(get_db),
                     user: models.User = Depends(security.require_roles("organizer"))):
    existing = db.query(models.NormalizedScore).filter(models.NormalizedScore.run_id == run_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Unknown normalization run_id")
    if publish:
        # Unpublish/unofficial-ize any previous official ranking for this hackathon
        db.query(models.Ranking).filter(
            models.Ranking.hackathon_id == hackathon_id, models.Ranking.is_official == True  # noqa: E712
        ).update({"is_official": False, "published": False})
    ranking = scoring.build_ranking(db, hackathon_id, run_id, mark_official=publish)
    log_event(db, user, "ranking.generate" if not publish else "ranking.publish", "hackathon", hackathon_id,
              {"run_id": run_id, "published": publish}, hackathon_id=hackathon_id)
    db.commit()
    return ranking


@router.get("/rank/official")
def official_ranking(hackathon_id: str, db: Session = Depends(get_db)):
    return scoring.get_official_ranking(db, hackathon_id)


@router.get("/why/{project_id}")
def why_this_score(project_id: str, hackathon_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    latest_norm = db.query(models.NormalizedScore).filter(
        models.NormalizedScore.project_id == project_id
    ).order_by(models.NormalizedScore.computed_at.desc()).first()

    evaluations = db.query(models.Evaluation).filter(
        models.Evaluation.project_id == project_id, models.Evaluation.locked == True  # noqa: E712
    ).all()

    raw_judge_scores = []
    criterion_totals = {}
    for e in evaluations:
        ws = scoring.weighted_score_for_evaluation(e)
        raw_judge_scores.append({"judge_id": e.judge_id, "weighted_score": ws})
        for s in e.scores:
            crit = s.criterion
            bucket = criterion_totals.setdefault(crit.name, {"weight_percent": crit.weight_percent, "scores": []})
            bucket["scores"].append(s.score)

    criterion_breakdown = [
        {"criterion": name, "weight_percent": d["weight_percent"],
         "average_score": round(sum(d["scores"]) / len(d["scores"]), 2) if d["scores"] else None,
         "num_scores": len(d["scores"])}
        for name, d in criterion_totals.items()
    ]

    audit_events = db.query(models.AuditLog).filter(
        models.AuditLog.resource_id == project_id
    ).order_by(models.AuditLog.timestamp).all()
    audit_out = [{"action": a.action, "timestamp": a.timestamp.isoformat(), "actor_role": a.actor_role}
                 for a in audit_events]

    return schemas.WhyScoreOut(
        project_id=project_id,
        project_name=project.name,
        num_evaluations=len(evaluations),
        criterion_breakdown=criterion_breakdown,
        raw_judge_scores=raw_judge_scores,
        weighted_raw_score=latest_norm.raw_score if latest_norm else (
            round(sum(x["weighted_score"] for x in raw_judge_scores) / len(raw_judge_scores), 4)
            if raw_judge_scores else 0.0
        ),
        normalized_score=latest_norm.normalized_score if latest_norm else 0.0,
        final_score=latest_norm.final_score if latest_norm else 0.0,
        normalization_method=latest_norm.method if latest_norm else "not yet computed",
        audit_events=audit_out,
    )


# ---------- Ranking Lab (what-if simulations) ----------
@router.post("/simulate")
def run_simulation(payload: schemas.SimulationRequest, db: Session = Depends(get_db),
                    user: models.User = Depends(security.require_roles("organizer"))):
    official = scoring.get_official_ranking(db, payload.hackathon_id)
    official_rank_by_project = {r["project_id"]: r["rank"] for r in official}

    sim_scores = scoring.compute_project_scores(
        db, payload.hackathon_id, method=payload.method,
        exclude_judge_ids=set(payload.exclude_judge_ids),
        exclude_evaluation_ids=set(payload.exclude_evaluation_ids),
        weight_overrides=payload.weight_overrides,
    )
    ranked = sorted(sim_scores.items(), key=lambda kv: kv[1]["final"], reverse=True)
    sim_ranking = []
    positions_changed = 0
    for i, (project_id, r) in enumerate(ranked, start=1):
        project = db.query(models.Project).filter(models.Project.id == project_id).first()
        old_rank = official_rank_by_project.get(project_id)
        if old_rank is not None and old_rank != i:
            positions_changed += 1
        sim_ranking.append({
            "rank": i, "project_id": project_id, "project_name": project.name if project else "?",
            "final_score": r["final"], "official_rank": old_rank,
        })

    diff_summary = f"{positions_changed} ranking position(s) changed vs. the official ranking." if official else \
        "No official ranking exists yet to compare against."

    sim = models.RankingSimulation(
        hackathon_id=payload.hackathon_id, name=payload.name,
        config_json=json.dumps(payload.model_dump()),
        result_json=json.dumps(sim_ranking),
        diff_summary=diff_summary,
        created_by=user.id,
    )
    db.add(sim)
    db.flush()
    log_event(db, user, "simulation.run", "ranking_simulation", sim.id,
              {"name": payload.name, "diff_summary": diff_summary}, hackathon_id=payload.hackathon_id)
    db.commit()

    return {
        "simulation_id": sim.id,
        "official_ranking": official,
        "simulated_ranking": sim_ranking,
        "diff_summary": diff_summary,
    }


@router.get("/simulations")
def list_simulations(hackathon_id: str, db: Session = Depends(get_db),
                      user: models.User = Depends(security.require_roles("organizer"))):
    sims = db.query(models.RankingSimulation).filter(
        models.RankingSimulation.hackathon_id == hackathon_id
    ).order_by(models.RankingSimulation.created_at.desc()).all()
    return [
        {"id": s.id, "name": s.name, "diff_summary": s.diff_summary, "created_at": s.created_at.isoformat(),
         "config": json.loads(s.config_json), "result": json.loads(s.result_json)}
        for s in sims
    ]


# ---------- Ranking Replay ----------
@router.get("/replay")
def ranking_replay(hackathon_id: str, db: Session = Depends(get_db)):
    """Reconstructs the actual sequence of stored events that produced the
    current official ranking, straight from the audit log — not a
    scripted animation."""
    relevant_actions = [
        "project.submit", "project.auto_lock", "judge.assign", "evaluation.lock",
        "rubric.create", "normalization.run", "ranking.generate", "ranking.publish",
    ]
    events = db.query(models.AuditLog).filter(
        models.AuditLog.hackathon_id == hackathon_id, models.AuditLog.action.in_(relevant_actions)
    ).order_by(models.AuditLog.timestamp).all()
    return [
        {"action": e.action, "resource_type": e.resource_type, "resource_id": e.resource_id,
         "timestamp": e.timestamp.isoformat(), "metadata": json.loads(e.metadata_json or "{}")}
        for e in events
    ]


# ---------- Judging Observatory ----------
@router.get("/observatory")
def observatory(hackathon_id: str, db: Session = Depends(get_db),
                 user: models.User = Depends(security.require_roles("organizer"))):
    total_submissions = db.query(models.Project).filter(
        models.Project.hackathon_id == hackathon_id,
        models.Project.status.in_([models.ProjectStatus.submitted, models.ProjectStatus.locked]),
    ).count()
    total_assignments = db.query(models.JudgeAssignment).filter(
        models.JudgeAssignment.hackathon_id == hackathon_id
    ).count()
    total_evaluations = db.query(models.Evaluation).filter(
        models.Evaluation.hackathon_id == hackathon_id
    ).count()
    completed_evaluations = db.query(models.Evaluation).filter(
        models.Evaluation.hackathon_id == hackathon_id, models.Evaluation.locked == True  # noqa: E712
    ).count()
    pending = max(total_assignments - completed_evaluations, 0)

    judges = db.query(models.User).filter(models.User.role == models.Role.judge).all()
    judge_dist = []
    for j in judges:
        evals = db.query(models.Evaluation).filter(
            models.Evaluation.judge_id == j.id, models.Evaluation.hackathon_id == hackathon_id,
            models.Evaluation.locked == True,  # noqa: E712
        ).all()
        if not evals:
            continue
        weighted = [scoring.weighted_score_for_evaluation(e) for e in evals]
        judge_dist.append({
            "judge_id": j.id, "judge_name": j.full_name, "count": len(weighted),
            "average": round(sum(weighted) / len(weighted), 2), "min": round(min(weighted), 2),
            "max": round(max(weighted), 2),
        })

    latest_norm = db.query(models.NormalizedScore).filter(
        models.NormalizedScore.hackathon_id == hackathon_id
    ).order_by(models.NormalizedScore.computed_at.desc()).first()

    return {
        "total_submissions": total_submissions,
        "total_assignments": total_assignments,
        "total_evaluations": total_evaluations,
        "completed_evaluations": completed_evaluations,
        "pending_evaluations": pending,
        "assignment_coverage_percent": round(100 * completed_evaluations / total_assignments, 1) if total_assignments else 0.0,
        "judge_score_distributions": judge_dist,
        "normalization_last_run": latest_norm.computed_at.isoformat() if latest_norm else None,
        "normalization_method": latest_norm.method if latest_norm else None,
    }
