import datetime
import platform
from langchain_core.tools import tool
from app.core.logger import logger


@tool
def get_current_datetime() -> str:
    """Returns the current local system date and time in ISO-like format."""
    logger.info("Executing tool: get_current_datetime")

    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
def get_system_platform() -> str:
    """Returns information about the host operating system and hardware architecture."""
    logger.info("Executing tool: get_system_platform")

    return f"OS: {platform.system()} {platform.release()} | Architecture: {platform.machine()}"
