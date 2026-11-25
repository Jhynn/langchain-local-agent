from collections.abc import Callable
from typing import Any
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.genai import types
from langchain_core.tools import StructuredTool
from app.core.config import settings
from app.core.logger import logger
from app.tools.db_tools import (
    execute_readonly_sql,
    get_department_spending_summary,
    get_expenses_by_status,
)
from app.tools.system_tools import get_current_datetime, get_system_platform
from app.tools.text_tools import count_characters, count_words

APP_NAME: str = "corporate_expense_adk"
DEFAULT_USER_ID: str = "local_user"


class AdkAssistantAgent:
    def __init__(self) -> None:
        # Extract underlying typed Python callables from LangChain StructuredTool wrappers
        wrapped_tools: list[StructuredTool] = [
            get_current_datetime,
            get_system_platform,
            count_characters,
            count_words,
            get_expenses_by_status,
            get_department_spending_summary,
            execute_readonly_sql,
        ]
        plain_tools: list[Callable[..., Any]] = [
            tool_obj.func for tool_obj in wrapped_tools if tool_obj.func is not None
        ]

        # LiteLlm bridges Google ADK to local Ollama using the /api/chat endpoint
        llm_model: LiteLlm = LiteLlm(
            model=f"ollama_chat/{settings.LLM_MODEL}",
            api_base=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
        )

        self.agent: Agent = Agent(
            name="corporate_financial_assistant",
            model=llm_model,
            description="Assistant that queries corporate expenses in MariaDB and system metrics.",
            instruction=(
                "You are a precise technical and financial data assistant. "
                "Use the provided database and system tools whenever factual data or calculations are needed. "
                "Never fabricate database records; always query the database tools first. "
                "Use conversation history to resolve follow-up questions accurately."
            ),
            tools=plain_tools,
        )

        self.session_service: InMemorySessionService = InMemorySessionService()
        self.runner: Runner = Runner(
            agent=self.agent,
            app_name=APP_NAME,
            session_service=self.session_service,
        )
        logger.info(
            f"Google ADK Agent initialized with LiteLlm ('ollama_chat/{settings.LLM_MODEL}')."
        )

    async def _ensure_session(self, session_id: str, user_id: str = DEFAULT_USER_ID) -> Session:
        session: Session | None = await self.session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        if session is None:
            session = await self.session_service.create_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )
        return session

    async def run(self, user_input: str, session_id: str) -> tuple[str, list[str]]:
        await self._ensure_session(session_id=session_id)

        user_message: types.Content = types.Content(
            role="user",
            parts=[types.Part(text=user_input)],
        )

        tools_used: list[str] = []
        final_reply: str = ""

        async for event in self.runner.run_async(
            user_id=DEFAULT_USER_ID,
            session_id=session_id,
            new_message=user_message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call and part.function_call.name:
                        tools_used.append(part.function_call.name)

            if event.is_final_response() and event.content and event.content.parts:
                text_parts: list[str] = [
                    part.text for part in event.content.parts if part.text
                ]
                final_reply = "\n".join(text_parts)

        return final_reply, tools_used

    async def get_history(self, session_id: str) -> list[dict[str, str]]:
        session: Session | None = await self.session_service.get_session(
            app_name=APP_NAME,
            user_id=DEFAULT_USER_ID,
            session_id=session_id,
        )
        if session is None:
            return []

        history: list[dict[str, str]] = []
        for event in session.events:
            if not event.content or not event.content.parts:
                continue
            text_parts: list[str] = [part.text for part in event.content.parts if part.text]
            if not text_parts:
                continue
            role: str = "user" if event.author == "user" else "assistant"
            history.append({"role": role, "content": "\n".join(text_parts)})

        return history


adk_assistant_agent: AdkAssistantAgent = AdkAssistantAgent()
