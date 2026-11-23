from langchain_core.tools import tool
from app.core.logger import logger


@tool
def count_characters(text: str) -> int:
    """Counts and returns the exact number of characters in a given string."""
    logger.info(f"Executing tool: count_characters on text of length {len(text)}")

    return len(text)


@tool
def count_words(text: str) -> int:
    """Counts and returns the exact number of words in a given string."""
    logger.info("Executing tool: count_words")

    return len(text.split())
