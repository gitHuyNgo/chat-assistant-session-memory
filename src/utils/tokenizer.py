import logging
from typing import Any, Dict, List

import tiktoken

from src.config import settings

logger = logging.getLogger(__name__)

DEFAULT_ENCODING = "cl100k_base"


def get_encoding_for_model(model_name: str) -> tiktoken.Encoding:
    """Return the token encoding associated with a given model name.

    If the model name is not recognized by `tiktoken`, this function falls back
    to the default encoding used by GPT-3.5/GPT-4-class models.
    """
    try:
        return tiktoken.encoding_for_model(model_name)
    except KeyError:
        logger.warning(
            "Model '%s' not found. Falling back to default encoding '%s'.",
            model_name,
            DEFAULT_ENCODING,
        )
        return tiktoken.get_encoding(DEFAULT_ENCODING)


def count_tokens(text: str, model_name: str = settings.MODEL_NAME) -> int:
    """Count the number of tokens in a plain text string.

    This helper is intended for quick checks on individual prompts or summaries.
    """
    if not text:
        return 0

    encoding = get_encoding_for_model(model_name)
    return len(encoding.encode(text))


def count_messages_tokens(
    messages: List[Dict[str, Any]],
    model_name: str = settings.MODEL_NAME,
) -> int:
    """Count the total number of tokens for a list of chat messages.

    This implementation follows OpenAI's ChatML accounting rules, including
    fixed overhead per message and per name field.

    Reference:
    https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
    """
    encoding = get_encoding_for_model(model_name)

    # ChatML overhead:
    # <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_message = 3
    tokens_per_name = 1

    num_tokens = 0

    for message in messages:
        num_tokens += tokens_per_message

        for key, value in message.items():
            # Only count standard OpenAI fields to avoid inflating totals
            # with internal or diagnostic metadata.
            if key in ["content", "name"] and isinstance(value, str):
                num_tokens += len(encoding.encode(value))

                if key == "name":
                    num_tokens += tokens_per_name

            # REVIEW NOTE (not changed): Function-calling fields are intentionally
            # excluded and would require explicit handling if introduced.

    # Every reply is primed with <|start|>assistant<|message|>
    num_tokens += 3

    return num_tokens