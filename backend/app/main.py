from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app import models  # noqa: F401 ensures models are registered before create_all
from app.routers import (
    auth, skills, hackathons, teams, projects, judging, scoring, audit_router, export, community, users,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="SkillForge API",
    description="Skill-based team formation, claim-and-evidence submissions, and an auditable judging engine.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(skills.router)
app.include_router(hackathons.router)
app.include_router(teams.router)
app.include_router(projects.router)
app.include_router(judging.router)
app.include_router(scoring.router)
app.include_router(audit_router.router)
app.include_router(export.router)
app.include_router(community.router)
app.include_router(users.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "product": "SkillForge"}
