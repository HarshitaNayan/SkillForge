import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text,
    UniqueConstraint, Enum as SAEnum
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id():
    return str(uuid.uuid4())


class Role(str, enum.Enum):
    participant = "participant"
    judge = "judge"
    organizer = "organizer"
    admin = "admin"


class HackathonStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    judging = "judging"
    results_published = "results_published"
    closed = "closed"


class ProjectStatus(str, enum.Enum):
    draft = "draft"
    submitted = "submitted"
    locked = "locked"


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=gen_id)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(SAEnum(Role), nullable=False, default=Role.participant)
    institution = Column(String, nullable=True)
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    team_memberships = relationship("TeamMember", back_populates="user")


class Skill(Base):
    __tablename__ = "skills"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, unique=True, nullable=False)
    category = Column(String, nullable=True)


class SkillKind(str, enum.Enum):
    have = "have"
    want = "want"


class UserSkill(Base):
    __tablename__ = "user_skills"
    id = Column(String, primary_key=True, default=gen_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    skill_id = Column(String, ForeignKey("skills.id"), nullable=False)
    kind = Column(SAEnum(SkillKind), nullable=False, default=SkillKind.have)
    proficiency = Column(Integer, nullable=True)  # 0-100, only for kind=have

    user = relationship("User", back_populates="skills")
    skill = relationship("Skill")

    __table_args__ = (UniqueConstraint("user_id", "skill_id", "kind", name="uq_user_skill_kind"),)


class Hackathon(Base):
    __tablename__ = "hackathons"
    id = Column(String, primary_key=True, default=gen_id)
    name = Column(String, nullable=False)
    tagline = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    rules = Column(Text, nullable=True)
    registration_deadline = Column(DateTime, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    submission_deadline = Column(DateTime, nullable=False)
    min_team_size = Column(Integer, default=1)
    max_team_size = Column(Integer, default=5)
    blind_judging = Column(Boolean, default=True)
    status = Column(SAEnum(HackathonStatus), default=HackathonStatus.open)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class Team(Base):
    __tablename__ = "teams"
    id = Column(String, primary_key=True, default=gen_id)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    name = Column(String, nullable=False)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    requirements = relationship("TeamSkillRequirement", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(String, primary_key=True, default=gen_id)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    is_leader = Column(Boolean, default=False)

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_memberships")

    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_user"),)


class TeamSkillRequirement(Base):
    __tablename__ = "team_skill_requirements"
    id = Column(String, primary_key=True, default=gen_id)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    skill_id = Column(String, ForeignKey("skills.id"), nullable=False)

    team = relationship("Team", back_populates="requirements")
    skill = relationship("Skill")


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=gen_id)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    name = Column(String, nullable=False)
    short_description = Column(String, nullable=True)
    detailed_description = Column(Text, nullable=True)
    technologies = Column(String, nullable=True)  # comma separated
    repo_url = Column(String, nullable=True)
    demo_url = Column(String, nullable=True)
    status = Column(SAEnum(ProjectStatus), default=ProjectStatus.draft)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    claims = relationship("ProjectClaim", back_populates="project", cascade="all, delete-orphan")


class ProjectClaim(Base):
    __tablename__ = "project_claims"
    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="claims")
    evidence = relationship("ClaimEvidence", back_populates="claim", cascade="all, delete-orphan")


class EvidenceType(str, enum.Enum):
    repository = "repository"
    demo = "demo"
    documentation = "documentation"
    architecture_diagram = "architecture_diagram"
    screenshot = "screenshot"
    test_result = "test_result"
    explanation = "explanation"


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"
    id = Column(String, primary_key=True, default=gen_id)
    claim_id = Column(String, ForeignKey("project_claims.id"), nullable=False)
    type = Column(SAEnum(EvidenceType), nullable=False)
    content = Column(Text, nullable=False)  # URL or free text depending on type
    created_at = Column(DateTime, default=datetime.utcnow)

    claim = relationship("ProjectClaim", back_populates="evidence")


class JudgeAssignment(Base):
    __tablename__ = "judge_assignments"
    id = Column(String, primary_key=True, default=gen_id)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    judge_id = Column(String, ForeignKey("users.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(String, ForeignKey("users.id"), nullable=True)

    __table_args__ = (UniqueConstraint("judge_id", "project_id", name="uq_judge_project"),)


class JudgeConflict(Base):
    __tablename__ = "judge_conflicts"
    id = Column(String, primary_key=True, default=gen_id)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    judge_id = Column(String, ForeignKey("users.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    reason = Column(String, nullable=True)
    declared_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("judge_id", "project_id", name="uq_conflict_judge_project"),)


class Rubric(Base):
    __tablename__ = "rubrics"
    id = Column(String, primary_key=True, default=gen_id)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    name = Column(String, default="Default Rubric")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    criteria = relationship("RubricCriterion", back_populates="rubric", cascade="all, delete-orphan")


class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"
    id = Column(String, primary_key=True, default=gen_id)
    rubric_id = Column(String, ForeignKey("rubrics.id"), nullable=False)
    name = Column(String, nullable=False)
    weight_percent = Column(Float, nullable=False)  # sums to 100 across a rubric
    order_index = Column(Integer, default=0)

    rubric = relationship("Rubric", back_populates="criteria")


class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(String, primary_key=True, default=gen_id)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    assignment_id = Column(String, ForeignKey("judge_assignments.id"), nullable=False)
    judge_id = Column(String, ForeignKey("users.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    rubric_id = Column(String, ForeignKey("rubrics.id"), nullable=False)
    overall_comment = Column(Text, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    scores = relationship("EvaluationScore", back_populates="evaluation", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("assignment_id", name="uq_eval_assignment"),)


class EvaluationScore(Base):
    __tablename__ = "evaluation_scores"
    id = Column(String, primary_key=True, default=gen_id)
    evaluation_id = Column(String, ForeignKey("evaluations.id"), nullable=False)
    criterion_id = Column(String, ForeignKey("rubric_criteria.id"), nullable=False)
    score = Column(Float, nullable=False)  # 0-10
    comment = Column(Text, nullable=True)

    evaluation = relationship("Evaluation", back_populates="scores")
    criterion = relationship("RubricCriterion")

    __table_args__ = (UniqueConstraint("evaluation_id", "criterion_id", name="uq_eval_criterion"),)


class NormalizedScore(Base):
    __tablename__ = "normalized_scores"
    id = Column(String, primary_key=True, default=gen_id)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    run_id = Column(String, nullable=False)  # groups a normalization run
    raw_score = Column(Float, nullable=False)
    normalized_score = Column(Float, nullable=False)
    final_score = Column(Float, nullable=False)
    num_evaluations = Column(Integer, nullable=False)
    method = Column(String, nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow)


class Ranking(Base):
    __tablename__ = "rankings"
    id = Column(String, primary_key=True, default=gen_id)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    run_id = Column(String, nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    rank = Column(Integer, nullable=False)
    final_score = Column(Float, nullable=False)
    is_official = Column(Boolean, default=False)
    computed_at = Column(DateTime, default=datetime.utcnow)
    published = Column(Boolean, default=False)


class RankingSimulation(Base):
    __tablename__ = "ranking_simulations"
    id = Column(String, primary_key=True, default=gen_id)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=False)
    name = Column(String, nullable=False)
    config_json = Column(Text, nullable=False)
    result_json = Column(Text, nullable=False)
    diff_summary = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=gen_id)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    actor_role = Column(String, nullable=True)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True)
    metadata_json = Column(Text, nullable=True)
    hackathon_id = Column(String, ForeignKey("hackathons.id"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Vote(Base):
    __tablename__ = "votes"
    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("project_id", "user_id", name="uq_vote_project_user"),)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(String, primary_key=True, default=gen_id)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
