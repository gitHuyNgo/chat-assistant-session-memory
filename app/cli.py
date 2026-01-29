import json
import os
import sys
from typing import Dict, List

import typer

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# --- IMPORTS FROM SRC ---
from src.core.llm import ChatGenerator
from src.core.memory import MemoryManager
from src.core.pipeline import QueryPipeline
from src.schemas.memory import MessageRange, SessionSummary, UserProfile

app = typer.Typer()


def load_log_file(file_path: str) -> List[Dict]:
    """Load a JSON conversation log file.

    Returns an empty list on failure to preserve current CLI behavior.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)
    except Exception as exc:
        # REVIEW NOTE (not changed): Uses print instead of logging to preserve
        # current runtime behavior and output destination.
        print(f"❌ Error loading file: {exc}")
        return []


@app.command()
def test_pipeline(query: str) -> None:
    """Test the Query Pipeline with a simulated query."""
    print(f"Analyzing query: '{query}'...")

    try:
        pipeline = QueryPipeline()

        result = pipeline.analyze_query(
            current_query=query,
            recent_messages=[],
            session_memory=None,
        )

        print("\n--- RESULT ---")
        print(result.model_dump_json(indent=2))

    except Exception as exc:
        print(f"Error: {exc}")


@app.command()
def test_memory() -> None:
    """Test the Memory Manager (Flow 1).

    Simulates a long conversation and forces a summary via a low token threshold.
    """
    print("Testing Memory Manager...")

    # 1) Fake a long conversation.
    dummy_messages = [
        {"role": "user", "content": "My name is Huy."},
        {"role": "assistant", "content": "Hello Huy."},
        {"role": "user", "content": "I am studying Computer Science in Vietnam."},
        {"role": "assistant", "content": "That's great! Focus on AI."},
        {"role": "user", "content": "I hate Java but I love Python."},
    ] * 3  # Duplicate 3 times to ensure it's long enough.

    manager = MemoryManager(threshold=50)  # Low threshold to force summary.

    if manager.should_summarize(dummy_messages):
        print(f"Buffer full! Summarizing {len(dummy_messages)} messages...")

        summary = manager.summarize_messages(dummy_messages)

        print("\n--- SUMMARY RESULT ---")
        print(summary.model_dump_json(indent=2))
    else:
        print("Buffer not full yet.")


@app.command()
def test_generation() -> None:
    """Test Flow 3: generation with memory injection.

    Simulates a user profile where the user dislikes Java and prefers Python.
    """
    print("🤖 Testing Chat Generator with Memory...")

    # 1) Create a fake memory (simulating Flow 1 output).
    fake_memory = SessionSummary(
        user_profile=UserProfile(
            prefs=["Loves Python code"],
            constraints=["Hates Java", "Be concise"],
        ),
        key_facts=[],
        decisions=[],
        open_questions=[],
        todos=[],
        message_range_summarized=MessageRange(start_index=0, end_index=10),
    )

    generator = ChatGenerator()

    # 2) Ask a generic question (memory injection influences the system prompt).
    query = "Write a hello world function."
    print(f"\nUser Query: '{query}'")
    print("(Context: User HATES Java, LOVES Python)\n")

    # 3) Generate.
    response = generator.generate_response(
        user_query=query,
        context_messages=[],  # No recent chat.
        session_memory=fake_memory,
    )

    print("--- AI RESPONSE ---")
    print(response)


@app.command()
def run_log(file_path: str) -> None:
    """[DELIVERABLE] Run a conversation simulation from a JSON log file.

    Demonstrates:
      - Flow 1: Memory trigger + consolidation
      - Flow 2: Ambiguity detection
      - Flow 3: Instant extraction

    Usage:
        python app/cli.py run-log tests/data/ambiguous.json
    """
    print(f"\n📂 Loading simulation from: {file_path}")
    messages = load_log_file(file_path)
    if not messages:
        return

    # Initialize core modules.
    pipeline = QueryPipeline()
    memory_manager = MemoryManager(threshold=200)  # Lower threshold to test triggering.
    generator = ChatGenerator()

    # Simulated state.
    session_memory = None
    processed_messages: List[Dict] = []

    print(f"▶️ Starting simulation with {len(messages)} messages...\n")

    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"]

        print(f"--- [Step {i + 1}] Role: {role.upper()} ---")
        if len(content) > 100:
            print(f"💬 Content: {content[:100]}...")
        else:
            print(f"💬 Content: {content}")

        # Only run analysis/generation for user messages (assistant messages are appended).
        if role == "user":
            # 1) Pipeline analysis (Flow 2).
            print("   🕵️ [Flow 2] Analyzing Query...")
            analysis = pipeline.analyze_query(
                content,
                processed_messages[-5:],
                session_memory,
            )

            if analysis.is_ambiguous:
                reason_str = (
                    analysis.ambiguity_reason.name
                    if hasattr(analysis.ambiguity_reason, "name")
                    else str(analysis.ambiguity_reason)
                )
                print(f"   ⚠️ AMBIGUITY DETECTED! Type: {reason_str}")

                if analysis.clarification_options:
                    print(f"   💡 Options offered: {analysis.clarification_options}")

            if analysis.new_user_facts or analysis.new_user_preferences:
                print(
                    "   🧠 Instant Learning: Facts=%s, Prefs=%s"
                    % (analysis.new_user_facts, analysis.new_user_preferences)
                )

            # 2) Generation (Flow 3) - demo-only.
            # Only generate when the query is not ambiguous.
            if not analysis.is_ambiguous:
                print("   🤖 [Flow 3] Generating Response...")
                # REVIEW NOTE (not changed): Intentionally not printing the model output
                # because the log may already include an assistant response.

        # Append to history.
        processed_messages.append(msg)

        # 3) Memory check (Flow 1).
        if memory_manager.should_summarize(processed_messages):
            print("   💾 [Flow 1] MEMORY TRIGGERED! (Buffer exceeded threshold)")
            print("   ⏳ Consolidating...")
            session_memory = memory_manager.summarize_messages(
                processed_messages,
                session_memory,
            )
            print("   ✅ Consolidation Complete. New Memory State:")
            print(
                session_memory.model_dump_json(
                    indent=2,
                    exclude={"message_range_summarized"},
                )
            )

            # Reset simulated buffer (in production, this would trim the message list).
            processed_messages = []

        print("")

    # REVIEW NOTE (not changed): `generator` is initialized but not used during log
    # replay unless generation is fully enabled. Kept to preserve structure and
    # future demo intent.


if __name__ == "__main__":
    app()