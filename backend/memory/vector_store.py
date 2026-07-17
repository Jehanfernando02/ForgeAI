import os
import uuid
import chromadb
from typing import List, Dict, Any, Optional
from backend.memory.embeddings import GeminiEmbeddingFunction

CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")

def get_chroma_client() -> chromadb.PersistentClient:
    """Initialize and return a persistent ChromaDB client."""
    return chromadb.PersistentClient(path=CHROMA_PATH)

def get_collection(collection_name: str) -> chromadb.Collection:
    """
    Get or create a collection in ChromaDB.
    Sets the distance metric space to 'cosine'.
    """
    client = get_chroma_client()
    embedding_fn = GeminiEmbeddingFunction()
    # Using cosine space: similarity = 1 - distance
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"}
    )

# ── STORAGE FUNCTIONS ─────────────────────────────────────────────────────────

def store_user_note(user_id: str, note_type: str, content: str, note_id: Optional[str] = None) -> str:
    """
    Store a user-specific fact or note in the 'user_notes' collection.
    
    Args:
        user_id: The session ID or user identifier
        note_type: Category (e.g., 'injury', 'goal', 'preference', 'coaching_summary')
        content: The text description of the note
        note_id: Optional custom ID. If None, a UUID is generated.
        
    Returns:
        The ID of the stored note.
    """
    collection = get_collection("user_notes")
    if not note_id:
        note_id = f"note_{uuid.uuid4().hex}"
        
    metadata = {
        "user_id": user_id,
        "note_type": note_type,
        "created_at": os.getenv("CURRENT_TIME", "") or str(os.times()[4])
    }
    
    collection.upsert(
        ids=[note_id],
        documents=[content],
        metadatas=[metadata]
    )
    return note_id

def store_workout_log(user_id: str, date_str: str, summary: str, log_id: Optional[str] = None) -> str:
    """
    Store a workout summary in the 'user_workout_logs' collection.
    
    Args:
        user_id: The user ID
        date_str: Date of the workout session
        summary: Structured summary of the logged exercises and notes
        log_id: Optional log ID
        
    Returns:
        The stored log ID.
    """
    collection = get_collection("user_workout_logs")
    if not log_id:
        log_id = f"work_{uuid.uuid4().hex}"
        
    metadata = {
        "user_id": user_id,
        "date": date_str,
        "created_at": os.getenv("CURRENT_TIME", "") or str(os.times()[4])
    }
    
    collection.upsert(
        ids=[log_id],
        documents=[summary],
        metadatas=[metadata]
    )
    return log_id

def store_exercise_knowledge(exercise_name: str, instructions: str, equipment: str, difficulty: str) -> str:
    """Store exercise details for semantic searching."""
    collection = get_collection("exercise_knowledge")
    metadata = {
        "name": exercise_name,
        "equipment": equipment,
        "difficulty": difficulty
    }
    collection.upsert(
        ids=[f"ex_{exercise_name.replace(' ', '_').lower()}"],
        documents=[f"{exercise_name}: {instructions}"],
        metadatas=[metadata]
    )
    return exercise_name

def store_research(research_title: str, summary_content: str, source: str = "") -> str:
    """Store evidence-based fitness research summaries."""
    collection = get_collection("fitness_research")
    metadata = {
        "title": research_title,
        "source": source
    }
    collection.upsert(
        ids=[f"res_{research_title.replace(' ', '_').lower()}"],
        documents=[summary_content],
        metadatas=[metadata]
    )
    return research_title

# ── RETRIEVAL FUNCTIONS ───────────────────────────────────────────────────────

def query_collection_with_threshold(
    collection_name: str,
    query_text: str,
    limit: int,
    threshold: float,
    where_filter: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Helper to query a collection, apply metadata filters,
    and filter out results that fall below a minimum similarity threshold.
    """
    collection = get_collection(collection_name)
    
    query_args = {
        "query_texts": [query_text],
        "n_results": limit
    }
    if where_filter:
        query_args["where"] = where_filter
        
    results = collection.query(**query_args)
    
    filtered_results = []
    
    if not results or not results.get("documents") or len(results["documents"][0]) == 0:
        return []
        
    documents = results["documents"][0]
    metadatas = results["metadatas"][0] if results.get("metadatas") else [{} for _ in documents]
    distances = results["distances"][0] if results.get("distances") else [0.0 for _ in documents]
    ids = results["ids"][0]
    
    for i in range(len(documents)):
        # Under cosine space, similarity = 1.0 - distance
        similarity = 1.0 - distances[i]
        if similarity >= threshold:
            filtered_results.append({
                "id": ids[i],
                "document": documents[i],
                "metadata": metadatas[i],
                "similarity": similarity
            })
            
    return filtered_results

def retrieve_user_notes(user_id: str, query: str, limit: int = 5, threshold: float = 0.55, note_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieve semantic matches from the user notes collection.
    Guarantees user isolation via user_id metadata filtering.
    """
    where_filter = {"user_id": user_id}
    if note_type:
        where_filter = {
            "$and": [
                {"user_id": user_id},
                {"note_type": note_type}
            ]
        }
    return query_collection_with_threshold(
        collection_name="user_notes",
        query_text=query,
        limit=limit,
        threshold=threshold,
        where_filter=where_filter
    )

def retrieve_workout_history(user_id: str, query: str, limit: int = 3, threshold: float = 0.50) -> List[Dict[str, Any]]:
    """
    Retrieve semantic matches from the user's past workout logs.
    Guarantees user isolation via user_id metadata filtering.
    """
    return query_collection_with_threshold(
        collection_name="user_workout_logs",
        query_text=query,
        limit=limit,
        threshold=threshold,
        where_filter={"user_id": user_id}
    )

def retrieve_exercise_knowledge(query: str, limit: int = 3, threshold: float = 0.50) -> List[Dict[str, Any]]:
    """Retrieve semantically related exercise guides."""
    return query_collection_with_threshold(
        collection_name="exercise_knowledge",
        query_text=query,
        limit=limit,
        threshold=threshold
    )

def retrieve_fitness_research(query: str, limit: int = 3, threshold: float = 0.50) -> List[Dict[str, Any]]:
    """Retrieve evidence-based fitness research matching the query."""
    return query_collection_with_threshold(
        collection_name="fitness_research",
        query_text=query,
        limit=limit,
        threshold=threshold
    )
