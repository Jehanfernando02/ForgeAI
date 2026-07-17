import os
import sys
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.resolve()))

from backend.database import SessionLocal, ExerciseLibrary, init_db
from backend.memory.vector_store import (
    get_collection, store_exercise_knowledge, store_research
)

RESEARCH_PAPERS = [
    {
        "title": "Progressive Overload for Hypertrophy",
        "content": "Research shows that muscle hypertrophy is primarily driven by progressive overload, which is the gradual increase of stress placed upon the musculoskeletal system. This is best achieved by increasing weight, volume (reps/sets), or decreasing rest periods over time while maintaining proper form.",
        "source": "Journal of Strength and Conditioning Research (2010)"
    },
    {
        "title": "Volume and Frequency Guidelines",
        "content": "Evidence suggests that doing 10 to 20 working sets per muscle group per week is optimal for muscle growth. For best results, this volume should be split across 2 to 3 weekly sessions per muscle group, rather than done all in one session ('junk volume').",
        "source": "Sports Medicine Review (2016)"
    },
    {
        "title": "Rest Periods for Strength",
        "content": "Studies show that resting 3 to 5 minutes between sets of heavy compound exercises (like squats or bench press) maximizes strength gains by allowing full replenishment of ATP-CP stores. For hypertrophy-focused workouts, 1 to 2 minutes of rest is sufficient.",
        "source": "European Journal of Applied Physiology (2017)"
    },
    {
        "title": "RPE and Training to Failure",
        "content": "Training with a Rate of Perceived Exertion (RPE) of 7 to 9 (1 to 3 repetitions in reserve, or RIR) is highly effective for building muscle while avoiding excessive central nervous system fatigue. Training to absolute muscular failure (RPE 10) is not necessary for every set and should be used sparingly.",
        "source": "Journal of Sports Sciences (2020)"
    },
    {
        "title": "Dietary Protein Guidelines",
        "content": "To support muscle protein synthesis and recovery, active individuals should consume 1.6 to 2.2 grams of protein per kilogram of body weight per day (0.7 to 1.0 grams per pound). This protein intake should ideally be distributed evenly across 3 to 5 meals throughout the day.",
        "source": "International Society of Sports Nutrition (2017)"
    },
    {
        "title": "TDEE and Mifflin-St Jeor Accuracy",
        "content": "The Mifflin-St Jeor equation is considered one of the most reliable formulas for estimating Basal Metabolic Rate (BMR) in healthy adults. It calculates BMR using weight, height, age, and gender, which is then multiplied by an activity factor to find Total Daily Energy Expenditure (TDEE).",
        "source": "American Journal of Clinical Nutrition (1990)"
    },
    {
        "title": "Deload Week Protocols",
        "content": "A deload week is a planned reduction in training volume and intensity (typically a 30% to 50% decrease in sets and a 10% reduction in weight) every 6 to 12 weeks. Deload weeks allow joints, tendons, and the nervous system to fully recover from accumulated training stress, preventing plateaus and overtraining.",
        "source": "Strength & Conditioning Journal (2018)"
    },
    {
        "title": "DOMS and Recovery Signs",
        "content": "Delayed Onset Muscle Soreness (DOMS) typically peaks 24 to 72 hours after unaccustomed exercise. It is caused by micro-tears in muscle fibers and is a normal part of training. Severe pain that is sharp, unilateral, or persists for more than 5 days, or occurs in a joint rather than muscle, is a warning sign of injury, not normal soreness.",
        "source": "Sports Medicine (2003)"
    },
    {
        "title": "Sleep and Muscle Recovery",
        "content": "Research shows that sleep deprivation (less than 7 hours per night) significantly impairs muscle recovery, decreases protein synthesis rates, alters hormone levels (elevating cortisol and lowering testosterone), and increases the risk of training-related injuries. 8 to 9 hours is optimal for athletes.",
        "source": "Medical Hypotheses (2011)"
    },
    {
        "title": "Warm-Up and Mobility",
        "content": "An effective warm-up should consist of 5-10 minutes of light cardiovascular activity followed by dynamic stretching and ramp-up sets for the target exercises. Static stretching before lifting can temporarily reduce maximum strength output and should be avoided.",
        "source": "Journal of Strength & Conditioning Research (2012)"
    }
]

def seed_exercise_knowledge(db_session):
    """Seed the exercise_knowledge vector collection from SQLite exercise_library."""
    collection = get_collection("exercise_knowledge")
    if collection.count() > 0:
        print("  exercise_knowledge vector collection already seeded.")
        return

    exercises = db_session.query(ExerciseLibrary).all()
    if not exercises:
        print("  SQL database is empty. Seeding SQL database first...")
        init_db()
        exercises = db_session.query(ExerciseLibrary).all()

    print(f"  Seeding {len(exercises)} exercises into ChromaDB...")
    for ex in exercises:
        # Formulate a descriptive text representation for embeddings
        instruction_text = (
            f"Exercise Name: {ex.name}\n"
            f"Primary Target Muscle Group: {ex.muscle_group}\n"
            f"Secondary Muscles: {ex.secondary_muscles or 'None'}\n"
            f"Equipment: {ex.equipment}\n"
            f"Movement Pattern: {ex.movement_pattern or 'N/A'}\n"
            f"Difficulty Level: {ex.difficulty}\n"
            f"Instructions:\n{ex.instructions}\n"
            f"Coaching Cues: {ex.coaching_cues}"
        )
        store_exercise_knowledge(
            exercise_name=ex.name,
            instructions=instruction_text,
            equipment=ex.equipment,
            difficulty=ex.difficulty
        )
    print("  Exercise library vector seeding complete.")

def seed_fitness_research():
    """Seed the fitness_research vector collection with evidence-based summaries."""
    collection = get_collection("fitness_research")
    if collection.count() > 0:
        print("  fitness_research vector collection already seeded.")
        return

    print(f"  Seeding {len(RESEARCH_PAPERS)} research articles into ChromaDB...")
    for paper in RESEARCH_PAPERS:
        store_research(
            research_title=paper["title"],
            summary_content=paper["content"],
            source=paper["source"]
        )
    print("  Fitness research vector seeding complete.")

def seed_all():
    """Seed all static collections in ChromaDB."""
    print("Initializing SQLite database connection...")
    init_db()
    db = SessionLocal()
    try:
        print("Seeding exercise guides...")
        seed_exercise_knowledge(db)
        print("Seeding research guidelines...")
        seed_fitness_research()
        print("\n🎉 ChromaDB Seeding completed successfully.")
    except Exception as e:
        print(f"\n❌ Seeding failed: {str(e)}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_all()
