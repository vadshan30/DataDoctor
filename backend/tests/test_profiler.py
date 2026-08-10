import io
import os
import tempfile

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.dataset import Dataset
from app.models.dataset_profile import DatasetProfile
from app.models.user import User

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

Base.metadata.create_all(bind=engine)
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

_upload_dir = tempfile.mkdtemp()
_counter = 0

@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    global _counter
    _counter += 1

    from app.core import config
    monkeypatch.setattr(config.settings, "UPLOAD_DIR", _upload_dir)
    os.makedirs(_upload_dir, exist_ok=True)

    db = TestingSessionLocal()
    db.query(DatasetProfile).delete()
    db.query(Dataset).delete()
    db.query(User).delete()
    db.commit()
    db.close()

    yield

    for f in os.listdir(_upload_dir):
        path = os.path.join(_upload_dir, f)
        if os.path.isfile(path):
            os.remove(path)


def _unique_email():
    global _counter
    _counter += 1
    return f"user_profile_{_counter}@test.com"


def _register_and_login(email: str, password: str = "testpass123"):
    response = client.post(
        "/api/v1/auth/register",
        params={"email": email, "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 200, response.json()
    response = client.post(
        "/api/v1/auth/login",
        params={"email": email, "password": password},
    )
    assert response.status_code == 200, response.json()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _upload_test_csv(headers, content="num,cat,dt\n1,A,2023-01-01\n2,B,2023-01-02\n3,A,2023-01-03\n4,C,\n5,C,2023-01-05\n100,A,2023-01-06\n"):
    csv_data = io.BytesIO(content.encode())
    response = client.post(
        "/api/v1/datasets/upload",
        headers=headers,
        files={"file": ("test.csv", csv_data, "text/csv")},
    )
    return response.json()["dataset"]["dataset_id"]


class TestDatasetProfiler:
    def test_profile_csv_dataset(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers)
        
        response = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
        assert response.status_code == 200, response.json()
        data = response.json()
        
        assert data["row_count"] == 6
        assert data["column_count"] == 3
        assert data["numerical_column_count"] == 1
        
        cols = {c["column_name"]: c for c in data["columns"]}
        
        # Numeric checks
        num_col = cols["num"]
        assert num_col["data_type"] == "numerical"
        assert num_col["numeric_stats"]["min"] == 1.0
        assert num_col["numeric_stats"]["max"] == 100.0
        assert num_col["numeric_stats"]["outliers"]["count"] == 1  # 100 is an outlier
        
        # Categorical checks
        cat_col = cols["cat"]
        assert cat_col["data_type"] == "categorical"
        assert cat_col["categorical_stats"]["top_values"][0] == "A"
        
        # Datetime checks (parsed as categorical since CSV doesn't auto-parse dates without kwargs, but let's check it doesn't crash)
        # Actually in pandas 2.2.3, string dates are objects/categorical unless parsed
        assert cols["dt"]["data_type"] == "categorical"
        assert cols["dt"]["null_count"] == 1

    def test_profile_caching(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers)
        
        # First call generates profile
        response1 = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
        assert response1.status_code == 200
        
        # Second call uses cache
        response2 = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
        assert response2.status_code == 200
        assert response1.json() == response2.json()

    def test_profile_unauthorized(self):
        owner_headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(owner_headers)
        
        other_headers = _register_and_login(_unique_email())
        response = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=other_headers)
        assert response.status_code == 403

    def test_profile_not_found(self):
        headers = _register_and_login(_unique_email())
        response = client.get("/api/v1/datasets/99999/profile", headers=headers)
        assert response.status_code == 404

def test_profiling_health():
    response = client.get("/api/v1/profiling/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_profiling_placeholder():
    response = client.get("/api/v1/profiling/")
    assert response.status_code == 200
    assert "Phase 1" in response.json()["message"]
