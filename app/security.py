
import os
import secrets

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader


api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="Application API key"
)


def verify_api_key(
    api_key: str | None = Security(api_key_header)
):
    expected_key = os.getenv("APP_API_KEY")

    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="API authentication not configured"
        )

    if not api_key or not secrets.compare_digest(
        api_key,
        expected_key
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "APIKey"}
        )

    return True
