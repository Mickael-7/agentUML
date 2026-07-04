from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from agentics.api.app import create_app

client = TestClient(create_app())


def _canned(verdict: str) -> dict:
    return {
        "verdict": verdict,
        "checks": {
            "has_requirement": True,
            "has_use_case_context": True,
            "symbology_correct": True,
        },
        "errors": [],
        "justification": "x",
        "correction": "",
        "summary": "x",
    }


@patch("agentics.config.Config.validate_llm", return_value=None)
@patch("agentics.api.routers.quality.create_llm_client", return_value=MagicMock())
@patch("agentics.api.routers.quality.UseCaseDocumentEvaluator")
def test_empty_list_returns_422(mock_eval, _mock_create, _mock_validate):
    resp = client.post("/api/quality/use-cases", json={"documents": []})
    assert resp.status_code == 422
    mock_eval.assert_not_called()


@patch("agentics.config.Config.validate_llm", return_value=None)
@patch("agentics.api.routers.quality.create_llm_client", return_value=MagicMock())
@patch("agentics.api.routers.quality.UseCaseDocumentEvaluator")
def test_single_doc_no_ground_truth(mock_eval, _mock_create, _mock_validate):
    mock_eval.return_value.evaluate_documents.return_value = [_canned("correct")]
    resp = client.post(
        "/api/quality/use-cases",
        json={"documents": [{"name": "d1", "text": "..."}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["accuracy"] is None
    assert body["summary"]["correct"] == 1
    assert body["summary"]["evaluated"] == 1
    assert body["documents"][0]["verdict"] == "correct"
    assert body["documents"][0]["matches_expected"] is None


@patch("agentics.config.Config.validate_llm", return_value=None)
@patch("agentics.api.routers.quality.create_llm_client", return_value=MagicMock())
@patch("agentics.api.routers.quality.UseCaseDocumentEvaluator")
def test_accuracy_over_labeled_subset(mock_eval, _mock_create, _mock_validate):
    mock_eval.return_value.evaluate_documents.return_value = [
        _canned("correct"),
        _canned("incorrect"),
    ]
    resp = client.post(
        "/api/quality/use-cases",
        json={
            "documents": [
                {"name": "a", "text": "x", "expected_verdict": "correct"},
                {"name": "b", "text": "x", "expected_verdict": "correct"},
            ]
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # 1 of 2 labeled matched -> 50.0%
    assert body["summary"]["accuracy"] == 50.0
    assert body["documents"][0]["matches_expected"] is True
    assert body["documents"][1]["matches_expected"] is False


@patch("agentics.config.Config.validate_llm", return_value=None)
@patch("agentics.api.routers.quality.create_llm_client", return_value=MagicMock())
@patch("agentics.api.routers.quality.UseCaseDocumentEvaluator")
def test_max_documents_cap(mock_eval, _mock_create, _mock_validate):
    mock_eval.return_value.evaluate_documents.return_value = [_canned("correct")] * 2
    resp = client.post(
        "/api/quality/use-cases",
        json={
            "documents": [{"name": f"d{i}", "text": "x"} for i in range(5)],
            "max_documents": 2,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["total"] == 5
    assert body["summary"]["evaluated"] == 2
    sent = mock_eval.return_value.evaluate_documents.call_args.args[0]
    assert len(sent) == 2
