"""
ForgeAI Phase 5: LangGraph Workflow Compilation
================================================

This module compiles the complete multi-agent StateGraph and exposes
run_graph() as the single entry point used by chains.py.

Graph topology:
  START
    │
    ▼
  rag_context          ← extracts facts, runs once before all agents
    │
    ▼
  supervisor           ← routing decision (conditional edges below)
    │
    ├──────────────────────────────────────────┐
    │ (workout route)          (nutrition route)│  ← parallel fan-out
    ▼                                          ▼
  workout_planner              nutrition_agent
    │                                          │
    ▼                                          │
  recovery_check               │               │
    │                          │               │
    └──────────────────────────┘               │
                 │                             │
                 ▼                             ▼
               assembler  ◄──────────────────
                 │
                 ▼
                END

All other specialists (progress_analyst, motivational_coach,
recovery_agent) connect directly to assembler, bypassing recovery_check.
"""

from langgraph.graph import StateGraph, START, END

from backend.graph.state import ForgeAIState
from backend.graph.nodes import (
    rag_context_node,
    supervisor_node,
    workout_planner_node,
    nutrition_agent_node,
    progress_analyst_node,
    motivational_coach_node,
    recovery_agent_node,
    recovery_check_node,
    assembler_node,
)
from backend.graph.router import route_after_supervisor, route_after_recovery_check


def build_graph():
    """
    Compile and return the ForgeAI multi-agent LangGraph.

    This function constructs the StateGraph, wires all nodes and
    conditional edges, and calls .compile() to produce an executable
    graph object.
    """
    workflow = StateGraph(ForgeAIState)

    # ── Register all nodes ─────────────────────────────────────────────────
    workflow.add_node("rag_context",      rag_context_node)
    workflow.add_node("supervisor",       supervisor_node)
    workflow.add_node("workout_planner",  workout_planner_node)
    workflow.add_node("nutrition_agent",  nutrition_agent_node)
    workflow.add_node("progress_analyst", progress_analyst_node)
    workflow.add_node("motivational_coach", motivational_coach_node)
    workflow.add_node("recovery_agent",   recovery_agent_node)
    workflow.add_node("recovery_check",   recovery_check_node)
    workflow.add_node("assembler",        assembler_node)

    # ── Entry point: START → rag_context → supervisor ──────────────────────
    workflow.add_edge(START, "rag_context")
    workflow.add_edge("rag_context", "supervisor")

    # ── Conditional fan-out: supervisor → specialist(s) or END ─────────────
    # route_after_supervisor returns a list for parallel or END for early exit.
    # The third argument is a list of ALL possible destination nodes so
    # LangGraph knows the complete set of reachable nodes from this edge.
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        [
            "workout_planner",
            "nutrition_agent",
            "progress_analyst",
            "motivational_coach",
            "recovery_agent",
            "recovery_check",
            END,
        ]
    )

    # ── Workout planner always runs through the safety check ────────────────
    workflow.add_edge("workout_planner", "recovery_check")

    # ── Conditional edge after recovery_check ──────────────────────────────
    # Always routes to assembler; kept conditional for future blocked re-gen.
    workflow.add_conditional_edges(
        "recovery_check",
        route_after_recovery_check,
        ["assembler"]
    )

    # ── All other specialists route directly to assembler ──────────────────
    workflow.add_edge("nutrition_agent",   "assembler")
    workflow.add_edge("progress_analyst",  "assembler")
    workflow.add_edge("motivational_coach","assembler")
    workflow.add_edge("recovery_agent",    "assembler")

    # ── Assembler is the final node ─────────────────────────────────────────
    workflow.add_edge("assembler", END)

    return workflow.compile()


# ── Module-level graph singleton ────────────────────────────────────────────
# Build the graph once at import time (cached for the lifetime of the process)
_graph = None


def get_graph():
    """Return the compiled graph, building it on first call."""
    global _graph
    if _graph is None:
        print("[Workflow] Compiling ForgeAI multi-agent graph...")
        _graph = build_graph()
        print("[Workflow] Graph compiled successfully.")
    return _graph


def run_graph(
    session_id: str,
    user_message: str,
    conversation_history: list,
) -> dict:
    """
    Execute the ForgeAI multi-agent graph for a single user message.

    Args:
        session_id:           User's session ID (used as user_id in ChromaDB)
        user_message:         The raw user input text
        conversation_history: List of previous turns [{role, content}]

    Returns:
        The final state dict after all nodes have executed.
        Key fields to read: final_response, agents_used, tools_used,
        routes, needs_clarification, recovery_flag.
    """
    # Provide all required state fields up front.
    # Fields annotated with operator.add (agent_outputs, agents_used,
    # tools_used) must be initialized as empty lists — LangGraph will
    # append to them as parallel nodes execute.
    initial_state: ForgeAIState = {
        "session_id":            session_id,
        "user_message":          user_message,
        "conversation_history":  conversation_history,
        "rag_context":           "",
        "routes":                [],
        "needs_clarification":   False,
        "clarification_question": None,
        "agent_outputs":         [],
        "agents_used":           [],
        "tools_used":            [],
        "recovery_flag":         "safe",
        "recovery_note":         "",
        "final_response":        "",
    }

    graph = get_graph()
    print(f"[Workflow] Running graph for session {session_id[:8]}... message: '{user_message[:60]}...'")
    
    final_state = graph.invoke(initial_state)
    print(f"[Workflow] Graph complete. Agents used: {final_state.get('agents_used', [])}")
    
    return final_state
