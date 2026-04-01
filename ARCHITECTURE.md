"""
ForgeAI Complete Architecture
============================

Shows full system from frontend to database.
"""

COMPLETE_ARCHITECTURE = """
╔════════════════════════════════════════════════════════════════════════════╗
║                         FORGEAI COMPLETE SYSTEM                           ║
║                      Phase 1 + 2 + 3 (All Integrated)                     ║
╚════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND LAYER                                │
├──────────────────────────────────────────────────────────────────────────┤
│  • React SPA (port 5173)                                                 │
│  • Chat interface with message history                                   │
│  • Agent badges showing which agent responded                            │
│  • Activity panel showing tool usage                                     │
│  • Displays session stats and facts extracted                            │
│                                                                          │
│  Components: App.jsx, Chat, Sidebar, Activity, Markdown rendering       │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                         API LAYER (Flask)                                │
├──────────────────────────────────────────────────────────────────────────┤
│  Endpoints:                                                              │
│  • POST /api/chat/start           → Create session                       │
│  • POST /api/chat/send            → Send message (MAIN)                  │
│  • GET  /api/chat/facts           → View extracted facts                 │
│  • GET  /api/chat/history         → Get conversation history             │
│  • POST /api/chat/profile         → Update user profile                  │
│  • GET  /api/chat/session-info    → Session stats                        │
│  • GET  /api/health               → Health check                         │
│  • GET  /api/debug/sessions       → Debug (dev only)                     │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                   CONVERSATION ORCHESTRATION                             │
├──────────────────────────────────────────────────────────────────────────┤
│  1. Retrieve conversation history from MemoryManager                     │
│  2. Pass to conversation_flow()                                          │
│     ├→ Supervisor Chain (low temp 0.1, no tools)                         │
│     │   └→ Routes to appropriate specialist                             │
│     ├→ Tool-Enabled ReAct Agent                                          │
│     │   └→ Reason → Act (call tools) → Observe → Loop                   │
│     └→ Format response (markdown)                                        │
│  3. Store results in MemoryManager                                       │
│  4. Return response with tools_used metadata                             │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
                    ┌───────────────┼───────────────┐
                    ↓               ↓               ↓
        ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐
        │ ROUTING         │ │ AGENTS          │ │  TOOLS       │
        ├─────────────────┤ ├─────────────────┤ ├──────────────┤
        │ Supervisor      │ │ Workout Planner │ │ Workout:     │
        │ (0 tools)       │ │ (7 tools)       │ │ • log        │
        │                 │ │                 │ │ • history    │
        │ Decides route   │ │ Nutrition Agent │ │ • 1RM calc   │
        │ Returns tags:   │ │ (4 tools)       │ │ • progression│
        │ - WORKOUT       │ │                 │ │              │
        │ - NUTRITION     │ │ Progress        │ │ Nutrition:   │
        │ - PROGRESS      │ │ Analyst         │ │ • TDEE calc  │
        │ - EMOTIONAL     │ │ (5 tools)       │ │ • logging    │
        │ - RECOVERY      │ │                 │ │ • history    │
        │ - ASSESSMENT    │ │ Recovery Agent  │ │              │
        │ - GENERAL       │ │ (3 tools)       │ │ Exercise:    │
        │                 │ │                 │ │ • search     │
        │ Also checks:    │ │ Motivational    │ │ • details    │
        │ - urgency       │ │ Coach           │ │              │
        │ - clarification │ │ (2 tools)       │ │ User:        │
        │   needed        │ │                 │ │ • profile    │
        │                 │ │                 │ │ • update     │
        │ Uses LLM        │ │ Uses LLM +      │ │ • metrics    │
        │ (prompt in      │ │ ReAct pattern   │ │              │
        │ prompts/)       │ │                 │ │ Via @tool    │
        │                 │ │ Calls tools as  │ │ decorators   │
        │                 │ │ needed during   │ │ in registry  │
        │                 │ │ reasoning loop  │ │              │
        └─────────────────┘ └─────────────────┘ └──────────────┘
                    │               │               │
                    └───────────────┼───────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                     MEMORY MANAGEMENT LAYER                              │
├──────────────────────────────────────────────────────────────────────────┤
│  MemoryManager (Singleton)                                               │
│  ├→ Sessions (in-memory, keyed by session_id)                            │
│  │   ├→ conversation_history (messages: user/model)                      │
│  │   ├→ user_profile (goals, measurements, preferences)                  │
│  │   ├→ routing_history (agent usage stats)                              │
│  │   └→ metadata (timestamps, token counts)                              │
│  │                                                                        │
│  ├→ Automatic fact extraction from each message                          │
│  ├→ History trimming (keep last 10 turns)                                │
│  ├→ Profile updates from extracted facts                                 │
│  └→ Session statistics (agent usage, turn count, etc)                    │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌──────────────────────────────────────────────────────────────────────────┐
│                        DATABASE LAYER                                    │
├──────────────────────────────────────────────────────────────────────────┤
│  SQLite (forgeai.db) with SQLAlchemy ORM                                 │
│                                                                          │
│  ┌─ Users Table ──────────────────────────────────────────┐              │
│  │ id, name, age, weight_kg, height_cm, gender            │              │
│  │ fitness_level, goal, injuries, equipment               │              │
│  │ created_at, updated_at                                 │              │
│  └───────────────────────────────────────────────────────┘              │
│                                                                          │
│  ┌─ WorkoutLogs Table ────────────────────────────────────┐              │
│  │ id, user_id (FK), session_date                         │              │
│  │ exercises (JSON), total_volume_kg                      │              │
│  │ session_notes, perceived_difficulty, duration_minutes  │              │
│  │ created_at                                             │              │
│  └───────────────────────────────────────────────────────┘              │
│                                                                          │
│  ┌─ NutritionLogs Table ──────────────────────────────────┐              │
│  │ id, user_id (FK), log_date                             │              │
│  │ meals (JSON), total_calories, total_protein_g          │              │
│  │ total_carbs_g, total_fat_g, notes                      │              │
│  │ created_at                                             │              │
│  └───────────────────────────────────────────────────────┘              │
│                                                                          │
│  ┌─ ExerciseLibrary Table ────────────────────────────────┐              │
│  │ id, name, muscle_group, equipment, difficulty          │              │
│  │ movement_pattern, secondary_muscles, instructions      │              │
│  │ coaching_cues (25 exercises pre-seeded)                │              │
│  └───────────────────────────────────────────────────────┘              │
│                                                                          │
│  Initialized automatically on startup                                   │
│  Tables created if don't exist                                          │
│  Exercise library seeded with 25 common exercises                       │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                         MCP SERVER (Optional)                            │
├──────────────────────────────────────────────────────────────────────────┤
│  HTTP Server (port 8000)                                                 │
│  Exposes all 12 tools via REST API                                       │
│  • GET /tools - List all available tools                                 │
│  • POST /tools/call - Execute a tool                                     │
│  • GET /health - Server status                                           │
│                                                                          │
│  Allows:                                                                 │
│  - Direct tool calls from external clients                               │
│  - Integration with other AI systems                                     │
│  - Microservice-style tool access                                        │
│  - MCP compatibility                                                     │
└──────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════

                        EXAMPLE MESSAGE FLOW

User: "I just squatted 3x5 @ 100kg. Have I made progress?"

    1. Frontend sends POST /api/chat/send
       {
         "session_id": "abc123...",
         "message": "I just squatted 3x5 @ 100kg. Have I made progress?"
       }

    2. Backend retrieves session from MemoryManager

    3. Supervisor chain routes:
       "This is about workouts and progress"
       → route: ["WORKOUT", "PROGRESS"]

    4. Workout Planner agent selected (primary route)
       Gets 7 tools: log_workout, get_workout_history, etc.

    5. Agent reasoning with ReAct:
       Thought: "User described a squat. I should log it and check progression."
       Action: log_workout
       Action Input: {
         "user_id": "abc123...",
         "exercises": [{"name": "Squat", "sets": 3, "reps": 5, "weight_kg": 100}],
         "perceived_difficulty": "moderate"
       }
       Observation: Logged successfully. Total volume: 1500kg.
       
       Thought: "Now I should check if this is progression."
       Action: check_progressive_overload
       Action Input: {"user_id": "abc123...", "exercise_name": "Squat"}
       Observation: Compared to 4 weeks ago (95kg), you've added 5kg (5% gain).
       
       Thought: I have all the info I need.
       Final Answer: "Great session! You've logged 3x5 @ 100kg. Plus, you're up 
                     5kg from a month ago—that's solid progression on the squat!"

    6. Response formatted and sent:
       {
         "response": "Great session! You've logged...",
         "agent_used": "workout_planner",
         "tools_used": ["log_workout", "check_progressive_overload"],
         "routing": {"route": ["WORKOUT", "PROGRESS"], ...},
         "session_stats": {
           "total_messages": 2,
           "agent_stats": {"workout_planner": 1, ...}
         }
       }

    7. Frontend displays response with tool badges

═══════════════════════════════════════════════════════════════════════════════

                          AGENT CAPABILITIES

┌─ Workout Planner (7 tools) ──────────────────────────────────────────────┐
│ Can: Log workouts, view history, estimate 1RM, check progression         │
│ Search exercises, view exercise details, get profile                     │
│ Example: "Design a chest workout with dumbbells"                         │
│   → Searches for dumbbell chest exercises → Gets details → Designs plan  │
└──────────────────────────────────────────────────────────────────────────┘

┌─ Nutrition Agent (4 tools) ─────────────────────────────────────────────┐
│ Can: Calculate TDEE, log meals, view nutrition history, check profile    │
│ Example: "What macros should I eat to bulk?"                             │
│   → Gets profile → Calculates TDEE → Adjusts for goal → Recommends plan │
└──────────────────────────────────────────────────────────────────────────┘

┌─ Progress Analyst (5 tools) ────────────────────────────────────────────┐
│ Can: Get profile, workout history, progress metrics, progression check   │
│ View nutrition history                                                   │
│ Example: "Am I making progress?"                                         │
│   → Gets metrics → Analyzes volume trend → Checks PRs → Gives analysis   │
└──────────────────────────────────────────────────────────────────────────┘

┌─ Recovery Agent (3 tools) ──────────────────────────────────────────────┐
│ Can: Get profile, workout history, progress metrics                      │
│ Example: "Should I take a rest day?"                                     │
│   → Checks frequency → Analyzes volume → Gives recommendation             │
└──────────────────────────────────────────────────────────────────────────┘

┌─ Motivational Coach (2 tools) ──────────────────────────────────────────┐
│ Can: Get profile, progress metrics                                       │
│ Example: "I feel unmotivated"                                            │
│   → Checks progress → Celebrates wins → Gives pep talk                   │
└──────────────────────────────────────────────────────────────────────────┘

┌─ Supervisor (0 tools) ──────────────────────────────────────────────────┐
│ Can: Route to agents based on intent                                     │
│ Does NOT call tools — only routes and escalates to specialists           │
└──────────────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════

                        DEPLOYMENT TOPOLOGY

Local Development:
  Frontend:  npm run dev (port 5173)
  Backend:   python app.py (port 5001)
  MCP:       python mcp_server.py (port 8000) [optional]
  Database:  SQLite at forgeai.db

Deployed (Current):
  Frontend:  Vercel (Next.js ready when migrated)
  Backend:   Render.com (Python/Flask)
  Database:  SQLite file in Render filesystem
  MCP:       Can be deployed separately

Future (Phase 4+):
  Frontend:  Vercel/Netlify
  Backend:   AWS Lambda / Google Cloud Run
  Database:  PostgreSQL / Cloud SQL
  Tools:     Kubernetes microservices
  Vector DB: Pinecone / Weaviate (ChromaDB)
  Cache:     Redis

═══════════════════════════════════════════════════════════════════════════════
"""

if __name__ == "__main__":
    print(COMPLETE_ARCHITECTURE)
