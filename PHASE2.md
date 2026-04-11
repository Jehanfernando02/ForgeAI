# Phase 2: LangChain & Memory Implementation

## Overview

Phase 2 replaces raw Gemini API calls with composable LangChain chains and implements proper conversation memory management with automatic fact extraction.

**Status**: ✅ Complete and Tested

## Architecture Changes

### Phase 1 → Phase 2

**Before (Phase 1)**:
```python
# Raw API calls for each request
response = client.models.generate_content(
    model="gemini-1.5-flash",
    contents=manual_message_list,
    generation_config=config
)
```

**After (Phase 2)**:
```python
# LangChain chains with memory
conversation_flow = build_conversation_flow()
result = conversation_flow(user_message, conversation_history)
memory.add_message(session_id, 'user', user_message)
memory.trim_history(session_id)
```

## New Modules

### 1. `backend/core.py` - LLM Configuration & Utilities

Core module that all other components depend on.

**Key Functions**:
- `get_llm(temperature)` - Initialize ChatGoogleGenerativeAI
- `load_prompt(agent_name)` - Load prompt templates from files
- `build_message_chain()` - Build formatted message lists
- `extract_json_from_response()` - Parse JSON from LLM responses
- `format_agent_response()` - Convert structured JSON to markdown

**Example**:
```python
from backend.core import get_llm, load_prompt, build_message_chain

llm = get_llm(temperature=0.3)
system_prompt = load_prompt('workout_planner')
messages = build_message_chain(system_prompt, history, user_msg)
response = llm.invoke(messages)
```

### 2. `backend/chains.py` - Composable LangChain Chains

Builds specialized chains for different tasks.

**Key Functions**:
- `build_supervisor_chain()` - Low-temp routing (0.1)
- `build_agent_chain(name, temp)` - Generic specialist chain factory
- `build_workout_log_chain()` - Parse workout entries
- `build_nutrition_log_chain()` - Parse meal entries
- `build_fact_extraction_chain()` - Extract user facts
- `build_conversation_flow()` - Main orchestrator combining all

**Example**:
```python
from backend.chains import build_conversation_flow

flow = build_conversation_flow()
result = flow("I want to build muscle", conversation_history)

print(result['agent_used'])          # 'workout_planner'
print(result['structured_response'])  # JSON from agent
print(result['routing'])              # Supervisor routing decision
```

### 3. `backend/memory_manager.py` - Session Memory Management

Singleton memory manager for all active sessions.

**Key Classes**:
- `UserProfile` - Goals, measurements, preferences, facts
- `Session` - Complete session state
- `MemoryManager` - Singleton managing all sessions

**Key Methods**:
```python
memory = MemoryManager.get_instance()

# Session management
session = memory.create_session()
memory.delete_session(session_id)

# History management
memory.add_message(session_id, 'user', 'Hello!')
history = memory.get_history(session_id, limit=20)
memory.trim_history(session_id, keep_last_turns=10)

# User profile
memory.add_facts(session_id, ['User likes mornings', ...])
memory.update_profile(session_id, goals={...}, measurements={...})
profile = memory.get_profile(session_id)

# Analytics
stats = memory.get_session_stats(session_id)
memory.record_routing(session_id, route_data, agent_used)
```

### 4. `backend/api/chat.py` - Rewritten Endpoints

Complete rewrite using LangChain chains and memory.

**Core Endpoints**:
- `POST /api/chat/start` - Create new session
- `POST /api/chat/send` - Send message (processes through chains + memory)
- `GET /api/chat/facts` - Get extracted user facts
- `POST /api/chat/profile` - Update user profile
- `GET /api/chat/history` - Get conversation history
- `GET /api/chat/session-info` - Get session stats
- `GET /api/health` - Health check

**Example Request/Response**:
```bash
curl -X POST http://localhost:5001/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "abc123...",
    "message": "Build me a shoulder workout"
  }'

# Response:
{
  "response": "## Your Shoulder Workout\n**Focus**: Building mass...",
  "structured_response": {
    "workout": {
      "name": "Shoulder Pump",
      "exercises": [...]
    }
  },
  "agent_used": "workout_planner",
  "routing": {
    "route": ["WORKOUT"],
    "reasoning": "User requesting workout plan"
  },
  "session_stats": {
    "total_messages": 4,
    "total_turns": 2,
    "agent_stats": {"workout_planner": 2}
  }
}
```

## Processing Flow

### Message Processing Pipeline

```
User Message
    ↓
[Fact Extraction] → Extract goals, measurements, injuries, etc.
    ↓
[Supervisor Routing] → Determine which specialist(s) needed
    ↓
    ├─→ needs_clarification? → Return clarification Q
    │
    └─→ Route to Specialist Agent → Generate response
    ↓
[Format Response] → Convert JSON to markdown
    ↓
[Update Memory] → Add to history, trim old messages
    ↓
[Record Analytics] → Track agent usage, routing patterns
    ↓
Return Response
```

### Memory Management Strategy

**History Trimming**:
- Keep last 10 conversation turns (20 messages)
- Oldest messages removed automatically
- In Phase 3+: Could store summaries of older context

**Fact Storage**:
- Extracted from every user message
- Stored in user profile
- Used for context-aware responses

**Session Lifecycle**:
- Created: `POST /api/chat/start`
- Active: Conversation happens, facts accumulate
- Terminated: `DELETE /api/chat/end` (future endpoint)

## Chain Temperature Settings

Each chain has optimized temperature for its purpose:

```python
supervisor_chain(temp=0.1)           # Low: Consistent routing
workout_planner_chain(temp=0.3)      # Medium: Creative but structured
nutrition_agent_chain(temp=0.1)      # Low: Precise calculations
progress_analyst_chain(temp=0.2)     # Low-Medium: Analytical
motivational_coach_chain(temp=0.75)  # High: Personalized motivation
recovery_agent_chain(temp=0.2)       # Low-Medium: Safe recommendations
workout_log_chain(temp=0.0)          # Very low: Data extraction
nutrition_log_chain(temp=0.0)        # Very low: Data extraction
```

## Dependencies Added

```
langchain>=0.1.0,<0.2.0
langchain-core>=0.1.0,<0.2.0
langchain-google-genai>=0.0.1
langchain-community>=0.0.1
```

Install with:
```bash
pip install -r requirements.txt
```

## Testing Phase 2

### Quick Verification
```bash
python3 test_phase2.py
```

Runs:
1. Module imports
2. LLM initialization
3. Prompt loading
4. Memory Manager operations
5. JSON extraction
6. Chain building
7. Supervisor routing test
8. Flask app routes

### Manual Testing

1. **Start backend**:
```bash
cd backend
python3 app.py
```

2. **Create session**:
```bash
curl -X POST http://localhost:5001/api/chat/start
# Returns: {"session_id": "abc123...", "welcome": "..."}
```

3. **Send message**:
```bash
curl -X POST http://localhost:5001/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"session_id": "abc123...", "message": "Hi!"}'
```

4. **Check facts**:
```bash
curl http://localhost:5001/api/chat/facts?session_id=abc123...
```

5. **Get session info**:
```bash
curl http://localhost:5001/api/chat/session-info?session_id=abc123...
```

## File Changes Summary

### Created Files
- ✅ `backend/core.py` (340 lines)
- ✅ `backend/chains.py` (320 lines)
- ✅ `backend/memory_manager.py` (460 lines)
- ✅ `test_phase2.py` (200 lines)

### Modified Files
- ✅ `backend/api/chat.py` - Completely rewritten (300 → 350 lines, all new LangChain code)
- ✅ `requirements.txt` - Added LangChain dependencies

### Unchanged Files
- `backend/app.py` - Flask setup (no changes needed)
- `backend/prompt_lab.py` - Phase 1 testing (kept for reference)
- `prompts/*.md` - All 6 agent prompts (used by core.py)

## Next Steps (Phase 3+)

### Phase 3: Vector Storage & Retrieval
- [ ] Add Pinecone/Supabase for long-term memory
- [ ] Store user facts in vector DB
- [ ] Retrieve relevant facts for context
- [ ] Implement semantic search

### Phase 4: Production Database
- [ ] Replace in-memory sessions with PostgreSQL
- [ ] Implement user authentication
- [ ] Store conversation history permanently
- [ ] Add session persistence

### Phase 5: Advanced Features
- [ ] Workout/nutrition logging with images
- [ ] Social features (compare with friends)
- [ ] Scheduling & reminders
- [ ] Mobile app

## Deployment

### Local Testing
```bash
# Install deps
pip install -r requirements.txt

# Run tests
python3 test_phase2.py

# Start backend
cd backend && python3 app.py
```

### Production (Render/Vercel)
```bash
# Backend (Render)
- Push to `feat/phase2-langchain-memory` branch
- Render auto-deploys from git
- Verify at: https://forgeai-backend.onrender.com/api/health

# Frontend (Vercel)
- Already deployed, no changes to Phase 2
- Consumes new endpoints automatically
```

## Rollback Plan

If Phase 2 has issues in production:

1. Keep Phase 1 (`prompt_lab.py`) active
2. Switch frontend back to Phase 1 endpoints
3. Debug Phase 2 locally
4. Redeploy once fixed

```bash
# Switch to Phase 1 temporarily
git checkout phase-1
git push origin phase-1:main

# Debug Phase 2
git checkout feat/phase2-langchain-memory
# ... fix issues ...
git push origin feat/phase2-langchain-memory:main
```

## Performance Notes

### Token Usage
- Supervisor: ~200-300 tokens per routing decision
- Specialist: ~500-1000 tokens per response
- Fact extraction: ~100-200 tokens per message
- **Total per turn**: ~800-1500 tokens

### Memory Usage
- Per session: ~10-50 KB (10 turns of history + profile)
- 100 active sessions: ~1-5 MB
- In-memory is fine for Phase 2; Phase 4 moves to DB

### Response Time
- Supervisor routing: ~1-2 seconds
- Specialist agent: ~2-4 seconds
- **Total latency**: ~3-6 seconds per message

## Troubleshooting

### "GOOGLE_API_KEY not found"
```bash
# Check .env file exists
ls -la .env
# Should have: GOOGLE_API_KEY=sk_...

# If missing, add it:
echo "GOOGLE_API_KEY=sk_..." >> .env
```

### "No valid JSON in response"
- Some specialist agents may fail to parse
- Check if prompt requires stricter JSON format
- Review prompts in `prompts/` directory

### Import errors
```bash
# Verify installation
python3 -c "import langchain; print(langchain.__version__)"

# Reinstall if needed
pip install --force-reinstall -r requirements.txt
```

## Contact & Support

For Phase 2 issues:
- Check logs: `backend/logs/` (future)
- Debug endpoint: `GET /api/debug/sessions`
- Review test output: `python3 test_phase2.py`
