"""
User Profile Tools — Phase 3

Tools for managing user profiles and progress metrics.
"""

from datetime import datetime, timedelta
from backend.database import SessionLocal, User, WorkoutLog, NutritionLog


def get_user_profile(user_id: str) -> dict:
    """
    Retrieve a user's stored profile.

    Returns profile data if it exists, or a message
    indicating the user needs to complete assessment.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            return {
                "success": True,
                "profile_exists": False,
                "message": "No profile found. User needs to complete assessment."
            }

        return {
            "success": True,
            "profile_exists": True,
            "profile": {
                "name":          user.name,
                "age":           user.age,
                "weight_kg":     user.weight_kg,
                "height_cm":     user.height_cm,
                "gender":        user.gender,
                "fitness_level": user.fitness_level,
                "goal":          user.goal,
                "injuries":      user.injuries,
                "equipment":     user.equipment
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def update_user_profile(user_id: str, **kwargs) -> dict:
    """
    Create or update a user's profile.

    Accepts any profile fields as keyword arguments:
    name, age, weight_kg, height_cm, gender,
    fitness_level, goal, injuries, equipment
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            user = User(id=user_id)
            db.add(user)

        allowed_fields = [
            'name', 'age', 'weight_kg', 'height_cm',
            'gender', 'fitness_level', 'goal', 'injuries', 'equipment'
        ]
        updated = []
        for field in allowed_fields:
            if field in kwargs and kwargs[field] is not None:
                setattr(user, field, kwargs[field])
                updated.append(field)

        user.updated_at = datetime.utcnow()
        db.commit()

        return {
            "success": True,
            "updated_fields": updated,
            "message": f"Profile updated: {', '.join(updated)}"
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_progress_metrics(user_id: str, days: int = 30) -> dict:
    """
    Compute progress metrics from workout and nutrition history.

    Returns strength trends, consistency stats, volume progression,
    and personal records for main lifts.

    Args:
        user_id: the user's ID
        days: how many days to analyze

    Returns:
        dict with comprehensive progress metrics
    """
    db = SessionLocal()
    try:
        cutoff   = datetime.utcnow() - timedelta(days=days)
        workouts = db.query(WorkoutLog).filter(
            WorkoutLog.user_id == user_id,
            WorkoutLog.session_date >= cutoff
        ).order_by(WorkoutLog.session_date.asc()).all()

        if not workouts:
            return {
                "success": True,
                "has_data": False,
                "message": f"No workout data in the last {days} days"
            }

        # Workout frequency
        total_sessions  = len(workouts)
        weeks           = max(days / 7, 1)
        sessions_per_week = round(total_sessions / weeks, 1)

        # Volume trend (split into first half vs second half)
        mid             = len(workouts) // 2
        first_half_vol  = sum(w.total_volume_kg or 0 for w in workouts[:mid])
        second_half_vol = sum(w.total_volume_kg or 0 for w in workouts[mid:])
        volume_trend    = "increasing" if second_half_vol > first_half_vol else (
                          "stable" if abs(second_half_vol - first_half_vol) < 100
                          else "decreasing"
        )

        # Personal records — find max weight per exercise
        prs = {}
        for w in workouts:
            for ex in (w.exercises or []):
                name   = ex.get('name', 'Unknown')
                weight = float(ex.get('weight_kg') or 0)
                if weight > 0:
                    if name not in prs or weight > prs[name]['weight']:
                        prs[name] = {
                            'weight': weight,
                            'date': w.session_date.strftime("%Y-%m-%d")
                        }

        # Consistency score (days trained / total days * 100)
        consistency_score = round(
            (total_sessions / max(days / 7 * 3, 1)) * 100, 1
        )
        consistency_score = min(consistency_score, 100)

        return {
            "success": True,
            "has_data": True,
            "period_days": days,
            "total_sessions": total_sessions,
            "sessions_per_week": sessions_per_week,
            "consistency_score": consistency_score,
            "volume_trend": volume_trend,
            "total_volume_kg": round(
                sum(w.total_volume_kg or 0 for w in workouts), 2
            ),
            "personal_records": prs,
            "summary": (
                f"{total_sessions} sessions in {days} days "
                f"({sessions_per_week}/week). "
                f"Volume trend: {volume_trend}. "
                f"Consistency: {consistency_score}%"
            )
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()
