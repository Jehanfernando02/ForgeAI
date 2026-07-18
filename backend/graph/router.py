"""
ForgeAI Phase 5: Graph Routing Logic
======================================

These functions define the CONDITIONAL EDGES in the LangGraph.

In a directed graph, a conditional edge means: "after running this node,
look at the current state, and DECIDE which node(s) to visit next."

When route_after_supervisor returns a LIST, LangGraph fans out to all
listed nodes and runs them IN PARALLEL (both fire at the same time,
writing to agent_outputs concurrently using the operator.add reducer).
"""

from typing import List, Union
from langgraph.graph import END

from backend.graph.state import ForgeAIState


# Map supervisor route labels → graph node names
ROUTE_TO_NODE = {
    "WORKOUT":    "workout_planner",
    "ASSESSMENT": "workout_planner",
    "GENERAL":    "workout_planner",
    "NUTRITION":  "nutrition_agent",
    "PROGRESS":   "progress_analyst",
    "EMOTIONAL":  "motivational_coach",
    "RECOVERY":   "recovery_agent",   # recovery specialist (advice)
}


def route_after_supervisor(state: ForgeAIState) -> Union[List[str], str]:
    """
    Conditional edge: supervisor → specialist node(s).

    Called immediately after supervisor_node completes. Inspects the
    routes stored in state and returns either:
    - A single node name string  → routes to exactly one specialist
    - A list of node name strings → LangGraph fans out (parallel execution)
    - END                         → graph terminates (clarification needed)

    Design decision: deduplicate destinations to avoid firing the same
    agent twice if multiple routes resolve to the same node.
    """
    # If supervisor wants more info, end the graph immediately
    if state.get("needs_clarification"):
        print("[Router] Clarification needed — ending graph early.")
        return END

    routes: List[str] = state.get("routes", ["GENERAL"])
    destinations = []
    seen = set()

    for route in routes:
        node_name = ROUTE_TO_NODE.get(route)
        if node_name and node_name not in seen:
            destinations.append(node_name)
            seen.add(node_name)

    # Default fallback
    if not destinations:
        destinations = ["workout_planner"]

    print(f"[Router] Activating nodes: {destinations}")
    return destinations


def route_after_recovery_check(state: ForgeAIState) -> str:
    """
    Conditional edge: recovery_check → assembler.

    Currently always routes to assembler. Kept as a conditional edge
    so future versions can re-route to workout_planner if the plan
    was 'blocked' and needs to be regenerated.
    """
    flag = state.get("recovery_flag", "safe")

    if flag == "blocked":
        # In a production system, we might regenerate the workout plan.
        # For now, we pass the blocked flag to the assembler which will
        # include a strong warning in the final response.
        print("[Router] Recovery flag BLOCKED — notifying assembler.")

    return "assembler"
