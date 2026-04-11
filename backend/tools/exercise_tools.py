"""
Exercise Library Tools — Phase 3

Tools for searching and retrieving exercises from the database.
"""

from backend.database import SessionLocal, ExerciseLibrary


def search_exercises(
    muscle_group: str = None,
    equipment: str = None,
    difficulty: str = None,
    movement_pattern: str = None,
    limit: int = 10
) -> dict:
    """
    Search the exercise library by various filters.

    Args:
        muscle_group: chest/back/legs/shoulders/arms/core
        equipment: barbell/dumbbell/cable/machine/bodyweight
        difficulty: beginner/intermediate/advanced
        movement_pattern: push/pull/squat/hinge/carry
        limit: max results to return

    Returns:
        dict with matching exercises
    """
    db = SessionLocal()
    try:
        query = db.query(ExerciseLibrary)

        if muscle_group:
            query = query.filter(
                ExerciseLibrary.muscle_group.ilike(f"%{muscle_group}%")
            )
        if equipment:
            query = query.filter(
                ExerciseLibrary.equipment.ilike(f"%{equipment}%")
            )
        if difficulty:
            query = query.filter(
                ExerciseLibrary.difficulty == difficulty.lower()
            )
        if movement_pattern:
            query = query.filter(
                ExerciseLibrary.movement_pattern == movement_pattern.lower()
            )

        exercises = query.limit(limit).all()

        if not exercises:
            return {
                "success": True,
                "exercises": [],
                "message": "No exercises found matching those criteria"
            }

        return {
            "success": True,
            "exercises": [
                {
                    "name": ex.name,
                    "muscle_group": ex.muscle_group,
                    "secondary_muscles": ex.secondary_muscles,
                    "equipment": ex.equipment,
                    "difficulty": ex.difficulty,
                    "movement_pattern": ex.movement_pattern,
                    "instructions": ex.instructions,
                    "coaching_cues": ex.coaching_cues
                }
                for ex in exercises
            ],
            "count": len(exercises)
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_exercise_details(exercise_name: str) -> dict:
    """
    Get full details for a specific exercise by name.

    Args:
        exercise_name: name of the exercise

    Returns:
        dict with complete exercise information
    """
    db = SessionLocal()
    try:
        exercise = db.query(ExerciseLibrary).filter(
            ExerciseLibrary.name.ilike(f"%{exercise_name}%")
        ).first()

        if not exercise:
            return {
                "success": False,
                "message": f"Exercise '{exercise_name}' not found in library"
            }

        return {
            "success": True,
            "exercise": {
                "name": exercise.name,
                "muscle_group": exercise.muscle_group,
                "secondary_muscles": exercise.secondary_muscles,
                "equipment": exercise.equipment,
                "difficulty": exercise.difficulty,
                "movement_pattern": exercise.movement_pattern,
                "instructions": exercise.instructions,
                "coaching_cues": exercise.coaching_cues
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()
