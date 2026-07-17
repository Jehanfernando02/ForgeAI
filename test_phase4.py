import os
import sys
from pathlib import Path

# Add project root to python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv
load_dotenv()

from backend.memory.embeddings import get_embeddings_client
from backend.memory.vector_store import (
    get_collection, store_user_note, retrieve_user_notes,
    retrieve_workout_history, store_workout_log
)
from backend.memory.rag_pipeline import extract_and_store_facts, build_rag_context
from backend.memory.seed_knowledge import seed_all

def test_embeddings():
    print("\n--- 1. Testing Embedding Generation ---")
    client = get_embeddings_client()
    text = "Hello world from ForgeAI!"
    embedding = client.embed_query(text)
    print(f"Embedding generated successfully! Vector length: {len(embedding)}")
    assert len(embedding) > 0, "Embedding length must be greater than 0"
    print("✅ Embedding generation verified.")

def test_multi_tenancy_guardrails():
    print("\n--- 2. Testing Multi-Tenancy Security Guardrails ---")
    user_a = "test_user_alice_999"
    user_b = "test_user_bob_888"
    
    # Clean old notes for these users
    notes_coll = get_collection("user_notes")
    try:
        notes_coll.delete(where={"user_id": user_a})
        notes_coll.delete(where={"user_id": user_b})
    except Exception:
        pass
        
    # Store note for Alice
    store_user_note(user_id=user_a, note_type="injury", content="Alice has a bad rotator cuff in her left shoulder.")
    # Store note for Bob
    store_user_note(user_id=user_b, note_type="injury", content="Bob has a severe right knee ligament strain.")
    
    # Retrieve notes for Alice with a shoulder query
    alice_results = retrieve_user_notes(user_id=user_a, query="shoulder pain", limit=2, threshold=0.1)
    print(f"Alice's search results for 'shoulder pain':")
    for r in alice_results:
        print(f"  - Document: {r['document']} (Similarity: {r['similarity']:.3f})")
    assert len(alice_results) == 1, "Alice should retrieve exactly 1 result"
    assert "Alice" in alice_results[0]["document"], "Alice should retrieve her own note"
    
    # Search for shoulder pain under Bob's ID
    bob_shoulder_results = retrieve_user_notes(user_id=user_b, query="shoulder pain", limit=2, threshold=0.1)
    print(f"Bob's search results for 'shoulder pain': {bob_shoulder_results}")
    for r in bob_shoulder_results:
        assert r['metadata']['user_id'] == user_b, f"Security Violation: Bob retrieved Alice's note: {r}"
        assert "Alice" not in r['document'], f"Security Violation: Bob retrieved Alice's content: {r}"
        
    # Search for knee pain under Alice's ID
    alice_knee_results = retrieve_user_notes(user_id=user_a, query="knee strain", limit=2, threshold=0.1)
    print(f"Alice's search results for 'knee strain': {alice_knee_results}")
    for r in alice_knee_results:
        assert r['metadata']['user_id'] == user_a, f"Security Violation: Alice retrieved Bob's note: {r}"
        assert "Bob" not in r['document'], f"Security Violation: Alice retrieved Bob's content: {r}"
    
    print("✅ Multi-tenancy isolation and security guardrails verified.")

def test_semantic_retrieval():
    print("\n--- 3. Testing Semantic Matching Thresholds ---")
    user = "test_user_charlie_777"
    
    notes_coll = get_collection("user_notes")
    try:
        notes_coll.delete(where={"user_id": user})
    except Exception:
        pass
        
    store_user_note(user_id=user, note_type="injury", content="Charlie has chronic discomfort in his left knee joint during lower body workouts.")
    
    # Match query "leg routine" semantically (knee joint should match lower body workouts)
    results = retrieve_user_notes(user_id=user, query="leg routine", limit=2, threshold=0.55)
    print(f"Charlie's search results for 'leg routine':")
    for r in results:
        print(f"  - Document: {r['document']} (Similarity: {r['similarity']:.3f})")
    assert len(results) == 1, "Charlie should semantically match the knee note with 'leg routine'"
    
    # Match query "sore knee joint" (should have high similarity)
    high_match = retrieve_user_notes(user_id=user, query="sore knee joint", limit=2, threshold=0.60)
    print(f"Charlie's search results for 'sore knee joint':")
    for r in high_match:
        print(f"  - Document: {r['document']} (Similarity: {r['similarity']:.3f})")
    assert len(high_match) == 1, "Charlie should match high similarity"
    
    # Test threshold rejection: query something completely unrelated
    unrelated = retrieve_user_notes(user_id=user, query="lasagna recipe", limit=2, threshold=0.55)
    print(f"Charlie's search results for 'lasagna recipe': {unrelated}")
    assert len(unrelated) == 0, "Unrelated queries should be filtered out by similarity threshold"
    
    print("✅ Semantic retrieval and similarity thresholds verified.")

def test_llm_fact_extraction():
    print("\n--- 4. Testing LLM-Based Fact Extraction ---")
    user = "test_user_dan_555"
    
    notes_coll = get_collection("user_notes")
    try:
        notes_coll.delete(where={"user_id": user})
    except Exception:
        pass
        
    message = "I am recovering from a bad left knee injury and I only have access to dumbbells at my home setup."
    print(f"Processing user message: \"{message}\"")
    
    facts = extract_and_store_facts(user, message)
    print(f"Extracted and stored facts: {facts}")
    
    assert len(facts) >= 2, "Should extract at least two facts (knee injury and dumbbell access)"
    
    # Retrieve notes from vector store to verify they got persisted correctly
    notes = retrieve_user_notes(user, "leg workout", limit=5, threshold=0.1)
    print("Retrieved notes from vector store:")
    for n in notes:
         print(f"  - [{n['metadata']['note_type']}]: {n['document']}")
         
    assert any(n['metadata']['note_type'] == 'injury' for n in notes), "Injury note should be present"
    assert any(n['metadata']['note_type'] == 'equipment' for n in notes), "Equipment note should be present"
    
    print("✅ LLM-based fact extraction and persistence verified.")

def test_seeding_and_rag_context():
    print("\n--- 5. Testing Seeding and RAG Context Building ---")
    # Seed static exercise library and research papers
    seed_all()
    
    # Query Workout Planner context for user Dan (who has the knee injury and dumbbell access)
    user = "test_user_dan_555"
    context = build_rag_context(user, "workout_planner", "Can you design a leg workout?")
    
    print("\nGenerated RAG Context for Workout Planner:")
    print("=" * 80)
    print(context)
    print("=" * 80)
    
    assert "knee" in context.lower(), "Context should contain knee injury facts"
    assert "dumbbell" in context.lower(), "Context should contain dumbbell equipment details"
    assert "squat" in context.lower() or "deadlift" in context.lower(), "Context should retrieve relevant exercise knowledge"
    
    print("✅ Seeding and RAG context building verified.")

if __name__ == "__main__":
    print("Starting Phase 4 Automated Test suite...")
    try:
        test_embeddings()
        test_multi_tenancy_guardrails()
        test_semantic_retrieval()
        test_llm_fact_extraction()
        test_seeding_and_rag_context()
        print("\n🎉 ALL PHASE 4 AUTOMATED TESTS PASSED SUCCESSFULLY! 🎉\n")
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {str(e)}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
