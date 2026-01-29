import json
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

from src.config import settings
from src.constants import MEMORY_MANAGER_PROMPT
from src.schemas.memory import MessageRange, SessionSummary, SessionSummaryContent
from src.utils.tokenizer import count_messages_tokens

logger = logging.getLogger(__name__)


class MemoryManager:
    """Flow 1: Memory consolidation.

    Manages a sliding context window and compresses older messages into a
    structured summary when the token threshold is exceeded.
    """

    def __init__(
        self,
        model_name: str = settings.MODEL_NAME,
        threshold: int = settings.MEMORY_THRESHOLD_TOKENS,
    ) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model_name = model_name
        self.threshold = threshold
        self.system_prompt = MEMORY_MANAGER_PROMPT

    def should_summarize(self, messages: List[Dict[str, Any]]) -> bool:
        """Return True when the message buffer exceeds the configured token threshold."""
        total_tokens = count_messages_tokens(messages, model_name=self.model_name)

        # Log for debugging visibility.
        logger.info("Buffer Status: %s/%s tokens", total_tokens, self.threshold)

        return total_tokens > self.threshold

    def summarize_messages(
        self,
        messages: List[Dict],
        previous_summary: Optional[SessionSummary] = None,
    ) -> SessionSummary:
        """Merge prior summary content with recent messages into a new summary."""
        # 1) Prepare context.
        current_profile_context = "None"
        if previous_summary:
            # Provide only content fields to the model; metadata is computed in Python.
            current_profile_context = previous_summary.user_profile.model_dump_json()

        # 2) Build prompt.
        user_content = (
            "=== CURRENT USER PROFILE (Raw/Accumulated) ===\n"
            f"{current_profile_context}\n\n"
            "=== RECENT MESSAGES TO CONSOLIDATE ===\n"
            f"{json.dumps(messages, ensure_ascii=False)}\n\n"
            "TASK: Consolidate profile and summarize session."
        )

        # 3) Call the model.
        completion = self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_content},
            ],
            # Use the content-only schema to prevent hallucination of message indices.
            response_format=SessionSummaryContent,
            temperature=0,
        )

        ai_content = completion.choices[0].message.parsed

        # 4) Calculate metadata (application responsibility).
        # Calculate exactly which messages were summarized.
        start_index = (
            previous_summary.message_range_summarized.end_index if previous_summary else 0
        )
        end_index = start_index + len(messages)

        # 5) Merge AI content + Python metadata into the final object.
        return SessionSummary(
            **ai_content.model_dump(),
            message_range_summarized=MessageRange(
                start_index=start_index,
                end_index=end_index,
            ),
        )