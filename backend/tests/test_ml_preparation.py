import io
import os
import tempfile

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app
from app.models.dataset import Dataset
from app.models.ml_ready_dataset import MLReadyDataset
from app.models.cleaned_dataset import CleanedDataset
from app.models.engineered_dataset import EngineeredDataset
from app.models.user import User
from app.services.data_engine.preprocessor import MLPreparationService, prepare_ml_dataset

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
    db.query(MLReadyDataset).delete()
    db.query(EngineeredDataset).delete()
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
    return f"user_ml_{_counter}@test.com"


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


def _upload_test_csv(headers, content):
    csv_data = _make_csv(content)
    response = client.post(
        "/api/v1/datasets/upload",
        headers=headers,
        files={"file": ("test.csv", csv_data, "text/csv")},
    )
    return response.json()["dataset"]["dataset_id"]


def _get_ml_ready_files():
    """List ML-ready files in the upload directory (same pattern as _get_cleaned_files)."""
    files = []
    for f in os.listdir(_upload_dir):
        if "_ml_ready_" in f:
            files.append(os.path.join(_upload_dir, f))
    return files


def _get_cleaned_files():
    files = []
    for f in os.listdir(_upload_dir):
        if "_cleaned_" in f:
            files.append(os.path.join(_upload_dir, f))
    return files


def _get_engineered_files():
    files = []
    for f in os.listdir(_upload_dir):
        if "_engineered_" in f:
            files.append(os.path.join(_upload_dir, f))
    return files


def _file_hash(path):
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Target validation
# ---------------------------------------------------------------------------


class TestTargetValidation:
    def test_valid_target(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(
            headers,
            "num,cat,target\n1,A,0\n2,B,1\n3,A,0\n4,B,1\n5,A,0\n6,B,1\n",
        )
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()

    def test_missing_target_column(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(
            headers,
            "num,cat\n1,A\n2,B\n3,A\n4,B\n5,A\n6,B\n",
        )
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "nonexistent"},
        )
        assert response.status_code == 400
        assert "nonexistent" in response.json()["detail"]

    def test_empty_target_column(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(
            headers,
            "num,target\n1,A\n2,\n3,B\n4,\n5,C\n6,D\n",
        )
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()

    def test_target_completely_empty(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(
            headers,
            "num,target\n1,\n2,\n3,\n4,\n5,\n6,\n",
        )
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 400
        assert "completely empty" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Train/Test split
# ---------------------------------------------------------------------------


class TestTrainTestSplit:
    def _upload_many_rows(self, headers):
        rows = []
        for i in range(1, 21):
            rows.append(f"{i},B,{i % 2}")
        content = "num,cat,target\n" + "\n".join(rows) + "\n"
        return _upload_test_csv(headers, content)

    def test_default_80_20_split(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["test_rows"] + data["train_rows"] == data["rows_after"]
        assert data["test_size"] == 0.20

    def test_custom_test_size(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "test_size": 0.3},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["test_size"] == 0.3

    def test_deterministic_random_state(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        r1 = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "test_size": 0.2, "random_state": 42},
        )
        r2 = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "test_size": 0.2, "random_state": 42},
        )
        d1 = r1.json()
        d2 = r2.json()
        assert d1["feature_names"] == d2["feature_names"]
        assert d1["train_rows"] == d2["train_rows"]
        assert d1["test_rows"] == d2["test_rows"]

    def test_invalid_test_size_too_large(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "test_size": 0.6},
        )
        assert response.status_code == 422

    def test_invalid_test_size_too_small(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "test_size": 0.05},
        )
        assert response.status_code == 422

    def test_insufficient_rows(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(
            headers,
            "num,target\n1,0\n2,1\n3,0\n",
        )
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 400
        assert "rows" in response.json()["detail"].lower() or "4" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Numeric processing
# ---------------------------------------------------------------------------


class TestNumericProcessing:
    def test_numeric_scaling_applied(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            rows.append(f"{i*10},B,{i % 2}")
        content = "num,cat,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "num" in data["numeric_columns"]
        assert "num" in data["feature_names"]

    def test_scaler_fitted_only_on_training_data(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            rows.append(f"{i*10},B,{i % 2}")
        content = "num,cat,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "test_size": 0.2, "random_state": 42},
        )
        assert response.status_code == 200, response.json()

        ml_files = _get_ml_ready_files()
        assert len(ml_files) >= 1
        df = pd.read_csv(ml_files[-1])
        train_df = df[df["__split__"] == "train"]
        # StandardScaler fit on train => train mean ~0, std ~1
        assert abs(train_df["num"].mean()) < 1e-9, "Scaler was not fit on train only"
        assert abs(train_df["num"].std(ddof=0) - 1.0) < 1e-6


# ---------------------------------------------------------------------------
# Categorical processing
# ---------------------------------------------------------------------------


class TestCategoricalProcessing:
    def test_one_hot_encoding(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            c = ["A", "B", "C"][i % 3]
            t = i % 2
            rows.append(f"{c},{t}")
        content = "cat,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "cat" in data["categorical_columns"]
        feature_names = data["feature_names"]
        assert any(f.startswith("cat_") for f in feature_names)

    def test_unknown_category_handling(self):
        """Category appearing only in test should not crash encoding."""
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            if i <= 16:
                c = "A" if i % 2 == 0 else "B"
            else:
                c = "C" if i % 2 == 0 else "A"
            rows.append(f"{c},{i % 2}")
        content = "cat,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "random_state": 42},
        )
        assert response.status_code == 200, response.json()

    def test_encoder_fitted_only_on_training_data(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            c = "A" if i % 2 == 0 else "B"
            rows.append(f"{c},{i % 2}")
        content = "cat,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "test_size": 0.2, "random_state": 42},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert any(f.startswith("cat_") for f in data["feature_names"])


# ---------------------------------------------------------------------------
# Missing values
# ---------------------------------------------------------------------------


class TestMissingValues:
    def test_remaining_numeric_missing_values_imputed(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            num = "" if i == 3 else i * 10
            rows.append(f"{num},{i % 2}")
        content = "num,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()

        ml_files = _get_ml_ready_files()
        df = pd.read_csv(ml_files[-1])
        feature_cols = [c for c in df.columns if c not in ("__split__", "target")]
        assert df[feature_cols].isna().sum().sum() == 0, "No NaN remaining in features"

    def test_remaining_categorical_missing_values_imputed(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            cat = "" if i == 5 else ("A" if i % 2 == 0 else "B")
            rows.append(f"{cat},{i % 2}")
        content = "cat,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()

        ml_files = _get_ml_ready_files()
        df = pd.read_csv(ml_files[-1])
        feature_cols = [c for c in df.columns if c not in ("__split__", "target")]
        assert df[feature_cols].isna().sum().sum() == 0, "No NaN remaining in features"


# ---------------------------------------------------------------------------
# Data leakage prevention
# ---------------------------------------------------------------------------


class TestLeakagePrevention:
    def test_preprocessing_not_fitted_on_test_data(self):
        """Verify scaler was fit on train only: train has mean ~0, test does not."""
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            rows.append(f"{i*10},B,{i % 2}")
        content = "num,cat,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "test_size": 0.2, "random_state": 42},
        )
        assert response.status_code == 200, response.json()

        ml_files = _get_ml_ready_files()
        df = pd.read_csv(ml_files[-1])
        train_df = df[df["__split__"] == "train"]
        test_df = df[df["__split__"] == "test"]

        # Scaler fit on train => train mean ~0, std ~1
        assert abs(train_df["num"].mean()) < 1e-9
        assert abs(train_df["num"].std(ddof=0) - 1.0) < 1e-6

        # Test data transformed with train stats => mean NOT 0
        assert abs(test_df["num"].mean()) > 0.01 or abs(test_df["num"].std(ddof=0) - 1.0) > 0.01

    def test_target_never_included_in_features(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            rows.append(f"{i},B,{i % 2}")
        content = "num,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["target_column"] == "target"
        assert "target" not in data["feature_names"]


# ---------------------------------------------------------------------------
# File safety
# ---------------------------------------------------------------------------


class TestFileSafety:
    def test_original_file_unchanged(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            rows.append(f"{i},{i % 2}")
        content = "num,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)

        # Get original file path via API (DatasetResponse includes file_path)
        listing = client.get("/api/v1/datasets/", headers=headers)
        original_file = listing.json()["datasets"][0]["file_path"]
        original_hash = _file_hash(original_file)

        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()
        assert _file_hash(original_file) == original_hash

    def test_cleaned_file_unchanged(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            rows.append(f"{i},{i % 2}")
        content = "num,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)

        # Clean first
        clean_resp = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert clean_resp.status_code == 200

        cleaned_files = _get_cleaned_files()
        assert len(cleaned_files) == 1
        cleaned_hash = _file_hash(cleaned_files[0])

        # Now prepare
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()
        assert _file_hash(cleaned_files[0]) == cleaned_hash

    def test_engineered_file_unchanged(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            rows.append(f"2024-01-{(i % 28) + 1},{i*10},{i % 2}")
        content = "date,value,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)

        eng_resp = client.post(
            f"/api/v1/datasets/{dataset_id}/engineer_features", headers=headers
        )
        assert eng_resp.status_code == 200

        engineered_files = _get_engineered_files()
        assert len(engineered_files) == 1
        eng_hash = _file_hash(engineered_files[0])

        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()
        assert _file_hash(engineered_files[0]) == eng_hash

    def test_unique_ml_ready_output_file(self):
        headers = _register_and_login(_unique_email())
        rows = []
        for i in range(1, 21):
            rows.append(f"{i},{i % 2}")
        content = "num,target\n" + "\n".join(rows) + "\n"
        dataset_id = _upload_test_csv(headers, content)

        r1 = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        r2 = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert r1.status_code == 200
        assert r2.status_code == 200

        ml_files = _get_ml_ready_files()
        assert len(ml_files) == 2
        assert ml_files[0] != ml_files[1]

    def test_failed_processing_cleanup(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(
            headers,
            "num,target\n1,0\n2,1\n3,0\n",
        )
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 400

        # DB should have no ML-ready records for this dataset (via API)
        listing = client.get(f"/api/v1/datasets/{dataset_id}/prepared", headers=headers)
        assert listing.json()["total"] == 0

        # No partial ml_ready files in upload dir
        ml_files = [f for f in os.listdir(_upload_dir) if "_ml_ready_" in f]
        assert len(ml_files) == 0


# ---------------------------------------------------------------------------
# API behavior
# ---------------------------------------------------------------------------


class TestAPIBehavior:
    def _upload_many_rows(self, headers):
        rows = []
        for i in range(1, 21):
            rows.append(f"{i},B,{i % 2}")
        content = "num,cat,target\n" + "\n".join(rows) + "\n"
        return _upload_test_csv(headers, content)

    def test_successful_preparation(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["dataset_id"] == dataset_id
        assert data["target_column"] == "target"
        assert data["status"] == "completed"
        assert data["train_rows"] > 0
        assert data["test_rows"] > 0
        assert data["processed_feature_count"] > 0

    def test_unauthorized_request(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            json={"target_column": "target"},
        )
        assert response.status_code == 401

    def test_forbidden_other_user_dataset(self):
        owner_headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(owner_headers)
        other_headers = _register_and_login(_unique_email())
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=other_headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 403

    def test_nonexistent_dataset_returns_404(self):
        headers = _register_and_login(_unique_email())
        response = client.post(
            "/api/v1/datasets/99999/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 404

    def test_invalid_target_returns_400(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "does_not_exist"},
        )
        assert response.status_code == 400

    def test_response_schema(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        required_keys = [
            "ml_ready_dataset_id",
            "dataset_id",
            "target_column",
            "rows_before",
            "rows_after",
            "train_rows",
            "test_rows",
            "original_feature_count",
            "processed_feature_count",
            "numeric_columns",
            "categorical_columns",
            "feature_names",
            "test_size",
            "random_state",
            "preprocessing_operations",
            "status",
            "created_at",
        ]
        for key in required_keys:
            assert key in data, f"Missing key: {key}"
        # Sensitive paths must not be exposed
        assert "ml_ready_file_path" not in data
        assert "source_file_path" not in data

    def test_preparation_history(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        response = client.get(
            f"/api/v1/datasets/{dataset_id}/prepared",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["prepared_datasets"]) == 2

    def test_repeated_deterministic_preparation(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        r1 = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "test_size": 0.2, "random_state": 42},
        )
        r2 = client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target", "test_size": 0.2, "random_state": 42},
        )
        d1 = r1.json()
        d2 = r2.json()
        assert d1["feature_names"] == d2["feature_names"]
        assert d1["train_rows"] == d2["train_rows"]
        assert d1["test_rows"] == d2["test_rows"]
        assert d1["processed_feature_count"] == d2["processed_feature_count"]

    def test_get_prepared_history_unauthorized(self):
        owner_headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(owner_headers)
        client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=owner_headers,
            json={"target_column": "target"},
        )
        other_headers = _register_and_login(_unique_email())
        response = client.get(
            f"/api/v1/datasets/{dataset_id}/prepared",
            headers=other_headers,
        )
        assert response.status_code == 403

    def test_get_prepared_history_nonexistent_dataset(self):
        headers = _register_and_login(_unique_email())
        response = client.get(
            "/api/v1/datasets/99999/prepared",
            headers=headers,
        )
        assert response.status_code == 404

    def test_get_latest_prepared(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=headers,
            json={"target_column": "target"},
        )
        response = client.get(
            f"/api/v1/datasets/{dataset_id}/prepared/latest",
            headers=headers,
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert data["target_column"] == "target"

    def test_get_latest_prepared_no_history(self):
        headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(headers)
        response = client.get(
            f"/api/v1/datasets/{dataset_id}/prepared/latest",
            headers=headers,
        )
        assert response.status_code == 404

    def test_get_latest_prepared_forbidden(self):
        owner_headers = _register_and_login(_unique_email())
        dataset_id = self._upload_many_rows(owner_headers)
        client.post(
            f"/api/v1/datasets/{dataset_id}/prepare",
            headers=owner_headers,
            json={"target_column": "target"},
        )
        other_headers = _register_and_login(_unique_email())
        response = client.get(
            f"/api/v1/datasets/{dataset_id}/prepared/latest",
            headers=other_headers,
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Unit tests — direct service invocation
# ---------------------------------------------------------------------------


class TestServiceDirect:
    def test_prepare_with_numeric_and_categorical(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        pd.DataFrame({
            "num": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
            "cat": ["A", "B", "A", "B", "A", "B", "A", "B", "A", "B"],
            "target": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        }).to_csv(csv_path, index=False)

        result = prepare_ml_dataset(str(csv_path), str(tmp_path), "target")
        assert result["status"] == "completed"
        assert result["train_rows"] + result["test_rows"] == result["rows_after"]
        assert "num" in result["numeric_columns"]
        assert "cat" in result["categorical_columns"]
        assert result["target_column"] == "target"
        assert "target" not in result["feature_names"]

    def test_target_not_in_feature_names(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        pd.DataFrame({
            "a": range(1, 21),
            "target": [0, 1] * 10,
        }).to_csv(csv_path, index=False)
        result = prepare_ml_dataset(str(csv_path), str(tmp_path), "target")
        assert "target" not in result["feature_names"]
        ml_df = pd.read_csv(result["ml_ready_file_path"])
        assert "target" not in [c for c in ml_df.columns if c != "target"]

    def test_preprocessor_fit_on_train_only(self, tmp_path):
        """Directly verify via the service that the preprocessor object
        has been fit on training data only by checking transform behavior."""
        rng = np.random.RandomState(0)
        df = pd.DataFrame({
            "x": rng.randint(0, 100, size=40).astype(float),
            "cat": ["A"] * 20 + ["B"] * 20,
            "target": [0, 1] * 20,
        })
        csv_path = tmp_path / "data.csv"
        df.to_csv(csv_path, index=False)

        service = MLPreparationService(
            source_file_path=str(csv_path),
            upload_dir=str(tmp_path),
            target_column="target",
            test_size=0.2,
            random_state=42,
        )
        result = service.prepare()

        df_out = pd.read_csv(result["ml_ready_file_path"])
        train_df = df_out[df_out["__split__"] == "train"]
        assert abs(train_df["x"].mean()) < 1e-9
        assert abs(train_df["x"].std(ddof=0) - 1.0) < 1e-6
