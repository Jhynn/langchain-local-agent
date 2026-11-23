import sqlite3

from typing import Any
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langchain.agents import create_agent

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
            "Never fabricate database records; always query the database tools first. "
            "Use conversation history to resolve follow-up questions accurately."
        )

        self.conn: sqlite3.Connection = sqlite3.connect(
            settings.CHECKPOINT_DB_PATH,
            check_same_thread=False,
        )
        self.memory: SqliteSaver = SqliteSaver(self.conn)
        self.memory.setup()

        self.graph: CompiledStateGraph = create_agent(
            model=self.llm,
            tools=self.tools,
            checkpointer=self.memory,
        )
        logger.info(
            f"LangGraph ReAct agent initialized with SqliteSaver ('{settings.CHECKPOINT_DB_PATH}') "
            f"and model '{settings.LLM_MODEL}'."
        )

    def run(self, user_input: str, session_id: str) -> tuple[str, list[str]]:
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        current_state = self.graph.get_state(config)
        existing_messages: list[BaseMessage] = current_state.values.get("messages", [])

        input_messages: list[BaseMessage] = []
        if not existing_messages:
            input_messages.append(SystemMessage(content=self.system_prompt))
        input_messages.append(HumanMessage(content=user_input))

        result: dict[str, Any] = self.graph.invoke({"messages": input_messages}, config=config)
        all_messages: list[BaseMessage] = result["messages"]

        last_human_idx: int = max(
            idx for idx, msg in enumerate(all_messages) if isinstance(msg, HumanMessage)
        )
        turn_messages: list[BaseMessage] = all_messages[last_human_idx:]
        tools_used: list[str] = [
            tool_call["name"]
            for msg in turn_messages
            if isinstance(msg, AIMessage) and msg.tool_calls
            for tool_call in msg.tool_calls
        ]

        final_message: BaseMessage = all_messages[-1]

        return str(final_message.content), tools_used

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        config: RunnableConfig = {"configurable": {"thread_id": session_id}}
        current_state = self.graph.get_state(config)
        messages: list[BaseMessage] = current_state.values.get("messages", [])

        history: list[dict[str, str]] = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                history.append({"role": "user", "content": str(msg.content)})
            elif isinstance(msg, AIMessage) and msg.content:
                history.append({"role": "assistant", "content": str(msg.content)})

        return history

    def close(self) -> None:
        self.conn.close()
        logger.info("SQLite checkpointer connection closed.")


assistant_agent: AssistantAgent = AssistantAgent()
