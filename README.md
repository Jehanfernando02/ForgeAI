# ForgeAI — Multi-Agent AI Personal Coaching Platform

A sophisticated AI coaching system where 6 specialized agents collaborate behind the scenes. You chat naturally, and a team of experts — workout planner, nutritionist, progress analyst, recovery specialist, motivational coach, and supervisor — work together to provide personalized guidance.

## Phase 1: LLM Foundations & Prompt Engineering

### What You Get

- **6 Agent Personas** with carefully crafted system prompts
- **Supervisor Routing** — intelligently classifies messages and routes to specialists
- **Prompt Testing Lab** — experiment with temperature, outputs, and reasoning
- **Flask Backend** — routes messages to the right agent
- **Stunning React Frontend** — chat interface with agent badges and activity panel

### Project Structure

```
ForgeAI/
├── backend/
│   ├── agents/          # Agent implementations (Phase 2+)
│   ├── tools/           # Tool definitions (Phase 3+)
│   ├── memory/          # Memory system (Phase 2+)
│   ├── api/
│   │   └── chat.py      # Flask chat endpoints
│   ├── app.py           # Flask application
│   ├── prompt_lab.py    # Agent testing & experimentation
│   └── __init__.py
├── frontend/
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       ├── context/
│       ├── assets/
│       ├── App.jsx      # Main React component
│       ├── App.css      # Styling
│       └── index.css    # Global styles
├── prompts/
│   ├── supervisor.md
│   ├── workout_planner.md
│   ├── nutrition_agent.md
│   ├── progress_analyst.md
│   ├── motivational_coach.md
│   └── recovery_agent.md
├── docs/
│   └── architecture.md
├── .env                 # Environment variables
├── .gitignore
└── README.md
```

## Quick Start

### 1. Backend Setup

```bash
cd /Users/jehanfernando/Desktop/Projects/ForgeAI
python3 -m venv venv
source venv/bin/activate
pip install google-genai python-dotenv flask flask-cors
pip freeze > requirements.txt
```

### 2. Configure API Key

Edit `.env` and add your Gemini API key:

```
GOOGLE_API_KEY=your_actual_gemini_key_here
GEMINI_MODEL=models/gemini-2.5-flash
PORT=5001
```

### 3. Frontend Setup

```bash
cd frontend
npm create vite@latest . -- --template react
npm install
npm install axios react-markdown lucide-react
npm run dev
```

### 4. Run the System

**Terminal 1 — Backend:**

```bash
cd ForgeAI
source venv/bin/activate
python backend/app.py
```

**Terminal 2 — Frontend:**

```bash
cd ForgeAI/frontend
npm run dev
```

**Terminal 3 — Test Agents:**

```bash
cd ForgeAI
source venv/bin/activate
python backend/prompt_lab.py
```

Open http://localhost:3000 in your browser.

## The 6 Agents

1. **Supervisor** — Routes messages to specialists (never provides coaching)
2. **Workout Planner** (Dr. Alex Chen) — Program design, periodization, progressive overload
3. **Nutrition Agent** (Maya Patel) — Macros, meal planning, calorie tracking
4. **Progress Analyst** (Jordan Kim) — Trends, PRs, performance insights
5. **Motivational Coach** (Sam Rivera) — Psychology, accountability, genuine support
6. **Recovery Agent** (Dr. Priya Sharma) — Fatigue management, overtraining prevention

## Experiments in Phase 1

The `prompt_lab.py` file includes 5 experiments you can run:

1. **Supervisor Routing** — Test message classification
2. **Temperature Effect** — See how temperature changes coach tone
3. **Workout Planner** — Structured JSON output for workouts
4. **Nutrition Calculations** — Verify calorie and macro math
5. **Multi-turn Memory** — Test conversation context across turns

## What's Working

✅ Chat interface with real API responses  
✅ Intelligent message routing via Supervisor  
✅ Agent badges showing which agent responded  
✅ Live activity panel  
✅ Beautiful dark theme UI  
✅ Markdown rendering in responses  
✅ Quick prompt buttons  

## What's Coming (Future Phases)

- Phase 2: LangChain chains & persistent memory
- Phase 3: Tool calling & MCP server
- Phase 4: Vector database & semantic RAG
- Phase 5: Multi-agent orchestration (LangGraph)
- Phase 6: LLMOps & observability
- Phase 7: Docker & deployment
- Phase 8: Full reactive UI with real-time streaming

## Development

To experiment with prompts, edit the files in `prompts/` and re-run `prompt_lab.py`.

To modify agent behavior, adjust the system prompts and temperature settings in `backend/api/chat.py`.

## License

MIT

