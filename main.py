
import logging
import time
import uuid

from fastapi import FastAPI, Request
from app.routes import router
from app.observability import (
    request_id_context,
    log_event
)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

app = FastAPI(
    title="Production-Style AI Email Generator",
    description="FastAPI with managed LLM inference and observability",
    version="1.2.0"
)


@app.middleware("http")
async def observability_middleware(
    request: Request,
    call_next
):
    # Generate a unique ID for every API request
    request_id = str(uuid.uuid4())

    # Associate the ID with this request
    context_token = request_id_context.set(
        request_id
    )

    start_time = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code

        # Return request ID to the caller
        response.headers["X-Request-ID"] = request_id

        return response

    finally:
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        log_event(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=duration_ms
        )

        request_id_context.reset(context_token)


app.include_router(router)
