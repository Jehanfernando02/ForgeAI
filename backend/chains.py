"""
ForgeAI Phase 3: LangChain Chains with Tool Support
======================================================

Composable chains for routing, specialist agents with tool calling,
and structured data extraction. Each chain can invoke tools during reasoning.
"""

from typing import Any, Dict, List, Optional
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate
from backend.core import get_llm, build_system_message, build_message_chain, extract_json_from_response
from backend.tools.registry import AGENT_TOOLS


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
    
    def agent_chain(user_message: str, conversation_history: list = None) -> Dict[str, Any]:
        """Execute specialist agent."""
        if conversation_history is None:
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
# TOOL-ENABLED AGENT CHAIN (Phase 3)
# ============================================================================

def build_tool_agent_chain(agent_name: str, temperature: float = 0.5, user_id: str = None):
    """
    Build an agent chain that can call tools during reasoning.

    This uses LangChain's create_react_agent to give the agent
    a ReAct reasoning loop — it can think, call a tool, observe
    the result, think again, and repeat until it has an answer.

    Args:
        agent_name: which specialist agent to build
        temperature: controls response creativity
        user_id: injected into tool calls automatically

    Returns:
        a runnable that accepts {"message": str, "history": list}
    """
    
    llm        = get_llm(temperature=temperature)
    tools      = AGENT_TOOLS.get(agent_name, [])
    sys_prompt = build_system_message(agent_name)

    # ReAct prompt template — tells the agent how to reason and use tools
    react_template = """{system_prompt}

You have access to these tools:
{{tools}}

Use this EXACT format when using tools:
Thought: [your reasoning about what to do next]
Action: [tool name exactly as listed]
Action Input: [tool parameters as JSON]
Observation: [tool result — filled in automatically]
... (repeat Thought/Action/Observation as needed)
Thought: I now have enough information to respond
Final Answer: [your complete response to the user in markdown]

If you don't need tools, respond directly:
Thought: I can answer this directly
Final Answer: [your response]

User ID for tool calls: {user_id}

Conversation history:
{{chat_history}}

Current question: {{input}}
{{agent_scratchpad}}"""

    if not tools:
        # If no tools available, fall back to basic chain
        return build_agent_chain(agent_name, temperature)

    try:
        prompt = PromptTemplate(
            template=react_template.format(
                system_prompt=sys_prompt,
                user_id=user_id or "unknown"
            ),
            input_variables=["input", "tools", "tool_names",
                             "agent_scratchpad", "chat_history"]
        )

        agent = create_react_agent(llm=llm, tools=tools, prompt=prompt)

        executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=False,
            max_iterations=5,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )

        def run(inputs: dict) -> dict:
            history      = inputs.get("history", [])
            chat_history = "\n".join(
                f"{'User' if t['role']=='user' else 'Assistant'}: {t['content']}"
                for t in history[-6:]  # Last 3 turns for context
            )
            try:
                result = executor.invoke({
                    "input": inputs["message"],
                    "chat_history": chat_history
                })
                raw      = result.get("output", "")
                steps    = result.get("intermediate_steps", [])
                tools_used = [
                    step[0].tool for step in steps
                    if hasattr(step[0], 'tool')
                ] if steps else []

                return {
                    "agent": agent_name,
                    "raw_response": raw,
                    "structured_response": extract_json_from_response(raw),
                    "tools_used": tools_used,
                    "steps": len(steps)
                }
            except Exception as e:
                print(f"[Tool Agent Error] {agent_name}: {str(e)}")
                return {
                    "agent": agent_name,
                    "raw_response": f"I encountered an issue: {str(e)}. Let me try to help directly.",
                    "structured_response": None,
                    "tools_used": [],
                    "error": str(e)
                }

        return run

    except Exception as e:
        print(f"[Chain Build Error] {agent_name}: {str(e)}")
        return build_agent_chain(agent_name, temperature)


# ============================================================================
# FULL CONVERSATION FLOW (HIGH-LEVEL ORCHESTRATOR)
# ============================================================================

def build_conversation_flow():
    """
    Build the complete conversation flow orchestrator.

    Combines supervisor routing -> specialist agent (with tools) -> response formatting.
    This is the main entry point for processing user messages in Phase 3.
    """
    supervisor = build_supervisor_chain()
    
    # Map routes to agent names and temperatures
    AGENT_CONFIG = {
        "WORKOUT": ("workout_planner", 0.3),
        "NUTRITION": ("nutrition_agent", 0.1),
        "PROGRESS": ("progress_analyst", 0.2),
        "EMOTIONAL": ("motivational_coach", 0.75),
        "ASSESSMENT": ("workout_planner", 0.3),
        "RECOVERY": ("recovery_agent", 0.2),
        "GENERAL": ("workout_planner", 0.4),
    }
    
    def conversation_flow(
        user_message: str,
        conversation_history: list = None,
        user_id: str = None
    ) -> Dict[str, Any]:
        """Process a user message through the full flow."""
        if conversation_history is None:
            conversation_history = []
        
        # Step 1: Supervisor routing
        routing_result = supervisor(user_message, conversation_history)
        route_data = routing_result.get('structured_response', {})
        routes = route_data.get('route', ['GENERAL'])
        needs_clarification = route_data.get('needs_clarification', False)
        clarification = route_data.get('clarification_question')
        
        # Step 2: Handle clarification
        if needs_clarification and clarification:
            return {
                "response": clarification,
                "agent_used": "supervisor",
                "routing": route_data,
                "needs_clarification": True,
                "structured_response": {},
                "tools_used": [],
            }
        
        # Step 3: Route to primary specialist
        primary_route = routes[0] if routes else 'GENERAL'
        agent_name, temperature = AGENT_CONFIG.get(primary_route, ("workout_planner", 0.4))
        
        # Build tool-enabled agent for Phase 3
        specialist_chain = build_tool_agent_chain(agent_name, temperature, user_id=user_id)
        specialist_result = specialist_chain({
            "message": user_message,
            "history": conversation_history
        })
        
        return {
            "agent_used": agent_name,
            "routing": route_data,
            "routes": routes,
            "raw_response": specialist_result.get('raw_response', ''),
            "structured_response": specialist_result.get('structured_response', {}),
            "needs_clarification": False,
            "tools_used": specialist_result.get('tools_used', []),
        }
    
    return conversation_flow
