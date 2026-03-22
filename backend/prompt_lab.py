import os
import json
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash")


def load_prompt(agent_name: str) -> str:
    """Load a system prompt from the prompts directory."""
    # Handle both running from root and from backend/
    for path in [f"prompts/{agent_name}.md", f"../prompts/{agent_name}.md"]:
        if os.path.exists(path):
            with open(path, "r") as f:
                return f.read()
    raise FileNotFoundError(f"Prompt not found for agent: {agent_name}")


def ask_agent(
    agent_name: str,
    user_message: str,
    temperature: float = 0.5,
    conversation_history: list = None
) -> dict:
    """
    Send a message to a specific agent and return structured response.
    
    Args:
        agent_name: matches filename in prompts/ directory
        user_message: the user's input
        temperature: 0.0 (precise) to 1.0 (creative)
        conversation_history: list of previous turns
    
    Returns:
        dict containing raw response, parsed JSON if available, and metadata
    """
    system_prompt = load_prompt(agent_name)
    
    messages = []
    if conversation_history:
        # Flatten conversation history to a list of strings
        for turn in conversation_history:
            if isinstance(turn, dict) and "content" in turn:
                messages.append(turn["content"])
            elif isinstance(turn, str):
                messages.append(turn)
    messages.append(user_message)
    
    response = client.models.generate_content(
        model=MODEL,
        contents=messages,
        config={
            "system_instruction": system_prompt,
            "temperature": temperature,
            "max_output_tokens": 2048,
        }
    )
    
    response_text = response.text
    
    # Attempt JSON extraction
    structured = None
    try:
        clean = response_text.strip()
        if "```" in clean:
            parts = clean.split("```")
            for part in parts:
                if part.startswith("json"):
                    clean = part[4:].strip()
                    break
                elif part.strip().startswith("{"):
                    clean = part.strip()
                    break
        structured = json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        pass
    
    return {
        "agent": agent_name,
        "temperature": temperature,
        "user_message": user_message,
        "raw_response": response_text,
        "structured_response": structured,
        "token_count": (
            response.usage_metadata.total_token_count
            if response.usage_metadata else None
        )
    }


def print_result(result: dict):
    """Pretty print an agent result in the terminal."""
    print("\n" + "=" * 65)
    print(f"  AGENT : {result['agent'].upper().replace('_', ' ')}")
    print(f"  TEMP  : {result['temperature']}")
    print(f"  TOKENS: {result['token_count']}")
    print("-" * 65)
    print(f"  USER  : {result['user_message'][:80]}...")
    print("-" * 65)
    if result['structured_response']:
        print("  STRUCTURED OUTPUT:")
        print(json.dumps(result['structured_response'], indent=4))
    else:
        print("  RESPONSE:")
        print(result['raw_response'])
    print("=" * 65)


# ──────────────────────────────────────────────────────────────
# EXPERIMENTS — Run this file directly to test your agents
# python backend/prompt_lab.py
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":

    print("\n▶  EXPERIMENT 1: Supervisor Routing")
    messages = [
        "I want to start building muscle",
        "I've missed 3 workouts and feel like a failure",
        "What should my protein intake be at 80kg?",
        "I benched 100kg for the first time today!",
        "My squat hasn't improved in 6 weeks",
        "I'm really sore from yesterday, should I still train?",
    ]
    for msg in messages:
        result = ask_agent("supervisor", msg, temperature=0.1)
        print_result(result)

    print("\n▶  EXPERIMENT 2: Temperature Effect — Motivational Coach")
    msg = "I've been training 3 months and look exactly the same. What's the point?"
    for temp in [0.2, 0.7, 1.0]:
        result = ask_agent("motivational_coach", msg, temperature=temp)
        print_result(result)

    print("\n▶  EXPERIMENT 3: Workout Planner Structured Output")
    result = ask_agent(
        "workout_planner",
        """
        25 year old male, 8 months training, goal is hypertrophy.
        Full commercial gym. No injuries. Training 4 days per week.
        Design a chest and triceps session for today.
        """,
        temperature=0.3
    )
    print_result(result)

    print("\n▶  EXPERIMENT 4: Nutrition Agent Calculation")
    result = ask_agent(
        "nutrition_agent",
        """
        28 year old female, 65kg, 168cm. Trains 4 days per week with weights.
        Goal: body recomposition (lose fat, maintain muscle).
        Calculate my calorie and macro targets.
        """,
        temperature=0.1
    )
    print_result(result)

    print("\n▶  EXPERIMENT 5: Multi-turn Memory")
    history = []
    first = ask_agent(
        "workout_planner",
        "I want to start a new training program",
        temperature=0.3,
        conversation_history=history
    )
    print_result(first)
    history.append({"role": "user", "content": "I want to start a new training program"})
    history.append({"role": "model", "content": first['raw_response']})

    second = ask_agent(
        "workout_planner",
        "I should mention I have a bad left knee from a football injury",
        temperature=0.3,
        conversation_history=history
    )
    print_result(second)
