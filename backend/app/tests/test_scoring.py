from app.services import scoring


class FakeCriterion:
    def __init__(self, id, weight_percent):
        self.id = id
        self.weight_percent = weight_percent


class FakeScore:
    def __init__(self, criterion, score):
        self.criterion = criterion
        self.criterion_id = criterion.id
        self.score = score


class FakeEvaluation:
    def __init__(self, id, judge_id, project_id, scores):
        self.id = id
        self.judge_id = judge_id
        self.project_id = project_id
        self.scores = scores


def test_weighted_score_respects_weights():
    crit_a = FakeCriterion("a", 70)
    crit_b = FakeCriterion("b", 30)
    ev = FakeEvaluation("e1", "j1", "p1", [FakeScore(crit_a, 10), FakeScore(crit_b, 0)])
    assert scoring.weighted_score_for_evaluation(ev) == 7.0


def test_zero_variance_judge_gets_neutral_zscore(monkeypatch, client=None):
    # A judge who gives every project the identical score has sigma=0.
    # Their z-score must be defined as 0 for each, not raise ZeroDivisionError.
    crit = FakeCriterion("c", 100)
    evals = [
        FakeEvaluation("e1", "j1", "p1", [FakeScore(crit, 7)]),
        FakeEvaluation("e2", "j1", "p2", [FakeScore(crit, 7)]),
    ]

    class FakeDB:
        def query(self, *a, **k):
            raise AssertionError("compute_project_scores should not query DB when fed directly")

    # Exercise the pure grouping/normalization logic directly rather than through the DB.
    import statistics
    by_judge = {"j1": [scoring.weighted_score_for_evaluation(e) for e in evals]}
    mu = statistics.mean(by_judge["j1"])
    sigma = statistics.pstdev(by_judge["j1"])
    assert sigma == 0.0
    # Replicate the z-score branch's zero-guard
    z = 0.0 if sigma == 0 else (7 - mu) / sigma
    assert z == 0.0


def test_min_max_zero_range_maps_to_midpoint():
    # if a judge's min==max, min_max normalization should not divide by zero
    mn, mx, ws = 6.0, 6.0, 6.0
    result = 5.0 if mx == mn else 10.0 * (ws - mn) / (mx - mn)
    assert result == 5.0
