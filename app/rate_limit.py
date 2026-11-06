
import os
import math
import time
import threading
import logging
from functools import lru_cache

from upstash_redis import Redis
from upstash_ratelimit import Ratelimit, FixedWindow

from collections import deque
from fastapi import HTTPException


class SlidingWindowLimiter:

    def __init__(self):
        self.timestamps = deque()
        self.lock = threading.Lock()

    def check(self):
        max_requests = int(
            os.getenv("RATE_LIMIT_REQUESTS", "5")
        )

        window_seconds = int(
            os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")
        )

        if max_requests < 1 or window_seconds < 1:
            raise RuntimeError(
                "Invalid rate-limit configuration"
            )

        now = time.monotonic()

        with self.lock:

            # Remove requests outside the time window
            while (
                self.timestamps
                and now - self.timestamps[0] >= window_seconds
            ):
                self.timestamps.popleft()

            # Reject requests exceeding the limit
            if len(self.timestamps) >= max_requests:
                retry_after = max(
                    1,
                    math.ceil(
                        window_seconds -
                        (now - self.timestamps[0])
                    )
                )

                raise HTTPException(
                    status_code=429,
                    detail="Application rate limit exceeded",
                    headers={
                        "Retry-After": str(retry_after)
                    }
                )

            # Record the accepted request
            self.timestamps.append(now)

    def reset(self):
        # For test isolation only
        with self.lock:
            self.timestamps.clear()


limiter = SlidingWindowLimiter()



@lru_cache(maxsize=1)
def get_distributed_limiters():

    redis = Redis.from_env()

    minute_limiter = Ratelimit(
        redis=redis,
        limiter=FixedWindow(
            max_requests=int(
                os.getenv("RATE_LIMIT_REQUESTS", "5")
            ),
            window=int(
                os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")
            )
        ),
        prefix="email:minute"
    )

    daily_limiter = Ratelimit(
        redis=redis,
        limiter=FixedWindow(
            max_requests=int(
                os.getenv("DAILY_RATE_LIMIT_REQUESTS", "100")
            ),
            window=86400
        ),
        prefix="email:daily"
    )

    return minute_limiter, daily_limiter


def check_rate_limit():

    backend = os.getenv(
        "RATE_LIMIT_BACKEND",
        "memory"
    )

    if backend == "memory":
        limiter.check()
        return

    if backend != "redis":
        raise HTTPException(
            status_code=503,
            detail="Rate limiter misconfigured"
        )

    try:
        minute_limiter, daily_limiter = (
            get_distributed_limiters()
        )

        for distributed_limiter in (
            minute_limiter,
            daily_limiter
        ):
            result = distributed_limiter.limit(
                "email-generator-global"
            )

            if not result.allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Application quota exceeded"
                )

    except HTTPException:
        raise

    except Exception:
        logging.exception(
            "Redis rate limiting failed"
        )

        raise HTTPException(
            status_code=503,
            detail="Rate limiting temporarily unavailable"
        )

