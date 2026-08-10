import io
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.dataset import Dataset
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
    return f"user_{_counter}@test.com"


def _register_and_login(email: str, password: str = "testpass123"):
    response = client.post(
        "/api/v1/auth/register",
        params={"email": email, "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 200

    response = client.post(
        "/api/v1/auth/login",
        params={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _make_csv(content: str) -> io.BytesIO:
    return io.BytesIO(content.encode())


def _make_xlsx() -> io.BytesIO:
    import pandas as pd
    df = pd.DataFrame({"col_a": [1, 2, 3], "col_b": ["x", "y", "z"]})
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    buf.seek(0)
    return buf


def _make_xls() -> io.BytesIO:
    import xlwt
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet('Sheet1')
    
    sheet.write(0, 0, 'col_a')
    sheet.write(0, 1, 'col_b')
    sheet.write(1, 0, 10)
    sheet.write(1, 1, 'p')
    sheet.write(2, 0, 20)
    sheet.write(2, 1, 'q')
    
    buf = io.BytesIO()
    workbook.save(buf)
    buf.seek(0)
    return buf


class TestDatasetUpload:
    def test_upload_csv(self):
        headers = _register_and_login(_unique_email())
        csv_data = _make_csv("name,age,city\nAlice,30,NYC\nBob,25,LA\n")
        response = client.post(
            "/api/v1/datasets/upload",
            headers=headers,
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["message"] == "Dataset uploaded successfully"
        assert data["dataset"]["name"] == "test.csv"
        assert data["dataset"]["row_count"] == 2
        assert data["dataset"]["column_count"] == 3
        assert data["dataset"]["file_size"] > 0
        assert data["dataset"]["file_type"] == "csv"
        assert "dataset_id" in data["dataset"]
        assert data["dataset"]["version"] == 1
        assert data["dataset"]["status"] == "uploaded"

    def test_upload_xlsx(self):
        headers = _register_and_login(_unique_email())
        xlsx_data = _make_xlsx()
        response = client.post(
            "/api/v1/datasets/upload",
            headers=headers,
            files={"file": ("test.xlsx", xlsx_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["message"] == "Dataset uploaded successfully"
        assert data["dataset"]["name"] == "test.xlsx"
        assert data["dataset"]["row_count"] == 3
        assert data["dataset"]["column_count"] == 2
        assert data["dataset"]["file_type"] == "xlsx"

    def test_upload_xls(self):
        headers = _register_and_login(_unique_email())
        xls_data = _make_xls()
        response = client.post(
            "/api/v1/datasets/upload",
            headers=headers,
            files={"file": ("test.xls", xls_data, "application/vnd.ms-excel")},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["message"] == "Dataset uploaded successfully"
        assert data["dataset"]["name"] == "test.xls"
        assert data["dataset"]["row_count"] == 2
        assert data["dataset"]["column_count"] == 2
        assert data["dataset"]["file_type"] == "xls"

    def test_upload_without_auth(self):
        csv_data = _make_csv("a,b\n1,2\n")
        response = client.post(
            "/api/v1/datasets/upload",
            files={"file": ("test.csv", csv_data, "text/csv")},
        )
        assert response.status_code == 401

    def test_upload_invalid_extension(self):
        headers = _register_and_login(_unique_email())
        txt_data = _make_csv("just some text")
        response = client.post(
            "/api/v1/datasets/upload",
            headers=headers,
            files={"file": ("test.txt", txt_data, "text/plain")},
        )
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()

    def test_upload_empty_file(self):
        headers = _register_and_login(_unique_email())
        empty_data = _make_csv("")
        response = client.post(
            "/api/v1/datasets/upload",
            headers=headers,
            files={"file": ("empty.csv", empty_data, "text/csv")},
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()

    def test_upload_empty_dataset(self):
        headers = _register_and_login(_unique_email())
        empty_dataset = _make_csv("col1,col2\n")
        response = client.post(
            "/api/v1/datasets/upload",
            headers=headers,
            files={"file": ("empty_data.csv", empty_dataset, "text/csv")},
        )
        assert response.status_code == 422
        assert "empty" in response.json()["detail"].lower()


class TestDatasetList:
    def test_list_datasets_empty(self):
        headers = _register_and_login(_unique_email())
        response = client.get("/api/v1/datasets/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["datasets"] == []
        assert data["total"] == 0

    def test_list_datasets_with_data(self):
        headers = _register_and_login(_unique_email())
        csv_data = _make_csv("x,y\n1,2\n3,4\n5,6\n")
        response = client.post(
            "/api/v1/datasets/upload",
            headers=headers,
            files={"file": ("list_test.csv", csv_data, "text/csv")},
            data={"description": "A test dataset"},
        )
        assert response.status_code == 200

        response = client.get("/api/v1/datasets/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["datasets"]) == 1
        assert data["datasets"][0]["name"] == "list_test.csv"
        assert data["datasets"][0]["description"] == "A test dataset"
        assert data["datasets"][0]["row_count"] == 3
        assert data["datasets"][0]["column_count"] == 2
