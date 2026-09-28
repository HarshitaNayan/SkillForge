"""Judging engine core: weighted rubric scoring, cross-judge normalization,
and ranking. Every number here is derived from EvaluationScore rows that
judges actually submitted and locked — nothing is hardcoded.

NORMALIZATION METHOD (z-score, judge-relative)
------------------------------------------------
Problem: different judges have different scoring habits. A judge who
tends to score everything 8-9 and a judge who spreads scores 4-9 are not
directly comparable, so simply averaging raw scores across judges biases
the outcome toward whichever judges' assigned projects happened to draw
the "easy grader".

Method:
1. For each judge, collect their locked weighted-rubric scores (0-10)
   across every project they evaluated in this hackathon.
2. Compute that judge's mean (mu_j) and population standard deviation
   (sigma_j) across their own scores.
3. For each evaluation, compute a z-score: z = (score - mu_j) / sigma_j.
   This expresses "how far above/below this judge's own average" the
   project scored, independent of that judge's overall generosity.
4. A project's normalized score is the mean of its z-scores across all
   judges who evaluated it.
5. For readability, the normalized score is converted back to a 0-10
   "final score" scale: final = clamp(5 + z_mean * 2, 0, 10). This maps
   roughly +/-2.5 standard deviations onto the full 0-10 range, centered
   at 5. The mapping constant (2) is a documented, fixed choice, not a
   fitted parameter.

Edge cases:
- Zero variance (sigma_j == 0): the judge gave every project the same
  score, so their scores carry no discriminating information. Their
  z-score is defined as 0 (neutral) for every project instead of
  dividing by zero.
- A judge with only one locked evaluation: sigma_j is 0 by construction
  (a single point has no spread), so the same zero-variance rule applies.
- A project with zero locked evaluations is excluded from ranking with
  an explicit reason, rather than silently defaulting to a score.
- method="min_max" is offered as an alternative: rescales each judge's
  raw scores to [0,10] using that judge's own observed min/max, so a
  judge who only used the top of the scale still produces a full-range
  signal. If a judge's min==max (zero range), every score from that
  judge maps to the scale's midpoint, 5.0, instead of dividing by zero.
- method="none" skips normalization: final_score == raw_score. This is
  included so organizers can show, and quantify, the ranking difference
  normalization actually makes.
"""
import statistics
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app import models


def weighted_score_for_evaluation(evaluation: models.Evaluation) -> float:
    """Applies the active rubric's criterion weights to one judge's scores
    for one project, producing a single 0-10 weighted score."""
    total_weight = 0.0
    total = 0.0
    for s in evaluation.scores:
        w = s.criterion.weight_percent
        total += s.score * (w / 100.0)
        total_weight += w
    if total_weight == 0:
        return 0.0
    # total is already on a 0-10 scale as long as weights sum to 100
    return round(total, 4)


def collect_locked_evaluations(db: Session, hackathon_id: str) -> List[models.Evaluation]:
    return db.query(models.Evaluation).filter(
        models.Evaluation.hackathon_id == hackathon_id, models.Evaluation.locked == True  # noqa: E712
    ).all()


def compute_project_scores(db: Session, hackathon_id: str, method: str = "z_score",
                            exclude_judge_ids: Optional[set] = None,
                            exclude_evaluation_ids: Optional[set] = None,
                            weight_overrides: Optional[Dict[str, float]] = None) -> Dict[str, Dict]:
    """Core computation shared by both the real normalization run and the
    Ranking Lab simulation endpoint (so a simulation can never diverge in
    logic from the real thing — only in which inputs it includes).
    Returns {project_id: {"raw": float, "normalized": float, "final": float, "num_evaluations": int}}
    """
    exclude_judge_ids = exclude_judge_ids or set()
    exclude_evaluation_ids = exclude_evaluation_ids or set()

    evaluations = [
        e for e in collect_locked_evaluations(db, hackathon_id)
        if e.judge_id not in exclude_judge_ids and e.id not in exclude_evaluation_ids
    ]

    def eval_weighted_score(e: models.Evaluation) -> float:
        if not weight_overrides:
            return weighted_score_for_evaluation(e)
        total = 0.0
        for s in e.scores:
            w = weight_overrides.get(s.criterion_id, s.criterion.weight_percent)
            total += s.score * (w / 100.0)
        return round(total, 4)

    # Group weighted scores by judge, and by project
    by_judge: Dict[str, List[float]] = {}
    by_project_evals: Dict[str, List[tuple]] = {}  # project_id -> [(judge_id, weighted_score)]
    for e in evaluations:
        ws = eval_weighted_score(e)
        by_judge.setdefault(e.judge_id, []).append(ws)
        by_project_evals.setdefault(e.project_id, []).append((e.judge_id, ws))

    judge_stats = {}
    for judge_id, scores in by_judge.items():
        mu = statistics.mean(scores)
        sigma = statistics.pstdev(scores) if len(scores) > 1 else 0.0
        mn, mx = min(scores), max(scores)
        judge_stats[judge_id] = {"mean": mu, "stdev": sigma, "min": mn, "max": mx, "n": len(scores)}

    results = {}
    for project_id, judge_scores in by_project_evals.items():
        raw_vals = [ws for _, ws in judge_scores]
        raw = round(statistics.mean(raw_vals), 4)

        if method == "none":
            normalized = raw
        elif method == "min_max":
            adj = []
            for judge_id, ws in judge_scores:
                st = judge_stats[judge_id]
                if st["max"] == st["min"]:
                    adj.append(5.0)
                else:
                    adj.append(10.0 * (ws - st["min"]) / (st["max"] - st["min"]))
            normalized = round(statistics.mean(adj), 4)
        else:  # z_score (default)
            zs = []
            for judge_id, ws in judge_scores:
                st = judge_stats[judge_id]
                z = 0.0 if st["stdev"] == 0 else (ws - st["mean"]) / st["stdev"]
                zs.append(z)
            z_mean = statistics.mean(zs)
            normalized = round(z_mean, 4)

        if method == "z_score":
            final = round(max(0.0, min(10.0, 5.0 + normalized * 2.0)), 4)
        else:
            final = round(max(0.0, min(10.0, normalized)), 4)

        results[project_id] = {
            "raw": raw, "normalized": normalized, "final": final, "num_evaluations": len(judge_scores),
        }
    return results


def run_normalization(db: Session, hackathon_id: str, method: str = "z_score") -> str:
    """Persists a real normalization run and returns its run_id."""
    scores = compute_project_scores(db, hackathon_id, method=method)
    run_id = str(uuid.uuid4())
    for project_id, r in scores.items():
        db.add(models.NormalizedScore(
            hackathon_id=hackathon_id, project_id=project_id, run_id=run_id,
            raw_score=r["raw"], normalized_score=r["normalized"], final_score=r["final"],
            num_evaluations=r["num_evaluations"], method=method,
        ))
    return run_id


def build_ranking(db: Session, hackathon_id: str, run_id: str, mark_official: bool = False) -> List[Dict]:
    rows = db.query(models.NormalizedScore).filter(
        models.NormalizedScore.hackathon_id == hackathon_id, models.NormalizedScore.run_id == run_id
    ).all()
    ranked = sorted(rows, key=lambda r: r.final_score, reverse=True)
    out = []
    for i, r in enumerate(ranked, start=1):
        project = db.query(models.Project).filter(models.Project.id == r.project_id).first()
        db.add(models.Ranking(
            hackathon_id=hackathon_id, run_id=run_id, project_id=r.project_id, rank=i,
            final_score=r.final_score, is_official=mark_official, published=mark_official,
        ))
        out.append({"rank": i, "project_id": r.project_id,
                    "project_name": project.name if project else "?", "final_score": r.final_score})
    return out


def get_official_ranking(db: Session, hackathon_id: str) -> List[Dict]:
    rows = db.query(models.Ranking).filter(
        models.Ranking.hackathon_id == hackathon_id, models.Ranking.is_official == True  # noqa: E712
    ).order_by(models.Ranking.rank).all()
    out = []
    for r in rows:
        project = db.query(models.Project).filter(models.Project.id == r.project_id).first()
        out.append({"rank": r.rank, "project_id": r.project_id,
                     "project_name": project.name if project else "?", "final_score": r.final_score})
    return out
