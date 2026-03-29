"""
ForgeAI Phase 2: Core LangChain Configuration
==============================================

Provides LLM initialization, prompt loading, and message chain building utilities.
All chains in ForgeAI are built using these core components.
"""

import os
import json
from pathlib import Path
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# LLM CONFIGURATION
# ============================================================================

def get_llm(temperature: float = 0.3) -> ChatGoogleGenerativeAI:
    """
    Initialize and return a ChatGoogleGenerativeAI instance.
    
    Args:
        temperature: Controls randomness (0.0 = deterministic, 1.0 = creative)
    
    Returns:
        ChatGoogleGenerativeAI configured with ForgeAI settings
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")
    
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=temperature,
        google_api_key=api_key,
        top_p=0.95,
        top_k=40,
    )


# ============================================================================
# PROMPT LOADING
# ============================================================================

def load_prompt(agent_name: str) -> str:
    """
    Load a prompt file from the prompts directory.
    
    Args:
        agent_name: Name of the agent (e.g., 'supervisor', 'workout_planner')
    
    Returns:
        The full prompt text from the .md file
    
    Raises:
        FileNotFoundError: If the prompt file doesn't exist
    """
    prompt_path = Path(__file__).parent.parent / "prompts" / f"{agent_name}.md"
    
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    
    with open(prompt_path, 'r') as f:
        return f.read()


def build_system_message(agent_name: str) -> str:
    """
    Build a system message for an agent by loading its prompt.
    
    Args:
        agent_name: Name of the agent
    
    Returns:
        System message content string
    """
    return load_prompt(agent_name)


# ============================================================================
# MESSAGE CHAIN BUILDING
# ============================================================================

def build_message_chain(
    system_prompt: str,
    conversation_history: list,
    user_message: str
) -> list:
    """
    Build a complete message chain for LLM consumption.
    
    Args:
        system_prompt: System instructions for the LLM
        conversation_history: List of dicts with 'role' and 'content' keys
        user_message: The current user message
    
    Returns:
        List of message objects suitable for LLM API
    """
    messages = [SystemMessage(content=system_prompt)]
    
    # Add conversation history
    for msg in conversation_history:
        if msg['role'] == 'user':
            messages.append(HumanMessage(content=msg['content']))
        elif msg['role'] == 'model':
            messages.append(AIMessage(content=msg['content']))
    
    # Add current user message
    messages.append(HumanMessage(content=user_message))
    
    return messages


# ============================================================================
# JSON EXTRACTION UTILITIES
# ============================================================================

def extract_json_from_response(response_text: str) -> dict | None:
    """
    Extract and parse JSON from LLM response text.
    
    Handles nested JSON objects and partial responses gracefully.
    
    Args:
        response_text: Raw LLM response text
    
    Returns:
        Parsed JSON dict, or None if no valid JSON found
    """
    try:
        # Find the first opening brace
        start = response_text.find('{')
        if start == -1:
            return None
        
        # Count braces to find the matching closing brace
        brace_count = 0
        for i in range(start, len(response_text)):
            if response_text[i] == '{':
                brace_count += 1
            elif response_text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_str = response_text[start:i+1]
                    return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    
    return None


def extract_facts_from_message(message: str) -> list:
    """
    Extract key facts/entities from a user message for memory storage.
    
    Simple implementation: looks for fitness-related keywords and measurements.
    Could be enhanced with NER or dedicated extraction chain.
    
    Args:
        message: User message text
    
    Returns:
        List of extracted fact strings
    """
    facts = []
    
    # Simple keyword-based fact extraction
    keywords = {
        'weight': ['kg', 'lbs', 'lb', 'pounds', 'kilos'],
        'exercise': ['squat', 'bench', 'deadlift', 'press', 'curl', 'row', 'pull', 'push'],
        'goal': ['goal', 'target', 'want to', 'trying to', 'aim'],
        'injury': ['injury', 'pain', 'sore', 'hurt', 'ache'],
        'time': ['morning', 'afternoon', 'evening', 'night'],
    }
    
    message_lower = message.lower()
    
    for category, keywords_list in keywords.items():
        for keyword in keywords_list:
            if keyword in message_lower:
                # Extract a snippet around the keyword
                idx = message_lower.find(keyword)
                start = max(0, idx - 20)
                end = min(len(message), idx + len(keyword) + 20)
                snippet = message[start:end].strip()
                facts.append(snippet)
    
    return facts


# ============================================================================
# TOKEN COUNTING
# ============================================================================

def estimate_token_count(text: str) -> int:
    """
    Estimate token count for a text string.
    
    Uses a simple heuristic: ~4 characters per token.
    For precise counts, use the LLM's tokenizer.
    
    Args:
        text: Text to estimate tokens for
    
    Returns:
        Estimated token count
    """
    return len(text) // 4


# ============================================================================
# RESPONSE FORMATTING
# ============================================================================

def format_workout_response(structured: dict) -> str:
    """Format a structured workout response into readable markdown."""
    if 'workout' not in structured:
        return structured.get('summary', 'Workout plan created.')
    
    w = structured['workout']
    exercises = w.get('exercises', [])
    lines = [
        f"## {w.get('name', 'Your Workout')}",
        f"**Focus:** {w.get('focus', '')}  ",
        f"**Duration:** ~{w.get('estimated_duration_minutes', '?')} mins",
        "",
        "### Exercises",
    ]
    
    for ex in exercises:
        lines.append(
            f"- **{ex['name']}** — {ex['sets']} sets × {ex['reps']} reps · Rest {ex.get('rest_seconds', 60)}s · RPE {ex.get('rpe', '?')}"
        )
        lines.append(f"  *Cue: {ex.get('coaching_cue', '')}*")
    
    lines.append(f"\n---\n💬 {structured.get('coaching_note', '')}")
    lines.append(f"\n**Next session tip:** {structured.get('next_session_tip', '')}")
    
    return "\n".join(lines)


def format_nutrition_response(structured: dict) -> str:
    """Format a structured nutrition response into readable markdown."""
    if 'calculation' not in structured:
        return structured.get('summary', 'Nutrition plan created.')
    
    c = structured['calculation']
    tips = structured.get('practical_tips', [])
    tip_lines = "\n".join(f"- {t}" for t in tips)
    meal_tips = structured.get('meal_timing_tips', [])
    meal_tip_lines = "\n".join(f"- {t}" for t in meal_tips)
    
    return (
        f"## Your Nutrition Targets\n\n"
        f"| Metric | Value |\n|--------|-------|\n"
        f"| Calories | **{c.get('goal_calories', '?')} kcal** |\n"
        f"| Protein | **{c.get('protein_g', '?')}g** |\n"
        f"| Carbs | **{c.get('carb_g', '?')}g** |\n"
        f"| Fats | **{c.get('fat_g', '?')}g** |\n\n"
        f"{structured.get('summary', '')}\n\n"
        f"### How We Got Here\n{c.get('calculation_shown', '')}\n\n"
        f"### Meal Timing Tips\n{meal_tip_lines}\n\n"
        f"### Practical Tips\n{tip_lines}"
    )


def format_progress_response(structured: dict) -> str:
    """Format a structured progress analysis into readable markdown."""
    if 'findings' not in structured:
        return structured.get('summary', 'Progress report created.')
    
    findings = structured.get('findings', [])
    trend_emoji = {'improving': '📈', 'plateau': '➡️', 'declining': '📉'}
    lines = [
        f"## Progress Report\n",
        structured.get('summary', ''),
        "\n### Findings\n"
    ]
    
    for f in findings:
        emoji = trend_emoji.get(f.get('trend', ''), '•')
        lines.append(f"{emoji} **{f.get('metric', '')}** — {f.get('detail', '')}")
        lines.append(f"  → {f.get('recommendation', '')}\n")
    
    wins = structured.get('wins_to_celebrate', [])
    if wins:
        lines.append("### 🏆 Wins to Celebrate")
        for w in wins:
            lines.append(f"- {w}")
    
    lines.append(f"\n**Priority action:** {structured.get('priority_action', '')}")
    
    return "\n".join(lines)


def format_recovery_response(structured: dict) -> str:
    """Format a structured recovery status into readable markdown."""
    status_emoji = {'good': '✅', 'caution': '⚠️', 'rest_needed': '🛑'}
    emoji = status_emoji.get(structured.get('recovery_status', ''), '•')
    warnings = structured.get('warning_signs_detected', [])
    warning_lines = "\n".join(f"- ⚠️ {w}" for w in warnings) if warnings else ""
    
    return (
        f"{emoji} **Recovery Status: {structured.get('recovery_status', '').replace('_', ' ').title()}**\n\n"
        f"**Recommendation:** {structured.get('recommendation', '')}\n\n"
        f"**Today's suggestion:** {structured.get('todays_suggestion', '')}\n\n"
        f"{warning_lines}"
    )


def format_agent_response(agent_name: str, structured: dict) -> str:
    """
    Route structured response to appropriate formatter.
    
    Args:
        agent_name: Name of the agent that produced the response
        structured: Structured (JSON) response dict
    
    Returns:
        Formatted markdown string for display
    """
    formatters = {
        'workout_planner': format_workout_response,
        'nutrition_agent': format_nutrition_response,
        'progress_analyst': format_progress_response,
        'recovery_agent': format_recovery_response,
    }
    
    formatter = formatters.get(agent_name)
    if formatter:
        return formatter(structured)
    
    # Fallback
    return structured.get('summary', '') or "Here's your result!"
