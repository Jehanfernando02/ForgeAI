"""
ForgeAI Phase 6: Token Usage & Cost Metrics
=============================================

Tracks LLM token usage and estimated cost per session.

Why does this matter?
  In production, every LLM call costs money. Senior engineers track
  cost per request so they can optimize prompts, reduce context window
  size, and detect runaway requests. This module provides that layer.

Pricing (approximate, Gemini 2.5 Flash as of July 2025):
  Input:  $0.075 per 1 million tokens
  Output: $0.30  per 1 million tokens

Usage:
    from backend.observability.metrics import record_llm_call, get_session_summary

    record_llm_call(session_id, "workout_planner", input_tokens=1200, output_tokens=400, latency_ms=1823)
    summary = get_session_summary(session_id)
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List

# Gemini 2.5 Flash pricing (USD per token)
GEMINI_25_FLASH_INPUT_COST_PER_TOKEN  = 0.075 / 1_000_000
GEMINI_25_FLASH_OUTPUT_COST_PER_TOKEN = 0.30  / 1_000_000


@dataclass
class CallMetrics:
    """
    Records token usage and cost for a single LLM invocation.

    Fields:
        agent:         Name of the agent that made the call
        input_tokens:  Number of tokens in the prompt (estimated)
        output_tokens: Number of tokens in the response (estimated)
        latency_ms:    Wall-clock time for the LLM call in milliseconds
        cost_usd:      Estimated cost of this call in US dollars
        timestamp:     Unix timestamp of when the call was made
    """
    agent: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    timestamp: float = field(default_factory=time.time)


class SessionMetrics:
    """
    Tracks all LLM calls for a single user session.

    Methods:
        record():       Add a new call record
        total_cost():   Sum of all call costs in USD
        total_tokens(): Sum of all input + output tokens
        to_dict():      Serialize to JSON-compatible dict for the API
    """

    def __init__(self):
        self.calls: List[CallMetrics] = []
        self.created_at: float = time.time()

    def record(
        self,
        agent: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float
    ) -> None:
        """Record a single LLM call and compute its estimated cost."""
        input_cost  = input_tokens  * GEMINI_25_FLASH_INPUT_COST_PER_TOKEN
        output_cost = output_tokens * GEMINI_25_FLASH_OUTPUT_COST_PER_TOKEN
        cost        = input_cost + output_cost

        self.calls.append(CallMetrics(
            agent=agent,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
        ))

    def total_cost(self) -> float:
        """Return total estimated cost in USD across all calls."""
        return sum(c.cost_usd for c in self.calls)

    def total_tokens(self) -> int:
        """Return total tokens (input + output) across all calls."""
        return sum(c.input_tokens + c.output_tokens for c in self.calls)

    def avg_latency_ms(self) -> float:
        """Return average latency per LLM call in milliseconds."""
        if not self.calls:
            return 0.0
        return sum(c.latency_ms for c in self.calls) / len(self.calls)

    def to_dict(self) -> dict:
        """Serialize metrics to a JSON-friendly dict for API responses."""
        return {
            "session_duration_seconds": round(time.time() - self.created_at, 2),
            "total_llm_calls":          len(self.calls),
            "total_tokens":             self.total_tokens(),
            "total_cost_usd":           round(self.total_cost(), 8),
            "avg_latency_ms":           round(self.avg_latency_ms(), 2),
            "pricing_model":            "gemini-2.5-flash",
            "calls": [
                {
                    "agent":         c.agent,
                    "input_tokens":  c.input_tokens,
                    "output_tokens": c.output_tokens,
                    "latency_ms":    round(c.latency_ms, 2),
                    "cost_usd":      round(c.cost_usd, 8),
                }
                for c in self.calls
            ]
        }


# ── Module-level session store ─────────────────────────────────────────────
# Simple in-memory dict: session_id → SessionMetrics
# In production this would be backed by Redis or a time-series database.
_session_metrics: Dict[str, SessionMetrics] = {}


def _get_or_create(session_id: str) -> SessionMetrics:
    """Return existing SessionMetrics for a session or create a new one."""
    if session_id not in _session_metrics:
        _session_metrics[session_id] = SessionMetrics()
    return _session_metrics[session_id]


def record_llm_call(
    session_id: str,
    agent: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float,
) -> None:
    """
    Record a single LLM call for a session.

    Args:
        session_id:    User's session identifier
        agent:         Name of the agent (e.g. "workout_planner")
        input_tokens:  Number of input tokens (use estimate_token_count() if exact count unavailable)
        output_tokens: Number of output tokens
        latency_ms:    Elapsed time for the LLM call in milliseconds
    """
    _get_or_create(session_id).record(agent, input_tokens, output_tokens, latency_ms)


def get_session_summary(session_id: str) -> dict:
    """
    Return the full metrics summary dict for a session.

    Returns an empty summary if no calls have been recorded yet.
    """
    if session_id not in _session_metrics:
        return {
            "session_duration_seconds": 0,
            "total_llm_calls": 0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "pricing_model": "gemini-2.5-flash",
            "calls": [],
        }
    return _session_metrics[session_id].to_dict()


def estimate_token_count(text: str) -> int:
    """
    Estimate the token count for a text string.

    Uses the standard heuristic of 4 characters ≈ 1 token.
    For precise counts, read from LLM response metadata when available.
    """
    return max(1, len(text) // 4)
