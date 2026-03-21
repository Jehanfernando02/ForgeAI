# ForgeAI Phase 1 — Git Commit Strategy

Branch: `phase/1-llm-foundations`

## Commits (in order)

### 1. Project Structure & Configuration
```bash
git add .gitignore README.md .env docs/ prompts/ backend/__init__.py backend/agents/__init__.py backend/tools/__init__.py backend/memory/__init__.py backend/api/__init__.py
git commit -m "chore: init project structure and configuration"
```

### 2. Agent System Prompts
```bash
git add prompts/
git commit -m "feat: add 6 agent system prompts (supervisor, workout planner, nutrition, progress, motivation, recovery)"
```

### 3. Backend — Prompt Lab
```bash
git add backend/prompt_lab.py requirements.txt
git commit -m "feat: build prompt lab with 5 experiments for agent testing"
```

### 4. Backend — Flask API
```bash
git add backend/app.py backend/api/chat.py
git commit -m "feat: create Flask backend with supervisor routing and chat endpoints"
```

### 5. Frontend — Package & Configuration
```bash
git add frontend/package.json frontend/vite.config.js frontend/index.html frontend/src/main.jsx
git commit -m "chore: set up Vite React frontend with npm dependencies"
```

### 6. Frontend — Global Styling
```bash
git add frontend/src/index.css
git commit -m "style: add CSS variables and global theme foundation"
```

### 7. Frontend — React App Component
```bash
git add frontend/src/App.jsx
git commit -m "feat: build main chat UI with sidebar, messages, activity panel, and stats"
```

### 8. Frontend — App Styling
```bash
git add frontend/src/App.css
git commit -m "style: add beautiful dark theme with agent badges and animations"
```

## Complete Single Command (if you want to commit everything at once)

```bash
git add .
git commit -m "phase-1: LLM foundations, prompt engineering, and stunning UI"
git branch -m phase/1-llm-foundations
```

## Pushing to Remote

After commits:
```bash
git remote add origin https://github.com/yourusername/forgeai.git
git push -u origin phase/1-llm-foundations
```

## What's Ready to Test

✅ 6 agent personas defined through system prompts
✅ Supervisor routing logic
✅ Flask backend running on :5001
✅ React frontend on :3000
✅ Prompt testing lab for experiments
✅ Beautiful dark-themed UI with animations
✅ Agent badges on responses
✅ Activity panel showing agent execution
✅ Stats dashboard placeholder

## Next: Run Everything

Terminal 1:
```bash
cd /Users/jehanfernando/Desktop/Projects/ForgeAI
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python backend/app.py
```

Terminal 2:
```bash
cd /Users/jehanfernando/Desktop/Projects/ForgeAI/frontend
npm install
npm run dev
```

Terminal 3 (test agents):
```bash
cd /Users/jehanfernando/Desktop/Projects/ForgeAI
source venv/bin/activate
python backend/prompt_lab.py
```

Open: http://localhost:3000
