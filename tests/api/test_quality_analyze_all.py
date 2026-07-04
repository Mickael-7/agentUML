from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from agentics.api.app import create_app

client = TestClient(create_app())


def _req_result() -> dict:
    return {
        "is_valid": True,
        "report": {
            "clarity": {"highlights": [], "issues": []},
            "completeness": {"highlights": [], "issues": []},
            "consistency": {"highlights": [], "issues": []},
            "verifiability": {"highlights": [], "issues": []},
            "summary": "Documento adequado.",
            "suggestions": [],
        },
    }


def _uc_result(verdict: str = "correct") -> dict:
    return {
        "verdict": verdict,
        "checks": {"has_requirement": True, "has_use_case_context": True, "symbology_correct": None},
        "errors": [],
        "justification": "ok",
        "correction": "",
        "summary": "ok",
    }


@patch("agentics.config.Config.validate_llm", return_value=None)
@patch("agentics.api.routers.quality.create_llm_client", return_value=MagicMock())
@patch("agentics.api.routers.quality.RequirementsQualityAgent")
@patch("agentics.api.routers.quality.UseCaseExtractorAgent")
@patch("agentics.api.routers.quality.UseCaseDocumentEvaluator")
def test_returns_combined_shape(mock_eval, mock_extract, mock_req, _create, _val):
    mock_req.return_value.evaluate.return_value = _req_result()
    mock_extract.return_value.extract.return_value = [{"name": "Login", "text": "logar"}]
    mock_eval.return_value.evaluate_documents.return_value = [_uc_result("correct")]

    resp = client.post("/api/quality/analyze-all", data={"text": "REQ-001: O usuario deve logar."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["requirements"]["is_valid"] is True
    assert body["use_cases"][0]["name"] == "Login"
    assert body["use_cases"][0]["verdict"] == "correct"
    assert body["summary"] == {"use_cases_found": 1, "correct": 1, "incorrect": 0}


@patch("agentics.config.Config.validate_llm", return_value=None)
@patch("agentics.api.routers.quality.create_llm_client", return_value=MagicMock())
@patch("agentics.api.routers.quality.RequirementsQualityAgent")
@patch("agentics.api.routers.quality.UseCaseExtractorAgent")
@patch("agentics.api.routers.quality.UseCaseDocumentEvaluator")
def test_no_use_cases_extracted(mock_eval, mock_extract, mock_req, _create, _val):
    mock_req.return_value.evaluate.return_value = _req_result()
    mock_extract.return_value.extract.return_value = []

    resp = client.post("/api/quality/analyze-all", data={"text": "apenas dados"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["use_cases"] == []
    assert body["summary"]["use_cases_found"] == 0
    mock_eval.return_value.evaluate_documents.assert_called_once_with([])


def test_empty_text_returns_422():
    resp = client.post("/api/quality/analyze-all", data={"text": ""})
    assert resp.status_code == 422
