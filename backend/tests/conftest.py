import pytest
from fastapi.testclient import TestClient
from backend.app.core.database import SessionLocal, engine, Base
from backend.app.main import app
from backend.app.seeds.seed_streamlined import seed_platform

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    seed_platform()

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
