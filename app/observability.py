
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

request_id_context = ContextVar(
    "request_id",
    default=None
)

logger = logging.getLogger("email_generator")


def log_event(event: str, **fields):
    record = {
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat(),
        "event": event,
        "request_id": request_id_context.get(),
        **fields
    }

    logger.info(json.dumps(record))
