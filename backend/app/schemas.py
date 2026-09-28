from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, field_validator


# ---------- Auth / Users ----------
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    institution: Optional[str] = None
    role: str = "participant"  # participant | judge (organizer/admin created by admin only)

    @field_validator("role")
    @classmethod
    def role_must_be_self_registerable(cls, v):
        if v not in ("participant", "judge"):
            raise ValueError("Self-registration is only allowed as participant or judge")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    institution: Optional[str] = None
    is_demo: bool = False

    class Config:
        from_attributes = True


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- Skills ----------
class SkillOut(BaseModel):
    id: str
    name: str
    category: Optional[str] = None

    class Config:
        from_attributes = True


class SkillCreate(BaseModel):
    name: str
    category: Optional[str] = None


class UserSkillIn(BaseModel):
    skill_name: str
    kind: str  # have | want
    proficiency: Optional[int] = None

    @field_validator("kind")
    @classmethod
    def kind_valid(cls, v):
        if v not in ("have", "want"):
            raise ValueError("kind must be 'have' or 'want'")
        return v

    @field_validator("proficiency")
    @classmethod
    def prof_range(cls, v):
        if v is not None and not (0 <= v <= 100):
            raise ValueError("proficiency must be between 0 and 100")
        return v


class UserSkillOut(BaseModel):
    skill_name: str
    kind: str
    proficiency: Optional[int] = None

    class Config:
        from_attributes = True


# ---------- Hackathon ----------
class HackathonCreate(BaseModel):
    name: str
    tagline: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    submission_deadline: datetime
    min_team_size: int = 1
    max_team_size: int = 5
    blind_judging: bool = True


class HackathonUpdate(BaseModel):
    name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    submission_deadline: Optional[datetime] = None
    min_team_size: Optional[int] = None
    max_team_size: Optional[int] = None
    blind_judging: Optional[bool] = None
    status: Optional[str] = None


class HackathonOut(BaseModel):
    id: str
    name: str
    tagline: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[str] = None
    registration_deadline: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    submission_deadline: datetime
    min_team_size: int
    max_team_size: int
    blind_judging: bool
    status: str

    class Config:
        from_attributes = True


# ---------- Teams ----------
class TeamCreate(BaseModel):
    hackathon_id: str
    name: str
    looking_for_skill_names: List[str] = []


class TeamMemberOut(BaseModel):
    user_id: str
    full_name: str
    is_leader: bool

    class Config:
        from_attributes = True


class TeamOut(BaseModel):
    id: str
    hackathon_id: str
    name: str
    members: List[TeamMemberOut] = []
    looking_for: List[str] = []

    class Config:
        from_attributes = True


class MatchExplain(BaseModel):
    candidate_id: str
    candidate_name: str
    coverage_score: float
    matched_skills: List[str]
    still_missing: List[str]
    reasoning: str


# ---------- Projects / Claims / Evidence ----------
class ProjectCreate(BaseModel):
    team_id: str
    hackathon_id: str
    name: str
    short_description: Optional[str] = None
    detailed_description: Optional[str] = None
    technologies: Optional[str] = None
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None
    detailed_description: Optional[str] = None
    technologies: Optional[str] = None
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None


class EvidenceIn(BaseModel):
    type: str
    content: str


class EvidenceOut(BaseModel):
    id: str
    type: str
    content: str

    class Config:
        from_attributes = True


class ClaimCreate(BaseModel):
    title: str
    description: Optional[str] = None


class ClaimOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    evidence: List[EvidenceOut] = []

    class Config:
        from_attributes = True


class ProjectOut(BaseModel):
    id: str
    team_id: str
    hackathon_id: str
    name: str
    short_description: Optional[str] = None
    detailed_description: Optional[str] = None
    technologies: Optional[str] = None
    repo_url: Optional[str] = None
    demo_url: Optional[str] = None
    status: str
    submitted_at: Optional[datetime] = None
    claims: List[ClaimOut] = []

    class Config:
        from_attributes = True


# ---------- Judging ----------
class AssignmentCreate(BaseModel):
    hackathon_id: str
    judge_id: str
    project_id: str


class AssignmentOut(BaseModel):
    id: str
    hackathon_id: str
    judge_id: str
    project_id: str

    class Config:
        from_attributes = True


class ConflictCreate(BaseModel):
    hackathon_id: str
    judge_id: str
    project_id: str
    reason: Optional[str] = None


class ConflictOut(BaseModel):
    id: str
    judge_id: str
    project_id: str
    reason: Optional[str] = None

    class Config:
        from_attributes = True


class RubricCriterionIn(BaseModel):
    name: str
    weight_percent: float


class RubricCreate(BaseModel):
    hackathon_id: str
    name: str = "Default Rubric"
    criteria: List[RubricCriterionIn]

    @field_validator("criteria")
    @classmethod
    def weights_sum_100(cls, v):
        if not v:
            raise ValueError("Rubric must have at least one criterion")
        total = sum(c.weight_percent for c in v)
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Criterion weights must sum to 100, got {total}")
        return v


class RubricCriterionOut(BaseModel):
    id: str
    name: str
    weight_percent: float

    class Config:
        from_attributes = True


class RubricOut(BaseModel):
    id: str
    hackathon_id: str
    name: str
    is_active: bool
    criteria: List[RubricCriterionOut]

    class Config:
        from_attributes = True


class ScoreIn(BaseModel):
    criterion_id: str
    score: float
    comment: Optional[str] = None

    @field_validator("score")
    @classmethod
    def score_range(cls, v):
        if not (0 <= v <= 10):
            raise ValueError("score must be between 0 and 10")
        return v


class EvaluationSubmit(BaseModel):
    project_id: str
    scores: List[ScoreIn]
    overall_comment: Optional[str] = None
    submit_final: bool = False  # if True, locks the evaluation


class EvaluationOut(BaseModel):
    id: str
    project_id: str
    judge_id: str
    rubric_id: str
    locked: bool
    submitted_at: Optional[datetime] = None
    overall_comment: Optional[str] = None
    scores: List[ScoreIn] = []

    class Config:
        from_attributes = True


# ---------- Normalization / Ranking ----------
class NormalizationRunRequest(BaseModel):
    hackathon_id: str
    method: str = "z_score"  # z_score | min_max | none


class ProjectScoreBreakdown(BaseModel):
    project_id: str
    project_name: str
    raw_score: float
    normalized_score: float
    final_score: float
    num_evaluations: int


class RankingEntry(BaseModel):
    rank: int
    project_id: str
    project_name: str
    final_score: float


class SimulationRequest(BaseModel):
    hackathon_id: str
    name: str
    exclude_judge_ids: List[str] = []
    exclude_evaluation_ids: List[str] = []
    weight_overrides: Optional[dict] = None  # criterion_id -> new weight_percent
    method: str = "z_score"


class WhyScoreOut(BaseModel):
    project_id: str
    project_name: str
    num_evaluations: int
    criterion_breakdown: list
    raw_judge_scores: list
    weighted_raw_score: float
    normalized_score: float
    final_score: float
    normalization_method: str
    audit_events: list
