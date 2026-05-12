# ForgeAI — AI-Powered Personal Coaching Platform

> *Your AI coaching team. Knows your history. Adapts to your progress. Always in your corner.*

---

## What is ForgeAI?

ForgeAI is a full-stack AI personal coaching platform built on a multi-agent 
architecture. Instead of a single generic chatbot, ForgeAI runs a team of 6 
specialized AI agents that collaborate in real time to give you coaching advice 
that is genuinely specific to you.

Most AI fitness apps give everyone the same response. ForgeAI is different 
because it actually remembers you. Every workout you log, every goal you 
mention, every injury you bring up gets stored in a semantic memory system. 
The next time you ask anything, the agents retrieve your personal history 
before responding. The longer you use it, the smarter it gets about you 
specifically.

---

## The Agent Team

ForgeAI runs 6 specialized agents coordinated by a supervisor:

**Supervisor** reads every message and decides which specialists should handle 
it, in what order, and whether multiple agents should collaborate.

**Workout Planner** is your exercise science specialist. It designs programs, 
selects exercises based on your equipment and injury history, tracks progressive 
overload, and gives coaching cues with every movement.

**Nutrition Agent** handles your macros and meal planning. It calculates your 
TDEE using the Mifflin-St Jeor equation, sets protein and calorie targets based 
on your goal, and analyzes your food logs.

**Progress Analyst** is your data interpreter. It looks at your training history 
over weeks and months, identifies real plateaus versus normal variation, 
celebrates genuine PRs, and tells you what is actually working.

**Recovery Agent** monitors your training load and flags overtraining risk. 
It recommends deload weeks, identifies when fatigue is accumulating, and 
distinguishes between normal soreness and warning signs.

**Motivational Coach** handles the psychological side. When you express 
discouragement or burnout, this agent responds first — acknowledging what you 
feel before any analysis or advice happens.

---

## How the Memory Works

This is what separates ForgeAI from a chatbot.

When you mention a knee injury, that gets embedded as a vector and stored in 
ChromaDB. When you ask for a leg workout three weeks later in a completely new 
session, the RAG pipeline retrieves that injury note automatically and injects 
it into the workout planner's prompt before it generates anything. The planner 
responds knowing about your knee — without you having to mention it again.

The same happens with your workout history, your goals, your equipment, your 
preferences, and every significant coaching conversation. Everything gets stored 
semantically, retrieved by meaning rather than exact keywords, and used to 
personalize every response.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Recharts, WebSocket |
| Backend | Python, Flask, SQLAlchemy |
| AI Orchestration | LangChain, LangGraph |
| Language Model | Google Gemini 2.5 Flash |
| Vector Database | ChromaDB |
| Structured Database | SQLite (PostgreSQL in production) |
| Observability | LangSmith |
| Deployment | Docker, Render, Vercel |
| CI/CD | GitHub Actions |

---

## Getting Started

## What You Can Do With It

- Chat naturally about workouts, nutrition, recovery, or motivation
- Log workouts in plain English and have them structured and saved automatically
- Get a macro calculation with full working shown
- Ask why you are not progressing and get a data-driven analysis
- Mention an injury once and never have it ignored in future recommendations
- Watch the live agent activity panel show exactly which agents fired and 
  what tools they called for every response
- See your strength progression and nutrition trends on the dashboard

---

## Build Phases

| Phase | What Was Built |
|---|---|
| 1 — LLM Foundations | 6 agent personas via prompt engineering, Flask API, React UI |
| 2 — LangChain & Memory | Chains, conversation memory, fact extraction |
| 3 — Tools & MCP | 6 tools, SQLite database, exercise library, MCP server |
| 4 — RAG & ChromaDB | Vector store, semantic memory, fitness research knowledge base |
| 5 — LangGraph | Multi-agent orchestration, parallel execution, full team coordination |
| 6 — LLMOps | LangSmith tracing, cost tracking, prompt versioning, rate limiting |
| 7 — Deployment | Docker, Render, Vercel, GitHub Actions CI/CD |
| 8 — Frontend Polish | WebSocket streaming, progress charts, mobile responsive design |

---
