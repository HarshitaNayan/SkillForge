from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app import models, schemas, security
from app.audit import log_event
from app.deadlines import assert_before_submission_deadline

router = APIRouter(prefix="/api/judging", tags=["judging"])


# ---------- Assignments ----------
@router.post("/assignments", response_model=schemas.AssignmentOut)
def create_assignment(payload: schemas.AssignmentCreate, db: Session = Depends(get_db),
                       user: models.User = Depends(security.require_roles("organizer"))):
    judge = db.query(models.User).filter(models.User.id == payload.judge_id).first()
    if not judge or judge.role != models.Role.judge:
        raise HTTPException(status_code=400, detail="Target user is not a registered judge")
    project = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    conflict = db.query(models.JudgeConflict).filter(
        models.JudgeConflict.judge_id == payload.judge_id, models.JudgeConflict.project_id == payload.project_id
    ).first()
    if conflict:
        raise HTTPException(status_code=400, detail="Cannot assign: judge has a declared conflict of interest with this project")

    existing = db.query(models.JudgeAssignment).filter(
        models.JudgeAssignment.judge_id == payload.judge_id, models.JudgeAssignment.project_id == payload.project_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Judge is already assigned to this project")

    a = models.JudgeAssignment(hackathon_id=payload.hackathon_id, judge_id=payload.judge_id,
                                project_id=payload.project_id, assigned_by=user.id)
    db.add(a)
    log_event(db, user, "judge.assign", "assignment", a.id,
              {"judge_id": payload.judge_id, "project_id": payload.project_id}, hackathon_id=payload.hackathon_id)
    db.commit()
    db.refresh(a)
    return a


@router.delete("/assignments/{assignment_id}")
def remove_assignment(assignment_id: str, db: Session = Depends(get_db),
                       user: models.User = Depends(security.require_roles("organizer"))):
    a = db.query(models.JudgeAssignment).filter(models.JudgeAssignment.id == assignment_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Assignment not found")
    locked_eval = db.query(models.Evaluation).filter(
        models.Evaluation.assignment_id == assignment_id, models.Evaluation.locked == True  # noqa: E712
    ).first()
    if locked_eval:
        raise HTTPException(status_code=403, detail="Cannot remove an assignment with a locked evaluation")
    hackathon_id = a.hackathon_id
    db.delete(a)
    log_event(db, user, "judge.unassign", "assignment", assignment_id, {}, hackathon_id=hackathon_id)
    db.commit()
    return {"ok": True}


@router.get("/assignments", response_model=List[schemas.AssignmentOut])
def list_assignments(hackathon_id: str, db: Session = Depends(get_db),
                      user: models.User = Depends(security.require_roles("organizer", "judge"))):
    q = db.query(models.JudgeAssignment).filter(models.JudgeAssignment.hackathon_id == hackathon_id)
    if user.role == models.Role.judge:
        q = q.filter(models.JudgeAssignment.judge_id == user.id)
    return q.all()


# ---------- Conflicts of interest ----------
@router.post("/conflicts", response_model=schemas.ConflictOut)
def declare_conflict(payload: schemas.ConflictCreate, db: Session = Depends(get_db),
                      user: models.User = Depends(security.require_roles("organizer", "judge"))):
    if user.role == models.Role.judge and user.id != payload.judge_id:
        raise HTTPException(status_code=403, detail="Judges may only declare their own conflicts")
    existing = db.query(models.JudgeConflict).filter(
        models.JudgeConflict.judge_id == payload.judge_id, models.JudgeConflict.project_id == payload.project_id
    ).first()
    if existing:
        return existing
    c = models.JudgeConflict(hackathon_id=payload.hackathon_id, judge_id=payload.judge_id,
                              project_id=payload.project_id, reason=payload.reason, declared_by=user.id)
    db.add(c)
    db.flush()
    # Enforcement: remove any existing assignment for this judge/project pair,
    # and block that judge's evaluation from counting if one already exists.
    assignment = db.query(models.JudgeAssignment).filter(
        models.JudgeAssignment.judge_id == payload.judge_id, models.JudgeAssignment.project_id == payload.project_id
    ).first()
    if assignment:
        db.delete(assignment)
    log_event(db, user, "conflict.declare", "conflict", c.id,
              {"judge_id": payload.judge_id, "project_id": payload.project_id, "reason": payload.reason},
              hackathon_id=payload.hackathon_id)
    db.commit()
    db.refresh(c)
    return c


@router.get("/conflicts", response_model=List[schemas.ConflictOut])
def list_conflicts(hackathon_id: str, db: Session = Depends(get_db),
                    user: models.User = Depends(security.require_roles("organizer"))):
    return db.query(models.JudgeConflict).filter(models.JudgeConflict.hackathon_id == hackathon_id).all()


# ---------- Rubrics ----------
@router.post("/rubrics", response_model=schemas.RubricOut)
def create_rubric(payload: schemas.RubricCreate, db: Session = Depends(get_db),
                   user: models.User = Depends(security.require_roles("organizer"))):
    # Deactivate any previous active rubric for this hackathon (only one active at a time)
    db.query(models.Rubric).filter(
        models.Rubric.hackathon_id == payload.hackathon_id, models.Rubric.is_active == True  # noqa: E712
    ).update({"is_active": False})

    rubric = models.Rubric(hackathon_id=payload.hackathon_id, name=payload.name, is_active=True)
    db.add(rubric)
    db.flush()
    for idx, c in enumerate(payload.criteria):
        db.add(models.RubricCriterion(rubric_id=rubric.id, name=c.name, weight_percent=c.weight_percent, order_index=idx))
    log_event(db, user, "rubric.create", "rubric", rubric.id,
              {"criteria": [c.name for c in payload.criteria]}, hackathon_id=payload.hackathon_id)
    db.commit()
    db.refresh(rubric)
    return rubric


@router.get("/rubrics/active", response_model=schemas.RubricOut)
def get_active_rubric(hackathon_id: str, db: Session = Depends(get_db)):
    rubric = db.query(models.Rubric).filter(
        models.Rubric.hackathon_id == hackathon_id, models.Rubric.is_active == True  # noqa: E712
    ).first()
    if not rubric:
        raise HTTPException(status_code=404, detail="No active rubric configured for this hackathon yet")
    return rubric


# ---------- Evaluations ----------
def _assert_can_judge(db: Session, judge: models.User, project: models.Project):
    assignment = db.query(models.JudgeAssignment).filter(
        models.JudgeAssignment.judge_id == judge.id, models.JudgeAssignment.project_id == project.id
    ).first()
    if not assignment:
        raise HTTPException(status_code=403, detail="You are not assigned to judge this project")
    conflict = db.query(models.JudgeConflict).filter(
        models.JudgeConflict.judge_id == judge.id, models.JudgeConflict.project_id == project.id
    ).first()
    if conflict:
        raise HTTPException(status_code=403, detail="You have declared a conflict of interest with this project")
    return assignment


@router.get("/my-projects")
def my_judging_queue(hackathon_id: str, db: Session = Depends(get_db),
                      user: models.User = Depends(security.require_roles("judge"))):
    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == hackathon_id).first()
    if not hackathon:
        raise HTTPException(status_code=404, detail="Hackathon not found")
    assignments = db.query(models.JudgeAssignment).filter(
        models.JudgeAssignment.hackathon_id == hackathon_id, models.JudgeAssignment.judge_id == user.id
    ).all()
    out = []
    for a in assignments:
        p = db.query(models.Project).filter(models.Project.id == a.project_id).first()
        if not p:
            continue
        existing_eval = db.query(models.Evaluation).filter(models.Evaluation.assignment_id == a.id).first()
        item = {
            "assignment_id": a.id,
            "project_id": p.id,
            "project_name": p.name,
            "short_description": p.short_description,
            "technologies": p.technologies,
            "repo_url": p.repo_url,
            "demo_url": p.demo_url,
            "claims": [
                {"id": c.id, "title": c.title, "description": c.description,
                 "evidence": [{"type": e.type.value, "content": e.content} for e in c.evidence]}
                for c in p.claims
            ],
            "evaluated": existing_eval is not None and existing_eval.locked,
        }
        if hackathon.blind_judging:
            # Blind judging: never expose team identity or members to the judge.
            pass
        else:
            team = db.query(models.Team).filter(models.Team.id == p.team_id).first()
            item["team_name"] = team.name if team else None
            item["team_members"] = [m.user.full_name for m in team.members] if team else []
        out.append(item)
    return out


@router.post("/evaluations", response_model=schemas.EvaluationOut)
def submit_evaluation(payload: schemas.EvaluationSubmit, db: Session = Depends(get_db),
                       user: models.User = Depends(security.require_roles("judge"))):
    project = db.query(models.Project).filter(models.Project.id == payload.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    assignment = _assert_can_judge(db, user, project)

    hackathon = db.query(models.Hackathon).filter(models.Hackathon.id == project.hackathon_id).first()
    rubric = db.query(models.Rubric).filter(
        models.Rubric.hackathon_id == hackathon.id, models.Rubric.is_active == True  # noqa: E712
    ).first()
    if not rubric:
        raise HTTPException(status_code=400, detail="No active rubric configured for this hackathon")
    criterion_ids = {c.id for c in rubric.criteria}
    given_ids = {s.criterion_id for s in payload.scores}
    if given_ids != criterion_ids:
        raise HTTPException(status_code=422, detail="Scores must be provided for exactly the active rubric's criteria")

    evaluation = db.query(models.Evaluation).filter(models.Evaluation.assignment_id == assignment.id).first()
    if evaluation and evaluation.locked:
        raise HTTPException(status_code=403, detail="This evaluation has already been submitted and locked")

    if not evaluation:
        evaluation = models.Evaluation(
            hackathon_id=hackathon.id, assignment_id=assignment.id, judge_id=user.id,
            project_id=project.id, rubric_id=rubric.id,
        )
        db.add(evaluation)
        db.flush()
    else:
        db.query(models.EvaluationScore).filter(models.EvaluationScore.evaluation_id == evaluation.id).delete()

    for s in payload.scores:
        db.add(models.EvaluationScore(evaluation_id=evaluation.id, criterion_id=s.criterion_id,
                                       score=s.score, comment=s.comment))

    evaluation.overall_comment = payload.overall_comment
    if payload.submit_final:
        evaluation.locked = True
        evaluation.submitted_at = datetime.utcnow()

    log_event(db, user, "evaluation.lock" if payload.submit_final else "evaluation.save_draft",
              "evaluation", evaluation.id, {"project_id": project.id}, hackathon_id=hackathon.id)
    db.commit()
    db.refresh(evaluation)
    return schemas.EvaluationOut(
        id=evaluation.id, project_id=evaluation.project_id, judge_id=evaluation.judge_id,
        rubric_id=evaluation.rubric_id, locked=evaluation.locked, submitted_at=evaluation.submitted_at,
        overall_comment=evaluation.overall_comment,
        scores=[schemas.ScoreIn(criterion_id=s.criterion_id, score=s.score, comment=s.comment) for s in evaluation.scores],
    )


@router.get("/my-history", response_model=List[schemas.EvaluationOut])
def my_history(db: Session = Depends(get_db), user: models.User = Depends(security.require_roles("judge"))):
    evals = db.query(models.Evaluation).filter(models.Evaluation.judge_id == user.id).all()
    return [
        schemas.EvaluationOut(
            id=e.id, project_id=e.project_id, judge_id=e.judge_id, rubric_id=e.rubric_id,
            locked=e.locked, submitted_at=e.submitted_at, overall_comment=e.overall_comment,
            scores=[schemas.ScoreIn(criterion_id=s.criterion_id, score=s.score, comment=s.comment) for s in e.scores],
        ) for e in evals
    ]
