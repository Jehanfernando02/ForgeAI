import json
from typing import List, Optional
from backend.core import get_llm, extract_json_from_response
from backend.memory.vector_store import (
    store_user_note, retrieve_user_notes, retrieve_workout_history,
    retrieve_exercise_knowledge, retrieve_fitness_research
)

# ── RAG CONTEXT BUILDER ───────────────────────────────────────────────────────

def build_rag_context(user_id: str, agent_name: str, user_message: str) -> str:
    """
    Retrieve relevant history, guides, and science to build context for the active agent.
    
    Args:
        user_id: User identifier (session_id)
        agent_name: Active specialist agent (e.g., 'workout_planner')
        user_message: Current user message to match semantically
        
    Returns:
        A formatted markdown context block to prepend to the user query.
    """
    context_sections = []
    
    # 1. Retrieve User Notes (Goals, Injuries, Habits) - universally helpful
    # We query with slightly different thresholds depending on agent
    notes = retrieve_user_notes(user_id, user_message, limit=4, threshold=0.55)
    if notes:
        section = "### Relevant User Facts & Injuries:\n"
        for n in notes:
            section += f"- [{n['metadata'].get('note_type', 'note')}]: {n['document']}\n"
        context_sections.append(section)
        
    # 2. Agent-Specific Retrieval
    if agent_name == "workout_planner":
        # Workout Planner needs workout history, exercise knowledge, and sports science
        history = retrieve_workout_history(user_id, user_message, limit=2, threshold=0.50)
        if history:
            sect = "### User's Recent Workout History:\n"
            for h in history:
                sect += f"- [Date: {h['metadata'].get('date', 'unknown')}]: {h['document']}\n"
            context_sections.append(sect)
            
        exercises = retrieve_exercise_knowledge(user_message, limit=3, threshold=0.50)
        if exercises:
            sect = "### Exercise Guides from Library:\n"
            for e in exercises:
                sect += f"- {e['document']}\n"
            context_sections.append(sect)
            
        research = retrieve_fitness_research(user_message, limit=2, threshold=0.50)
        if research:
            sect = "### Relevant Evidence-Based Training Research:\n"
            for r in research:
                sect += f"- *{r['metadata'].get('title', 'Research')}*: {r['document']}\n"
            context_sections.append(sect)
            
    elif agent_name == "progress_analyst":
        # Progress Analyst needs workout history & user notes
        history = retrieve_workout_history(user_id, user_message, limit=4, threshold=0.50)
        if history:
            sect = "### User's Logged Workouts:\n"
            for h in history:
                sect += f"- [Date: {h['metadata'].get('date', 'unknown')}]: {h['document']}\n"
            context_sections.append(sect)
            
    elif agent_name == "recovery_agent":
        # Recovery Agent needs workout history
        history = retrieve_workout_history(user_id, user_message, limit=3, threshold=0.50)
        if history:
            sect = "### Recent Training Load (Workout Summaries):\n"
            for h in history:
                sect += f"- [Date: {h['metadata'].get('date', 'unknown')}]: {h['document']}\n"
            context_sections.append(sect)
            
    elif agent_name == "nutrition_agent":
        # Nutrition Agent needs fitness research on dieting/nutrition
        research = retrieve_fitness_research(user_message, limit=2, threshold=0.50)
        if research:
            sect = "### Nutrition Research Guidelines:\n"
            for r in research:
                if "nutrition" in r['metadata'].get('title', '').lower() or "protein" in r['metadata'].get('title', '').lower():
                    sect += f"- *{r['metadata'].get('title', 'Research')}*: {r['document']}\n"
            context_sections.append(sect)
            
    if not context_sections:
        return ""
        
    header = "IMPORTANT: You are provided with the following retrieved contextual information about the user and research guidelines. Use this to personalize your response. Respect any injuries, goals, and equipment limits specified below:\n\n"
    return header + "\n".join(context_sections)

# ── FACT EXTRACTION ───────────────────────────────────────────────────────────

def extract_and_store_facts(user_id: str, user_message: str) -> List[str]:
    """
    Use Gemini to extract permanent facts (injuries, equipment, goals) and save them to vector store.
    """
    llm = get_llm(temperature=0.1)
    
    prompt = f"""You are a fitness profile extraction system. Read the user message below and extract any permanent personal facts relating to the following categories:
- Goals (e.g. want to build muscle, lose weight)
- Injuries/Pain (e.g. bad left shoulder, lower back tendonitis)
- Equipment Access (e.g. home gym with dumbbells, no barbell)
- Schedule/Habits (e.g. can only train 3 days a week, morning runner)

Rules:
1. Extract ONLY facts that are long-term constraints or characteristics. Do NOT extract temporary statements like "I am tired today."
2. Output your answer STRICTLY as a JSON list of strings (e.g. ["User has a left shoulder injury", "User only has access to dumbbells"]).
3. If no permanent facts are present, return an empty list: [].
4. Output ONLY valid JSON. No conversational introductions or markups.

User Message: "{user_message}"
JSON output:"""

    try:
        response = llm.invoke(prompt)
        facts = extract_json_from_response(response.content)
        
        if not facts or not isinstance(facts, list):
            return []
            
        stored_facts = []
        for fact in facts:
            fact_str = str(fact).strip()
            if not fact_str:
                continue
                
            # Classify note_type based on semantic keyword presence
            note_type = "preference"
            fact_lower = fact_str.lower()
            if any(k in fact_lower for k in ["hurt", "pain", "injury", "sore", "knee", "shoulder", "back", "wrist", "ankle"]):
                note_type = "injury"
            elif any(k in fact_lower for k in ["goal", "target", "want to", "aim"]):
                note_type = "goal"
            elif any(k in fact_lower for k in ["gym", "dumbbell", "barbell", "equipment", "cable", "machine"]):
                note_type = "equipment"
            elif any(k in fact_lower for k in ["day", "week", "time", "schedule", "morning", "night"]):
                note_type = "schedule"
                
            store_user_note(user_id, note_type, fact_str)
            stored_facts.append(fact_str)
            
        return stored_facts
    except Exception as e:
        print(f"[RAG Fact Extraction Error]: {str(e)}")
        return []

# ── INTERACTION SUMMARIZATION ──────────────────────────────────────────────────

def store_coaching_interaction(user_id: str, user_message: str, agent_response: str) -> Optional[str]:
    """
    Summarize a coaching turn and store it in vector memory as a 'coaching_summary'.
    """
    llm = get_llm(temperature=0.2)
    
    prompt = f"""You are a conversation summarizer. Summarize this user query and trainer response into a 1-sentence description of what happened for long-term memory retrieval.
    
User: "{user_message}"
Trainer: "{agent_response}"

Summarize as a 1-sentence note (e.g., "User asked for back exercises; Coach suggested Barbell Rows focusing on driving elbows to hips"):"""

    try:
        response = llm.invoke(prompt)
        summary = response.content.strip()
        if summary:
            # Store summary in ChromaDB
            return store_user_note(user_id, "coaching_summary", summary)
    except Exception as e:
        print(f"[RAG Interaction Store Error]: {str(e)}")
    return None
