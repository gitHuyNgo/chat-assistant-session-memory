from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.config import settings
from src.schemas.memory import SessionSummary


class ChatGenerator:
    """Flow 3: Response generation.

    Constructs the final system prompt by injecting long-term memory (when
    available) and generates the response via the configured LLM.
    """

    def __init__(self, model_name: str = settings.MODEL_NAME) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model_name = model_name

    def _build_system_prompt(self, session_memory: Optional[SessionSummary]) -> str:
        """Build a system prompt that optionally includes long-term memory.

        Memory is injected selectively to reduce token usage while preserving the
        most actionable personalization signals (constraints, preferences, and
        stable facts).
        """
        base_prompt = (
            "You are a helpful and intelligent AI Assistant.\n"
            "Answer the user's questions clearly and accurately.\n"
        )

        if not session_memory:
            return base_prompt

        # Inject memory into the system prompt (context injection).
        # Only include high-signal fields to keep the prompt compact.
        context_blocks: List[str] = []

        # 1) User profile (who they are)
        if session_memory.user_profile:
            profile_text = "\n=== USER PROFILE (Remember this) ===\n"

            if session_memory.user_profile.constraints:
                profile_text += "CONSTRAINTS (Must Follow):\n"
                for constraint in session_memory.user_profile.constraints:
                    profile_text += f"- {constraint}\n"

            if session_memory.user_profile.prefs:
                profile_text += "PREFERENCES:\n"
                for preference in session_memory.user_profile.prefs:
                    profile_text += f"- {preference}\n"

            context_blocks.append(profile_text)

        # 2) Key facts (what we know)
        if session_memory.key_facts:
            facts_text = "\n=== KEY FACTS ===\n" + "\n".join(
                [f"- {fact}" for fact in session_memory.key_facts]
            )
            context_blocks.append(facts_text)

        # Combine prompt sections.
        return base_prompt + "\n".join(context_blocks)

    def generate_response(
        self,
        user_query: str,
        context_messages: List[Dict[str, Any]],
        session_memory: Optional[SessionSummary] = None,
    ) -> str:
        """Generate the final assistant response.

        Args:
            user_query: The user query (potentially rewritten upstream).
            context_messages: Recent short-term conversation history.
            session_memory: Consolidated long-term memory for personalization.
        """
        # 1) Build the personalized system prompt.
        system_prompt = self._build_system_prompt(session_memory)

        # 2) Assemble messages payload.
        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]

        # Add recent context while excluding non-standard fields (e.g., debug_info).
        for msg in context_messages:
            clean_msg = {k: v for k, v in msg.items() if k in ["role", "content", "name"]}
            messages.append(clean_msg)

        # Add the current query.
        messages.append({"role": "user", "content": user_query})

        # 3) Call the LLM.
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.7,  # Higher temperature for more natural creativity.
        )

        return response.choices[0].message.content