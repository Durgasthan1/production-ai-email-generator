
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import rate_limit


@pytest.fixture(autouse=True)
def redis_test_mode(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "redis")


def test_redis_request_allowed(monkeypatch):
    class FakeLimiter:
        def limit(self, identifier):
            return SimpleNamespace(allowed=True)

    monkeypatch.setattr(
        rate_limit,
        "get_distributed_limiters",
        lambda: (FakeLimiter(), FakeLimiter())
    )

    rate_limit.check_rate_limit()


def test_redis_minute_limit_exceeded(monkeypatch):
    class FakeMinuteLimiter:
        def limit(self, identifier):
            return SimpleNamespace(allowed=False)

    class FakeDailyLimiter:
        def limit(self, identifier):
            return SimpleNamespace(allowed=True)

    monkeypatch.setattr(
        rate_limit,
        "get_distributed_limiters",
        lambda: (FakeMinuteLimiter(), FakeDailyLimiter())
    )

    with pytest.raises(HTTPException) as exc:
        rate_limit.check_rate_limit()

    assert exc.value.status_code == 429


def test_redis_daily_limit_exceeded(monkeypatch):
    class FakeMinuteLimiter:
        def limit(self, identifier):
            return SimpleNamespace(allowed=True)

    class FakeDailyLimiter:
        def limit(self, identifier):
            return SimpleNamespace(allowed=False)

    monkeypatch.setattr(
        rate_limit,
        "get_distributed_limiters",
        lambda: (FakeMinuteLimiter(), FakeDailyLimiter())
    )

    with pytest.raises(HTTPException) as exc:
        rate_limit.check_rate_limit()

    assert exc.value.status_code == 429


def test_redis_unavailable(monkeypatch):
    def broken_redis():
        raise ConnectionError("Redis unavailable")

    monkeypatch.setattr(
        rate_limit,
        "get_distributed_limiters",
        broken_redis
    )

    with pytest.raises(HTTPException) as exc:
        rate_limit.check_rate_limit()

    assert exc.value.status_code == 503
