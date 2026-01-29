from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AmbiguityType(str, Enum):
    """Enumerates ambiguity categories that may occur in a user query.

    This taxonomy is intended to align with common research categorizations
    (e.g., CLAMBER, 2024) while staying stable for downstream consumers.
    """

    NONE = "none"
    AMBIGUOUS_REFERENCE = "ambiguous_reference"  # Example: "it", "they"
    AMBIGUOUS_TOPIC = "ambiguous_topic"  # Example: "bank" (river vs. finance)
    INCOMPLETE_CONTEXT = "incomplete_context"  # Example: "How about next week?"


class QueryAnalysis(BaseModel):
    """Structured output for the Query Understanding Pipeline (Flow 2).

    This schema is designed to force analysis prior to answer generation, enabling
    deterministic downstream handling for ambiguity and memory extraction.
    """

    # --- Ambiguity detection ---
    is_ambiguous: bool = Field(
        ...,
        description="True if the user's query is unclear or lacks required context.",
    )
    ambiguity_reason: AmbiguityType = Field(
        default=AmbiguityType.NONE,
        description="The specific ambiguity category detected.",
    )
    rewritten_query: Optional[str] = Field(
        default=None,
        description=(
            "A self-contained, disambiguated query when it can be resolved using "
            "available memory/context."
        ),
    )

    # --- Advanced ambiguity handling (multiple choice) ---
    clarifying_question: Optional[str] = Field(
        default=None,
        description=(
            "A question to ask the user when the ambiguity cannot be resolved "
            "automatically."
        ),
    )
    clarification_options: List[str] = Field(
        default_factory=list,
        description=(
            "Possible interpretations for the user to select from "
            "(e.g., ['Financial bank', 'River bank'])."
        ),
    )

    # --- Instant memory extraction (fast path) ---
    new_user_facts: List[str] = Field(
        default_factory=list,
        description=(
            "Explicit facts about the user stated in this query "
            "(e.g., 'My name is Huy')."
        ),
    )
    new_user_preferences: List[str] = Field(
        default_factory=list,
        description=(
            "Explicit preferences or constraints stated in this query "
            "(e.g., 'I hate Java')."
        ),
    )