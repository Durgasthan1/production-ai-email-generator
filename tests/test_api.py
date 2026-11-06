
import uuid

import pytest
from fastapi.testclient import TestClient

from main import app
from app import routes
from app.schemas import EmailResponse
from app.service import LLMRateLimitError
from app.rate_limit import limiter


client = TestClient(app)

TEST_API_KEY = "test-only-secret-key"

VALID_REQUEST = {
    "purpose": "Request two days of leave",
    "tone": "Formal",
    "recipient": "Manager"
}


@pytest.fixture(autouse=True)
def configure_test_environment(monkeypatch):
    monkeypatch.setenv("APP_API_KEY", TEST_API_KEY)
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "5")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    limiter.reset()

    yield

    limiter.reset()


def authenticated_post(payload):
    return client.post(
        "/api/v1/emails/generate",
        json=payload,
        headers={"X-API-Key": TEST_API_KEY}
    )


def fake_generate_email(request):
    return EmailResponse(
        subject="Leave Request",
        body="Dear Manager, I request two days of leave."
    )


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_generate_email(monkeypatch):
    monkeypatch.setattr(
        routes,
        "generate_email",
        fake_generate_email
    )

    response = authenticated_post(VALID_REQUEST)

    assert response.status_code == 200
    assert response.json()["subject"] == "Leave Request"


def test_invalid_purpose():
    payload = {
        **VALID_REQUEST,
        "purpose": ""
    }

    response = authenticated_post(payload)

    assert response.status_code == 422


def test_invalid_tone():
    payload = {
        **VALID_REQUEST,
        "tone": "Unknown"
    }

    response = authenticated_post(payload)

    assert response.status_code == 422


def test_provider_rate_limit(monkeypatch):
    def mock_rate_limit(request):
        raise LLMRateLimitError()

    monkeypatch.setattr(
        routes,
        "generate_email",
        mock_rate_limit
    )

    response = authenticated_post(VALID_REQUEST)

    assert response.status_code == 429


def test_response_contains_request_id():
    response = client.get("/health")

    assert response.status_code == 200

    request_id = response.headers.get("X-Request-ID")

    assert request_id is not None
    uuid.UUID(request_id)


def test_unique_request_ids():
    response_1 = client.get("/health")
    response_2 = client.get("/health")

    assert (
        response_1.headers["X-Request-ID"]
        != response_2.headers["X-Request-ID"]
    )


def test_missing_api_key():
    response = client.post(
        "/api/v1/emails/generate",
        json=VALID_REQUEST
    )

    assert response.status_code == 401


def test_invalid_api_key():
    response = client.post(
        "/api/v1/emails/generate",
        json=VALID_REQUEST,
        headers={"X-API-Key": "incorrect-secret"}
    )

    assert response.status_code == 401


def test_application_rate_limit(monkeypatch):
    monkeypatch.setattr(
        routes,
        "generate_email",
        fake_generate_email
    )

    # First five requests should succeed
    for _ in range(5):
        response = authenticated_post(VALID_REQUEST)
        assert response.status_code == 200

    # Sixth request should be rejected
    response = authenticated_post(VALID_REQUEST)

    assert response.status_code == 429
    assert "Retry-After" in response.headers
