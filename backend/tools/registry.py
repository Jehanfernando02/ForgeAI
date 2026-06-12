"""
Tool Registry — Phase 3

Wraps all tool functions as LangChain tools.

This is the single place where tools get registered.
Each agent gets a curated subset — not every agent
needs every tool. Giving agents only relevant tools
keeps their reasoning clean and focused.
"""

from langchain_core.tools import tool
from backend.tools.workout_tools import (
    log_workout,
    get_workout_history,
    calculate_one_rep_max,
    check_progressive_overload
)
from backend.tools.exercise_tools import (
    search_exercises,
    get_exercise_details
)
from backend.tools.nutrition_tools import (
    calculate_tdee,
    log_nutrition,
    get_nutrition_history
)
from backend.tools.user_tools import (
    get_user_profile,
    update_user_profile,
    get_progress_metrics
)


# ── Wrap each function as a LangChain tool ────────────────────
# The docstring becomes the tool description the agent reads.
# Write descriptions as if explaining to the AI when to use it.

@tool
def tool_log_workout(
    user_id: str,
    exercises: list,
    session_notes: str = "",
    perceived_difficulty: str = "moderate",
    duration_minutes: int = None
) -> dict:
    """
    Save a completed workout session to the database.
    Use this when the user describes a workout they just finished.
    Input exercises as a list of dicts with name, sets, reps, weight_kg.
    """
    return log_workout(user_id, exercises, session_notes,
                       perceived_difficulty, duration_minutes)


@tool
def tool_get_workout_history(
    user_id: str,
    days: int = 30,
    muscle_group: str = None
) -> dict:
    """
    Retrieve the user's past workout sessions from the database.
    Use this before recommending a new program or analyzing progress.
    Filter by muscle_group if you only need specific muscles.
    """
    return get_workout_history(user_id, days, muscle_group)


@tool
def tool_calculate_one_rep_max(weight_kg: float, reps: int) -> dict:
    """
    Estimate a one rep max using the Epley formula.
    Use this when the user asks about their max strength
    or when you need to set training percentages.
    """
    return calculate_one_rep_max(weight_kg, reps)


@tool
def tool_check_progressive_overload(
    user_id: str,
    exercise_name: str
) -> dict:
    """
    Check if the user is making progress on a specific exercise.
    Compares recent performance to 2-4 weeks ago.
    Use this when analyzing strength progression or plateau issues.
    """
    return check_progressive_overload(user_id, exercise_name)


@tool
def tool_search_exercises(
    muscle_group: str = None,
    equipment: str = None,
    difficulty: str = None,
    movement_pattern: str = None
) -> dict:
    """
    Search the exercise library by muscle group, equipment,
    difficulty, or movement pattern.
    Use this when selecting exercises for a workout program.
    Always search before recommending exercises to ensure they
    match the user's available equipment.
    """
    return search_exercises(muscle_group, equipment, difficulty, movement_pattern)


@tool
def tool_get_exercise_details(exercise_name: str) -> dict:
    """
    Get full instructions and coaching cues for a specific exercise.
    Use this when the user asks how to perform an exercise correctly.
    """
    return get_exercise_details(exercise_name)


@tool
def tool_calculate_tdee(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    goal: str
) -> dict:
    """
    Calculate Total Daily Energy Expenditure and macro targets.
    Use this whenever the user asks for nutrition targets or calories.
    activity_level: sedentary/light/moderate/active
    goal: cut/maintain/bulk
    """
    return calculate_tdee(weight_kg, height_cm, age, gender,
                          activity_level, goal)


@tool
def tool_log_nutrition(
    user_id: str,
    meals: list,
    notes: str = ""
) -> dict:
    """
    Save a nutrition log entry for the user.
    Use this when the user describes what they ate today.
    """
    return log_nutrition(user_id, meals, notes)


@tool
def tool_get_nutrition_history(user_id: str, days: int = 7) -> dict:
    """
    Retrieve the user's past nutrition logs.
    Use this when analyzing eating patterns or checking
    if nutrition is aligned with training goals.
    """
    return get_nutrition_history(user_id, days)


@tool
def tool_get_user_profile(user_id: str) -> dict:
    """
    Retrieve the user's stored profile including goals,
    fitness level, injuries, and equipment access.
    Always call this at the start of a session before
    making any recommendations.
    """
    return get_user_profile(user_id)


@tool
def tool_update_user_profile(user_id: str, **kwargs) -> dict:
    """
    Update the user's profile with new information.
    Use this when the user reveals new facts about themselves:
    their age, weight, goals, injuries, or equipment.
    """
    return update_user_profile(user_id, **kwargs)


@tool
def tool_get_progress_metrics(user_id: str, days: int = 30) -> dict:
    """
    Compute comprehensive progress metrics from workout history.
    Returns consistency score, volume trends, and personal records.
    Use this for any progress analysis or plateau investigation.
    """
    return get_progress_metrics(user_id, days)


# ── Tool sets per agent ───────────────────────────────────────
# Each agent gets only the tools relevant to their role.
# This keeps reasoning focused and prevents inappropriate calls.

WORKOUT_PLANNER_TOOLS = [
    tool_get_user_profile,
    tool_get_workout_history,
    tool_search_exercises,
    tool_get_exercise_details,
    tool_log_workout,
    tool_check_progressive_overload,
    tool_calculate_one_rep_max,
]

NUTRITION_AGENT_TOOLS = [
    tool_get_user_profile,
    tool_calculate_tdee,
    tool_log_nutrition,
    tool_get_nutrition_history,
]

PROGRESS_ANALYST_TOOLS = [
    tool_get_user_profile,
    tool_get_workout_history,
    tool_get_progress_metrics,
    tool_check_progressive_overload,
    tool_get_nutrition_history,
]

RECOVERY_AGENT_TOOLS = [
    tool_get_user_profile,
    tool_get_workout_history,
    tool_get_progress_metrics,
]

MOTIVATIONAL_COACH_TOOLS = [
    tool_get_user_profile,
    tool_get_progress_metrics,
]

SUPERVISOR_TOOLS = []  # Supervisor never calls tools — only routes

AGENT_TOOLS = {
    "workout_planner":    WORKOUT_PLANNER_TOOLS,
    "nutrition_agent":    NUTRITION_AGENT_TOOLS,
    "progress_analyst":   PROGRESS_ANALYST_TOOLS,
    "recovery_agent":     RECOVERY_AGENT_TOOLS,
    "motivational_coach": MOTIVATIONAL_COACH_TOOLS,
    "supervisor":         SUPERVISOR_TOOLS,
}
