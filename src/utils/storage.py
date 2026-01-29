import json
import logging
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


def save_json(data: Any, file_path: Union[str, Path]) -> None:
    """Persist data to a JSON file in a safe and deterministic manner.

    This function ensures that parent directories are created if they do not
    already exist and writes JSON using UTF-8 encoding to preserve non-ASCII
    characters (e.g., Vietnamese text).

    Args:
        data: Arbitrary JSON-serializable data to persist.
        file_path: Target file path as a string or Path object.

    Raises:
        Exception: Re-raises any exception encountered during file I/O or
            serialization to preserve existing error-handling behavior.
    """
    try:
        path = Path(file_path)

        # Ensure parent directories exist (e.g., "data/").
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as file_handle:
            # ensure_ascii=False preserves readable non-ASCII characters.
            json.dump(data, file_handle, indent=2, ensure_ascii=False)

        logger.info("Successfully saved data to %s", path)

    except Exception as exc:
        logger.error("Failed to save JSON to %s: %s", file_path, exc)
        # REVIEW NOTE (not changed): Explicit re-raise preserves original behavior.
        raise exc


def load_json(file_path: Union[str, Path]) -> Optional[Any]:
    """Load and deserialize data from a JSON file.

    If the target file does not exist, this function returns None instead of
    raising an exception, allowing callers to handle missing files gracefully.

    Args:
        file_path: Source file path as a string or Path object.

    Returns:
        The deserialized JSON content if successful, or None if the file does
        not exist or contains invalid JSON.

    Raises:
        Exception: Re-raises unexpected I/O errors to preserve existing behavior.
    """
    path = Path(file_path)

    if not path.exists():
        logger.warning("File not found: %s. Returning None.", path)
        return None

    try:
        with open(path, "r", encoding="utf-8") as file_handle:
            return json.load(file_handle)

    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON format in %s: %s", path, exc)
        return None

    except Exception as exc:
        logger.error("Failed to load JSON from %s: %s", path, exc)
        # REVIEW NOTE (not changed): Explicit re-raise preserves original behavior.
        raise exc