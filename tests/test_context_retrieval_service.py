from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from app.config import get_settings
from app.main import app
from app.models.context_models import ContextRetrievalRequest
from app.services.context_retrieval_service import ContextRetrievalService


FIXTURE_POLICY_PATH = Path(__file__).resolve().parent / "fixtures" / "policysphere_lab"


@pytest.fixture(autouse=True)
def clear_settings(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_API_KEY", raising=False)
    monkeypatch.delenv("POLICYSPHERE_LAB_PATH", raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def restore_context_service():
    original_context_service = app.state.context_retrieval_service
    yield
    app.state.context_retrieval_service = original_context_service


def test_context_retrieval_succeeds_with_valid_fake_path(monkeypatch) -> None:
    monkeypatch.setenv("POLICYSPHERE_LAB_PATH", str(FIXTURE_POLICY_PATH))
    get_settings.cache_clear()
    service = ContextRetrievalService()

    response = service.run(
        ContextRetrievalRequest(
            feature_description="Add document upload retry visibility for failed processing.",
            mode="full",
            context={},
        )
    )

    assert response.source_files_loaded
    assert response.retrieval_confidence in {"high", "medium"}
    assert any(item.name == "DocumentUploadPage" for item in response.matched_ui_screens)


def test_context_retrieval_handles_missing_path_gracefully() -> None:
    service = ContextRetrievalService()

    response = service.run(
        ContextRetrievalRequest(
            feature_description="Investigate email resend handling.",
            mode="full",
            context={},
        )
    )

    assert response.retrieval_confidence == "low"
    assert response.source_files_loaded == []
    assert "POLICYSPHERE_LAB_PATH is not configured." in response.open_context_questions


def test_email_resend_request_matches_resend_artifacts(monkeypatch) -> None:
    monkeypatch.setenv("POLICYSPHERE_LAB_PATH", str(FIXTURE_POLICY_PATH))
    get_settings.cache_clear()
    service = ContextRetrievalService()

    response = service.run(
        ContextRetrievalRequest(
            feature_description="Support resend failed email from email history with retry visibility.",
            mode="full",
            context={},
        )
    )

    assert any(item.name == "failed_email_resend" for item in response.matched_features)
    assert any(item.name == "EmailHistoryPage" for item in response.matched_ui_screens)
    assert any(item.name == "POST /emails/{email_id}/resend" or item.name == "Email resend endpoint" for item in response.matched_api_endpoints)
    assert any(item.name == "email_history" for item in response.matched_database_tables)
    assert any(item.name == "email_resend_attempts" for item in response.matched_database_tables)
    assert any(item.name == "EmailHistoryResendTest" for item in response.matched_automation_tests)
    assert any("duplicate" in item.name.lower() for item in response.matched_known_defects)


def test_policy_comparison_request_matches_comparison_artifacts(monkeypatch) -> None:
    monkeypatch.setenv("POLICYSPHERE_LAB_PATH", str(FIXTURE_POLICY_PATH))
    get_settings.cache_clear()
    service = ContextRetrievalService()

    response = service.run(
        ContextRetrievalRequest(
            feature_description="Improve policy comparison for missing term metadata and sorting.",
            mode="story_only",
            context={},
        )
    )

    assert any(item.name == "policy_term_comparison" for item in response.matched_features)
    assert any(item.name == "PolicyComparisonPage" for item in response.matched_ui_screens)
    assert any("comparison" in item.name.lower() for item in response.matched_api_endpoints)
    assert any(item.name == "policy_terms" for item in response.matched_database_tables)
    assert any(item.name == "policy_comparisons" for item in response.matched_database_tables)


def test_document_upload_request_matches_upload_artifacts(monkeypatch) -> None:
    monkeypatch.setenv("POLICYSPHERE_LAB_PATH", str(FIXTURE_POLICY_PATH))
    get_settings.cache_clear()
    service = ContextRetrievalService()

    response = service.run(
        ContextRetrievalRequest(
            feature_description="Review document upload processing, upload status, and retry behavior for failed jobs.",
            mode="automation_only",
            context={},
        )
    )

    assert any(item.name == "document_upload_processing" for item in response.matched_features)
    assert any(item.name == "DocumentUploadPage" for item in response.matched_ui_screens)
    assert len(response.matched_api_endpoints) >= 2
    assert any(item.name == "document_uploads" for item in response.matched_database_tables)
    assert any(item.name == "document_processing_jobs" for item in response.matched_database_tables)


def test_retrieve_context_endpoint_returns_expected_packet(monkeypatch) -> None:
    monkeypatch.setenv("POLICYSPHERE_LAB_PATH", str(FIXTURE_POLICY_PATH))
    get_settings.cache_clear()
    app.state.context_retrieval_service = ContextRetrievalService()
    client = TestClient(app)

    response = client.post(
        "/retrieve-context",
        json={
            "feature_description": "Support resend failed email from email history.",
            "mode": "full",
            "context": {},
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["retrieval_confidence"] in {"high", "medium"}
    assert any(item["name"] == "failed_email_resend" for item in body["matched_features"])
