"""
ForgeAI Phase 2: Chat API
=========================

LangChain-powered chat endpoints with memory management and fact extraction.
Replaces Phase 1 raw API calls with composable chains.
"""

import os
from flask import Blueprint, request, jsonify

from backend.chains import build_conversation_flow, build_fact_extraction_chain
from backend.core import format_agent_response
from backend.memory_manager import MemoryManager

chat_bp = Blueprint('chat', __name__)

# Initialize memory manager (singleton)
memory = MemoryManager.get_instance()

# Build chains at startup
conversation_flow = build_conversation_flow()
fact_extractor = build_fact_extraction_chain()


# ============================================================================
# SESSION ENDPOINTS
# ============================================================================

@chat_bp.route('/api/chat/start', methods=['POST'])
def start_session():
    """
    Start a new conversation session.
    
    Returns:
        {
            "session_id": "...",
            "welcome": "ForgeAI coaching session started."
        }
    """
    # Create session in memory manager
    session = memory.create_session()
    
    return jsonify({
        "session_id": session.session_id,
        "welcome": "ForgeAI coaching session started."
    })


# ============================================================================
# MESSAGING ENDPOINTS
# ============================================================================

@chat_bp.route('/api/chat/send', methods=['POST'])
def send_message():
    """
    Send a message and get a response.
    
    Request:
        {
            "session_id": "...",
            "message": "..."
        }
    
    Response:
        {
            "response": "formatted markdown response",
            "structured_response": {...},
            "agent_used": "agent_name",
            "routing": {...},
            "routes": ["TAG1", "TAG2"],
            "needs_clarification": false,
            "session_stats": {...}
        }
    """
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message', '').strip()

    # Validate input
    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    try:
        # 1. Extract facts from user message
        fact_result = fact_extractor(user_message)
        facts = fact_result.get('structured_response', {}).get('facts', [])
        if facts:
            memory.add_facts(session_id, facts)

        # 2. Get conversation history
        history = memory.get_history(session_id)

        # 3. Run through conversation flow
        flow_result = conversation_flow(user_message, history)

        agent_used = flow_result.get('agent_used', 'unknown')
        route_data = flow_result.get('routing', {})
        raw_response = flow_result.get('raw_response', '')
        structured = flow_result.get('structured_response', {})
        needs_clarification = flow_result.get('needs_clarification', False)

        # 4. Format response for display
        if structured and not needs_clarification:
            display_response = format_agent_response(agent_used, structured)
        else:
            display_response = raw_response

        # 5. Update conversation history in memory
        memory.add_message(session_id, 'user', user_message)
        memory.add_message(session_id, 'model', raw_response)

        # 6. Record routing decision
        memory.record_routing(session_id, route_data, agent_used)

        # 7. Trim history to keep memory efficient
        memory.trim_history(session_id, keep_last_turns=10)

        return jsonify({
            "response": display_response,
            "structured_response": structured,
            "agent_used": agent_used,
            "routing": route_data,
            "routes": route_data.get('route', []),
            "needs_clarification": needs_clarification,
            "session_stats": memory.get_session_stats(session_id),
        })

    except Exception as e:
        print(f"[ERROR] Message processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to process message', 'detail': str(e)}), 500


# ============================================================================
# MEMORY & PROFILE ENDPOINTS
# ============================================================================

@chat_bp.route('/api/chat/facts', methods=['GET'])
def get_facts():
    """
    Get all extracted facts for a session.
    
    Query params:
        session_id: Session ID
    
    Returns:
        {
            "session_id": "...",
            "facts": [...],
            "profile": {
                "goals": {...},
                "measurements": {...},
                "preferences": {...}
            }
        }
    """
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
    """
    Update user profile directly.
    
    Request:
        {
            "session_id": "...",
            "goals": {...},
            "measurements": {...},
            "preferences": {...}
        }
    
    Returns:
        {
            "session_id": "...",
            "profile": {...}
        }
    """
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
    """
    Get conversation history for a session.
    
    Query params:
        session_id: Session ID
        limit: Max messages to return (default: all)
    
    Returns:
        {
            "session_id": "...",
            "history": [...]
        }
    """
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
    """
    Get complete session information and statistics.
    
    Query params:
        session_id: Session ID
    
    Returns:
        {
            "session_id": "...",
            "stats": {...},
            "profile": {...}
        }
    """
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


# ============================================================================
# HEALTH & DEBUG ENDPOINTS
# ============================================================================

@chat_bp.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'version': 'phase-2',
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
