import hashlib
import io
import os

import pytest

from tests import test_experiments as support


@pytest.fixture(autouse=True)
def reset_end_to_end_state(monkeypatch):
    state = support._reset_state.__wrapped__(monkeypatch)
    next(state)
    yield
    next(state, None)


def _upload(headers, content):
    response = support.client.post(
        "/api/v1/datasets/upload",
        headers=headers,
        files={"file": ("pipeline.csv", io.BytesIO(content.encode()), "text/csv")},
    )
    assert response.status_code == 200, response.json()
    return response.json()


def _pipeline_csv(rows=30):
    lines = ["num,cat,target"]
    for index in range(1, rows + 1):
        lines.append(f"{index},{'A' if index % 2 else 'B'},{index % 2}")
    return "\n".join(lines) + "\n"


def _sha256(path):
    with open(path, "rb") as stream:
        return hashlib.sha256(stream.read()).hexdigest()


def _prediction_features(prepared):
    features = {}
    for column in prepared["numeric_columns"]:
        features[column] = 1.0
    for column in prepared["categorical_columns"]:
        features[column] = "A"
    return features


def test_complete_pipeline_preserves_artifacts_and_builds_final_report():
    headers = support._register_and_login(support._unique_email())
    uploaded = _upload(headers, _pipeline_csv())
    dataset_id = uploaded["dataset"]["dataset_id"]
    original_path = uploaded["dataset"]["file_path"]
    original_hash = _sha256(original_path)
    assert os.path.exists(original_path)

    dataset_list = support.client.get("/api/v1/datasets/", headers=headers)
    assert dataset_list.status_code == 200
    assert any(item["dataset_id"] == dataset_id for item in dataset_list.json()["datasets"])

    profile_first = support.client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
    profile_second = support.client.get(f"/api/v1/datasets/{dataset_id}/profile", headers=headers)
    assert profile_first.status_code == profile_second.status_code == 200
    assert profile_first.json() == profile_second.json()

    quality_first = support.client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
    quality_second = support.client.get(f"/api/v1/datasets/{dataset_id}/quality", headers=headers)
    assert quality_first.status_code == quality_second.status_code == 200
    assert quality_first.json() == quality_second.json()

    cleaned = support.client.post(f"/api/v1/datasets/{dataset_id}/clean", headers=headers)
    assert cleaned.status_code == 200, cleaned.json()
    cleaned_data = cleaned.json()
    cleaned_path = os.path.join(
        support._upload_dir,
        next(
            name
            for name in os.listdir(support._upload_dir)
            if "_cleaned_" in name
        ),
    )
    cleaned_hash = _sha256(cleaned_path)
    assert os.path.exists(cleaned_path)
    assert _sha256(original_path) == original_hash

    engineered = support.client.post(
        f"/api/v1/datasets/{dataset_id}/engineer_features", headers=headers
    )
    assert engineered.status_code == 200, engineered.json()
    engineered_data = engineered.json()
    engineered_path = os.path.join(
        support._upload_dir,
        next(
            name
            for name in os.listdir(support._upload_dir)
            if "_engineered_" in name
        ),
    )
    engineered_hash = _sha256(engineered_path)
    assert os.path.exists(engineered_path)
    assert _sha256(cleaned_path) == cleaned_hash

    prepared = support.client.post(
        f"/api/v1/datasets/{dataset_id}/prepare",
        headers=headers,
        json={"target_column": "target"},
    )
    assert prepared.status_code == 200, prepared.json()
    prepared_data = prepared.json()
    ml_ready_path = os.path.join(
        support._upload_dir,
        next(
            name
            for name in os.listdir(support._upload_dir)
            if "_ml_ready_" in name
        ),
    )
    preprocessor_path = os.path.join(
        support._upload_dir,
        next(
            name
            for name in os.listdir(support._upload_dir)
            if "_preprocessor_" in name
        ),
    )
    assert os.path.exists(ml_ready_path)
    assert os.path.exists(preprocessor_path)
    assert prepared_data["target_column"] not in prepared_data["feature_names"]
    assert _sha256(engineered_path) == engineered_hash

    repeated_prepare = support.client.post(
        f"/api/v1/datasets/{dataset_id}/prepare",
        headers=headers,
        json={"target_column": "target"},
    )
    assert repeated_prepare.status_code == 200
    assert any("_ml_ready_" in name for name in os.listdir(support._upload_dir))

    experiment = support._post_exp(
        headers, dataset_id, prepared_data["ml_ready_dataset_id"]
    )
    assert experiment.status_code == 200, experiment.json()
    experiment_data = experiment.json()
    experiment_id = experiment_data["experiment_id"]
    assert experiment_data["status"] == "completed"
    assert experiment_data["best_model_id"] is not None

    model_paths = [
        os.path.join(support._model_dir, name)
        for name in os.listdir(support._model_dir)
        if name.endswith(".joblib")
    ]
    assert experiment_data["models"]
    assert model_paths
    assert all(os.path.exists(path) for path in model_paths)

    evaluation = support.client.post(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/evaluate",
        headers=headers,
    )
    assert evaluation.status_code == 200, evaluation.json()
    comparison = support.client.get(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/comparison",
        headers=headers,
    )
    assert comparison.status_code == 200, comparison.json()
    repeated_evaluation = support.client.post(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/evaluate",
        headers=headers,
    )
    assert repeated_evaluation.status_code == 200

    best = support.client.get(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/best",
        headers=headers,
    )
    assert best.status_code == 200, best.json()
    model_index = best.json()["model_id"]
    features = _prediction_features(prepared_data)

    single = support.client.post(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/models/{model_index}/predict",
        headers=headers,
        json={"features": features},
    )
    assert single.status_code == 200, single.json()
    assert "prediction" in single.json()

    batch = support.client.post(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/models/{model_index}/predict/batch",
        headers=headers,
        json={"rows": [features, features, features]},
    )
    assert batch.status_code == 200, batch.json()
    assert len(batch.json()["predictions"]) == 3

    explainability = support.client.get(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/models/{model_index}/explainability",
        headers=headers,
    )
    assert explainability.status_code == 200, explainability.json()
    assert explainability.json()["is_available"] is True
    assert explainability.json()["features"]

    generated_report = support.client.post(
        f"/api/v1/datasets/{dataset_id}/report", headers=headers
    )
    assert generated_report.status_code == 200, generated_report.json()
    report = generated_report.json()
    report_data = report["report_data"]
    assert report["status"] == "completed"
    assert report_data["dataset_summary"]["total_rows"] == 30
    assert report_data["quality_summary"] is not None
    assert report_data["cleaning_summary"] is not None
    assert report_data["feature_engineering_summary"] is not None
    assert report_data["ml_preparation_summary"] is not None
    assert report_data["experiment_summary"] is not None
    assert report_data["experiment_summary"]["evaluation"]["best_model_id"] is not None
    assert report_data["findings"]

    retrieved_report = support.client.get(
        f"/api/v1/datasets/{dataset_id}/report", headers=headers
    )
    assert retrieved_report.status_code == 200
    assert retrieved_report.json()["report_id"] == report["report_id"]

    persisted_report = support.client.get(
        f"/api/v1/datasets/{dataset_id}/report", headers=headers
    )
    assert persisted_report.status_code == 200
    assert persisted_report.json()["report_data"]["dataset_id"] == dataset_id
    persisted_experiment = support.client.get(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}",
        headers=headers,
    )
    assert persisted_experiment.status_code == 200
    assert persisted_experiment.json()["models"]
    persisted_evaluation = support.client.get(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/evaluation",
        headers=headers,
    )
    assert persisted_evaluation.status_code == 200
    persisted_predictions = support.client.get(
        f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/predictions",
        headers=headers,
    )
    assert persisted_predictions.status_code == 200
    assert persisted_predictions.json()["total_predictions"] >= 1
    assert _sha256(original_path) == original_hash
    assert _sha256(cleaned_path) == cleaned_hash
    assert _sha256(engineered_path) == engineered_hash


def test_pipeline_ownership_isolation_across_stages():
    owner_headers = support._register_and_login(support._unique_email())
    other_headers = support._register_and_login(support._unique_email())
    uploaded = _upload(owner_headers, _pipeline_csv())
    dataset_id = uploaded["dataset"]["dataset_id"]
    prepared = support.client.post(
        f"/api/v1/datasets/{dataset_id}/prepare",
        headers=owner_headers,
        json={"target_column": "target"},
    )
    assert prepared.status_code == 200
    experiment = support._post_exp(
        owner_headers, dataset_id, prepared.json()["ml_ready_dataset_id"]
    )
    assert experiment.status_code == 200
    experiment_id = experiment.json()["experiment_id"]

    protected_requests = [
        ("get", f"/api/v1/datasets/{dataset_id}/profile"),
        ("get", f"/api/v1/datasets/{dataset_id}/quality"),
        ("post", f"/api/v1/datasets/{dataset_id}/clean"),
        ("post", f"/api/v1/datasets/{dataset_id}/engineer_features"),
        ("post", f"/api/v1/datasets/{dataset_id}/prepare"),
        ("get", f"/api/v1/datasets/{dataset_id}/experiments"),
        ("get", f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}"),
        ("post", f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/evaluate"),
        ("get", f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/evaluation"),
        ("get", f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/predictions"),
        ("post", f"/api/v1/datasets/{dataset_id}/experiments/{experiment_id}/report"),
        ("post", f"/api/v1/datasets/{dataset_id}/report"),
        ("get", f"/api/v1/datasets/{dataset_id}/reports"),
    ]
    for method, path in protected_requests:
        request_kwargs = {"headers": other_headers}
        if path.endswith("/prepare"):
            request_kwargs["json"] = {"target_column": "target"}
        response = getattr(support.client, method)(path, **request_kwargs)
        assert response.status_code == 403, (method, path, response.json())
        assert "pipeline.csv" not in response.text
        assert uploaded["dataset"]["file_path"] not in response.text

    assert support.client.get(f"/api/v1/datasets/{dataset_id}/profile").status_code == 401
    assert support.client.get(f"/api/v1/datasets/{dataset_id}/report").status_code == 401


def test_pipeline_failure_recovery_and_invalid_inputs():
    headers = support._register_and_login(support._unique_email())
    uploaded = _upload(headers, _pipeline_csv(rows=2))
    dataset_id = uploaded["dataset"]["dataset_id"]
    original_hash = _sha256(uploaded["dataset"]["file_path"])

    missing_target = support.client.post(
        f"/api/v1/datasets/{dataset_id}/prepare",
        headers=headers,
        json={"target_column": "missing"},
    )
    assert missing_target.status_code == 400
    assert _sha256(uploaded["dataset"]["file_path"]) == original_hash

    no_experiment_report = support.client.post(
        f"/api/v1/datasets/{dataset_id}/experiments/999999/report",
        headers=headers,
    )
    assert no_experiment_report.status_code == 404

    invalid_model = support.client.post(
        f"/api/v1/datasets/{dataset_id}/experiments/999999/models/999999/predict",
        headers=headers,
        json={"features": {"num": 1, "cat": "A"}},
    )
    assert invalid_model.status_code == 404

    invalid_file = support.client.post(
        "/api/v1/datasets/upload",
        headers=headers,
        files={"file": ("broken.txt", io.BytesIO(b"not a dataset"), "text/plain")},
    )
    assert invalid_file.status_code == 400
