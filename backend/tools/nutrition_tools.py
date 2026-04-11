"""
Nutrition Tools — Phase 3

Tools for nutrition calculations and food logging.
"""

from datetime import datetime, timedelta
from backend.database import SessionLocal, NutritionLog, User


def calculate_tdee(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    goal: str
) -> dict:
    """
    Calculate Total Daily Energy Expenditure and macro targets.

    Uses Mifflin-St Jeor for BMR.
    Applies activity multiplier for TDEE.
    Adjusts calories based on goal.

    Args:
        weight_kg: body weight in kg
        height_cm: height in cm
        age: age in years
        gender: male/female
        activity_level: sedentary/light/moderate/active
        goal: cut/maintain/bulk

    Returns:
        dict with BMR, TDEE, goal calories, and macro targets
    """
    # BMR — Mifflin-St Jeor
    if gender.lower() == 'male':
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161

    # Activity multipliers
    multipliers = {
        'sedentary': 1.2,
        'light':     1.375,
        'moderate':  1.55,
        'active':    1.725
    }
    multiplier = multipliers.get(activity_level.lower(), 1.55)
    tdee       = bmr * multiplier

    # Goal adjustments
    goal_adjustments = {
        'cut':      -400,
        'cutting':  -400,
        'bulk':     +300,
        'bulking':  +300,
        'maintain': 0,
        'recomp':   0
    }
    adjustment    = goal_adjustments.get(goal.lower(), 0)
    goal_calories = tdee + adjustment

    # Safety floor
    if gender.lower() == 'female' and goal_calories < 1200:
        goal_calories = 1200
    elif gender.lower() == 'male' and goal_calories < 1500:
        goal_calories = 1500

    # Macros — protein first, then fats, then carbs
    protein_g = round(weight_kg * 2.0, 0)
    fat_g     = round(weight_kg * 1.0, 0)
    protein_cal = protein_g * 4
    fat_cal     = fat_g * 9
    carb_cal    = goal_calories - protein_cal - fat_cal
    carb_g      = round(carb_cal / 4, 0)

    return {
        "success": True,
        "bmr":           round(bmr, 0),
        "tdee":          round(tdee, 0),
        "goal_calories": round(goal_calories, 0),
        "adjustment":    adjustment,
        "protein_g":     protein_g,
        "fat_g":         fat_g,
        "carb_g":        max(carb_g, 50),  # minimum 50g carbs
        "calculation_shown": (
            f"BMR = (10×{weight_kg}) + (6.25×{height_cm}) - "
            f"(5×{age}) {'+ 5' if gender.lower()=='male' else '- 161'} "
            f"= {round(bmr,0)} kcal | "
            f"TDEE = {round(bmr,0)} × {multiplier} = {round(tdee,0)} kcal | "
            f"Goal = {round(tdee,0)} {'+' if adjustment>=0 else ''}"
            f"{adjustment} = {round(goal_calories,0)} kcal"
        )
    }


def log_nutrition(
    user_id: str,
    meals: list,
    notes: str = ""
) -> dict:
    """
    Save a nutrition log entry to the database.

    Args:
        user_id: the user's ID
        meals: list of meal dicts with foods and macros
        notes: any notes about the day's eating

    Returns:
        dict with success status and daily totals
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id)
            db.add(user)
            db.flush()

        # Sum daily totals from meals
        total_calories = sum(
            sum(f.get('estimated_calories', 0) for f in m.get('foods', []))
            for m in meals
        )
        total_protein = sum(
            sum(f.get('estimated_protein_g', 0) for f in m.get('foods', []))
            for m in meals
        )
        total_carbs = sum(
            sum(f.get('estimated_carbs_g', 0) for f in m.get('foods', []))
            for m in meals
        )
        total_fat = sum(
            sum(f.get('estimated_fat_g', 0) for f in m.get('foods', []))
            for m in meals
        )

        nutrition_log = NutritionLog(
            user_id=user_id,
            meals=meals,
            total_calories=round(total_calories, 1),
            total_protein=round(total_protein, 1),
            total_carbs=round(total_carbs, 1),
            total_fat=round(total_fat, 1),
            notes=notes,
            log_date=datetime.utcnow()
        )
        db.add(nutrition_log)
        db.commit()

        return {
            "success": True,
            "log_id": nutrition_log.id,
            "daily_totals": {
                "calories": round(total_calories, 1),
                "protein_g": round(total_protein, 1),
                "carbs_g": round(total_carbs, 1),
                "fat_g": round(total_fat, 1)
            },
            "message": f"Nutrition logged. {round(total_calories)} kcal, {round(total_protein)}g protein"
        }

    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def get_nutrition_history(user_id: str, days: int = 7) -> dict:
    """
    Retrieve nutrition logs for the past N days.

    Args:
        user_id: the user's ID
        days: how many days to look back

    Returns:
        dict with daily logs and averages
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        logs   = db.query(NutritionLog).filter(
            NutritionLog.user_id == user_id,
            NutritionLog.log_date >= cutoff
        ).order_by(NutritionLog.log_date.desc()).all()

        if not logs:
            return {
                "success": True,
                "logs": [],
                "message": f"No nutrition logs in the last {days} days",
                "averages": {}
            }

        daily_logs = [
            {
                "date": log.log_date.strftime("%Y-%m-%d"),
                "calories": log.total_calories,
                "protein_g": log.total_protein,
                "carbs_g": log.total_carbs,
                "fat_g": log.total_fat,
                "notes": log.notes
            }
            for log in logs
        ]

        avg_calories = sum(l['calories'] or 0 for l in daily_logs) / len(daily_logs)
        avg_protein  = sum(l['protein_g'] or 0 for l in daily_logs) / len(daily_logs)

        return {
            "success": True,
            "logs": daily_logs,
            "total_days_logged": len(daily_logs),
            "averages": {
                "calories": round(avg_calories, 1),
                "protein_g": round(avg_protein, 1)
            }
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.close()
