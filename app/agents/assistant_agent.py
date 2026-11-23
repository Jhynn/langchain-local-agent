from typing import Any
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama

from langgraph.prebuilt import create_react_agent
from langgraph.graph.state import CompiledStateGraph
from app.core.config import settings
from app.core.logger import logger

from app.tools.db_tools import (
    execute_readonly_sql,
    get_department_spending_summary,
    get_expenses_by_status,
)
from app.tools.system_tools import get_current_datetime, get_system_platform
from app.tools.text_tools import count_characters, count_words


class AssistantAgent:
    def __init__(self) -> None:
        self.tools: list[BaseTool] = [
            get_current_datetime,
            get_system_platform,
            count_characters,
            count_words,
            get_expenses_by_status,
            get_department_spending_summary,
            execute_readonly_sql,
        ]

        self.llm: ChatOllama = ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
        )

        self.system_prompt: str = (
            "You are a precise technical and financial data assistant. "
            "Use the provided database and system tools whenever factual data or calculations are needed. "
            "Never fabricate database records; always query the database tools first."
        )

        self.graph: CompiledStateGraph = create_react_agent(
            model=self.llm,
            tools=self.tools,
        )
        logger.info(f"LangGraph ReAct agent initialized with model '{settings.LLM_MODEL}'.")

    def run(self, user_input: str) -> str:
        messages: list[BaseMessage] = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_input),
        ]
        result: dict[str, Any] = self.graph.invoke({"messages": messages})
        final_message: BaseMessage = result["messages"][-1]

        return str(final_message.content)
