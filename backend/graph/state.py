"""
ForgeAI Phase 5: Shared Graph State
=====================================

ForgeAIState is the single source of truth that flows through every node
in the LangGraph directed acyclic graph.

Key design decisions:
- agent_outputs, agents_used, and tools_used use Annotated[List, operator.add]
  so that parallel nodes can each append to these fields without race conditions.
  LangGraph automatically merges them using the operator.add reducer.
- All other fields use simple overwrite semantics (last write wins).
"""

import operator
from typing import TypedDict, List, Optional, Annotated


class ForgeAIState(TypedDict):
    """
    The complete state object for the ForgeAI multi-agent graph.
    
    Every node receives the full state and returns a partial dict
    with only the fields it wants to update.
    """

    # ── Input ─────────────────────────────────────────────────────────────────
    session_id: str                    # User's session ID (used as user_id for ChromaDB)
    user_message: str                  # The raw user input
    conversation_history: List[dict]   # Previous turns [{role, content}, ...]

    # ── RAG context (populated by rag_context_node) ───────────────────────────
    rag_context: str                   # Retrieved user notes for context injection

    # ── Supervisor output ─────────────────────────────────────────────────────
    routes: List[str]                  # e.g. ["WORKOUT", "NUTRITION"]
    needs_clarification: bool          # True if supervisor wants more info
    clarification_question: Optional[str]  # The question to ask the user

    # ── Agent outputs (parallel-safe via operator.add) ────────────────────────
    # Each specialist node appends its result dict here.
    # The Annotated[List, operator.add] tells LangGraph: merge by concatenating.
    agent_outputs: Annotated[List[dict], operator.add]

    # Track which agents were used and which tools were called
    agents_used: Annotated[List[str], operator.add]
    tools_used: Annotated[List[str], operator.add]

    # ── Recovery safety check ─────────────────────────────────────────────────
    recovery_flag: str          # "safe" | "caution" | "blocked"
    recovery_note: str          # Brief note about any safety concerns

    # ── Final synthesized response ────────────────────────────────────────────
    final_response: str         # The combined, formatted response sent to the user
