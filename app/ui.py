import json
import os
import sys
import time
from typing import Optional

import streamlit as st

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

# --- IMPORTS ---
from src.config import settings
from src.core.llm import ChatGenerator
from src.core.memory import MemoryManager
from src.core.pipeline import QueryPipeline
from src.schemas.memory import MessageRange, SessionSummary, UserProfile
from src.utils.storage import load_json, save_json
from src.utils.tokenizer import count_messages_tokens

# --- CONFIG PAGE ---
st.set_page_config(
    page_title="Chat Assistant with Session Memory",
    page_icon="🧠",
    layout="wide",
)
st.markdown("<style>.stDeployButton{display:none;}</style>", unsafe_allow_html=True)

# --- INITIALIZE STATE ---
MEMORY_PATH = os.path.join(root_dir, "data", "session_memory.json")

DATA_DIR = os.path.join(root_dir, "data")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 1) Init messages
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2) Init session summary (load from disk if exists)
if "session_summary" not in st.session_state:
    data = load_json(MEMORY_PATH)
    if data:
        try:
            st.session_state.session_summary = SessionSummary(**data)
            print(f"Loaded memory from {MEMORY_PATH}")
        except Exception as exc:
            print(f"Error loading memory: {exc}")
            st.session_state.session_summary = None
    else:
        st.session_state.session_summary = None

# 3) Init last summary index
if "last_summary_index" not in st.session_state:
    st.session_state.last_summary_index = 0

# 4) Init helper states
if "pending_options" not in st.session_state:
    st.session_state.pending_options = []
if "test_prompt" not in st.session_state:
    st.session_state.test_prompt = None

# Lazy-load core modules
if "memory_manager" not in st.session_state:
    st.session_state.memory_manager = MemoryManager()
if "query_pipeline" not in st.session_state:
    st.session_state.query_pipeline = QueryPipeline()
if "chat_generator" not in st.session_state:
    st.session_state.chat_generator = ChatGenerator()


# --- HELPER: LOAD TEST DATA ---
def load_test_scenario(filename: str) -> None:
    """Load a JSON log and initialize Streamlit session state for testing."""
    file_path = os.path.join(root_dir, "tests", "data", filename)

    try:
        with open(file_path, "r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        # Reset state
        st.session_state.messages = []
        st.session_state.session_summary = None
        st.session_state.last_summary_index = 0
        st.session_state.pending_options = []

        # Test scenario routing
        if filename == "long_session.json":
            # [Test Memory] Load the full history to trigger summarization.
            st.session_state.messages = data
            st.session_state.test_prompt = None
            st.toast(f"Loaded {len(data)} messages. Checking memory...", icon="💾")
        else:
            # [Test Context/Ambiguity]
            if data and data[-1]["role"] == "user":
                # 1) Split history and active prompt
                history = data[:-1]
                active_prompt = data[-1]["content"]

                st.session_state.messages = history
                st.session_state.test_prompt = active_prompt

                # 2) Memory hydration from history (context.json only)
                if filename == "context.json":
                    with st.spinner("🧠 Hydrating memory from history..."):
                        for msg in history:
                            if msg["role"] == "user":
                                analysis = st.session_state.query_pipeline.analyze_query(
                                    msg["content"],
                                    [],
                                    st.session_state.session_summary,
                                )
                                if analysis.new_user_facts or analysis.new_user_preferences:
                                    if not st.session_state.session_summary:
                                        st.session_state.session_summary = SessionSummary(
                                            user_profile=UserProfile(),
                                            key_facts=[],
                                            decisions=[],
                                            open_questions=[],
                                            todos=[],
                                            message_range_summarized=MessageRange(
                                                start_index=0,
                                                end_index=0,
                                            ),
                                        )
                                    mem = st.session_state.session_summary
                                    mem.key_facts.extend(analysis.new_user_facts)
                                    mem.user_profile.constraints.extend(
                                        analysis.new_user_preferences
                                    )
            else:
                st.session_state.messages = data

            st.toast(f"Scenario '{filename}' loaded!", icon="🧪")

    except Exception as exc:
        st.error(f"Failed to load {filename}: {exc}")


# --- SIDEBAR ---
with st.sidebar:
    st.header("🧠 System Internals")

    # 1) Memory control
    threshold = st.slider(
        "Memory Threshold (Tokens)",
        100,
        2000,
        settings.MEMORY_THRESHOLD_TOKENS,
    )
    st.session_state.memory_manager.threshold = threshold

    # 2) Token usage
    active_msgs = st.session_state.messages[st.session_state.last_summary_index :]
    curr_tokens = count_messages_tokens(active_msgs)
    pct = min(curr_tokens / threshold, 1.0) if threshold > 0 else 1.0
    st.caption(f"Buffer Usage: {curr_tokens}/{threshold} tokens")
    st.progress(pct)

    st.divider()

    # 3) Test scenarios
    st.header("🧪 Test Scenarios")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Ambiguity", help="Load 'I want to open a bank'"):
            load_test_scenario("ambiguous.json")
            st.rerun()
    with c2:
        if st.button("Context", help="Load Python vs Java history"):
            load_test_scenario("context.json")
            st.rerun()
    with c3:
        if st.button("Memory", help="Load long conversation"):
            load_test_scenario("long_session.json")
            st.rerun()

    st.divider()

    # 4) View memory
    st.subheader("📚 Consolidated Memory")
    if st.session_state.session_summary:
        with st.expander("👤 User Profile", expanded=True):
            st.write("**Prefs:**", st.session_state.session_summary.user_profile.prefs)
            st.write(
                "**Constraints:**",
                st.session_state.session_summary.user_profile.constraints,
            )

        with st.expander("🔑 Key Facts", expanded=True):
            for fact in st.session_state.session_summary.key_facts:
                st.markdown(f"- {fact}")

        with st.expander("JSON Raw"):
            st.json(st.session_state.session_summary.model_dump())
    else:
        st.info("Memory is empty.")

    if st.button("🗑️ Reset Brain"):
        st.session_state.clear()

        # Remove persisted memory file if present.
        if os.path.exists(MEMORY_PATH):
            os.remove(MEMORY_PATH)

        st.rerun()


# --- MAIN UI ---
st.title("🤖 Chat Assistant")

# 1) Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "debug_info" in msg:
            with st.expander("🔍 Thought Process"):
                st.json(msg["debug_info"])

# 2) Input handling
prompt: Optional[str] = None
options_placeholder = st.empty()
pill_selection: Optional[str] = None

if st.session_state.test_prompt:
    prompt = st.session_state.test_prompt
    st.session_state.test_prompt = None
elif st.session_state.pending_options:
    with options_placeholder:
        pill_selection = st.pills(
            "💡 Did you mean:",
            st.session_state.pending_options,
            selection_mode="single",
            key="pills",
        )

chat_input_val = st.chat_input("Type your message...")

if pill_selection:
    prompt = pill_selection
    st.session_state.pending_options = []
    options_placeholder.empty()
elif chat_input_val:
    prompt = chat_input_val
    st.session_state.pending_options = []
    options_placeholder.empty()

# --- CORE LOGIC ---
if prompt:
    # A) Display user message
    st.chat_message("user").markdown(prompt)

    # B) [Flow 2] Query pipeline
    with st.status("🧠 Thinking...", expanded=True) as status:
        analysis = st.session_state.query_pipeline.analyze_query(
            prompt,
            st.session_state.messages[-5:],
            st.session_state.session_summary,
        )

        # C) Update memory (fast path)
        if analysis.new_user_facts or analysis.new_user_preferences:
            if not st.session_state.session_summary:
                st.session_state.session_summary = SessionSummary(
                    user_profile=UserProfile(),
                    key_facts=[],
                    decisions=[],
                    open_questions=[],
                    todos=[],
                    message_range_summarized=MessageRange(start_index=0, end_index=0),
                )
            mem = st.session_state.session_summary
            mem.key_facts.extend(analysis.new_user_facts)
            mem.user_profile.constraints.extend(analysis.new_user_preferences)

        # D) Handle ambiguity
        if analysis.is_ambiguous:
            reason_label = (
                analysis.ambiguity_reason.name
                if hasattr(analysis.ambiguity_reason, "name")
                else analysis.ambiguity_reason
            )
            status.update(label=f"Ambiguity: {reason_label}", state="error")

            if analysis.clarification_options:
                st.session_state.pending_options = analysis.clarification_options
                st.session_state.messages.append(
                    {
                        "role": "user",
                        "content": prompt,
                        "debug_info": analysis.model_dump(),
                    }
                )
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": analysis.clarifying_question or "Please clarify.",
                    }
                )
                st.rerun()
            else:
                st.warning(f"Rewritten: {analysis.rewritten_query}")
        else:
            status.update(label="Query Clear", state="complete", expanded=False)

    # E) [Flow 3] Generate (only if not blocked by clarifying options)
    if not (analysis.is_ambiguous and analysis.clarification_options):
        # Persist the user query in history.
        st.session_state.messages.append(
            {"role": "user", "content": prompt, "debug_info": analysis.model_dump()}
        )

        final_query = (
            analysis.rewritten_query
            if (analysis.is_ambiguous and analysis.rewritten_query)
            else prompt
        )

        with st.chat_message("assistant"):
            # 1) Placeholder to support incremental rendering.
            message_placeholder = st.empty()

            # 2) Spinner while waiting for the backend call.
            with st.spinner("Thinking..."):
                full_response = st.session_state.chat_generator.generate_response(
                    final_query,
                    st.session_state.messages[-5:],
                    st.session_state.session_summary,
                )

            # 3) Typing effect
            displayed_text = ""
            chunks = full_response.split(" ")

            for i, chunk in enumerate(chunks):
                displayed_text += f"{chunk} "

                if i < len(chunks) - 1:
                    message_placeholder.markdown(displayed_text + "|")
                else:
                    message_placeholder.markdown(displayed_text)

                time.sleep(0.02)

            # Ensure the final message is rendered without the cursor.
            message_placeholder.markdown(full_response)

        # Persist assistant response.
        st.session_state.messages.append({"role": "assistant", "content": full_response})

        st.rerun()

# F) [Flow 1] Memory consolidation (run after appending new messages)
active_buffer = st.session_state.messages[st.session_state.last_summary_index :]
if st.session_state.memory_manager.should_summarize(active_buffer):
    with st.sidebar:
        with st.spinner("💾 Consolidating Memory..."):
            new_summary = st.session_state.memory_manager.summarize_messages(
                active_buffer,
                st.session_state.session_summary,
            )
            st.session_state.session_summary = new_summary
            st.session_state.last_summary_index = len(st.session_state.messages)

            # Persist to disk.
            save_json(new_summary.model_dump(), MEMORY_PATH)

            st.toast("Memory Consolidated & Saved!", icon="💾")

            # Rerun to refresh the UI (e.g., sidebar state).
            st.rerun()