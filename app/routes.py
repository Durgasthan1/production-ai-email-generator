
from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from app.schemas import EmailRequest, EmailResponse

from app.service import (
    generate_email,
    LLMServiceError,
    LLMRateLimitError,
    LLMConfigurationError
)

from app.security import verify_api_key
from app.rate_limit import check_rate_limit


router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "healthy"}


@router.post(
    "/api/v1/emails/generate",
    response_model=EmailResponse,
    dependencies=[
        Depends(verify_api_key),
        Depends(check_rate_limit)
    ]
)
def create_email(request: EmailRequest):
    try:
        return generate_email(request)

    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=503,
            detail="LLM service not configured"
        ) from exc

    except LLMRateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="LLM provider rate limit exceeded"
        ) from exc

    except LLMServiceError as exc:
        raise HTTPException(
            status_code=502,
            detail="LLM provider unavailable or invalid response"
        ) from exc
