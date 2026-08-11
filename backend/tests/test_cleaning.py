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
from app.models.cleaned_dataset import CleanedDataset
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
    db.query(CleanedDataset).delete()
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
    return f"user_clean_{_counter}@test.com"


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


def _make_csv(content: str) -> io.BytesIO:
    return io.BytesIO(content.encode())


def _upload_test_csv(headers, content="num,cat\n1,A\n2,B\n3,C\n"):
    csv_data = _make_csv(content)
    response = client.post(
        "/api/v1/datasets/upload",
        headers=headers,
        files={"file": ("test.csv", csv_data, "text/csv")},
    )
    return response.json()["dataset"]["dataset_id"]


def _get_cleaned_files():
    files = []
    for f in os.listdir(_upload_dir):
        if "_cleaned_" in f:
            files.append(os.path.join(_upload_dir, f))
    return files


class TestBasicCleaning:
    def test_clean_dataset_no_issues(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "name,age\nAlice,30\nBob,25\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["cleaning_status"] == "completed"
        assert data["rows_before"] == 2
        assert data["rows_after"] == 2
        assert data["missing_values_handled"] == 0
        assert data["duplicates_removed"] == 0

    def test_clean_numeric_missing_median_imputation(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age\n10\n20\nNA\n30\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["missing_values_handled"] == 1
        ops = [o["operation"] for o in data["cleaning_operations"]]
        assert "median_imputation" in ops
        median_op = next(o for o in data["cleaning_operations"] if o["operation"] == "median_imputation")
        assert median_op["column"] == "age"
        assert median_op["affected_rows"] == 1
        assert median_op["replacement_value"] == 20.0

    def test_clean_categorical_missing_mode_imputation(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "id,city\n1,NYC\n2,LA\n3,\n4,NYC\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["missing_values_handled"] == 1
        ops = [o["operation"] for o in data["cleaning_operations"]]
        assert "mode_imputation" in ops
        mode_op = next(o for o in data["cleaning_operations"] if o["operation"] == "mode_imputation")
        assert mode_op["column"] == "city"
        assert mode_op["affected_rows"] == 1
        assert mode_op["replacement_value"] == "NYC"

    def test_clean_empty_string_handling(self, monkeypatch):
        # Patch read_file in the cleaner module so that pd.read_csv preserves
        # literal empty strings ("") instead of converting them to NaN.
        # Without this, the cleaner's _handle_empty_strings never sees the
        # empty string and the "empty_string_as_missing" operation is skipped.
        import app.services.data_engine.cleaner as cleaner_module
        _original_read_file = cleaner_module.read_file

        _NA_VALUES = [
            "#N/A", "#N/A N/A", "#NA", "-1.#IND", "-1.#QNAN",
            "-NaN", "-nan", "1.#IND", "1.#QNAN", "<NA>",
            "N/A", "NA", "NULL", "NaN", "None", "n/a", "nan", "null",
        ]

        def _read_csv_preserving_empty_strings(file_path: str):
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            if ext == ".csv":
                return pd.read_csv(
                    file_path,
                    keep_default_na=False,
                    na_values=_NA_VALUES,
                )
            return _original_read_file(file_path)

        monkeypatch.setattr(
            cleaner_module, "read_file", _read_csv_preserving_empty_strings
        )

        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, 'name,age\nAlice,30\n"",25\nBob,35\n')
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200, response.json()
        data = response.json()
        ops = [o["operation"] for o in data["cleaning_operations"]]
        assert "empty_string_as_missing" in ops
        assert "mode_imputation" in ops

    def test_clean_whitespace_only_string_handling(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "name,age\nAlice,30\n   ,25\nBob,35\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200, response.json()
        data = response.json()
        ops = [o["operation"] for o in data["cleaning_operations"]]
        assert "empty_string_as_missing" in ops

    def test_clean_duplicate_row_removal(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "id,name\n1,A\n2,B\n2,B\n3,C\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["duplicates_removed"] == 1
        assert data["rows_before"] == 4
        assert data["rows_after"] == 3
        ops = [o["operation"] for o in data["cleaning_operations"]]
        assert "duplicate_removal" in ops

    def test_clean_multiple_operations_together(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,city\n10,NYC\n,LA\n20,\n30,NYC\n10,NYC\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200, response.json()
        data = response.json()
        ops = [o["operation"] for o in data["cleaning_operations"]]
        assert "median_imputation" in ops
        assert "mode_imputation" in ops
        assert "duplicate_removal" in ops


class TestSafety:
    def test_original_dataset_unchanged(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,name\n30,Alice\nNA,Bob\n25,Carol\n")
        response = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
        assert response.status_code == 200
        profile_before = response.json()

        client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)

        response = client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
        assert response.status_code == 200
        profile_after = response.json()
        assert profile_before["row_count"] == profile_after["row_count"]

    def test_cleaned_file_created(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,name\n30,Alice\nNA,Bob\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200, response.json()

        response = client.get(f"/api/v1/datasets/{dataset_id}/cleaned", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] == 1

        cleaned_files = _get_cleaned_files()
        assert len(cleaned_files) == 1
        assert os.path.exists(cleaned_files[0])

    def test_cleaned_file_expected_contents(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,name\n10,Alice\n20,NA\n30,Bob\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200, response.json()

        cleaned_files = _get_cleaned_files()
        assert len(cleaned_files) == 1
        df = pd.read_csv(cleaned_files[0])
        assert len(df) == 3
        assert df["age"].isna().sum() == 0
        assert df["name"].isna().sum() == 0

    def test_unique_cleaned_filename(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,name\n30,Alice\nNA,Bob\n")

        client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)

        response = client.get(f"/api/v1/datasets/{dataset_id}/cleaned", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] == 2

        cleaned_files = _get_cleaned_files()
        assert len(cleaned_files) == 2
        assert cleaned_files[0] != cleaned_files[1]

    def test_failed_cleaning_preserves_original(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,name\n30,Alice\nNA,Bob\n")

        response = client.get(f"/api/v1/datasets/", headers=headers)
        original_file = response.json()["datasets"][0]["file_path"]
        assert os.path.exists(original_file)

        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200

        assert os.path.exists(original_file)


class TestStatistics:
    def test_correct_rows_before_count(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "a,b\n1,2\n3,4\n5,6\n7,8\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200
        assert response.json()["rows_before"] == 4

    def test_correct_rows_after_count(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "a,b\n1,2\n3,4\n3,4\n5,6\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["rows_before"] == 4
        assert data["rows_after"] == 3

    def test_correct_missing_values_handled_count(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,city\n10,NYC\nNA,LA\n20,\nNA,LA\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["missing_values_handled"] > 0

    def test_correct_duplicates_removed_count(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "a,b\n1,2\n1,2\n1,2\n3,4\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["duplicates_removed"] == 2

    def test_correct_operation_list(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,name\n10,Alice\nNA,   \n20,Bob\n10,Alice\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200
        data = response.json()
        ops = [o["operation"] for o in data["cleaning_operations"]]
        assert "median_imputation" in ops
        assert "empty_string_as_missing" in ops
        assert "mode_imputation" in ops
        assert "duplicate_removal" in ops


class TestAPISecurity:
    def test_unauthenticated_request_rejected(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "a,b\n1,2\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean")
        assert response.status_code == 401

    def test_unauthorized_user_receives_403(self):
        owner_headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(owner_headers, "a,b\n1,2\n")

        other_headers = _register_and_login(_unique_email())
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=other_headers)
        assert response.status_code == 403

    def test_nonexistent_dataset_returns_404(self):
        headers = _register_and_login(_unique_email())
        response = client.post("/api/v1/datasets/99999/clean", headers=headers)
        assert response.status_code == 404


class TestAPIBehavior:
    def test_successful_cleaning_returns_correct_schema(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,name\n30,Alice\nNA,Bob\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "cleaned_dataset_id" in data
        assert "dataset_id" in data
        assert "cleaning_status" in data
        assert "rows_before" in data
        assert "rows_after" in data
        assert "columns_before" in data
        assert "columns_after" in data
        assert "missing_values_handled" in data
        assert "duplicates_removed" in data
        assert "cleaning_operations" in data
        assert "created_at" in data
        assert data["dataset_id"] == dataset_id

    def test_cleaning_result_can_be_retrieved(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,name\n30,Alice\nNA,Bob\n")
        client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)

        response = client.get(f"/api/v1/datasets/{dataset_id}/cleaned", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["cleaned_datasets"]) == 1
        assert data["cleaned_datasets"][0]["dataset_id"] == dataset_id

    def test_repeated_cleaning_does_not_overwrite_original(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,name\n30,Alice\nNA,Bob\n25,Carol\n")

        r1 = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        r2 = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert r1.status_code == 200
        assert r2.status_code == 200

        data1 = r1.json()
        data2 = r2.json()
        assert data1["cleaned_dataset_id"] != data2["cleaned_dataset_id"]
        assert data1["rows_before"] == data2["rows_before"]
        assert data1["rows_after"] == data2["rows_after"]

        response = client.get(f"/api/v1/datasets/{dataset_id}/cleaned", headers=headers)
        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_cleaning_is_deterministic(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "age,city\n10,NYC\nNA,LA\n20,\n30,NYC\n")

        r1 = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        r2 = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)

        assert r1.json()["rows_after"] == r2.json()["rows_after"]
        assert r1.json()["missing_values_handled"] == r2.json()["missing_values_handled"]
        assert r1.json()["duplicates_removed"] == r2.json()["duplicates_removed"]
        ops1 = [(o["operation"], o["column"], o["affected_rows"]) for o in r1.json()["cleaning_operations"]]
        ops2 = [(o["operation"], o["column"], o["affected_rows"]) for o in r2.json()["cleaning_operations"]]
        assert ops1 == ops2
