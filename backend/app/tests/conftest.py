import os
import tempfile
import pytest

TEST_DB = os.path.join(tempfile.gettempdir(), "skillforge_test.db")
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["SKILLFORGE_DB"] = TEST_DB

from fastapi.testclient import TestClient  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


def register_and_login(client, email, password, full_name, role="participant"):
    r = client.post("/api/auth/register", json={
        "email": email, "password": password, "full_name": full_name, "role": role,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    return data["access_token"], data["user"]["id"]


def promote_role(user_id, role):
    """Test-only helper mirroring how a real deployment would bootstrap its
    first organizer/admin account -- directly in the DB, never via the API
    (the API intentionally refuses to let anyone self-assign those roles)."""
    from app.database import SessionLocal
    from app import models
    db = SessionLocal()
    u = db.query(models.User).filter(models.User.id == user_id).first()
    u.role = models.Role(role)
    db.commit()
    db.close()


def auth(token):
    return {"Authorization": f"Bearer {token}"}
