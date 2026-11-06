
import os
import math
import time
import threading

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


def check_rate_limit():
    limiter.check()
