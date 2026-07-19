"""
ForgeAI Phase 5 & 6: Chat API with LangGraph + LLMOps
======================================================

Changes from Phase 3:
  - conversation_flow now delegates to the LangGraph multi-agent workflow
  - configure_langsmith() called once at startup to enable tracing
  - Rate limiter enforces 10 messages per 60 seconds per session
  - /api/metrics/session endpoint exposes token cost data
  - /api/chat/send response includes rate_limit and session_metrics fields
"""

import os
import time
from flask import Blueprint, request, jsonify

from backend.database import init_db
from backend.chains import build_conversation_flow
from backend.core import configure_langsmith, format_agent_response
from backend.memory_manager import MemoryManager
from backend.observability.metrics import (
    record_llm_call,
    get_session_summary,
    estimate_token_count,
)
from backend.observability.rate_limiter import rate_limiter

# ── One-time startup configuration ────────────────────────────────────────────
init_db()
configure_langsmith()   # Phase 6: enable LangSmith tracing if API key is set

chat_bp = Blueprint('chat', __name__)

# Initialize memory manager (singleton)
memory = MemoryManager.get_instance()

# Build the Phase 5 LangGraph-backed conversation flow
conversation_flow = build_conversation_flow()


# ─────────────────────────────────────────────────────────────────────────────
# Session endpoints
# ─────────────────────────────────────────────────────────────────────────────

@chat_bp.route('/api/chat/start', methods=['POST'])
def start_session():
    """Start a new conversation session."""
    session = memory.create_session()

    return jsonify({
        "session_id": session.session_id,
        "welcome":    "ForgeAI coaching session started.",
    })


@chat_bp.route('/api/chat/send', methods=['POST'])
def send_message():
    """
    Send a message and get a response from the multi-agent graph.

    Phase 6 additions:
    - Rate limiting: returns HTTP 429 if session exceeds 10 msg/60s.
    - Metrics tracking: records estimated token cost for every call.
    - Response payload includes `rate_limit` and `session_metrics` fields.
    """
    data         = request.json
    session_id   = data.get('session_id')
    user_message = data.get('message', '').strip()

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400
    if not user_message:
        return jsonify({'error': 'Empty message'}), 400

    # ── Phase 6: Rate limiting ────────────────────────────────────────────
    if not rate_limiter.check(session_id):
        limit_info = rate_limiter.get_limit_info(session_id)
        return jsonify({
            'error':      'Rate limit exceeded',
            'detail':     f"Maximum {limit_info['limit']} messages per {limit_info['window_seconds']} seconds.",
            'reset_in_seconds': limit_info['reset_in'],
            'rate_limit': limit_info,
        }), 429

    try:
        history = memory.get_history(session_id)

        # ── Phase 5: LangGraph multi-agent call ──────────────────────────
        call_start = time.time()

        flow_result = conversation_flow(
            user_message,
            history,
            user_id=session_id,
        )

        call_latency_ms = (time.time() - call_start) * 1000

        agent_used         = flow_result.get('agent_used', 'unknown')
        agents_used        = flow_result.get('agents_used', [agent_used])
        route_data         = flow_result.get('routing', {})
        raw_response       = flow_result.get('raw_response', '')
        structured         = flow_result.get('structured_response', {})
        needs_clarification = flow_result.get('needs_clarification', False)
        tools_used         = flow_result.get('tools_used', [])
        recovery_flag      = flow_result.get('recovery_flag', 'safe')

        # Use raw_response as display response (Phase 5 assembler produces
        # markdown directly; structured formatting is a Phase 3 artifact)
        display_response = raw_response

        memory.add_message(session_id, 'user', user_message)
        memory.add_message(session_id, 'model', raw_response)
        memory.record_routing(session_id, route_data, agent_used)
        memory.trim_history(session_id, keep_last_turns=10)

        # ── Phase 6: Record token metrics ────────────────────────────────
        input_tokens  = estimate_token_count(user_message)
        output_tokens = estimate_token_count(raw_response)
        record_llm_call(
            session_id=session_id,
            agent=agent_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=call_latency_ms,
        )

        return jsonify({
            "response":          display_response,
            "structured_response": structured,
            "agent_used":        agent_used,
            "agents_used":       agents_used,
            "routing":           route_data,
            "routes":            route_data.get('route', []),
            "tools_used":        tools_used,
            "needs_clarification": needs_clarification,
            "recovery_flag":     recovery_flag,
            "session_stats":     memory.get_session_stats(session_id),
            # Phase 6 additions
            "rate_limit":        rate_limiter.get_limit_info(session_id),
            "session_metrics":   get_session_summary(session_id),
        })

    except Exception as e:
        print(f"[ERROR] Message processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': 'Failed to process message', 'detail': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────────
# Phase 6: Metrics endpoint
# ─────────────────────────────────────────────────────────────────────────────

@chat_bp.route('/api/metrics/session', methods=['GET'])
def session_metrics():
    """
    Return detailed LLM token usage and cost metrics for a session.

    Query params:
        session_id: The session identifier

    Response includes:
        - total_llm_calls
        - total_tokens (input + output)
        - total_cost_usd (estimated)
        - avg_latency_ms
        - per-call breakdown
    """
    session_id = request.args.get('session_id')

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400

    return jsonify({
        "session_id": session_id,
        "metrics":    get_session_summary(session_id),
    })


# ─────────────────────────────────────────────────────────────────────────────
# Existing helper endpoints (unchanged from Phase 3)
# ─────────────────────────────────────────────────────────────────────────────

@chat_bp.route('/api/chat/facts', methods=['GET'])
def get_facts():
    """Get all extracted facts for a session."""
    session_id = request.args.get('session_id')

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400

    profile = memory.get_profile(session_id)
    facts   = memory.get_facts(session_id)

    return jsonify({
        "session_id": session_id,
        "facts":      facts,
        "profile": {
            "goals":        profile.goals,
            "measurements": profile.measurements,
            "preferences":  profile.preferences,
        }
    })


@chat_bp.route('/api/chat/profile', methods=['POST'])
def update_profile():
    """Update user profile directly."""
    data       = request.json
    session_id = data.get('session_id')

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400

    goals        = data.get('goals')
    measurements = data.get('measurements')
    preferences  = data.get('preferences')

    memory.update_profile(session_id, goals, measurements, preferences)
    profile = memory.get_profile(session_id)

    return jsonify({
        "session_id": session_id,
        "profile": {
            "goals":        profile.goals,
            "measurements": profile.measurements,
            "preferences":  profile.preferences,
        }
    })


@chat_bp.route('/api/chat/history', methods=['GET'])
def get_history():
    """Get conversation history for a session."""
    session_id = request.args.get('session_id')
    limit      = request.args.get('limit', type=int)

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400

    history = memory.get_history(session_id, limit)
    return jsonify({
        "session_id": session_id,
        "history":    history,
    })


@chat_bp.route('/api/chat/session-info', methods=['GET'])
def session_info():
    """Get complete session information and statistics."""
    session_id = request.args.get('session_id')

    if not session_id or not memory.get_session(session_id):
        return jsonify({'error': 'Invalid or expired session'}), 400

    session = memory.get_session(session_id)
    stats   = memory.get_session_stats(session_id)
    profile = session.user_profile

    return jsonify({
        "session_id": session_id,
        "stats":      stats,
        "profile": {
            "goals":            profile.goals,
            "measurements":     profile.measurements,
            "preferences":      profile.preferences,
            "facts_extracted":  len(profile.facts),
        }
    })


@chat_bp.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        'status':          'ok',
        'version':         'phase-5-langgraph-phase-6-llmops',
        'active_sessions': len(memory.list_sessions()),
        'langsmith':       bool(os.getenv('LANGSMITH_API_KEY')),
    })


@chat_bp.route('/api/debug/sessions', methods=['GET'])
def debug_sessions():
    """Debug endpoint: list all active sessions."""
    if os.getenv('ENVIRONMENT') != 'development':
        return jsonify({'error': 'Endpoint only available in development'}), 403

    sessions_list = [
        memory.get_session_stats(sid)
        for sid in memory.list_sessions()
    ]
    return jsonify({
        "total_sessions": len(sessions_list),
        "sessions":       sessions_list,
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


