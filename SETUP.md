# ForgeAI Phase 1 — Quick Start Guide

## Prerequisites
- Python 3.9+
- Node.js 16+
- Gemini API Key (https://makersuite.google.com/app/apikey)

## Step 1: Get Your Gemini API Key

1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key

## Step 2: Configure Environment

Edit `.env` in the project root:
```
GOOGLE_API_KEY=your_actual_gemini_key_here
GEMINI_MODEL=models/gemini-2.5-flash
PORT=5001
```

## Step 3: Backend Setup

```bash
cd /Users/jehanfernando/Desktop/Projects/ForgeAI

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend
python backend/app.py
```

You should see:
```
  ForgeAI backend running → http://localhost:5001
```

## Step 4: Frontend Setup (NEW TERMINAL)

```bash
cd /Users/jehanfernando/Desktop/Projects/ForgeAI/frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

You should see:
```
VITE v5.0.0  ready in xxx ms

➜  Local:   http://localhost:3000/
```

## Step 5: Open in Browser

Open http://localhost:3000 in your browser.

You should see:
- ForgeAI logo and title
- Chat interface with welcome message
- Sidebar with 6 agents
- Quick prompt buttons

## Step 6: Test the Agents (OPTIONAL — NEW TERMINAL)

```bash
cd /Users/jehanfernando/Desktop/Projects/ForgeAI
source venv/bin/activate
python backend/prompt_lab.py
```

This will run 5 experiments:
1. Supervisor routing on various messages
2. Temperature effect on motivational coach
3. Workout planner structured output
4. Nutrition calculations
5. Multi-turn conversation memory

## Verify It Works

In the chat:
1. Type: "I want to build muscle"
2. Should get a response from Workout Planner
3. See orange badge showing "Workout Planner"
4. Activity panel shows supervisor routing

Try different messages:
- "What should I eat?" → Nutrition Agent
- "I feel unmotivated" → Motivational Coach
- "How's my progress?" → Progress Analyst
- "My muscles are sore" → Recovery Agent

## Troubleshooting

### Backend won't start
- Check `.env` has your real API key
- Make sure port 5001 is free: `lsof -i :5001`
- Activate venv: `source venv/bin/activate`

### Frontend won't load
- Check http://localhost:3000 (not 3001)
- Make sure backend is running
- Check browser console for errors (F12)

### No response from agents
- Verify API key in `.env` is correct
- Check backend terminal for error messages
- Make sure you're on the right Python environment

### Can't install dependencies
- Upgrade pip: `pip install --upgrade pip`
- Use Python 3.9+: `python3 --version`

## What's Next?

Phase 1 is done! You have:
- ✅ 6 agent personas
- ✅ Intelligent routing
- ✅ Beautiful UI
- ✅ Prompt testing lab
- ✅ Working chat interface

Phase 2 will add:
- Persistent conversation memory
- LangChain integration
- Context awareness across sessions

## Keep Terminal Windows Open

For development, keep 3 terminals open:
1. Backend: `python backend/app.py`
2. Frontend: `npm run dev`
3. (Optional) Agent testing: `python backend/prompt_lab.py`

Make changes to prompts or agents and restart as needed.
