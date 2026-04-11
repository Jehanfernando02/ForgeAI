"""
ForgeAI Phase 3: Chat API with Tool Support
"""

import os
from flask import Blueprint, request, jsonify

from backend.database import init_db
from backend.chains import build_conversation_flow
from backend.core import format_agent_response
from backend.memory_manager import MemoryManager

# Initialize database on startup
init_db()

chat_bp = Blueprint('chat', __name__)

# Initialize memory manager (singleton)
memory = MemoryManager.get_instance()

# Build chains at startup (Phase 3: with tool support)
conversation_flow = build_conversation_flow()


# Session endpoints

@chat_bp.route('/api/chat/start', methods=['POST'])
def start_session():
    """Start a new conversation session."""
    session = memory.create_session()
    
    return jsonify({
        "session_id": session.session_id,
        "welcome": "ForgeAI coaching session started."
    })


@chat_bp.route('/api/chat/send', methods=['POST'])
def send_message():
    """Send a message and get a response with tool usage."""
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message', '').strip()

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    try:
        history = memory.get_history(session_id)

        flow_result = conversation_flow(
            user_message,
            history,
            user_id=session_id
        )

        agent_used = flow_result.get('agent_used', 'unknown')
        route_data = flow_result.get('routing', {})
        raw_response = flow_result.get('raw_response', '')
        structured = flow_result.get('structured_response', {})
        needs_clarification = flow_result.get('needs_clarification', False)
        tools_used = flow_result.get('tools_used', [])

        if structured and not needs_clarification:
            display_response = format_agent_response(agent_used, structured)
        else:
            display_response = raw_response

        memory.add_message(session_id, 'user', user_message)
        memory.add_message(session_id, 'model', raw_response)

        memory.record_routing(session_id, route_data, agent_used)

        memory.trim_history(session_id, keep_last_turns=10)

        return jsonify({
            "response": display_response,
            "structured_response": structured,
            "agent_used": agent_used,
            "routing": route_data,
            "routes": route_data.get('route', []),
            "tools_used": tools_used,
            "needs_clarification": needs_clarification,
            "session_stats": memory.get_session_stats(session_id),
        })

    except Exception as e:
        print(f"[ERROR] Message processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to process message', 'detail': str(e)}), 500


@chat_bp.route('/api/chat/facts', methods=['GET'])
def get_facts():
    """Get all extracted facts for a session."""
    session_id = request.args.get('session_id')

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400

    profile = memory.get_profile(session_id)
    facts = memory.get_facts(session_id)

    return jsonify({
        "session_id": session_id,
        "facts": facts,
        "profile": {
            "goals": profile.goals,
            "measurements": profile.measurements,
            "preferences": profile.preferences,
        }
    })


@chat_bp.route('/api/chat/profile', methods=['POST'])
def update_profile():
    """Update user profile directly."""
    data = request.json
    session_id = data.get('session_id')

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400

    goals = data.get('goals')
    measurements = data.get('measurements')
    preferences = data.get('preferences')

    memory.update_profile(session_id, goals, measurements, preferences)
    profile = memory.get_profile(session_id)

    return jsonify({
        "session_id": session_id,
        "profile": {
            "goals": profile.goals,
            "measurements": profile.measurements,
            "preferences": profile.preferences,
        }
    })


@chat_bp.route('/api/chat/history', methods=['GET'])
def get_history():
    """Get conversation history for a session."""
    session_id = request.args.get('session_id')
    limit = request.args.get('limit', type=int)

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400

    history = memory.get_history(session_id, limit)

    return jsonify({
        "session_id": session_id,
        "history": history,
    })


@chat_bp.route('/api/chat/session-info', methods=['GET'])
def session_info():
    """Get complete session information and statistics."""
    session_id = request.args.get('session_id')

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400

    session = memory.get_session(session_id)
    stats = memory.get_session_stats(session_id)
    profile = session.user_profile

    return jsonify({
        "session_id": session_id,
        "stats": stats,
        "profile": {
            "goals": profile.goals,
            "measurements": profile.measurements,
            "preferences": profile.preferences,
            "facts_extracted": len(profile.facts),
        }
    })


@chat_bp.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'version': 'phase-3-tools',
        'active_sessions': len(memory.list_sessions()),
    })


@chat_bp.route('/api/debug/sessions', methods=['GET'])
def debug_sessions():
    """Debug endpoint: list all active sessions."""
    if os.getenv('ENVIRONMENT') != 'development':
        return jsonify({'error': 'Endpoint only available in development'}), 403

    sessions_list = []
    for session_id in memory.list_sessions():
        stats = memory.get_session_stats(session_id)
        sessions_list.append(stats)

    return jsonify({
        "total_sessions": len(sessions_list),
        "sessions": sessions_list,
    })


@chat_bp.route('/api/debug/session/<session_id>', methods=['GET'])
def debug_session(session_id):
    """Debug endpoint: get full session details."""
    if os.getenv('ENVIRONMENT') != 'development':
        return jsonify({'error': 'Endpoint only available in development'}), 403

    session_data = memory.export_session(session_id)
    if not session_data:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify(session_data)
