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
from app.models.ml_ready_dataset import MLReadyDataset
from app.models.experiment import Experiment
from app.models.model import TrainedModel
from app.models.evaluation import ModelEvaluation
from app.models.prediction import PredictionRecord
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

    # Ensure the TestClient and this module's TestingSessionLocal share the
    # SAME engine (other test modules reassign the global override at import).
    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    db.query(PredictionRecord).delete()
    db.query(ModelEvaluation).delete()
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
                p = os.path.join(d, f)
                if os.path.isfile(p):
                    os.remove(p)


def _unique_email():
    global _counter
    _counter += 1
    return f"eval_{_counter}@test.com"


def _register_and_login(email: str, password: str = "testpass123"):
    r = client.post(
        "/api/v1/auth/register",
        params={"email": email, "password": password, "full_name": "T"},
    )
    assert r.status_code == 200, r.json()
    r = client.post(
        "/api/v1/auth/login",
        params={"email": email, "password": password},
    )
    assert r.status_code == 200, r.json()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _upload_csv(headers, content):
    r = client.post(
        "/api/v1/datasets/upload",
        headers=headers,
        files={"file": ("t.csv", io.BytesIO(content.encode()), "text/csv")},
    )
    assert r.status_code == 200, r.json()
    return r.json()["dataset"]["dataset_id"]


def _prepare(headers, dataset_id, target="target"):
    r = client.post(
        f"/api/v1/datasets/{dataset_id}/prepare",
        headers=headers,
        json={"target_column": target},
    )
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


def _post_cls_exp(headers, ds, mrid):
    r = client.post(
        f"/api/v1/datasets/{ds}/experiments",
        headers=headers,
        json={
            "ml_ready_dataset_id": mrid,
            "experiment_name": "Cls",
            "target_column": "target",
            "problem_type": "classification",
        },
    )
    assert r.status_code == 200, r.json()
    return r.json()


def _post_reg_exp(headers, ds, mrid):
    r = client.post(
        f"/api/v1/datasets/{ds}/experiments",
        headers=headers,
        json={
            "ml_ready_dataset_id": mrid,
            "experiment_name": "Reg",
            "target_column": "value",
            "problem_type": "regression",
        },
    )
    assert r.status_code == 200, r.json()
    return r.json()


def _setup_classification():
    h = _register_and_login(_unique_email())
    ds = _upload_csv(h, _make_cls_csv())
    mrid = _prepare(h, ds)
    d = _post_cls_exp(h, ds, mrid)
    return h, ds, d


def _setup_regression():
    h = _register_and_login(_unique_email())
    ds = _upload_csv(h, _make_reg_csv())
    mrid = _prepare(h, ds, target="value")
    d = _post_reg_exp(h, ds, mrid)
    return h, ds, d


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------


class TestClassificationMetrics:
    def test_classification_metrics_present(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        r = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h
        )
        assert r.status_code == 200, r.json()
        body = r.json()
        for m in body["models"]:
            if m["evaluation_status"] == "completed":
                metrics = m["metrics"]
                assert "accuracy" in metrics
                assert "precision" in metrics
                assert "recall" in metrics
                assert "f1" in metrics
                assert "confusion_matrix" in metrics
                assert "confusion_matrix_labels" in metrics

    def test_regression_metrics_present(self):
        h, ds, d = _setup_regression()
        eid = d["experiment_id"]
        r = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h
        )
        assert r.status_code == 200, r.json()
        body = r.json()
        for m in body["models"]:
            if m["evaluation_status"] == "completed":
                metrics = m["metrics"]
                assert "mae" in metrics
                assert "mse" in metrics
                assert "rmse" in metrics
                assert "r2" in metrics
                assert "confusion_matrix" not in metrics

    def test_correct_metric_selection(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        r = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h
        )
        body = r.json()
        for m in body["models"]:
            if m["evaluation_status"] == "completed":
                assert "r2" not in m["metrics"]
                assert "f1" in m["metrics"]

        h2, ds2, d2 = _setup_regression()
        eid2 = d2["experiment_id"]
        r2 = client.post(
            f"/api/v1/datasets/{ds2}/experiments/{eid2}/evaluate", headers=h2
        )
        body2 = r2.json()
        for m in body2["models"]:
            if m["evaluation_status"] == "completed":
                assert "f1" not in m["metrics"]
                assert "r2" in m["metrics"]


# ---------------------------------------------------------------------------
# Primary metric & averaging
# ---------------------------------------------------------------------------


class TestPrimaryMetric:
    def test_primary_metric_classification_is_f1(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h)
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/comparison", headers=h
        )
        assert r.status_code == 200, r.json()
        assert r.json()["primary_metric"] == "f1"
        assert r.json()["averaging_strategy"] == "weighted"

    def test_primary_metric_regression_is_r2(self):
        h, ds, d = _setup_regression()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h)
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/comparison", headers=h
        )
        assert r.status_code == 200, r.json()
        assert r.json()["primary_metric"] == "r2"
        assert r.json()["averaging_strategy"] is None


# ---------------------------------------------------------------------------
# Persistence & idempotency
# ---------------------------------------------------------------------------


class TestEvaluationPersistence:
    def test_evaluation_persists_records(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h)

        db = TestingSessionLocal()
        try:
            count = (
                db.query(ModelEvaluation)
                .filter(ModelEvaluation.experiment_id == eid)
                .count()
            )
            tm_count = (
                db.query(TrainedModel)
                .filter(TrainedModel.experiment_id == eid)
                .count()
            )
        finally:
            db.close()
        assert count == tm_count
        assert count >= 1

    def test_evaluate_is_idempotent(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        r1 = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h
        )
        r2 = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h
        )
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json()["best_model_id"] == r2.json()["best_model_id"]
        assert r1.json()["best_score"] == r2.json()["best_score"]

    def test_recomputed_metrics_match_training_metrics(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h)

        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluation", headers=h
        )
        body = r.json()
        # Map model index -> training metrics
        train_metrics = {m["model_id"]: m["metrics"] for m in d["models"]}
        for ev in body["evaluations"]:
            idx = ev["model_id"]
            if ev["evaluation_status"] == "completed":
                tm_metrics = train_metrics.get(idx, {})
                assert ev["metrics"]["f1"] == pytest.approx(tm_metrics["f1"])
                assert ev["metrics"]["accuracy"] == pytest.approx(tm_metrics["accuracy"])


# ---------------------------------------------------------------------------
# Ranking & best-model selection
# ---------------------------------------------------------------------------


class TestModelRanking:
    def test_comparison_returns_ranked_models(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h)
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/comparison",
            headers=h,
        )
        body = r.json()
        ranked = body["ranked_models"]
        primary = body["primary_metric"]
        # Best first
        scores = [m["primary_metric_value"] for m in ranked]
        assert scores == sorted(scores, reverse=True)
        # Best ranked model is flagged
        assert ranked[0]["is_best"] is True

    def test_best_model_update_after_evaluate(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        r = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h
        )
        body = r.json()
        db = TestingSessionLocal()
        try:
            exp = db.query(Experiment).filter(Experiment.id == eid).first()
        finally:
            db.close()
        assert exp.best_model_id is not None
        trained = [m for m in body["models"] if m["evaluation_status"] == "completed"]
        best_f1 = max(m["primary_metric_value"] for m in trained)
        best_m = next(m for m in trained if m["model_id"] == body["best_model_id"])
        assert best_m["primary_metric_value"] == pytest.approx(best_f1)

    def test_evaluate_best_matches_training_best(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        training_best = d["best_model_id"]
        training_best_f1 = max(
            m["metrics"]["f1"]
            for m in d["models"]
            if m["status"] == "trained"
        )
        r = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h
        )
        body = r.json()
        assert body["best_model_id"] == training_best
        best_m = next(m for m in body["models"] if m["model_id"] == body["best_model_id"])
        assert best_m["metrics"]["f1"] == pytest.approx(training_best_f1)

    def test_second_ranked_not_best(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h)
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/comparison",
            headers=h,
        )
        ranked = r.json()["ranked_models"]
        assert len(ranked) >= 2
        assert ranked[1]["is_best"] is False


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class TestResponseSchemas:
    def test_evaluate_response_schema(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        r = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h
        )
        body = r.json()
        for key in [
            "experiment_id",
            "name",
            "problem_type",
            "primary_metric",
            "averaging_strategy",
            "best_model_id",
            "best_metric",
            "best_score",
            "models",
        ]:
            assert key in body, f"Missing {key}"
        for m in body["models"]:
            for key in [
                "model_id",
                "model_name",
                "algorithm",
                "model_type",
                "metrics",
                "primary_metric",
                "primary_metric_value",
                "averaging_strategy",
                "evaluation_status",
                "is_best",
            ]:
                assert key in m, f"Missing {key} in model entry"
        assert "model_path" not in str(body)

    def test_comparison_response_schema(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h)
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/comparison",
            headers=h,
        )
        body = r.json()
        for key in [
            "experiment_id",
            "experiment_name",
            "problem_type",
            "primary_metric",
            "secondary_metric",
            "ranked_models",
        ]:
            assert key in body, f"Missing {key}"
        assert len(body["ranked_models"]) >= 1

    def test_model_evaluation_endpoint_schema(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h)
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/models/0/evaluation",
            headers=h,
        )
        assert r.status_code == 200, r.json()
        body = r.json()
        for key in [
            "experiment_id",
            "trained_model_id",
            "model_name",
            "algorithm",
            "metrics",
            "primary_metric",
            "primary_metric_value",
            "evaluation_status",
            "is_best",
        ]:
            assert key in body, f"Missing {key}"

    def test_model_evaluation_fallback_to_training_metrics(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        # Do NOT call /evaluate; the endpoint should fall back to training
        # metrics stored on the TrainedModel.
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/models/0/evaluation",
            headers=h,
        )
        assert r.status_code == 200, r.json()
        body = r.json()
        assert body["evaluation_status"] == "not_evaluated"
        assert body["metrics"] is not None

    def test_get_evaluation_not_found_before_evaluate(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluation", headers=h
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Authorization & existence
# ---------------------------------------------------------------------------


class TestEvaluationAuthorization:
    def test_unauthorized_evaluate(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        r = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate",
        )
        assert r.status_code == 401

    def test_forbidden_other_user_evaluate(self):
        oh, ds, d = _setup_classification()
        eid = d["experiment_id"]
        nh = _register_and_login(_unique_email())
        r = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=nh
        )
        assert r.status_code == 403

    def test_nonexistent_experiment_evaluate(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        r = client.post(
            f"/api/v1/datasets/{ds}/experiments/99999/evaluate", headers=h
        )
        assert r.status_code == 404

    def test_nonexistent_experiment_get_evaluation(self):
        h = _register_and_login(_unique_email())
        ds = _upload_csv(h, _make_cls_csv())
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/99999/evaluation", headers=h
        )
        assert r.status_code == 404

    def test_nonexistent_model_evaluation(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h)
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/models/999/evaluation",
            headers=h,
        )
        assert r.status_code == 404

    def test_forbidden_get_comparison(self):
        oh, ds, d = _setup_classification()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=oh)
        nh = _register_and_login(_unique_email())
        r = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/comparison",
            headers=nh,
        )
        assert r.status_code == 403

    def test_nonexistent_dataset(self):
        h = _register_and_login(_unique_email())
        r = client.get(
            f"/api/v1/datasets/99999/experiments/1/evaluation", headers=h
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Tie-breaking determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_repeated_evaluate_same_best_model(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        r1 = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h
        ).json()
        r2 = client.post(
            f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h
        ).json()
        assert r1["best_model_id"] == r2["best_model_id"]
        assert r1["best_score"] == r2["best_score"]

    def test_comparison_ranking_is_deterministic(self):
        h, ds, d = _setup_classification()
        eid = d["experiment_id"]
        client.post(f"/api/v1/datasets/{ds}/experiments/{eid}/evaluate", headers=h)
        r1 = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/comparison",
            headers=h,
        ).json()
        r2 = client.get(
            f"/api/v1/datasets/{ds}/experiments/{eid}/comparison",
            headers=h,
        ).json()
        ids1 = [m["model_id"] for m in r1["ranked_models"]]
        ids2 = [m["model_id"] for m in r2["ranked_models"]]
        assert ids1 == ids2
