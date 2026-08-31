"""
Rate limiter for API requests.
Ensures maximum 60 requests per minute with token-bucket algorithm and backoff logic.
"""
from __future__ import annotations

import time
from typing import Optional


class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 60):
        self.capacity = float(max_requests_per_minute)
        self.tokens = float(max_requests_per_minute)
        self.fill_rate = float(max_requests_per_minute) / 60.0  # tokens per second
        self.last_update = time.monotonic()

    def acquire(self, tokens: float = 1.0) -> float:
        """
        Wait if necessary and acquire tokens.
        Returns the duration waited in seconds.
        """
        waited = 0.0
        while True:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.fill_rate)

            if self.tokens >= tokens:
                self.tokens -= tokens
                return waited

            needed = tokens - self.tokens
            sleep_time = needed / self.fill_rate
            time.sleep(sleep_time)
            waited += sleep_time
