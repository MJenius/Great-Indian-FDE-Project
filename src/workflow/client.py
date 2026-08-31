"""
HTTP Client for Competition Sandbox with Rate Limiting, Backoff, and Verification support.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional, Tuple
import requests

from .models import HttpMethod
from .rate_limiter import RateLimiter


class SandboxClientError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class SandboxClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8000/api/public/sandbox/v1",
        api_key: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
        max_retries: int = 3,
        timeout: float = 10.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.rate_limiter = rate_limiter or RateLimiter(max_requests_per_minute=60)
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def request(
        self,
        method: HttpMethod,
        endpoint: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[int, Any]:
        """
        Execute an HTTP request against the sandbox with rate limiting and exponential backoff for 429/5xx.
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = self._get_headers()

        retries = 0
        backoff = 1.0

        while True:
            self.rate_limiter.acquire()

            try:
                if method == HttpMethod.GET:
                    resp = self.session.get(url, headers=headers, timeout=self.timeout)
                elif method == HttpMethod.POST:
                    resp = self.session.post(url, headers=headers, json=payload, timeout=self.timeout)
                elif method == HttpMethod.PATCH:
                    resp = self.session.patch(url, headers=headers, json=payload, timeout=self.timeout)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Handle HTTP 429 (Rate Limit Exceeded)
                if resp.status_code == 429:
                    if retries >= self.max_retries:
                        raise SandboxClientError(f"HTTP 429 Rate Limit Exceeded after {retries} retries", status_code=429)
                    retry_after = resp.headers.get("Retry-After")
                    sleep_time = float(retry_after) if retry_after else backoff
                    time.sleep(sleep_time)
                    retries += 1
                    backoff *= 2.0
                    continue

                # Handle HTTP 5xx (Server Error: 500, 502, 503, 504)
                if 500 <= resp.status_code < 600:
                    if retries >= self.max_retries:
                        raise SandboxClientError(
                            f"HTTP {resp.status_code} Server Error after {retries} retries: {resp.text}",
                            status_code=resp.status_code,
                            response_body=resp.text,
                        )
                    time.sleep(backoff)
                    retries += 1
                    backoff *= 2.0
                    continue

                # Try parsing JSON body if possible
                try:
                    data = resp.json()
                except Exception:
                    data = resp.text

                # Handle Non-Retryable Client Errors (400, 401, 403, 404, 409)
                if 400 <= resp.status_code < 500 and resp.status_code != 429:
                    # Do NOT retry client errors
                    return resp.status_code, data

                return resp.status_code, data

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if retries >= self.max_retries:
                    raise SandboxClientError(f"Network error after {retries} retries: {str(e)}")
                time.sleep(backoff)
                retries += 1
                backoff *= 2.0
