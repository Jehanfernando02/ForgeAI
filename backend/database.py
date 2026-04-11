"""
ForgeAI Database — Phase 3

SQLite database using SQLAlchemy ORM.
Tables created automatically on first run.

In Phase 4 ChromaDB gets added alongside this for vector/semantic storage.
SQLite handles structured data (workouts, users, nutrition logs).
ChromaDB handles semantic search and memory retrieval.
"""

import os
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, Text, JSON, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

# Database file lives in the project root
DB_PATH = os.getenv("DATABASE_URL", "sqlite:///forgeai.db")
engine = create_engine(DB_PATH, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ── Models ────────────────────────────────────────────────────

class User(Base):
    """
    Stores user profile information.
    Created when a user completes the assessment flow.
    """
    __tablename__ = "users"

    id            = Column(String, primary_key=True)  # session_id for now
    name          = Column(String, nullable=True)
    age           = Column(Integer, nullable=True)
    weight_kg     = Column(Float, nullable=True)
    height_cm     = Column(Float, nullable=True)
    gender        = Column(String, nullable=True)
    fitness_level = Column(String, nullable=True)  # beginner/intermediate/advanced
    goal          = Column(String, nullable=True)
    injuries      = Column(Text, nullable=True)
    equipment     = Column(String, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    workouts      = relationship("WorkoutLog", back_populates="user")
    nutrition_logs = relationship("NutritionLog", back_populates="user")


class WorkoutLog(Base):
    """
    Each row is one complete workout session.
    exercises stored as JSON array of exercise objects.
    """
    __tablename__ = "workout_logs"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    user_id          = Column(String, ForeignKey("users.id"), nullable=False)
    session_date     = Column(DateTime, default=datetime.utcnow)
    exercises        = Column(JSON, nullable=False)   # list of exercise dicts
    total_volume_kg  = Column(Float, nullable=True)   # sum of sets*reps*weight
    session_notes    = Column(Text, nullable=True)
    perceived_difficulty = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    created_at       = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="workouts")


class NutritionLog(Base):
    """
    Daily nutrition log entries.
    meals stored as JSON array.
    """
    __tablename__ = "nutrition_logs"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(String, ForeignKey("users.id"), nullable=False)
    log_date     = Column(DateTime, default=datetime.utcnow)
    meals        = Column(JSON, nullable=True)
    total_calories = Column(Float, nullable=True)
    total_protein  = Column(Float, nullable=True)
    total_carbs    = Column(Float, nullable=True)
    total_fat      = Column(Float, nullable=True)
    notes          = Column(Text, nullable=True)
    created_at     = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="nutrition_logs")


class ExerciseLibrary(Base):
    """
    Static exercise database.
    Seeded on first run with common exercises.
    """
    __tablename__ = "exercise_library"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(String, nullable=False, unique=True)
    muscle_group    = Column(String, nullable=False)   # chest/back/legs/etc
    secondary_muscles = Column(JSON, nullable=True)
    equipment       = Column(String, nullable=False)   # barbell/dumbbell/bodyweight/cable/machine
    movement_pattern = Column(String, nullable=True)   # push/pull/hinge/squat/carry
    difficulty      = Column(String, nullable=True)    # beginner/intermediate/advanced
    instructions    = Column(Text, nullable=True)
    coaching_cues   = Column(Text, nullable=True)


def init_db():
    """Create all tables and seed exercise library if empty."""
    Base.metadata.create_all(engine)
    seed_exercise_library()
    print("  Database initialized")


def get_db():
    """Get a database session. Always close after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def seed_exercise_library():
    """Populate exercise library with common exercises if empty."""
    db = SessionLocal()
    try:
        if db.query(ExerciseLibrary).count() > 0:
            return  # Already seeded

        exercises = [
            # Chest
            {"name": "Barbell Bench Press", "muscle_group": "chest",
             "secondary_muscles": ["triceps", "front delts"],
             "equipment": "barbell", "movement_pattern": "push",
             "difficulty": "intermediate",
             "instructions": "Lie on bench, grip bar shoulder width plus, lower to chest, press up",
             "coaching_cues": "Retract scapula, drive feet into floor, bar path slight arc"},

            {"name": "Dumbbell Bench Press", "muscle_group": "chest",
             "secondary_muscles": ["triceps", "front delts"],
             "equipment": "dumbbell", "movement_pattern": "push",
             "difficulty": "beginner",
             "instructions": "Lie on bench with dumbbells, press up and in",
             "coaching_cues": "Control the descent, squeeze at top, neutral wrists"},

            {"name": "Incline Dumbbell Press", "muscle_group": "chest",
             "secondary_muscles": ["front delts", "triceps"],
             "equipment": "dumbbell", "movement_pattern": "push",
             "difficulty": "beginner",
             "instructions": "Set bench to 30-45 degrees, press dumbbells up",
             "coaching_cues": "Keep elbows at 45 degrees, feel upper chest stretch"},

            {"name": "Cable Fly", "muscle_group": "chest",
             "secondary_muscles": [],
             "equipment": "cable", "movement_pattern": "push",
             "difficulty": "beginner",
             "instructions": "Stand between cables, bring hands together in arc",
             "coaching_cues": "Slight elbow bend throughout, focus on chest squeeze"},

            {"name": "Push Up", "muscle_group": "chest",
             "secondary_muscles": ["triceps", "front delts", "core"],
             "equipment": "bodyweight", "movement_pattern": "push",
             "difficulty": "beginner",
             "instructions": "Plank position, lower chest to floor, push up",
             "coaching_cues": "Keep core tight, full range of motion"},

            # Back
            {"name": "Barbell Row", "muscle_group": "back",
             "secondary_muscles": ["biceps", "rear delts"],
             "equipment": "barbell", "movement_pattern": "pull",
             "difficulty": "intermediate",
             "instructions": "Hinge forward, row bar to lower chest",
             "coaching_cues": "Keep back flat, lead with elbows, squeeze shoulder blades"},

            {"name": "Pull Up", "muscle_group": "back",
             "secondary_muscles": ["biceps", "rear delts"],
             "equipment": "bodyweight", "movement_pattern": "pull",
             "difficulty": "intermediate",
             "instructions": "Hang from bar, pull chin over bar",
             "coaching_cues": "Full dead hang start, drive elbows to hips"},

            {"name": "Lat Pulldown", "muscle_group": "back",
             "secondary_muscles": ["biceps"],
             "equipment": "cable", "movement_pattern": "pull",
             "difficulty": "beginner",
             "instructions": "Pull bar to upper chest, controlled return",
             "coaching_cues": "Lean back slightly, drive elbows down, feel lats stretch"},

            {"name": "Seated Cable Row", "muscle_group": "back",
             "secondary_muscles": ["biceps", "rear delts"],
             "equipment": "cable", "movement_pattern": "pull",
             "difficulty": "beginner",
             "instructions": "Sit upright, pull handle to stomach",
             "coaching_cues": "Keep torso upright, squeeze at contraction"},

            {"name": "Dumbbell Row", "muscle_group": "back",
             "secondary_muscles": ["biceps"],
             "equipment": "dumbbell", "movement_pattern": "pull",
             "difficulty": "beginner",
             "instructions": "Support on bench, row dumbbell to hip",
             "coaching_cues": "Keep elbow close to body, full range of motion"},

            # Legs
            {"name": "Barbell Squat", "muscle_group": "legs",
             "secondary_muscles": ["glutes", "hamstrings", "core"],
             "equipment": "barbell", "movement_pattern": "squat",
             "difficulty": "intermediate",
             "instructions": "Bar on traps, squat to parallel or below",
             "coaching_cues": "Knees track toes, chest up, drive through heels"},

            {"name": "Romanian Deadlift", "muscle_group": "legs",
             "secondary_muscles": ["glutes", "lower back"],
             "equipment": "barbell", "movement_pattern": "hinge",
             "difficulty": "intermediate",
             "instructions": "Hinge at hips, lower bar along legs to mid shin",
             "coaching_cues": "Soft knee bend, push hips back, feel hamstring stretch"},

            {"name": "Leg Press", "muscle_group": "legs",
             "secondary_muscles": ["glutes"],
             "equipment": "machine", "movement_pattern": "squat",
             "difficulty": "beginner",
             "instructions": "Feet shoulder width on platform, press away",
             "coaching_cues": "Don't lock knees at top, control the descent"},

            {"name": "Bulgarian Split Squat", "muscle_group": "legs",
             "secondary_muscles": ["glutes", "core"],
             "equipment": "dumbbell", "movement_pattern": "squat",
             "difficulty": "intermediate",
             "instructions": "Rear foot elevated, squat on front leg",
             "coaching_cues": "Keep torso upright, knee tracks over toe"},

            {"name": "Leg Curl", "muscle_group": "legs",
             "secondary_muscles": [],
             "equipment": "machine", "movement_pattern": "hinge",
             "difficulty": "beginner",
             "instructions": "Curl weight toward glutes",
             "coaching_cues": "Full extension at start, squeeze at top"},

            # Shoulders
            {"name": "Overhead Press", "muscle_group": "shoulders",
             "secondary_muscles": ["triceps", "upper traps"],
             "equipment": "barbell", "movement_pattern": "push",
             "difficulty": "intermediate",
             "instructions": "Press bar from shoulder height to overhead",
             "coaching_cues": "Squeeze glutes, keep core tight, bar over mid foot"},

            {"name": "Dumbbell Lateral Raise", "muscle_group": "shoulders",
             "secondary_muscles": [],
             "equipment": "dumbbell", "movement_pattern": "push",
             "difficulty": "beginner",
             "instructions": "Raise dumbbells to shoulder height laterally",
             "coaching_cues": "Slight forward lean, lead with elbows, control descent"},

            {"name": "Face Pull", "muscle_group": "shoulders",
             "secondary_muscles": ["rear delts", "rotator cuff"],
             "equipment": "cable", "movement_pattern": "pull",
             "difficulty": "beginner",
             "instructions": "Pull rope to face, elbows high",
             "coaching_cues": "External rotation at end, great for shoulder health"},

            # Arms
            {"name": "Barbell Curl", "muscle_group": "arms",
             "secondary_muscles": ["brachialis"],
             "equipment": "barbell", "movement_pattern": "pull",
             "difficulty": "beginner",
             "instructions": "Curl bar from hips to chin",
             "coaching_cues": "Elbows stay fixed, squeeze at top, slow descent"},

            {"name": "Tricep Pushdown", "muscle_group": "arms",
             "secondary_muscles": [],
             "equipment": "cable", "movement_pattern": "push",
             "difficulty": "beginner",
             "instructions": "Push cable down, extend arms fully",
             "coaching_cues": "Elbows pinned to sides, full extension"},

            {"name": "Hammer Curl", "muscle_group": "arms",
             "secondary_muscles": ["brachialis", "brachioradialis"],
             "equipment": "dumbbell", "movement_pattern": "pull",
             "difficulty": "beginner",
             "instructions": "Neutral grip curl",
             "coaching_cues": "Neutral wrist throughout, controlled tempo"},

            {"name": "Skull Crusher", "muscle_group": "arms",
             "secondary_muscles": [],
             "equipment": "barbell", "movement_pattern": "push",
             "difficulty": "intermediate",
             "instructions": "Lower bar to forehead, extend up",
             "coaching_cues": "Elbows point to ceiling, controlled lowering"},

            # Core
            {"name": "Plank", "muscle_group": "core",
             "secondary_muscles": ["shoulders", "glutes"],
             "equipment": "bodyweight", "movement_pattern": "carry",
             "difficulty": "beginner",
             "instructions": "Hold plank position",
             "coaching_cues": "Neutral spine, squeeze everything, breathe"},

            {"name": "Cable Crunch", "muscle_group": "core",
             "secondary_muscles": [],
             "equipment": "cable", "movement_pattern": "push",
             "difficulty": "beginner",
             "instructions": "Kneel, crunch down against cable resistance",
             "coaching_cues": "Round the spine, feel abs contract"},

            {"name": "Deadlift", "muscle_group": "back",
             "secondary_muscles": ["legs", "glutes", "core"],
             "equipment": "barbell", "movement_pattern": "hinge",
             "difficulty": "advanced",
             "instructions": "Pull bar from floor to hip lockout",
             "coaching_cues": "Bar stays over mid foot, lat engagement, hip hinge"},
        ]

        for ex_data in exercises:
            db.add(ExerciseLibrary(**ex_data))

        db.commit()
        print(f"  Seeded {len(exercises)} exercises")

    finally:
        db.close()
