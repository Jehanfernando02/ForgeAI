"""
ForgeAI Phase 6: Sliding Window Rate Limiter
=============================================

Prevents any single session from sending too many messages in a short
time window, protecting against API cost runaway and abuse.

Algorithm: Sliding Window Counter
  - Each session has a queue of timestamps for recent requests.
  - Before allowing a new request, prune timestamps older than window_seconds.
  - If the remaining count >= max_calls, deny the request.
  - Otherwise, record the current timestamp and allow it.

This is more accurate than a fixed-window counter because it doesn't
allow bursts at window boundaries (e.g., 10 at 0:59 + 10 at 1:00).

Default: 10 messages per 60 seconds per session.

Usage:
    from backend.observability.rate_limiter import rate_limiter

    if not rate_limiter.check(session_id):
        return jsonify({"error": "Rate limit exceeded"}), 429

    remaining = rate_limiter.get_remaining(session_id)
"""

import time
from collections import deque
from typing import Dict


class RateLimiter:
    """
    In-memory sliding window rate limiter.

    Args:
        max_calls:       Maximum number of allowed calls within the window.
        window_seconds:  Duration of the sliding window in seconds.
    """

    def __init__(self, max_calls: int = 10, window_seconds: int = 60):
        self.max_calls      = max_calls
        self.window_seconds = window_seconds
        # Maps session_id → deque of request timestamps (float UNIX time)
        self._windows: Dict[str, deque] = {}

    def _prune(self, session_id: str) -> deque:
        """Remove expired timestamps and return the active window."""
        now    = time.time()
        cutoff = now - self.window_seconds

        if session_id not in self._windows:
            self._windows[session_id] = deque()

        window = self._windows[session_id]
        while window and window[0] < cutoff:
            window.popleft()

        return window

    def check(self, session_id: str) -> bool:
        """
        Check if a new request from session_id is within the rate limit.

        Returns True (allowed) and records the timestamp.
        Returns False (denied) if the limit has been reached.
        """
        window = self._prune(session_id)

        if len(window) >= self.max_calls:
            return False

        window.append(time.time())
        return True

    def get_remaining(self, session_id: str) -> int:
        """
        Return the number of allowed calls remaining in the current window.
        """
        window = self._prune(session_id)
        return max(0, self.max_calls - len(window))

    def get_reset_seconds(self, session_id: str) -> int:
        """
        Return how many seconds until the oldest call in the window expires,
        freeing up a slot. Returns 0 if the window is not full.
        """
        window = self._prune(session_id)
        if not window or len(window) < self.max_calls:
            return 0
        return max(0, int(window[0] + self.window_seconds - time.time()))

    def get_limit_info(self, session_id: str) -> dict:
        """
        Return a dict with full rate limit status for inclusion in API headers.

        Compatible with the standard RateLimit-* HTTP header convention.
        """
        remaining = self.get_remaining(session_id)
        return {
            "limit":     self.max_calls,
            "remaining": remaining,
            "reset_in":  self.get_reset_seconds(session_id),
            "window_seconds": self.window_seconds,
        }


# ── Module-level singleton ─────────────────────────────────────────────────
# Import and use this instance throughout the application.
rate_limiter = RateLimiter(max_calls=10, window_seconds=60)
