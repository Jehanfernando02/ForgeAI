"""
ForgeAI Phase 2: LangChain Chains
==================================

Composable chains for routing, specialist agents, and structured data extraction.
Each chain is built to be testable and reusable across different contexts.
"""

import json
from typing import Any, Dict, List
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import JsonOutputParser
from backend.core import (
    get_llm,
    build_system_message,
    build_message_chain,
    extract_json_from_response,
)


# ============================================================================
# SUPERVISOR ROUTING CHAIN
# ============================================================================

def build_supervisor_chain():
    """
    Build the supervisor routing chain.
    
    Returns:
        A chain that takes (user_message, conversation_history) 
        and returns structured routing decisions as JSON
    
    Output format:
    {
        "route": ["TAG1", "TAG2"],
        "reasoning": "...",
        "urgency": "normal|high",
        "needs_clarification": false,
        "clarification_question": null
    }
    """
    llm = get_llm(temperature=0.1)  # Low temperature for consistency
    
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
# SPECIALIST AGENT CHAINS (GENERIC FACTORY)
# ============================================================================

def build_agent_chain(agent_name: str, temperature: float = 0.3):
    """
    Build a specialist agent chain.
    
    Generic factory that works for any specialist agent (workout_planner,
    nutrition_agent, progress_analyst, motivational_coach, recovery_agent).
    
    Args:
        agent_name: Name of the specialist agent (must match prompt file)
        temperature: LLM temperature for this agent
    
    Returns:
        A chain that takes (user_message, conversation_history)
        and returns the agent's response with structured data extraction
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
# WORKOUT LOGGING CHAIN (STRUCTURED DATA EXTRACTION)
# ============================================================================

def build_workout_log_chain():
    """
    Build a chain specifically for parsing user workout logs.
    
    Returns:
        A chain that takes a workout description and returns:
    {
        "exercise": "name",
        "sets": 3,
        "reps": 10,
        "weight_kg": 50,
        "difficulty_rating": 7,
        "notes": "felt strong"
    }
    """
    llm = get_llm(temperature=0.0)  # Deterministic for data extraction
    
    system_prompt = """You are a workout logging assistant. Parse the user's workout description and extract:
- exercise name
- sets completed
- reps per set
- weight used (in kg)
- difficulty rating (1-10)
- any notes

Return ONLY valid JSON, no other text. If any field is missing, use null.

{
    "exercise": "...",
    "sets": null,
    "reps": null,
    "weight_kg": null,
    "difficulty_rating": null,
    "notes": "..."
}"""
    
    def workout_log_chain(workout_description: str) -> Dict[str, Any]:
        """Parse a workout log entry."""
        messages = build_message_chain(system_prompt, [], workout_description)
        response = llm.invoke(messages)
        response_text = response.content
        
        structured = extract_json_from_response(response_text)
        if not structured:
            structured = {}
        
        return {
            "raw_response": response_text,
            "structured_response": structured,
        }
    
    return workout_log_chain


# ============================================================================
# NUTRITION LOGGING CHAIN (STRUCTURED DATA EXTRACTION)
# ============================================================================

def build_nutrition_log_chain():
    """
    Build a chain specifically for parsing user meal logs.
    
    Returns:
        A chain that takes a meal description and returns:
    {
        "food_items": ["item1", "item2"],
        "estimated_calories": 500,
        "protein_g": 25,
        "carbs_g": 60,
        "fats_g": 15,
        "time_of_day": "breakfast|lunch|dinner|snack",
        "notes": "..."
    }
    """
    llm = get_llm(temperature=0.0)  # Deterministic for data extraction
    
    system_prompt = """You are a nutrition logging assistant. Parse the user's meal description and estimate:
- food items consumed
- total estimated calories
- protein grams
- carbohydrate grams
- fat grams
- time of day (breakfast, lunch, dinner, snack)
- any notes

Return ONLY valid JSON, no other text. Use reasonable estimates if exact values are unknown.

{
    "food_items": [...],
    "estimated_calories": null,
    "protein_g": null,
    "carbs_g": null,
    "fats_g": null,
    "time_of_day": "...",
    "notes": "..."
}"""
    
    def nutrition_log_chain(meal_description: str) -> Dict[str, Any]:
        """Parse a nutrition log entry."""
        messages = build_message_chain(system_prompt, [], meal_description)
        response = llm.invoke(messages)
        response_text = response.content
        
        structured = extract_json_from_response(response_text)
        if not structured:
            structured = {}
        
        return {
            "raw_response": response_text,
            "structured_response": structured,
        }
    
    return nutrition_log_chain


# ============================================================================
# FACT EXTRACTION CHAIN
# ============================================================================

def build_fact_extraction_chain():
    """
    Build a chain to extract user facts for memory storage.
    
    Takes any message and extracts key facts about the user
    (goals, body measurements, training preferences, etc.)
    
    Returns:
        A chain that returns:
    {
        "facts": ["fact1", "fact2", ...],
        "goal_updates": {"field": "value"},
        "measurements": {"weight_kg": 80}
    }
    """
    llm = get_llm(temperature=0.0)
    
    system_prompt = """Extract any user facts from this message. Look for:
- Body measurements (weight, height, body fat %)
- Fitness goals
- Exercise preferences
- Dietary preferences
- Injury history
- Training experience level
- Schedule/availability

Return JSON with:
- facts: list of extracted facts as strings
- goal_updates: dict of goal fields that changed
- measurements: dict of any body metrics

{
    "facts": [],
    "goal_updates": {},
    "measurements": {}
}"""
    
    def fact_extraction_chain(message: str) -> Dict[str, Any]:
        """Extract facts from a message."""
        messages = build_message_chain(system_prompt, [], message)
        response = llm.invoke(messages)
        response_text = response.content
        
        structured = extract_json_from_response(response_text)
        if not structured:
            structured = {"facts": [], "goal_updates": {}, "measurements": {}}
        
        return {
            "raw_response": response_text,
            "structured_response": structured,
        }
    
    return fact_extraction_chain


# ============================================================================
# FULL CONVERSATION FLOW (HIGH-LEVEL ORCHESTRATOR)
# ============================================================================

def build_conversation_flow():
    """
    Build the complete conversation flow orchestrator.
    
    Combines supervisor routing -> specialist agent -> response formatting.
    This is the main entry point for processing user messages.
    
    Returns:
        A function that takes (user_message, conversation_history)
        and returns the full processing result
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
        conversation_history: list = None
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
            }
        
        # Step 3: Route to primary specialist
        primary_route = routes[0] if routes else 'GENERAL'
        agent_name, temperature = AGENT_CONFIG.get(primary_route, ("workout_planner", 0.4))
        
        specialist_chain = build_agent_chain(agent_name, temperature)
        specialist_result = specialist_chain(user_message, conversation_history)
        
        return {
            "agent_used": agent_name,
            "routing": route_data,
            "routes": routes,
            "raw_response": specialist_result.get('raw_response', ''),
            "structured_response": specialist_result.get('structured_response', {}),
            "needs_clarification": False,
        }
    
    return conversation_flow
