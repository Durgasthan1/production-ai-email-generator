
import json
import logging
from types import SimpleNamespace

import httpx
import pytest

from fastapi.testclient import TestClient
from groq import APIConnectionError, APITimeoutError

from main import app
from app import service
from app.rate_limit import limiter


client = TestClient(app)

API_URL = "/api/v1/emails/generate"
TEST_KEY = "test-only-application-key"

VALID_REQUEST = {
    "purpose": "Request two days of leave",
    "tone": "Formal",
    "recipient": "Manager"
}


@pytest.fixture(autouse=True)
def test_setup(monkeypatch):
    # Never use real API credentials in tests
    monkeypatch.setenv("APP_API_KEY", TEST_KEY)
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "5")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "memory")

    monkeypatch.setattr(
        service,
        "GROQ_API_KEY",
        "fake-groq-key-for-testing"
    )

    limiter.reset()
    yield
    limiter.reset()


def post_email(payload=None):
    return client.post(
        API_URL,
        json=payload or VALID_REQUEST,
        headers={"X-API-Key": TEST_KEY}
    )


def mock_groq(monkeypatch, content):
    """Replace the real Groq client with a fake."""

    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content)
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )
    )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: completion
            )
        )
    )

    monkeypatch.setattr(
        service,
        "Groq",
        lambda **kwargs: fake_client
    )


def mock_groq_error(monkeypatch, error):
    """Make the fake provider raise an exception."""

    def raise_error(**kwargs):
        raise error

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=raise_error
            )
        )
    )

    monkeypatch.setattr(
        service,
        "Groq",
        lambda **kwargs: fake_client
    )


def test_valid_llm_response(monkeypatch):
    mock_groq(
        monkeypatch,
        json.dumps({
            "subject": "Leave Request",
            "body": "Dear Manager, I request two days of leave."
        })
    )

    response = post_email()

    assert response.status_code == 200
    assert response.json()["subject"] == "Leave Request"


def test_invalid_llm_json(monkeypatch):
    mock_groq(
        monkeypatch,
        "This response is not valid JSON"
    )

    response = post_email()

    assert response.status_code == 502
    assert response.json()["detail"] == (
        "LLM provider unavailable or invalid response"
    )


def test_missing_llm_fields(monkeypatch):
    mock_groq(
        monkeypatch,
        json.dumps({
            "subject": "Leave Request"
        })
    )

    response = post_email()

    assert response.status_code == 502


def test_missing_groq_key(monkeypatch):
    monkeypatch.setattr(
        service,
        "GROQ_API_KEY",
        None
    )

    response = post_email()

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "LLM service not configured"
    )


def test_groq_connection_failure(monkeypatch):
    request = httpx.Request(
        "POST",
        "https://api.groq.com/openai/v1/chat/completions"
    )

    mock_groq_error(
        monkeypatch,
        APIConnectionError(request=request)
    )

    response = post_email()

    assert response.status_code == 502


def test_groq_timeout(monkeypatch):
    request = httpx.Request(
        "POST",
        "https://api.groq.com/openai/v1/chat/completions"
    )

    mock_groq_error(
        monkeypatch,
        APITimeoutError(request=request)
    )

    response = post_email()

    assert response.status_code == 502


def test_logs_and_request_id(monkeypatch, caplog):
    marker = "PRIVATE_EMAIL_CONTENT_123"

    mock_groq(
        monkeypatch,
        json.dumps({
            "subject": "Leave Request",
            "body": "Dear Manager, " + marker
        })
    )

    with caplog.at_level(
        logging.INFO,
        logger="email_generator"
    ):
        response = post_email()

    assert response.status_code == 200

    request_id = response.headers["X-Request-ID"]

    records = []

    for log_record in caplog.records:
        try:
            data = json.loads(log_record.getMessage())
            if data.get("event") in (
                "llm_generation",
                "http_request"
            ):
                records.append(data)
        except (ValueError, TypeError):
            continue

    events = {record["event"]: record for record in records}

    assert "llm_generation" in events
    assert "http_request" in events

    assert (
        events["llm_generation"]["request_id"]
        == request_id
    )

    assert (
        events["http_request"]["request_id"]
        == request_id
    )

    assert events["llm_generation"]["total_tokens"] == 150

    assert marker not in caplog.text
    assert TEST_KEY not in caplog.text
    assert "fake-groq-key-for-testing" not in caplog.text
