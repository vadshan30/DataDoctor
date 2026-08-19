import hashlib

import pytest

from app.models.report import Report
from app.services.ml_engine.explainer import get_feature_importance
from tests import test_experiments as support


@pytest.fixture(autouse=True)
def reset_reporting_state(monkeypatch):
    state = support._reset_state.__wrapped__(monkeypatch)
    next(state)
    db = support.TestingSessionLocal()
    db.query(Report).delete()
    db.commit()
    db.close()
    yield
    next(state, None)


def test_dataset_report_generation_retrieval_and_cache():
    headers = support._register_and_login(support._unique_email())
    dataset_id = support._upload_csv(headers, support._make_cls_csv())

    generated = support.client.post(f"/api/v1/datasets/{dataset_id}/report", headers=headers)
    assert generated.status_code == 200, generated.json()
    report = generated.json()
    assert report["report_type"] == "dataset"
    assert report["report_data"]["dataset_summary"]["total_rows"] == 20

    cached = support.client.post(f"/api/v1/datasets/{dataset_id}/report", headers=headers)
    assert cached.status_code == 200
    assert cached.json()["report_id"] == report["report_id"]

    regenerated = support.client.post(
        f"/api/v1/datasets/{dataset_id}/report",
        headers=headers,
        json={"regenerate": True},
    )
    assert regenerated.status_code == 200
    assert regenerated.json()["report_id"] != report["report_id"]

    history = support.client.get(f"/api/v1/datasets/{dataset_id}/reports", headers=headers)
    assert history.status_code == 200
    assert history.json()["total"] == 2


def test_report_enforces_ownership_and_missing_resources():
    owner_headers = support._register_and_login(support._unique_email())
    dataset_id = support._upload_csv(owner_headers, support._make_cls_csv())
    other_headers = support._register_and_login(support._unique_email())

    forbidden = support.client.post(
        f"/api/v1/datasets/{dataset_id}/report", headers=other_headers
    )
    assert forbidden.status_code == 403

    missing = support.client.get("/api/v1/datasets/999999/report", headers=owner_headers)
    assert missing.status_code == 404

    missing_experiment = support.client.post(
        f"/api/v1/datasets/{dataset_id}/experiments/999999/report",
        headers=owner_headers,
    )
    assert missing_experiment.status_code == 404


def test_report_generation_does_not_modify_original_file():
    headers = support._register_and_login(support._unique_email())
    uploaded = support.client.post(
        "/api/v1/datasets/upload",
        headers=headers,
        files={"file": ("t.csv", support.io.BytesIO(support._make_cls_csv().encode()), "text/csv")},
    )
    assert uploaded.status_code == 200, uploaded.json()
    dataset_id = uploaded.json()["dataset"]["dataset_id"]
    path = uploaded.json()["dataset"]["file_path"]
    with open(path, "rb") as original:
        before = hashlib.sha256(original.read()).hexdigest()

    response = support.client.post(f"/api/v1/datasets/{dataset_id}/report", headers=headers)
    assert response.status_code == 200
    with open(path, "rb") as original:
        after = hashlib.sha256(original.read()).hexdigest()
    assert before == after


def test_unavailable_model_importance_is_structured(tmp_path):
    from sklearn.dummy import DummyClassifier
    import joblib

    model = DummyClassifier(strategy="most_frequent").fit([[0], [1]], [0, 1])
    path = tmp_path / "dummy.joblib"
    joblib.dump(model, path)
    assert get_feature_importance(str(path), "DummyClassifier", ["signal"]) is None


def test_experiment_report_contains_ranking_and_feature_importance():
    headers = support._register_and_login(support._unique_email())
    dataset_id = support._upload_csv(headers, support._make_cls_csv())
    ml_ready_id = support._prepare(headers, dataset_id)
    experiment = support._post_exp(headers, dataset_id, ml_ready_id)
    assert experiment.status_code == 200, experiment.json()
    experiment_id = experiment.json()["experiment_id"]

    response = support.client.post(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/report",
        headers=headers,
    )
    assert response.status_code == 200, response.json()
    summary = response.json()["report_data"]["experiment_summary"]
    assert summary["models_trained"] == 3
    assert summary["evaluation"]["best_model_id"] is not None
    assert len(summary["evaluation"]["model_rankings"]) == 3
    assert summary["feature_importance"]["is_available"] is True
    assert summary["feature_importance"]["features"][0]["feature_name"] in {
        "num",
        "cat_A",
        "cat_B",
    }