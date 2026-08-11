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
from app.models.cleaned_dataset import CleanedDataset
from app.models.engineered_dataset import EngineeredDataset
from app.models.user import User
from app.services.data_engine.feature_engineer import (
    _apply_feature_selection,
    _extract_categorical_features,
    _extract_datetime_features,
    _extract_interaction_features,
    _extract_numeric_features,
    _extract_text_features,
    _generate_engineered_filename,
    engineer_features,
)

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
    return f"user_fe_{_counter}@test.com"


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


def _get_engineered_files():
    files = []
    for f in os.listdir(_upload_dir):
        if "_engineered_" in f:
            files.append(os.path.join(_upload_dir, f))
    return files


# ---------------------------------------------------------------------------
# Unit tests — date/time features
# ---------------------------------------------------------------------------


class TestDatetimeFeatures:
    def test_date_extraction_works(self):
        df = pd.DataFrame({"signup_date": pd.to_datetime(["2024-01-15", "2024-06-20"])})
        df, ops, feats = _extract_datetime_features(df, {"signup_date"})
        assert "signup_date_year" in df.columns
        assert "signup_date_month" in df.columns
        assert "signup_date_day" in df.columns
        assert "signup_date_day_of_week" in df.columns
        assert "signup_date_quarter" in df.columns
        assert "signup_date_is_weekend" in df.columns
        assert "signup_date_days_since_reference" in df.columns
        assert df["signup_date_year"].tolist() == [2024, 2024]
        assert df["signup_date_month"].tolist() == [1, 6]
        assert ops[0]["operation"] == "date_extraction"

    def test_multiple_date_columns_handled(self):
        df = pd.DataFrame({
            "date_a": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "date_b": pd.to_datetime(["2023-03-15", "2023-07-20"]),
            "value": [1, 2],
        })
        df, ops, feats = _extract_datetime_features(df, {"date_a", "date_b"})
        assert "date_a_year" in df.columns
        assert "date_b_year" in df.columns
        assert len(ops) == 2

    def test_no_date_columns_handled_gracefully(self):
        df = pd.DataFrame({"num": [1, 2, 3], "cat": ["a", "b", "c"]})
        df, ops, feats = _extract_datetime_features(df, set())
        assert ops == []
        assert feats == []
        assert list(df.columns) == ["num", "cat"]


# ---------------------------------------------------------------------------
# Unit tests — text features
# ---------------------------------------------------------------------------


class TestTextFeatures:
    def test_text_feature_extraction_works(self):
        df = pd.DataFrame({"review": ["Hello World foo", "bar baz"]})
        df, ops, feats = _extract_text_features(df, {"review"})
        assert "review_word_count" in df.columns
        assert "review_char_count" in df.columns
        assert "review_avg_word_length" in df.columns
        assert "review_uppercase_count" in df.columns
        assert "review_lowercase_count" in df.columns
        assert "review_punctuation_count" in df.columns
        assert df["review_word_count"].tolist() == [3, 2]
        assert ops[0]["operation"] == "text_features"

    def test_empty_text_handled_gracefully(self):
        df = pd.DataFrame({"notes": ["", None, "hello"]})
        df, ops, feats = _extract_text_features(df, {"notes"})
        assert df["notes_word_count"].tolist()[0] == 0
        assert df["notes_char_count"].tolist()[1] == 0
        assert df["notes_word_count"].tolist()[2] == 1


# ---------------------------------------------------------------------------
# Unit tests — numeric features
# ---------------------------------------------------------------------------


class TestNumericFeatures:
    def test_polynomial_features_created(self):
        df = pd.DataFrame({"x": [2.0, 3.0, 4.0]})
        df, ops, feats = _extract_numeric_features(df, {"x"})
        assert df["x_squared"].tolist() == [4.0, 9.0, 16.0]
        assert df["x_cubed"].tolist() == [8.0, 27.0, 64.0]

    def test_log_transformation_applied_correctly(self):
        df = pd.DataFrame({"x": [0.0, 1.0, np.e - 1]})
        df, ops, feats = _extract_numeric_features(df, {"x"})
        expected = np.log1p([0.0, 1.0, np.e - 1])
        np.testing.assert_allclose(df["x_log"].values, expected, rtol=1e-10)

    def test_sqrt_transformation_applied(self):
        df = pd.DataFrame({"x": [4.0, 9.0, 16.0]})
        df, ops, feats = _extract_numeric_features(df, {"x"})
        assert df["x_sqrt"].tolist() == [2.0, 3.0, 4.0]


# ---------------------------------------------------------------------------
# Unit tests — interaction features
# ---------------------------------------------------------------------------


class TestInteractionFeatures:
    def test_product_features_created(self):
        df = pd.DataFrame({
            "a": [1.0, 2.0, 3.0, 4.0],
            "b": [2.0, 4.0, 6.0, 8.0],
        })
        df, ops, feats = _extract_interaction_features(df, {"a", "b"}, corr_threshold=0.3)
        assert "a_x_b" in df.columns
        assert df["a_x_b"].tolist() == [2.0, 8.0, 18.0, 32.0]

    def test_ratio_features_created(self):
        df = pd.DataFrame({
            "a": [1.0, 2.0, 3.0, 4.0],
            "b": [2.0, 4.0, 6.0, 8.0],
        })
        df, ops, feats = _extract_interaction_features(df, {"a", "b"}, corr_threshold=0.3)
        assert "a_div_b" in df.columns
        assert df["a_div_b"].tolist() == [0.5, 0.5, 0.5, 0.5]

    def test_uncorrelated_columns_skipped(self):
        rng = np.random.RandomState(42)
        df = pd.DataFrame({
            "a": rng.randn(100),
            "b": rng.randn(100),
        })
        df, ops, feats = _extract_interaction_features(df, {"a", "b"}, corr_threshold=0.9)
        assert ops == []


# ---------------------------------------------------------------------------
# Unit tests — categorical features
# ---------------------------------------------------------------------------


class TestCategoricalFeatures:
    def test_frequency_encoding_works(self):
        df = pd.DataFrame({"city": ["NYC", "LA", "NYC", "NYC"]})
        df, ops, feats = _extract_categorical_features(df, {"city"})
        assert "city_freq" in df.columns
        assert df["city_freq"].tolist() == [0.75, 0.25, 0.75, 0.75]

    def test_label_encoding_works(self):
        df = pd.DataFrame({"city": ["NYC", "LA", "NYC"]})
        df, ops, feats = _extract_categorical_features(df, {"city"})
        assert "city_label" in df.columns
        labels = df["city_label"].tolist()
        assert labels[0] == labels[2]
        assert labels[0] != labels[1]
        assert ops[0]["operation"] == "categorical_encoding"


# ---------------------------------------------------------------------------
# Unit tests — feature selection
# ---------------------------------------------------------------------------


class TestFeatureSelection:
    def test_correlation_filter_works(self):
        df = pd.DataFrame({
            "a": [1.0, 2.0, 3.0, 4.0, 5.0],
            "b": [1.1, 2.1, 3.1, 4.1, 5.1],
            "c": [5.0, 3.0, 1.0, 4.0, 2.0],
        })
        df, ops, surviving = _apply_feature_selection(df, ["a", "b", "c"])
        corr_ops = [o for o in ops if o["operation"] == "correlation_filter"]
        assert len(corr_ops) == 1
        assert "a" not in df.columns or "b" not in df.columns

    def test_variance_threshold_works(self):
        df = pd.DataFrame({
            "constant": [5.0] * 20,
            "varying": list(range(20)),
        })
        df, ops, surviving = _apply_feature_selection(df, ["constant", "varying"])
        var_ops = [o for o in ops if o["operation"] == "variance_threshold"]
        assert len(var_ops) == 1
        assert "constant" not in df.columns
        assert "varying" in df.columns

    def test_missing_value_filter_works(self):
        df = pd.DataFrame({
            "mostly_missing": [1.0, None, None, None, None, None, None, None, None, None],
            "complete": list(range(10)),
        })
        df, ops, surviving = _apply_feature_selection(df, ["mostly_missing", "complete"])
        missing_ops = [o for o in ops if o["operation"] == "missing_value_filter"]
        assert len(missing_ops) == 1
        assert "mostly_missing" not in df.columns
        assert "complete" in df.columns


# ---------------------------------------------------------------------------
# Unit tests — file handling
# ---------------------------------------------------------------------------


class TestFileHandling:
    def test_unique_filename_generated(self):
        name1 = _generate_engineered_filename("/data/dataset_abc123.csv")
        name2 = _generate_engineered_filename("/data/dataset_abc123.csv")
        assert name1 != name2
        assert name1.startswith("dataset_abc123_engineered_")
        assert name1.endswith(".csv")

    def test_engineered_file_created(self, tmp_path):
        csv_path = tmp_path / "input.csv"
        pd.DataFrame({"num": [1, 2, 3], "cat": ["a", "b", "a"]}).to_csv(csv_path, index=False)
        result = engineer_features(str(csv_path), str(tmp_path))
        assert os.path.exists(result["engineered_file_path"])
        assert "_engineered_" in result["engineered_file_path"]

    def test_original_dataset_unchanged(self, tmp_path):
        csv_path = tmp_path / "original.csv"
        original_df = pd.DataFrame({"num": [1, 2, 3], "cat": ["a", "b", "a"]})
        original_df.to_csv(csv_path, index=False)
        original_content = csv_path.read_bytes()

        engineer_features(str(csv_path), str(tmp_path))

        assert csv_path.read_bytes() == original_content

    def test_failed_engineering_does_not_corrupt_data(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        pd.DataFrame({"a": [1, 2]}).to_csv(csv_path, index=False)
        original_content = csv_path.read_bytes()

        with pytest.raises(FileNotFoundError):
            engineer_features(str(tmp_path / "nonexistent.csv"), str(tmp_path))

        assert csv_path.read_bytes() == original_content


# ---------------------------------------------------------------------------
# Unit tests — full pipeline
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_correct_rows_before_after(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-06-15", "2024-12-31"]),
            "value": [10.0, 20.0, 30.0],
        }).to_csv(csv_path, index=False)
        result = engineer_features(str(csv_path), str(tmp_path))
        assert result["rows_before"] == 3
        assert result["rows_after"] == 3

    def test_correct_columns_before_after(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-06-15", "2024-12-31"]),
            "value": [10.0, 20.0, 30.0],
        }).to_csv(csv_path, index=False)
        result = engineer_features(str(csv_path), str(tmp_path))
        assert result["columns_before"] == 2
        assert result["columns_after"] > 2

    def test_correct_operation_list(self, tmp_path):
        csv_path = tmp_path / "data.csv"
        pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-06-15", "2024-12-31"]),
            "value": [10.0, 20.0, 30.0],
        }).to_csv(csv_path, index=False)
        result = engineer_features(str(csv_path), str(tmp_path))
        op_names = [o["operation"] for o in result["feature_engineering_operations"]]
        assert "date_extraction" in op_names
        assert "numeric_transformation" in op_names

    def test_empty_dataset_handled(self, tmp_path):
        csv_path = tmp_path / "empty.csv"
        pd.DataFrame({"a": []}).to_csv(csv_path, index=False)
        result = engineer_features(str(csv_path), str(tmp_path))
        assert result["rows_before"] == 0
        assert result["rows_after"] == 0


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------


class TestAPISecurity:
    def test_unauthenticated_rejected(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(headers, "a,b\n1,2\n")
        response = client.post(f"/api/v1/datasets/{dataset_id}/engineer_features")
        assert response.status_code == 401

    def test_unauthorized_user_gets_403(self):
        owner_headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(owner_headers, "a,b\n1,2\n")

        other_headers = _register_and_login(_unique_email())
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/engineer_features", headers=other_headers
        )
        assert response.status_code == 403

    def test_nonexistent_dataset_returns_404(self):
        headers = _register_and_login(_unique_email())
        response = client.post("/api/v1/datasets/99999/engineer_features", headers=headers)
        assert response.status_code == 404


class TestAPIBehavior:
    def test_successful_engineering_returns_correct_schema(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(
            headers,
            "date,value\n2024-01-01,10\n2024-06-15,20\n2024-12-31,30\n",
        )
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/engineer_features", headers=headers
        )
        assert response.status_code == 200, response.json()
        data = response.json()
        assert "engineered_dataset_id" in data
        assert "dataset_id" in data
        assert "engineering_status" in data
        assert "rows_before" in data
        assert "rows_after" in data
        assert "columns_before" in data
        assert "columns_after" in data
        assert "features_added" in data
        assert "features_removed" in data
        assert "new_feature_names" in data
        assert "feature_engineering_operations" in data
        assert "created_at" in data
        assert data["engineering_status"] == "completed"
        assert data["features_added"] > 0
        # Sensitive paths must not be exposed
        assert "engineered_file_path" not in data
        assert "original_file_path" not in data

    def test_engineering_result_can_be_retrieved(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(
            headers,
            "date,value\n2024-01-01,10\n2024-06-15,20\n2024-12-31,30\n",
        )
        post_response = client.post(
            f"/api/v1/datasets/{dataset_id}/engineer_features", headers=headers
        )
        assert post_response.status_code == 200

        get_response = client.get(
            f"/api/v1/datasets/{dataset_id}/engineered", headers=headers
        )
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["total"] >= 1
        assert len(data["engineered_datasets"]) >= 1
        assert data["engineered_datasets"][0]["dataset_id"] == dataset_id

    def test_engineered_file_created_on_disk(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(
            headers,
            "date,value\n2024-01-01,10\n2024-06-15,20\n2024-12-31,30\n",
        )
        response = client.post(
            f"/api/v1/datasets/{dataset_id}/engineer_features", headers=headers
        )
        assert response.status_code == 200
        engineered_files = _get_engineered_files()
        assert len(engineered_files) >= 1

    def test_original_file_not_modified_by_api(self):
        headers = _register_and_login(_unique_email())
        content = "date,value\n2024-01-01,10\n2024-06-15,20\n2024-12-31,30\n"
        dataset_id = _upload_test_csv(headers, content)

        # Find the uploaded file on disk (the only non-engineered CSV)
        uploaded_files = [
            f for f in os.listdir(_upload_dir)
            if f.endswith(".csv") and "_engineered_" not in f
        ]
        assert len(uploaded_files) >= 1
        original_path = os.path.join(_upload_dir, uploaded_files[0])

        with open(original_path, "rb") as f:
            original_bytes = f.read()

        response = client.post(
            f"/api/v1/datasets/{dataset_id}/engineer_features", headers=headers
        )
        assert response.status_code == 200

        with open(original_path, "rb") as f:
            assert f.read() == original_bytes

    def test_uses_cleaned_dataset_when_available(self):
        headers = _register_and_login(_unique_email())
        dataset_id = _upload_test_csv(
            headers,
            "date,value\n2024-01-01,10\n2024-06-15,20\n2024-12-31,30\n",
        )
        # Clean first
        clean_response = client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
        assert clean_response.status_code == 200

        # Then engineer
        eng_response = client.post(
            f"/api/v1/datasets/{dataset_id}/engineer_features", headers=headers
        )
        assert eng_response.status_code == 200
        data = eng_response.json()
        assert data["cleaned_dataset_id"] is not None
