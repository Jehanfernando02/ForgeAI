"""
ForgeAI Phase 5: LangGraph Multi-Agent Orchestration
=====================================================

This package contains the directed state graph that replaces
the single-agent routing from Phase 3.

Graph flow:
  START → rag_context → supervisor
  supervisor → (conditional) → specialist agent(s)
  workout_planner → recovery_check → assembler
  all others → assembler → END
"""
