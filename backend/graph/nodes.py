"""
ForgeAI Phase 5: Graph Node Functions
=======================================

Each function in this file is a node in the LangGraph directed graph.

Contract:
  - Input:  the full ForgeAIState dict
  - Output: a partial dict containing ONLY the fields this node updates.
            LangGraph merges this partial dict back into the shared state.

Node execution order:
  rag_context_node → supervisor_node → [parallel specialists]
    → workout_planner_node → recovery_check_node → assembler_node
    → nutrition_agent_node ─────────────────────→ assembler_node
    → progress_analyst_node ────────────────────→ assembler_node
    → motivational_coach_node ──────────────────→ assembler_node
    → recovery_agent_node ──────────────────────→ assembler_node
"""

from typing import List
from backend.core import get_llm, extract_json_from_response
from backend.graph.state import ForgeAIState
from backend.memory.rag_pipeline import (
    build_rag_context,
    extract_and_store_facts,
    store_coaching_interaction
)


# ── Lazy imports to avoid circular deps at module load ────────────────────────

def _get_supervisor_chain():
    from backend.chains import build_supervisor_chain
    return build_supervisor_chain()


def _get_tool_agent_chain(agent_name: str, temperature: float, user_id: str):
    from backend.chains import build_tool_agent_chain
    return build_tool_agent_chain(agent_name, temperature, user_id=user_id)


def _friendly_error(e: Exception) -> str:
    """Delegate to chains._friendly_error for consistent messaging."""
    from backend.chains import _friendly_error as _fe
    return _fe(e)


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1: RAG Context — runs first, extracts facts from the user's message
# ─────────────────────────────────────────────────────────────────────────────

def rag_context_node(state: ForgeAIState) -> dict:
    """
    Extract permanent facts (injuries, goals, equipment) from the user message
    and persist them to ChromaDB.

    This node runs ONCE before all specialist agents, ensuring fact storage
    happens exactly once even when multiple agents run in parallel.

    Returns empty dict — side effect only (writes to ChromaDB).
    """
    session_id = state["session_id"]
    user_message = state["user_message"]

    try:
        extract_and_store_facts(session_id, user_message)
        print(f"[RAG Context Node] Fact extraction complete for session {session_id[:8]}...")
    except Exception as e:
        print(f"[RAG Context Node] Fact extraction failed: {e}")

    return {}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2: Supervisor — determines which specialist(s) to activate
# ─────────────────────────────────────────────────────────────────────────────

def supervisor_node(state: ForgeAIState) -> dict:
    """
    Route the user's message to the appropriate specialist agent(s).

    Uses the existing supervisor chain from Phase 3. The Supervisor reads
    the message, runs at temperature=0.1 for deterministic routing, and
    outputs a JSON routing decision.

    Returns: routes, needs_clarification, clarification_question
    """
    try:
        supervisor = _get_supervisor_chain()
        result = supervisor(state["user_message"], state["conversation_history"])
        route_data = result.get("structured_response", {})

        routes = route_data.get("route", ["GENERAL"])
        if not isinstance(routes, list):
            routes = ["GENERAL"]

        print(f"[Supervisor Node] Routes: {routes}")
        return {
            "routes": routes,
            "needs_clarification": route_data.get("needs_clarification", False),
            "clarification_question": route_data.get("clarification_question"),
        }
    except Exception as e:
        print(f"[Supervisor Node] Error: {e}")
        return {
            "routes": ["GENERAL"],
            "needs_clarification": False,
            "clarification_question": None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: Run a specialist agent and return its output dict
# ─────────────────────────────────────────────────────────────────────────────

def _run_specialist(
    agent_name: str,
    temperature: float,
    state: ForgeAIState
) -> dict:
    """
    Generic specialist runner. Builds RAG context, runs the ReAct agent,
    and returns a standardized output dict.
    """
    session_id = state["session_id"]
    user_message = state["user_message"]

    try:
        rag_context = build_rag_context(session_id, agent_name, user_message)
        enhanced_message = (
            f"{rag_context}\n\nUser Question: {user_message}"
            if rag_context else user_message
        )

        chain = _get_tool_agent_chain(agent_name, temperature, user_id=session_id)
        result = chain({"message": enhanced_message, "history": state["conversation_history"]})

        raw = result.get("raw_response", "")
        tools = result.get("tools_used", [])

        print(f"[{agent_name}] Responded. Tools used: {tools}")
        return {"response": raw, "agent": agent_name, "tools_used": tools}

    except Exception as e:
        print(f"[{agent_name}] Error: {e}")
        return {
            "response":   _friendly_error(e),
            "agent":      agent_name,
            "tools_used": [],
            "error":      str(e)
        }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3: Workout Planner
# ─────────────────────────────────────────────────────────────────────────────

def workout_planner_node(state: ForgeAIState) -> dict:
    """
    Run the Workout Planner specialist.

    Has access to: tool_get_workout_history, tool_search_exercises,
    tool_log_workout, tool_check_progressive_overload, tool_calculate_one_rep_max.

    After this node, the graph always routes to recovery_check_node
    to validate the proposed plan for injury risk.
    """
    output = _run_specialist("workout_planner", temperature=0.3, state=state)
    return {
        "agent_outputs": [output],
        "agents_used": ["workout_planner"],
        "tools_used": output.get("tools_used", []),
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4: Nutrition Agent
# ─────────────────────────────────────────────────────────────────────────────

def nutrition_agent_node(state: ForgeAIState) -> dict:
    """
    Run the Nutrition Agent specialist.

    Has access to: tool_calculate_tdee, tool_log_nutrition, tool_get_nutrition_history.
    """
    output = _run_specialist("nutrition_agent", temperature=0.1, state=state)
    return {
        "agent_outputs": [output],
        "agents_used": ["nutrition_agent"],
        "tools_used": output.get("tools_used", []),
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 5: Progress Analyst
# ─────────────────────────────────────────────────────────────────────────────

def progress_analyst_node(state: ForgeAIState) -> dict:
    """
    Run the Progress Analyst specialist.

    Has access to: tool_get_workout_history, tool_get_progress_metrics,
    tool_check_progressive_overload, tool_get_nutrition_history.
    """
    output = _run_specialist("progress_analyst", temperature=0.2, state=state)
    return {
        "agent_outputs": [output],
        "agents_used": ["progress_analyst"],
        "tools_used": output.get("tools_used", []),
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 6: Motivational Coach
# ─────────────────────────────────────────────────────────────────────────────

def motivational_coach_node(state: ForgeAIState) -> dict:
    """
    Run the Motivational Coach specialist.

    Operates at higher temperature (0.7) for more empathetic, varied responses.
    """
    output = _run_specialist("motivational_coach", temperature=0.7, state=state)
    return {
        "agent_outputs": [output],
        "agents_used": ["motivational_coach"],
        "tools_used": output.get("tools_used", []),
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 7: Recovery Agent (specialist for user recovery questions)
# ─────────────────────────────────────────────────────────────────────────────

def recovery_agent_node(state: ForgeAIState) -> dict:
    """
    Run the Recovery Specialist when the user asks about recovery, DOMS,
    rest days, or overtraining symptoms.

    This is the recovery SPECIALIST (gives advice), distinct from
    recovery_check_node which is the safety VALIDATOR for workout plans.
    """
    output = _run_specialist("recovery_agent", temperature=0.2, state=state)
    return {
        "agent_outputs": [output],
        "agents_used": ["recovery_agent"],
        "tools_used": output.get("tools_used", []),
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 8: Recovery Check — safety validator for proposed workout plans
# ─────────────────────────────────────────────────────────────────────────────

def recovery_check_node(state: ForgeAIState) -> dict:
    """
    Review any proposed workout plans in agent_outputs for injury/overtraining risk.

    This is NOT a specialist answering a recovery question — it is a safety
    gate that always runs after workout_planner_node. It checks the proposed
    plan against the user's stored injury profile and flags issues.

    Sets recovery_flag ("safe" | "caution" | "blocked") and recovery_note.
    Returns empty dict (no changes to state) if no workout plan was proposed.
    """
    workout_outputs = [
        o for o in state.get("agent_outputs", [])
        if o.get("agent") == "workout_planner"
    ]

    if not workout_outputs:
        # No workout was planned — safety check is a no-op
        return {"recovery_flag": "safe", "recovery_note": ""}

    session_id = state["session_id"]
    user_message = state["user_message"]
    workout_plan = workout_outputs[0].get("response", "")

    try:
        rag_context = build_rag_context(session_id, "recovery_agent", user_message)

        check_prompt = f"""You are a recovery and injury prevention specialist. 
Review the proposed workout plan below for safety risks based on the user's health context.

User Query: {user_message}
{f"User Health Context:{chr(10)}{rag_context}" if rag_context else ""}

Proposed Workout Plan:
{workout_plan[:2000]}

Respond ONLY with valid JSON (no other text):
{{
  "flag": "safe",
  "note": ""
}}

Values for flag:
- "safe": plan is appropriate, no concerns
- "caution": plan is acceptable but has minor risks worth mentioning  
- "blocked": plan could cause injury and should not be followed

Output ONLY the JSON object:"""

        llm = get_llm(temperature=0.0)
        response = llm.invoke(check_prompt)
        result = extract_json_from_response(response.content)

        if result and isinstance(result, dict):
            flag = result.get("flag", "safe")
            note = result.get("note", "")
            print(f"[Recovery Check] Flag: {flag} | Note: {note[:60] if note else 'none'}")
            return {
                "recovery_flag": flag,
                "recovery_note": note,
            }
    except Exception as e:
        print(f"[Recovery Check] Error: {e}")

    return {"recovery_flag": "safe", "recovery_note": ""}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 9: Assembler — final synthesis node
# ─────────────────────────────────────────────────────────────────────────────

def assembler_node(state: ForgeAIState) -> dict:
    """
    Synthesize all agent outputs into a single, coherent final response.

    Behaviour:
    - Clarification requested → returns the clarification question directly.
    - Single agent output → returns that response directly (no extra LLM call).
    - Multiple agent outputs → calls Gemini to synthesize into unified markdown.
    - Appends a recovery notice if recovery_flag is "caution" or "blocked".
    """
    # Case 1: Clarification needed — response was handled upstream
    if state.get("needs_clarification") and state.get("clarification_question"):
        return {"final_response": state["clarification_question"]}

    agent_outputs: List[dict] = state.get("agent_outputs", [])
    recovery_flag = state.get("recovery_flag", "safe")
    recovery_note = state.get("recovery_note", "")

    if not agent_outputs:
        return {"final_response": "I wasn't able to generate a response. Please try again."}

    # Case 2: Single agent — return directly
    if len(agent_outputs) == 1:
        response = agent_outputs[0].get("response", "")
        if recovery_note and recovery_flag in ("caution", "blocked"):
            flag_emoji = "⚠️" if recovery_flag == "caution" else "🛑"
            response += f"\n\n---\n{flag_emoji} **Recovery Notice:** {recovery_note}"
        return {"final_response": response}

    # Case 3: Multiple agents — synthesize with LLM
    combined = "\n\n".join([
        f"**{o.get('agent', 'unknown').replace('_', ' ').title()} Input:**\n{o.get('response', '')}"
        for o in agent_outputs
    ])

    recovery_section = ""
    if recovery_note and recovery_flag in ("caution", "blocked"):
        flag_emoji = "⚠️" if recovery_flag == "caution" else "🛑"
        recovery_section = f"\n\nRecovery Safety Notice ({recovery_flag.upper()}): {recovery_note}"

    synthesis_prompt = f"""You are the ForgeAI Master Coach. Multiple specialist coaches have provided their expert input below. Your job is to combine their advice into a single, coherent, well-structured response for the user.

RULES:
1. Do NOT simply concatenate — write a unified narrative.
2. Eliminate any repetition between specialists.
3. Use clear markdown headers (##) to separate major sections.
4. Preserve ALL specific numbers, exercise names, and recommendations.
5. The tone should be expert, encouraging, and direct.

User's Question: {state["user_message"]}

Specialist Inputs:
{combined}
{recovery_section}

Write the complete unified response now (in markdown):"""

    try:
        llm = get_llm(temperature=0.3)
        response = llm.invoke(synthesis_prompt)
        final = response.content

        # Append recovery notice if not already included
        if recovery_note and recovery_flag in ("caution", "blocked") and "Recovery Notice" not in final:
            flag_emoji = "⚠️" if recovery_flag == "caution" else "🛑"
            final += f"\n\n---\n{flag_emoji} **Recovery Notice:** {recovery_note}"

        return {"final_response": final}

    except Exception as e:
        print(f"[Assembler] Synthesis failed, returning first agent output: {e}")
        return {"final_response": agent_outputs[0].get("response", "Unable to generate response.")}
