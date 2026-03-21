import os
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

    # 4. Update history (keep last 20 messages = 10 turns)
    history.append({"role": "user", "content": user_message})
    history.append({"role": "model", "content": specialist['raw_response']})
    sessions[session_id]['history'] = history[-20:]

    return jsonify({
        "response": specialist['raw_response'],
        "structured_response": specialist['structured_response'],
        "agent_used": agent_name,
        "routing": route_data,
        "routes": routes,
        "tokens_used": specialist['token_count']
    })


@chat_bp.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'version': 'phase-1'})
