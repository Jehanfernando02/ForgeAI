"""
ForgeAI Phase 3: LangChain Chains with Tool Support
======================================================

Composable chains for routing, specialist agents with tool calling,
and structured data extraction. Each chain can invoke tools during reasoning.
"""

from typing import Any, Dict, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.prebuilt import create_react_agent
from backend.core import get_llm, build_system_message, build_message_chain, extract_json_from_response
from backend.tools.registry import AGENT_TOOLS
from backend.memory.rag_pipeline import build_rag_context, extract_and_store_facts, store_coaching_interaction


# ============================================================================
# SUPERVISOR ROUTING CHAIN (No tools)
# ============================================================================

def build_supervisor_chain():
    """
    Build the supervisor routing chain.
    
    Returns:
        A chain that takes (user_message, conversation_history) 
        and returns structured routing decisions as JSON
    """
    llm = get_llm(temperature=0.1)
    
    def supervisor_chain(user_message: str, conversation_history: list = None) -> Dict[str, Any]:
        """Execute supervisor routing."""
        if conversation_history is None:
            conversation_history = []
        
        system_prompt = build_system_message('supervisor')
        messages = build_message_chain(system_prompt, conversation_history, user_message)
        
        response = llm.invoke(messages)
        response_text = response.content
        
        # Extract JSON from response
        structured = extract_json_from_response(response_text)
        if not structured:
            # Fallback routing if extraction fails
            structured = {
                "route": ["GENERAL"],
                "reasoning": "Could not parse routing. Using default.",
                "urgency": "normal",
                "needs_clarification": False,
                "clarification_question": None
            }
        
        return {
            "raw_response": response_text,
            "structured_response": structured,
            "routing": structured,
        }
    
    return supervisor_chain


# ============================================================================
# BASIC AGENT CHAIN (No tools, Phase 2 compatibility)
# ============================================================================

def build_agent_chain(agent_name: str, temperature: float = 0.3):
    """
    Build a basic specialist agent chain (no tools).
    Used for fallback if tool execution fails.
    """
    llm = get_llm(temperature=temperature)
    
    def agent_chain(inputs) -> Dict[str, Any]:
        """Execute specialist agent."""
        # Handle both dict input {"message": ..., "history": ...} and direct args
        if isinstance(inputs, dict):
            user_message = inputs.get("message", "")
            conversation_history = inputs.get("history", [])
        else:
            user_message = inputs
            conversation_history = []
        
        if not isinstance(user_message, str):
            user_message = str(user_message)
        if not isinstance(conversation_history, list):
            conversation_history = []
        
        system_prompt = build_system_message(agent_name)
        messages = build_message_chain(system_prompt, conversation_history, user_message)
        
        response = llm.invoke(messages)
        response_text = response.content
        
        # Try to extract structured JSON from response
        structured = extract_json_from_response(response_text)
        
        return {
            "raw_response": response_text,
            "structured_response": structured or {},
            "agent_name": agent_name,
            "temperature": temperature,
        }
    
    return agent_chain


# ============================================================================
# TOOL-ENABLED AGENT CHAIN (Phase 3 / LangGraph Prebuilt ReAct)
# ============================================================================

def build_tool_agent_chain(agent_name: str, temperature: float = 0.5, user_id: str = None):
    """
    Build an agent chain that can call tools during reasoning.

    Uses langgraph.prebuilt.create_react_agent — the modern replacement for
    the deprecated langchain.agents.AgentExecutor pattern. This gives the
    agent a ReAct reasoning loop (Thought → Tool call → Observation → repeat)
    implemented as a compiled LangGraph StateGraph internally.

    Args:
        agent_name: which specialist agent to build
        temperature: controls response creativity
        user_id: injected into the system prompt for tool context

    Returns:
        a runnable that accepts {"message": str, "history": list}
    """
    llm        = get_llm(temperature=temperature)
    tools      = AGENT_TOOLS.get(agent_name, [])
    sys_prompt = build_system_message(agent_name)

    # Append user_id context to system prompt so tools can use it
    full_system_prompt = (
        f"{sys_prompt}\n\nUser ID for all tool calls: {user_id or 'unknown'}"
    )

    if not tools:
        # No tools for this agent — fall back to basic chain
        return build_agent_chain(agent_name, temperature)

    try:
        # create_react_agent from langgraph.prebuilt compiles a full
        # StateGraph with tool node internally. We invoke it directly.
        # NOTE: langgraph-prebuilt 1.0.x requires prompt to be a
        # SystemMessage object, not a raw string — raw strings cause
        # an internal .strip() call on a list → AttributeError.
        agent = create_react_agent(
            model=llm,
            tools=tools,
            prompt=SystemMessage(content=full_system_prompt),
        )

        def run(inputs: dict) -> dict:
            """Invoke the ReAct agent and return a standardized result dict."""
            user_message = inputs.get("message", "")
            history      = inputs.get("history", [])

            # Build message list: history turns + current message
            messages = []
            for turn in history[-6:]:   # Last 3 conversation turns
                role    = turn.get("role", "")
                content = turn.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                elif role == "model":
                    from langchain_core.messages import AIMessage
                    messages.append(AIMessage(content=content))

            messages.append(HumanMessage(content=user_message))

            try:
                result     = agent.invoke({"messages": messages})
                all_msgs   = result.get("messages", [])

                # The final AI message is the agent's answer
                raw = ""
                for msg in reversed(all_msgs):
                    if hasattr(msg, 'content') and msg.content and not hasattr(msg, 'tool_calls'):
                        raw = msg.content
                        break
                    # AIMessage with no tool_calls is the final answer
                    from langchain_core.messages import AIMessage as AIM
                    if isinstance(msg, AIM) and not getattr(msg, 'tool_calls', []):
                        raw = msg.content
                        break

                # Collect tool names from ToolMessages in the conversation
                from langchain_core.messages import ToolMessage
                tools_used = [
                    msg.name for msg in all_msgs
                    if hasattr(msg, 'name') and isinstance(msg, ToolMessage)
                ]

                return {
                    "agent":               agent_name,
                    "raw_response":        raw,
                    "structured_response": extract_json_from_response(raw) if raw else None,
                    "tools_used":          tools_used,
                }
            except Exception as e:
                print(f"[Tool Agent Error] {agent_name}: {str(e)}")
                return {
                    "agent":          agent_name,
                    "raw_response":   f"I encountered an issue processing your request: {str(e)}",
                    "structured_response": None,
                    "tools_used":     [],
                    "error":          str(e),
                }

        return run

    except Exception as e:
        print(f"[Chain Build Error] {agent_name}: {str(e)}")
        return build_agent_chain(agent_name, temperature)




# ============================================================================
# FULL CONVERSATION FLOW (HIGH-LEVEL ORCHESTRATOR)
# Phase 5: Delegates to LangGraph multi-agent workflow
# ============================================================================

def build_conversation_flow():
    """
    Build the complete conversation flow orchestrator.

    Phase 5 upgrade: This function now returns a closure that delegates
    to the LangGraph multi-agent workflow (backend/graph/workflow.py).

    The returned conversation_flow() function maintains the SAME interface
    as Phase 3 so that api/chat.py requires zero changes.

    Graph execution:
      rag_context → supervisor → [specialist(s)] → recovery_check → assembler

    Returns:
        A callable: (user_message, conversation_history, user_id) → dict
    """
    from backend.graph.workflow import run_graph

    def conversation_flow(
        user_message: str,
        conversation_history: list = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """Process a user message through the Phase 5 multi-agent graph."""
        if conversation_history is None:
            conversation_history = []

        # ── Execute the LangGraph ─────────────────────────────────────────
        final_state = run_graph(
            session_id=user_id or "anonymous",
            user_message=user_message,
            conversation_history=conversation_history,
        )

        raw_response    = final_state.get("final_response", "")
        agents_used     = final_state.get("agents_used", [])
        tools_used      = final_state.get("tools_used", [])
        routes          = final_state.get("routes", [])
        needs_clarif    = final_state.get("needs_clarification", False)
        clarif_question = final_state.get("clarification_question")
        recovery_flag   = final_state.get("recovery_flag", "safe")

        # Handle early-exit clarification path
        if needs_clarif and clarif_question:
            raw_response = clarif_question

        # Phase 4: Store coaching interaction in ChromaDB for long-term recall
        if user_id and raw_response:
            try:
                store_coaching_interaction(user_id, user_message, raw_response)
            except Exception as e:
                print(f"[Chains] store_coaching_interaction failed: {e}")

        # ── Return dict matching the contract expected by api/chat.py ─────
        return {
            "agent_used":          agents_used[0] if agents_used else "unknown",
            "agents_used":         agents_used,
            "routing":             {"route": routes},
            "routes":              routes,
            "raw_response":        raw_response,
            "structured_response": {},
            "needs_clarification": needs_clarif,
            "tools_used":          tools_used,
            "recovery_flag":       recovery_flag,
        }

    return conversation_flow

