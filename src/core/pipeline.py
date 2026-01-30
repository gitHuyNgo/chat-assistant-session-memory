import json
from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.config import settings
from src.constants import QUERY_PIPELINE_PROMPT
from src.schemas.chat import QueryAnalysis
from src.schemas.memory import SessionSummary


class QueryPipeline:
    """Flow 2: Query understanding and instant memory extraction.

    Analyzes the user's raw query to detect ambiguity and extract explicit
    real-time facts and preferences.
    """

    def __init__(self, model_name: str = settings.MODEL_NAME) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model_name = model_name

    def analyze_query(
        self,
        current_query: str,
        recent_messages: List[Dict[str, Any]],
        session_memory: Optional[SessionSummary],
    ) -> QueryAnalysis:
        """Analyze the user query using the LLM.

        Args:
            current_query: The raw user input.
            recent_messages: The short-term context window (e.g., last N messages).
            session_memory: The long-term consolidated memory (user profile + facts).

        Returns:
            QueryAnalysis: Structured output indicating ambiguity and extracted signals.

        Raises:
            Exception: Re-raises any exception to preserve existing error behavior.
        """
        memory_context_str = "None"
        if session_memory:
            memory_dict = session_memory.model_dump()

            relevant_memory = {
                "user_profile": memory_dict.get("user_profile"),
                "recent_session_summaries": memory_dict.get("session_summaries", [])[-10:]
            }

            memory_context_str = json.dumps(relevant_memory, ensure_ascii=False)


        user_input = (
            "=== SESSION MEMORY (What we know) ===\n"
            f"{memory_context_str}\n\n"
            "=== RECENT CONVERSATION HISTORY ===\n"
            f"{json.dumps(recent_messages, ensure_ascii=False)}\n\n"
            "=== CURRENT USER QUERY ===\n"
            f"'{current_query}'"
        )

        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": QUERY_PIPELINE_PROMPT},
                    {"role": "user", "content": user_input},
                ],
                response_format=QueryAnalysis,
                temperature=0,
            )
            return completion.choices[0].message.parsed

        except Exception as exc:
            # REVIEW NOTE (not changed): Uses print instead of logging to preserve
            # current runtime behavior and output destination.
            print(f"Error in QueryPipeline: {exc}")
            raise exc