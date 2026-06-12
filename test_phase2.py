#!/usr/bin/env python3
"""
Phase 2 Testing Script
======================

Tests the new LangChain chains and memory manager components.
Run this before deploying to verify everything works locally.

Usage:
    python3 test_phase2.py
"""

import os
import sys
from dotenv import load_dotenv

# Setup
load_dotenv()
if not os.getenv('GOOGLE_API_KEY'):
    print("❌ ERROR: GOOGLE_API_KEY not set in .env")
    sys.exit(1)

print("\n" + "="*70)
print("ForgeAI Phase 2 Testing")
print("="*70 + "\n")

# Test 1: Import all modules
print("📦 Test 1: Importing modules...")
try:
    from backend.core import (
        get_llm, load_prompt, build_message_chain, 
        extract_json_from_response, format_agent_response
    )
    from backend.chains import (
        build_supervisor_chain, build_agent_chain, 
        build_conversation_flow, build_fact_extraction_chain
    )
    from backend.memory_manager import MemoryManager, Session, UserProfile
    print("✅ All modules imported successfully\n")
except Exception as e:
    print(f"❌ Import failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: LLM initialization
print("🤖 Test 2: Initializing LLM...")
try:
    llm = get_llm(temperature=0.3)
    print(f"✅ LLM initialized: {llm.model_name}\n")
except Exception as e:
    print(f"❌ LLM initialization failed: {e}\n")
    sys.exit(1)

# Test 3: Prompt loading
print("📝 Test 3: Loading prompts...")
try:
    prompt = load_prompt('supervisor')
    print(f"✅ Supervisor prompt loaded ({len(prompt)} chars)\n")
except Exception as e:
    print(f"❌ Prompt loading failed: {e}\n")
    sys.exit(1)

# Test 4: Memory Manager
print("💾 Test 4: Testing Memory Manager...")
try:
    memory = MemoryManager.get_instance()
    
    # Create session
    session = memory.create_session()
    print(f"  ✓ Created session: {session.session_id}")
    
    # Add messages
    memory.add_message(session.session_id, 'user', 'Hello!')
    memory.add_message(session.session_id, 'model', 'Hi there!')
    print(f"  ✓ Added messages to history")
    
    # Get history
    history = memory.get_history(session.session_id)
    print(f"  ✓ Retrieved history ({len(history)} messages)")
    
    # Add facts
    memory.add_facts(session.session_id, ['User likes morning workouts', 'Goal: build muscle'])
    print(f"  ✓ Added facts")
    
    # Get facts
    facts = memory.get_facts(session.session_id)
    print(f"  ✓ Retrieved facts ({len(facts)} extracted)")
    
    # Get stats
    stats = memory.get_session_stats(session.session_id)
    print(f"  ✓ Retrieved stats")
    
    print("✅ Memory Manager working correctly\n")
except Exception as e:
    print(f"❌ Memory Manager test failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: JSON extraction
print("🔍 Test 5: Testing JSON extraction...")
try:
    test_response = """
    Here's the result:
    {
        "route": ["WORKOUT", "RECOVERY"],
        "reasoning": "User asking about exercise recovery",
        "urgency": "normal",
        "needs_clarification": false
    }
    Some trailing text.
    """
    
    extracted = extract_json_from_response(test_response)
    assert extracted is not None, "Failed to extract JSON"
    assert extracted['route'] == ["WORKOUT", "RECOVERY"], "Incorrect route extraction"
    print("✅ JSON extraction working correctly\n")
except Exception as e:
    print(f"❌ JSON extraction test failed: {e}\n")
    sys.exit(1)

# Test 6: Build chains
print("⛓️  Test 6: Building chains...")
try:
    supervisor_chain = build_supervisor_chain()
    print("  ✓ Supervisor chain built")
    
    agent_chain = build_agent_chain('workout_planner', temperature=0.3)
    print("  ✓ Agent chain built")
    
    fact_chain = build_fact_extraction_chain()
    print("  ✓ Fact extraction chain built")
    
    conversation_flow = build_conversation_flow()
    print("  ✓ Conversation flow built")
    
    print("✅ All chains built successfully\n")
except Exception as e:
    print(f"❌ Chain building failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Test supervisor chain (simple routing)
print("🧠 Test 7: Testing supervisor routing (calling LLM)...")
try:
    supervisor = build_supervisor_chain()
    result = supervisor("I want to build muscle with weights", [])
    
    print(f"  ✓ Supervisor responded")
    print(f"  Route: {result['structured_response'].get('route', [])}")
    print(f"  Reasoning: {result['structured_response'].get('reasoning', '')[:60]}...")
    print("✅ Supervisor chain working\n")
except Exception as e:
    print(f"❌ Supervisor test failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: Test Flask app
print("🚀 Test 8: Testing Flask app routes...")
try:
    from backend.app import create_app
    from flask import json
    
    app = create_app()
    client = app.test_client()
    
    # Test health
    resp = client.get('/api/health')
    assert resp.status_code == 200, "Health check failed"
    print("  ✓ Health check: OK")
    
    # Test session creation
    resp = client.post('/api/chat/start')
    assert resp.status_code == 200, "Session creation failed"
    session_data = json.loads(resp.data)
    session_id = session_data.get('session_id')
    print(f"  ✓ Session created: {session_id}")
    
    # Test invalid message
    resp = client.post('/api/chat/send', json={
        'session_id': session_id,
        'message': ''
    })
    assert resp.status_code == 400, "Should reject empty message"
    print("  ✓ Empty message rejected correctly")
    
    print("✅ Flask app routes working\n")
except Exception as e:
    print(f"❌ Flask app test failed: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Summary
print("="*70)
print("✅ All Phase 2 tests passed!")
print("="*70)
print("\nPhase 2 components:")
print("  ✓ core.py - LLM config, prompt loading, message building")
print("  ✓ chains.py - Supervisor, agents, and conversation flow")
print("  ✓ memory_manager.py - Session and conversation memory")
print("  ✓ api/chat.py - LangChain-powered API endpoints")
print("\nNew endpoints:")
print("  POST   /api/chat/start - Create session")
print("  POST   /api/chat/send - Send message (LangChain + memory)")
print("  GET    /api/chat/facts - Get extracted user facts")
print("  POST   /api/chat/profile - Update user profile")
print("  GET    /api/chat/history - Get conversation history")
print("  GET    /api/chat/session-info - Get session stats")
print("  GET    /api/health - Health check")
print("\n" + "="*70 + "\n")
