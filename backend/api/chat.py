import os
import json
from flask import Blueprint, request, jsonify
from backend.prompt_lab import ask_agent

chat_bp = Blueprint('chat', __name__)

# Phase 1: in-memory sessions (replaced by DB in Phase 4)
sessions = {}

AGENT_MAP = {
    "WORKOUT":   ("workout_planner",    0.3),
    "NUTRITION": ("nutrition_agent",    0.1),
    "PROGRESS":  ("progress_analyst",   0.2),
    "EMOTIONAL": ("motivational_coach", 0.75),
    "ASSESSMENT":("workout_planner",    0.3),
    "RECOVERY":  ("recovery_agent",     0.2),
    "GENERAL":   ("workout_planner",    0.4),
}

def try_parse_json(text):
    """Try to extract and parse JSON from text, handling nested braces."""
    try:
        start = text.find('{')
        if start == -1:
            return None
        
        # Count braces to find the matching closing brace
        brace_count = 0
        for i in range(start, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_str = text[start:i+1]
                    return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        pass
    return None

def format_agent_response(agent_name: str, structured: dict) -> str:
    """Convert structured JSON responses into clean, actionable markdown for the user."""
    if agent_name == 'workout_planner' and 'workout' in structured:
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

    if agent_name == 'nutrition_agent' and 'calculation' in structured:
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

    if agent_name == 'progress_analyst' and 'findings' in structured:
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

    if agent_name == 'recovery_agent' and 'recovery_status' in structured:
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

    # Fallback — return summary or a friendly message
    return structured.get('summary', '') or "Here's your result!"


@chat_bp.route('/api/chat/start', methods=['POST'])
def start_session():
    session_id = os.urandom(16).hex()
    sessions[session_id] = {"history": [], "user_profile": {}}
    return jsonify({
        "session_id": session_id,
        "welcome": "ForgeAI coaching session started."
    })


@chat_bp.route('/api/chat/send', methods=['POST'])
def send_message():
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message', '').strip()

    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid session'}), 400
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    session = sessions[session_id]
    history = session['history']

    # 1. Supervisor routes the message
    routing_result = ask_agent(
        "supervisor", user_message,
        temperature=0.1,
        conversation_history=history
    )
    route_data = routing_result.get('structured_response') or {}
    routes = route_data.get('route', ['GENERAL'])
    needs_clarification = route_data.get('needs_clarification', False)
    clarification = route_data.get('clarification_question')

    # 2. Handle clarification
    if needs_clarification and clarification:
        return jsonify({
            "response": clarification,
            "agent_used": "supervisor",
            "routing": route_data,
            "needs_clarification": True
        })

    # 3. Route to primary specialist
    primary_route = routes[0] if routes else 'GENERAL'
    agent_name, temperature = AGENT_MAP.get(primary_route, ("workout_planner", 0.4))

    specialist = ask_agent(
        agent_name, user_message,
        temperature=temperature,
        conversation_history=history
    )

    # After getting specialist response, format it for display
    raw = specialist['raw_response']
    structured = specialist['structured_response']

    # If the agent returned JSON, extract the human readable fields
    if structured:
        display_response = format_agent_response(agent_name, structured)
    else:
        # Try to parse JSON from the raw response if the LLM ignored the prompt
        parsed = try_parse_json(raw)
        if parsed:
            print(f"[DEBUG] Successfully parsed JSON from raw response for {agent_name}")
            display_response = format_agent_response(agent_name, parsed)
            structured = parsed  # Update structured so it's passed to frontend too
        else:
            print(f"[DEBUG] No JSON found in response from {agent_name}. Raw response length: {len(raw)}")
            display_response = raw

    # 4. Update history (keep last 20 messages = 10 turns)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "model", "content": specialist['raw_response']})
    sessions[session_id]['history'] = history[-20:]

    return jsonify({
        "response": display_response,
        "structured_response": structured,
        "agent_used": agent_name,
        "routing": route_data,
        "routes": routes,
        "tokens_used": specialist['token_count']
    })


@chat_bp.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'version': 'phase-1'})
