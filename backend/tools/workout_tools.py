"""
Workout Tools — Phase 3

Tools that agents use to interact with workout data.
Each function is a pure Python function first.
LangChain tool decorators are added in the registry.

Tools:
  - log_workout: save a workout session to the database
  - get_workout_history: retrieve past workouts for a user
  - calculate_one_rep_max: estimate 1RM from submaximal set
  - check_progressive_overload: compare recent vs previous performance
"""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.database import SessionLocal, WorkoutLog, User


def log_workout(
    user_id: str,
    exercises: list,
    session_notes: str = "",
    perceived_difficulty: str = "moderate",
    duration_minutes: int = None
) -> dict:
    """
    Save a completed workout session to the database.

    Args:
        user_id: the user's session ID
        exercises: list of dicts with name, sets, reps, weight_kg
        session_notes: any notes about the session
        perceived_difficulty: easy/moderate/hard/very_hard
        duration_minutes: how long the session took

    Returns:
        dict with success status and the logged workout ID
    """
    db = SessionLocal()
    try:
        # Ensure user exists — create a minimal record if not
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id)
            db.add(user)
            db.flush()

        # Calculate total volume (sets × reps × weight for each exercise)
        total_volume = 0.0
        for ex in exercises:
            try:
                sets   = int(ex.get('sets', 0))
                reps   = int(str(ex.get('reps', '0')).split('-')[0])  # handle "8-12"
                weight = float(ex.get('weight_kg') or 0)
                total_volume += sets * reps * weight
            except (ValueError, TypeError):
                pass

        workout = WorkoutLog(
            user_id=user_id,
            exercises=exercises,
            total_volume_kg=round(total_volume, 2),
            session_notes=session_notes,
            perceived_difficulty=perceived_difficulty,
            duration_minutes=duration_minutes,
            session_date=datetime.utcnow()
        )
        db.add(workout)
        db.commit()

        return {
            "success": True,
            "workout_id": workout.id,
            "total_volume_kg": workout.total_volume_kg,
            "exercises_logged": len(exercises),
            "message": f"Workout logged successfully. Total volume: {workout.total_volume_kg}kg"
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_workout_history(
    user_id: str,
    days: int = 30,
    muscle_group: str = None,
    limit: int = 20
) -> dict:
    """
    Retrieve a user's workout history from the database.

    Args:
        user_id: the user's ID
        days: how many days back to look (default 30)
        muscle_group: optional filter by muscle group
        limit: maximum number of sessions to return

    Returns:
        dict with list of workout sessions and summary stats
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        query  = db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user_id,
            WorkoutLog.session_date >= cutoff
        ).order_by(WorkoutLog.session_date.desc()).limit(limit)

        workouts = query.all()

        if not workouts:
            return {
                "success": True,
                "workouts": [],
                "summary": f"No workouts found in the last {days} days",
                "total_sessions": 0
            }

        workout_list = []
        for w in workouts:
            exercises = w.exercises or []

            # Filter by muscle group if requested
            if muscle_group:
                exercises = [
                    ex for ex in exercises
                    if muscle_group.lower() in str(ex.get('name', '')).lower()
                    or muscle_group.lower() in str(ex.get('muscle_group', '')).lower()
                ]

            workout_list.append({
                "id": w.id,
                "date": w.session_date.strftime("%Y-%m-%d"),
                "exercises": exercises,
                "total_volume_kg": w.total_volume_kg,
                "perceived_difficulty": w.perceived_difficulty,
                "notes": w.session_notes,
                "duration_minutes": w.duration_minutes
            })

        total_volume = sum(w.total_volume_kg or 0 for w in workouts)

        return {
            "success": True,
            "workouts": workout_list,
            "total_sessions": len(workout_list),
            "total_volume_kg": round(total_volume, 2),
            "average_volume_per_session": round(
                total_volume / len(workouts), 2
            ) if workouts else 0,
            "summary": (
                f"{len(workout_list)} sessions in the last {days} days. "
                f"Total volume: {round(total_volume, 2)}kg"
            )
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def calculate_one_rep_max(weight_kg: float, reps: int) -> dict:
    """
    Estimate one rep max using the Epley formula.
    1RM = weight × (1 + reps/30)

    Also returns percentage-based training weights.

    Args:
        weight_kg: weight used in the set
        reps: number of reps completed

    Returns:
        dict with estimated 1RM and training percentages
    """
    if reps == 1:
        one_rm = weight_kg
    else:
        one_rm = weight_kg * (1 + reps / 30)

    one_rm = round(one_rm, 2)

    return {
        "success": True,
        "estimated_1rm_kg": one_rm,
        "training_percentages": {
            "50%  (warm up)":    round(one_rm * 0.50, 1),
            "60%  (technique)":  round(one_rm * 0.60, 1),
            "70%  (hypertrophy)":round(one_rm * 0.70, 1),
            "75%  (hypertrophy)":round(one_rm * 0.75, 1),
            "80%  (strength)":   round(one_rm * 0.80, 1),
            "85%  (strength)":   round(one_rm * 0.85, 1),
            "90%  (peaking)":    round(one_rm * 0.90, 1),
            "95%  (peaking)":    round(one_rm * 0.95, 1),
        },
        "formula": f"Epley: {weight_kg} × (1 + {reps}/30) = {one_rm}kg"
    }


def check_progressive_overload(user_id: str, exercise_name: str) -> dict:
    """
    Compare a user's recent performance on an exercise to their
    performance 2-4 weeks ago to identify progressive overload.

    Args:
        user_id: the user's ID
        exercise_name: name of the exercise to analyze

    Returns:
        dict with comparison data and overload recommendation
    """
    db = SessionLocal()
    try:
        now        = datetime.utcnow()
        recent_cut = now - timedelta(days=14)
        older_cut  = now - timedelta(days=42)

        all_workouts = db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user_id,
            WorkoutLog.session_date >= older_cut
        ).order_by(WorkoutLog.session_date.desc()).all()

        if not all_workouts:
            return {
                "success": True,
                "message": "No workout history found. Log some workouts first.",
                "has_data": False
            }

        def extract_exercise_data(workouts, name):
            results = []
            for w in workouts:
                for ex in (w.exercises or []):
                    if name.lower() in ex.get('name', '').lower():
                        try:
                            results.append({
                                "date": w.session_date.strftime("%Y-%m-%d"),
                                "sets": ex.get('sets', 0),
                                "reps": ex.get('reps', 0),
                                "weight_kg": float(ex.get('weight_kg') or 0)
                            })
                        except (ValueError, TypeError):
                            pass
            return results

        recent_data = extract_exercise_data(
            [w for w in all_workouts if w.session_date >= recent_cut],
            exercise_name
        )
        older_data  = extract_exercise_data(
            [w for w in all_workouts if w.session_date < recent_cut],
            exercise_name
        )

        if not recent_data:
            return {
                "success": True,
                "message": f"No recent data found for {exercise_name}",
                "has_data": False
            }

        recent_max = max(d['weight_kg'] for d in recent_data) if recent_data else 0
        older_max  = max(d['weight_kg'] for d in older_data)  if older_data  else 0

        if older_max == 0:
            recommendation = "Not enough historical data to compare. Keep training consistently."
            progress_pct   = None
        elif recent_max > older_max:
            diff           = round(recent_max - older_max, 1)
            progress_pct   = round((diff / older_max) * 100, 1)
            recommendation = (
                f"Great progress! You have added {diff}kg "
                f"({progress_pct}%) in the last 4 weeks. "
                f"Consider adding another 2.5kg next session."
            )
        elif recent_max == older_max:
            recommendation = (
                f"Weight has been consistent at {recent_max}kg for 4 weeks. "
                f"Try adding 2.5kg or increasing reps before adding weight."
            )
        else:
            diff           = round(older_max - recent_max, 1)
            recommendation = (
                f"Performance has dipped by {diff}kg. "
                f"Check recovery, sleep, and nutrition. "
                f"A deload may be beneficial."
            )

        return {
            "success": True,
            "exercise": exercise_name,
            "has_data": True,
            "recent_max_kg": recent_max,
            "previous_max_kg": older_max,
            "recommendation": recommendation,
            "recent_sessions": recent_data,
            "older_sessions": older_data
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()
