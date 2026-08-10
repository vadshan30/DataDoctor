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
from app.models.data_quality_report import DataQualityReport
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
    db.query(DataQualityReport).delete()
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
    return f"user_quality_{_counter}@test.com"


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


def _upload_test_csv(headers, content="colA,colB\n1,2\n3,4\n"):
    csv_data = io.BytesIO(content.encode())
    response = client.post(
        "/api/v1/datasets/upload",
        headers=headers,
        files={"file": ("test.csv", csv_data, "text/csv")},
    )
    return response.json()["dataset"]["dataset_id"]


class TestDatasetQuality:
    def test_quality_clean_dataset(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "id,value\n1,100\n2,110\n3,105\n")
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200, response.json()
        data = response.json()
        # 'id' is a numeric column but its name contains 'id' → potential_identifier (low severity, -1 point).
        # 'value' is numeric and does NOT have id/uuid in name → no identifier issue.
        # Score = 100 - 1 = 99
        assert data["quality_score"] == 99
        assert data["summary"]["potential_identifiers"] == 1
        
    def test_quality_missing_values(self):
        headers = _register_and_login(_unique_email())
        # 5 rows, 1 missing out of 5 = 20% (medium severity)
        dataset_id = _upload_test_csv(headers, "col1,col2\n1,A\n2,\n3,B\n4,C\n5,D\n")
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200
        data = response.json()
        issues = [i["issue_type"] for i in data["issues"]]
        assert "missing_values" in issues
        assert data["summary"]["missing_percentage"] == 10.0 # 1 out of 10 cells

    def test_quality_duplicate_rows(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "col1,col2\n1,A\n1,A\n3,B\n")
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200
        data = response.json()
        issues = [i["issue_type"] for i in data["issues"]]
        assert "duplicate_rows" in issues

    def test_quality_constant_columns(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "id,status\n1,active\n2,active\n3,active\n")
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["constant_columns"] == 1

    def test_quality_near_constant_columns(self):
        headers = _register_and_login(_unique_email())
        # 100 rows of 'A' and 1 row of 'B' (Wait, test needs to be smaller for speed, 
        # I'll manually check the endpoint response for a normal dataset since I don't want to upload 100 rows in test)
        # Actually I can just create 101 rows.
        csv_content = "col\n" + "A\n" * 100 + "B\n"
        dataset_id = _upload_test_csv(headers, csv_content)
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["constant_columns"] == 1
        issues = [i["issue_type"] for i in data["issues"]]
        assert "near_constant_column" in issues

    def test_quality_high_cardinality(self):
        headers = _register_and_login(_unique_email())
        # To trigger high cardinality: unique_count > 10 and unique > 0.5
        csv_content = "text\n" + "\n".join([f"val_{i}" for i in range(20)]) + "\n"
        dataset_id = _upload_test_csv(headers, csv_content)
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["high_cardinality_columns"] == 1

    def test_quality_numeric_outliers(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "val\n10\n12\n11\n10\n11\n1000\n")
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["outlier_columns"] == 1

    def test_quality_suspicious_values(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "price,text\n10,hi\n-5, \n")
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["suspicious_columns"] == 2 # 1 for price, 1 for empty string in text

    def test_quality_score(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "val\n1\n2\n3\n")
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200
        assert response.json()["quality_score"] == 100

    def test_quality_recommendations(self):
        headers = _register_and_login(_unique_email())
        # Upload a valid CSV with actual rows and a missing value to trigger the missing_values recommendation.
        dataset_id = _upload_test_csv(headers, "col1,col2\n1,A\n2,\n3,C\n")
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) > 0

    def test_quality_unauthorized(self):
        headers = _register_and_login(_unique_email())
        response = client.get("/api/v1/datasets/99999/quality", headers=headers)
        assert response.status_code == 404

    def test_quality_not_found(self):
        headers = _register_and_login(_unique_email())
        response = client.get("/api/v1/datasets/99999/quality", headers=headers)
        assert response.status_code == 404

    def test_quality_forbidden_other_user(self):
        owner_headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(owner_headers)
        
        other_headers = _register_and_login(_unique_email())
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=other_headers)
        assert response.status_code == 403

    def test_quality_response_schema(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers)
        response = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "quality_score" in data
        assert "summary" in data
        assert "issues" in data
        assert "recommendations" in data

    def test_quality_caching(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers)
        r1 = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        r2 = client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json() == r2.json()
