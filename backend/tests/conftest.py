import pytest
import os
import sys
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.db.session import SessionLocal, engine
from backend.app.models.user import UserAccount
from backend.app.core.security import create_access_token
from backend.app.main import app


@pytest.fixture(scope="session")
def db_engine():
    return engine


@pytest.fixture(scope="function")
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


def get_headers_for_role(db_session, role_name: str) -> dict:
    user = db_session.query(UserAccount).filter_by(role=role_name).first()
    if not user:
        raise ValueError(f"No user with role {role_name} found in database. Ensure seed_data.py has run.")
    token = create_access_token(
        data={"sub": str(user.user_id), "username": user.username, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def researcher_headers(db):
    return get_headers_for_role(db, "researcher")


@pytest.fixture(scope="function")
def reviewer_headers(db):
    return get_headers_for_role(db, "reviewer")


@pytest.fixture(scope="function")
def steward_headers(db):
    return get_headers_for_role(db, "steward")


@pytest.fixture(scope="function")
def admin_headers(db):
    return get_headers_for_role(db, "admin")
