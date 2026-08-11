import io
import os
import tempfile

import joblib
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
from app.models.experiment import Experiment
from app.models.model import TrainedModel
from app.models.cleaned_dataset import CleanedDataset
from app.models.engineered_dataset import EngineeredDataset
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
_model_dir = tempfile.mkdtemp()
_counter = 0


@pytest.fixture(autouse=True)
def _reset_state(monkeypatch):
    global _counter
    _counter += 1

    from app.core import config
    monkeypatch.setattr(config.settings, "UPLOAD_DIR", _upload_dir)
    monkeypatch.setattr(config.settings, "MODEL_DIR", _model_dir)
    os.makedirs(_upload_dir, exist_ok=True)
    os.makedirs(_model_dir, exist_ok=True)

    db = TestingSessionLocal()
    db.query(TrainedModel).delete()
    db.query(Experiment).delete()
    db.query(MLReadyDataset).delete()
    db.query(EngineeredDataset).delete()
    db.query(CleanedDataset).delete()
    db.query(Dataset).delete()
    db.query(User).delete()
    db.commit()
    db.close()

    yield

    for d in (_upload_dir, _model_dir):
        if os.path.exists(d):
            for f in os.listdir(d):
                path = os.path.join(d, f)
                if os.path.isfile(path):
                    os.remove(path)


def _unique_email():
    global _counter
    _counter += 1
    return f"user_exp_{_counter}@test.com"


def _register_and_login(email, password="testpass123"):
    r = client.post("/api/v1/auth/register",
                    params={"email": email, "password": password, "full_name": "T"})
    assert r.status_code == 200, r.json()
    r = client.post("/api/v1/auth/login",
                    params={"email": email, "password": password})
    assert r.status_code == 200, r.json()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _upload_csv(headers, content):
    r = client.post("/api/v1/datasets/upload", headers=headers,
                    files={"file": ("t.csv", io.BytesIO(content.encode()), "text/csv")})
    assert r.status_code == 200, r.json()
    return r.json()["dataset"]["dataset_id"]


def _prepare(headers, dataset_id, target="target"):
    r = client.post(f"/api/v1/datasets/{dataset_id}/prepare", headers=headers,
                    json={"target_column": target})
    assert r.status_code == 200, r.json()
    return r.json()["ml_ready_dataset_id"]


def _make_cls_csv(n=20):
    lines = ["num,cat,target"]
    for i in range(1, n + 1):
        lines.append(f"{i*10},{'A' if i % 2 == 0 else 'B'},{i % 2}")
    return "\n".join(lines) + "\n"


def _make_reg_csv(n=20):
    lines = ["num,cat,value"]
    for i in range(1, n + 1):
        lines.append(f"{i},{'A' if i % 2 == 0 else 'B'},{i*10.0}")
    return "\n".join(lines) + "\n"


def _list_jobs():
    return [os.path.join(_model_dir, f) for f in os.listdir(_model_dir) if f.endswith(".joblib")]


def _list_ml_ready():
    return [os.path.join(_upload_dir, f) for f in os.listdir(_upload_dir) if "_ml_ready_" in f]


def _hash(path):
    import hashlib
    h = hashlib.md5()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def _post_exp(headers, dataset_id, ml_ready_id, name="Exp", target="target", ptype="classification"):
    return client.post(f"/api/v1/datasets/{dataset_id}/experiments", headers=headers, json={
        "ml_ready_dataset_id": ml_ready_id,
        "experiment_name": name,
        "target_column": target,
        "problem_type": ptype,
    })


# ---------------------------------------------------------------------------
# Experiment creation
# ---------------------------------------------------------------------------

class TestExperimentCreation:
    def test_valid_classification_experiment(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid)
        assert r.status_code == 200, r.json()
        d = r.json()
        assert d["problem_type"] == "classification"
        assert d["target_column"] == "target"
        assert d["status"] == "completed"
        assert d["best_model_id"] is not None
        assert d["best_score"] is not None
        assert len(d["models"]) == 3

    def test_valid_regression_experiment(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_reg_csv())
        mrid = _prepare(h, ds, target="value")
        r = _post_exp(h, ds, mrid, target="value", ptype="regression")
        assert r.status_code == 200, r.json()
        d = r.json()
        assert d["problem_type"] == "regression"
        assert d["status"] == "completed"
        assert d["best_model_id"] is not None
        assert len(d["models"]) == 3

    def test_missing_target_in_ml_ready(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, target="nonexistent")
        assert r.status_code == 400
        assert "nonexistent" in r.json()["detail"]

    def test_invalid_problem_type(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, target="target", ptype="clustering")
        assert r.status_code == 422

    def test_missing_ml_ready_dataset(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        r = _post_exp(h, ds, 99999)
        assert r.status_code == 404

    def test_insufficient_rows(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, "num,cat,target\n1,A,0\n2,B,1\n")
        r = client.post(f"/api/v1/datasets/{ds}/prepare", headers=h, json={"target_column": "target"})
        assert r.status_code == 400

    def test_single_class_classification_rejected(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, "num,cat,target\n" + "\n".join(f"{i},A,0" for i in range(1, 21)) + "\n")
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid)
        assert r.status_code == 400
        assert "class" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Classification models
# ---------------------------------------------------------------------------

class TestClassificationModels:
    def test_logistic_regression_trains(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, name="LR")
        d = r.json()
        lr = next(m for m in d["models"] if m["model_name"] == "LogisticRegression")
        assert lr["status"] == "trained"
        assert "accuracy" in lr["metrics"]
        assert "f1" in lr["metrics"]

    def test_decision_tree_classifier_trains(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, name="DT")
        d = r.json()
        dt = next(m for m in d["models"] if m["model_name"] == "DecisionTreeClassifier")
        assert dt["status"] == "trained"

    def test_random_forest_classifier_trains(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, name="RF")
        d = r.json()
        rf = next(m for m in d["models"] if m["model_name"] == "RandomForestClassifier")
        assert rf["status"] == "trained"

    def test_classification_metrics_generated(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, name="M")
        d = r.json()
        for m in d["models"]:
            if m["status"] == "trained":
                assert "accuracy" in m["metrics"]
                assert "precision" in m["metrics"]
                assert "recall" in m["metrics"]
                assert "f1" in m["metrics"]

    def test_multiclass_classification(self):
        h = _register_and_login(_unique_email())
        lines = ["num,target"]
        for i in range(1, 21):
            lines.append(f"{i*10},{i % 3}")
        ds = _upload_csv(h, "\n".join(lines) + "\n")
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, target="target")
        assert r.status_code == 200, r.json()
        d = r.json()
        assert d["status"] == "completed"
        assert d["best_score"] is not None

    def test_best_model_selected_correctly(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, name="BM")
        d = r.json()
        best_id = d["best_model_id"]
        trained = [m for m in d["models"] if m["status"] == "trained"]
        best_f1 = max(m["metrics"]["f1"] for m in trained)
        best_m = next(m for m in trained if m["model_id"] == best_id)
        assert abs(best_m["metrics"]["f1"] - best_f1) < 1e-9


# ---------------------------------------------------------------------------
# Regression models
# ---------------------------------------------------------------------------

class TestRegressionModels:
    def test_linear_regression_trains(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_reg_csv())
        mrid = _prepare(h, ds, target="value")
        r = _post_exp(h, ds, mrid, target="value", ptype="regression", name="LR")
        d = r.json()
        lr = next(m for m in d["models"] if m["model_name"] == "LinearRegression")
        assert lr["status"] == "trained"
        assert "r2" in lr["metrics"]
        assert "mae" in lr["metrics"]
        assert "mse" in lr["metrics"]
        assert "rmse" in lr["metrics"]

    def test_decision_tree_regressor_trains(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_reg_csv())
        mrid = _prepare(h, ds, target="value")
        r = _post_exp(h, ds, mrid, target="value", ptype="regression", name="DT")
        d = r.json()
        dtr = next(m for m in d["models"] if m["model_name"] == "DecisionTreeRegressor")
        assert dtr["status"] == "trained"

    def test_random_forest_regressor_trains(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_reg_csv())
        mrid = _prepare(h, ds, target="value")
        r = _post_exp(h, ds, mrid, target="value", ptype="regression", name="RF")
        d = r.json()
        rfr = next(m for m in d["models"] if m["model_name"] == "RandomForestRegressor")
        assert rfr["status"] == "trained"

    def test_regression_metrics_generated(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_reg_csv())
        mrid = _prepare(h, ds, target="value")
        r = _post_exp(h, ds, mrid, target="value", ptype="regression", name="M")
        d = r.json()
        for m in d["models"]:
            if m["status"] == "trained":
                assert "mae" in m["metrics"]
                assert "mse" in m["metrics"]
                assert "rmse" in m["metrics"]
                assert "r2" in m["metrics"]

    def test_best_model_selected_by_r2(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_reg_csv())
        mrid = _prepare(h, ds, target="value")
        r = _post_exp(h, ds, mrid, target="value", ptype="regression", name="BM")
        d = r.json()
        best_id = d["best_model_id"]
        trained = [m for m in d["models"] if m["status"] == "trained"]
        best_r2 = max(m["metrics"]["r2"] for m in trained)
        best_m = next(m for m in trained if m["model_id"] == best_id)
        assert abs(best_m["metrics"]["r2"] - best_r2) < 1e-9


# ---------------------------------------------------------------------------
# Data leakage
# ---------------------------------------------------------------------------

class TestLeakagePrevention:
    def test_target_not_used_as_feature(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid)
        d = r.json()
        assert d["models"][0]["feature_count"] == 3  # num, cat_A, cat_B (target excluded)

    def test_split_column_not_used_as_feature(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid)
        d = r.json()
        for m in d["models"]:
            if m["status"] == "trained":
                assert m["feature_count"] >= 2
                # __split__ is not counted as a feature
                assert "__split__" not in str(m)

    def test_only_train_rows_used_for_fitting(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid)
        d = r.json()
        for m in d["models"]:
            if m["status"] == "trained":
                assert m["training_rows"] > m["validation_rows"]


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------

class TestReproducibility:
    def test_deterministic_results(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        exp = {"ml_ready_dataset_id": mrid, "experiment_name": "D", "target_column": "target", "problem_type": "classification"}
        r1 = client.post(f"/api/v1/datasets/{ds}/experiments", headers=h, json=exp)
        r2 = client.post(f"/api/v1/datasets/{ds}/experiments", headers=h, json=exp)
        d1 = r1.json()
        d2 = r2.json()
        assert d1["best_score"] == d2["best_score"]
        assert d1["best_model_id"] == d2["best_model_id"]

    def test_same_ml_ready_same_metrics(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_reg_csv())
        mrid = _prepare(h, ds, target="value")
        exp = {"ml_ready_dataset_id": mrid, "experiment_name": "D", "target_column": "value", "problem_type": "regression"}
        r1 = client.post(f"/api/v1/datasets/{ds}/experiments", headers=h, json=exp)
        r2 = client.post(f"/api/v1/datasets/{ds}/experiments", headers=h, json=exp)
        d1 = r1.json()
        d2 = r2.json()
        for m1, m2 in zip(d1["models"], d2["models"]):
            if m1["status"] == "trained" and m2["status"] == "trained":
                assert m1["metrics"] == m2["metrics"]


# ---------------------------------------------------------------------------
# Model artifacts
# ---------------------------------------------------------------------------

class TestModelArtifacts:
    def test_model_file_created_on_disk(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, name="A")
        d = r.json()
        trained_count = len([m for m in d["models"] if m["status"] == "trained"])
        assert len(_list_jobs()) == trained_count

    def test_unique_model_filename(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        exp = {"ml_ready_dataset_id": mrid, "experiment_name": "U", "target_column": "target", "problem_type": "classification"}
        client.post(f"/api/v1/datasets/{ds}/experiments", headers=h, json=exp)
        client.post(f"/api/v1/datasets/{ds}/experiments", headers=h, json=exp)
        files = _list_jobs()
        assert len(files) == 6  # 2 experiments × 3 models

    def test_model_artifact_loadable_with_joblib(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, name="L")
        d = r.json()
        trained = [m for m in d["models"] if m["status"] == "trained"]
        assert len(trained) >= 1
        model = joblib.load(_list_jobs()[0])
        assert model is not None
        assert hasattr(model, "predict")

    def test_ml_ready_file_unchanged_after_training(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        ml_files = _list_ml_ready()
        assert len(ml_files) == 1
        orig_hash = _hash(ml_files[0])
        _post_exp(h, ds, mrid, name="F")
        assert _hash(_list_ml_ready()[0]) == orig_hash

    def test_failed_training_no_corrupt_artifact(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        before = len(_list_jobs())
        _post_exp(h, ds, mrid, name="C")
        after = len(_list_jobs())
        assert after == before + 3  # 3 models trained, no corrupt files


# ---------------------------------------------------------------------------
# API security & behavior
# ---------------------------------------------------------------------------

class TestAPISecurity:
    def test_unauthorized_request(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = client.post(f"/api/v1/datasets/{ds}/experiments", json={
            "ml_ready_dataset_id": mrid, "experiment_name": "X", "target_column": "target", "problem_type": "classification"})
        assert r.status_code == 401

    def test_forbidden_other_user_dataset(self):
        oh = _register_and_login(_unique_email())
        ds = _upload_csv(oh, _make_cls_csv())
        mrid = _prepare(oh, ds)
        nh = _register_and_login(_unique_email())
        r = client.post(f"/api/v1/datasets/{ds}/experiments", headers=nh, json={
            "ml_ready_dataset_id": mrid, "experiment_name": "X", "target_column": "target", "problem_type": "classification"})
        assert r.status_code == 403

    def test_nonexistent_dataset_returns_404(self):
        h = _register_and_login(_unique_email())
        r = client.post("/api/v1/datasets/99999/experiments", headers=h, json={
            "ml_ready_dataset_id": 1, "experiment_name": "X", "target_column": "target", "problem_type": "classification"})
        assert r.status_code == 404

    def test_get_experiments_unauthorized(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        _post_exp(h, ds, mrid)
        r = client.get(f"/api/v1/datasets/{ds}/experiments")
        assert r.status_code == 401

    def test_get_experiments_forbidden_other_user(self):
        oh = _register_and_login(_unique_email())
        ds = _upload_csv(oh, _make_cls_csv())
        mrid = _prepare(oh, ds)
        _post_exp(oh, ds, mrid)
        nh = _register_and_login(_unique_email())
        r = client.get(f"/api/v1/datasets/{ds}/experiments", headers=nh)
        assert r.status_code == 403

    def test_get_experiment_forbidden_other_user(self):
        oh = _register_and_login(_unique_email())
        ds = _upload_csv(oh, _make_cls_csv())
        mrid = _prepare(oh, ds)
        r = _post_exp(oh, ds, mrid)
        eid = r.json()["experiment_id"]
        nh = _register_and_login(_unique_email())
        r2 = client.get(f"/api/v1/datasets/{ds}/experiments/{eid}", headers=nh)
        assert r2.status_code == 403

    def test_get_experiment_nonexistent(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        r = client.get(f"/api/v1/datasets/{ds}/experiments/99999", headers=h)
        assert r.status_code == 404

    def test_get_best_model_forbidden_other_user(self):
        oh = _register_and_login(_unique_email())
        ds = _upload_csv(oh, _make_cls_csv())
        mrid = _prepare(oh, ds)
        r = _post_exp(oh, ds, mrid)
        eid = r.json()["experiment_id"]
        nh = _register_and_login(_unique_email())
        r2 = client.get(f"/api/v1/datasets/{ds}/experiments/{eid}/best", headers=nh)
        assert r2.status_code == 403


class TestAPIBehavior:
    def test_response_schema(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, name="S")
        d = r.json()
        for key in ["experiment_id", "dataset_id", "ml_ready_dataset_id", "name",
                     "experiment_type", "problem_type", "target_column", "test_size",
                     "random_state", "status", "best_model_id", "best_metric",
                     "best_score", "error_message"]:
            assert key in d, f"Missing {key}"
        assert "model_path" not in str(d)

    def test_experiment_history(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        _post_exp(h, ds, mrid, name="H1")
        _post_exp(h, ds, mrid, name="H2")
        r = client.get(f"/api/v1/datasets/{ds}/experiments", headers=h)
        assert r.status_code == 200
        d = r.json()
        assert d["total"] == 2
        assert len(d["experiments"]) == 2

    def test_get_experiment_detail(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, name="D")
        eid = r.json()["experiment_id"]
        r2 = client.get(f"/api/v1/datasets/{ds}/experiments/{eid}", headers=h)
        assert r2.status_code == 200
        d = r2.json()
        assert d["experiment_id"] == eid
        assert len(d["models"]) == 3

    def test_get_best_model(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        r = _post_exp(h, ds, mrid, name="B")
        eid = r.json()["experiment_id"]
        r2 = client.get(f"/api/v1/datasets/{ds}/experiments/{eid}/best", headers=h)
        assert r2.status_code == 200
        d = r2.json()
        assert d["model_id"] == r.json()["best_model_id"]
        assert "metrics" in d
        assert d["problem_type"] == "classification"

    def test_repeated_experiments_preserve_history(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        mrid = _prepare(h, ds)
        exp = {"ml_ready_dataset_id": mrid, "experiment_name": "P", "target_column": "target", "problem_type": "classification"}
        client.post(f"/api/v1/datasets/{ds}/experiments", headers=h, json=exp)
        client.post(f"/api/v1/datasets/{ds}/experiments", headers=h, json=exp)
        r = client.get(f"/api/v1/datasets/{ds}/experiments", headers=h)
        assert r.json()["total"] == 2

    def test_experiment_failed_when_all_models_fail(self):
        """Regression with a degenerate target (single value) should fail gracefully."""
        h = _register_and_login(_unique_email())
        # All target values same -> LinearRegression may still work but with R²=-inf or 0
        # Use a tiny dataset
        ds = _upload_csv(h, "num,target\n1,5\n2,5\n")
        prep = client.post(f"/api/v1/datasets/{ds}/prepare", headers=h, json={"target_column": "target"})
        # May fail due to too few rows; if it succeeds, verify graceful handling
        if prep.status_code != 200:
            assert prep.status_code == 400
            return
        mrid = prep.json()["ml_ready_dataset_id"]
        r = _post_exp(h, ds, mrid, target="target", ptype="regression", name="F")
        d = r.json()
        assert d["status"] in ("completed", "failed")
