from typing import Any
from collections.abc import Callable
from langchain_core.tools import StructuredTool

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.genai import types

from app.core.config import settings
from app.core.logger import logger
from app.tools.db_tools import (
    execute_readonly_sql,
    get_department_spending_summary,
    get_expenses_by_status,
)

from app.tools.system_tools import get_current_datetime, get_system_platform
from app.tools.text_tools import count_characters, count_words

APP_NAME: str = "corporate_multiagent_adk"
DEFAULT_USER_ID: str = "local_user"
COORDINATOR_NAME: str = "corporate_coordinator"


def _extract_plain_tools(wrapped_tools: list[StructuredTool]) -> list[Callable[..., Any]]:
    return [tool_obj.func for tool_obj in wrapped_tools if tool_obj.func is not None]


class AdkAssistantAgent:
    def __init__(self) -> None:
        llm_model: LiteLlm = LiteLlm(
            model=f"ollama_chat/{settings.LLM_MODEL}",
            api_base=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
        )

        # 1. Financial & Database Specialist Sub-Agent
        financial_tools: list[Callable[..., Any]] = _extract_plain_tools([
            get_expenses_by_status,
            get_department_spending_summary,
            execute_readonly_sql,
        ]) # type: ignore

        self.financial_agent: Agent = Agent(
            name="financial_analyst",
            model=llm_model,
            description=(
                "Specialist in querying corporate expenses, approval statuses, "
                "department spending summaries, and read-only SQL queries on MariaDB."
            ),
            instruction=(
                "You are a financial data analyst with direct read-only access to the MariaDB expenses database. "
                "Always query your database tools to retrieve factual numbers before answering. "
                "Never fabricate records. Provide clear, concise financial answers."
            ),
            tools=financial_tools, # type: ignore
        )

        # 2. System Diagnostics & Text Metrics Specialist Sub-Agent
        system_tools: list[Callable[..., Any]] = _extract_plain_tools([
            get_current_datetime,
            get_system_platform,
            count_characters,
            count_words,
        ]) # type: ignore
        self.system_agent: Agent = Agent(
            name="system_utility",
            model=llm_model,
            description=(
                "Specialist in host operating system diagnostics, current system date and time, "
                "and exact character or word count calculations on text."
            ),
            instruction=(
                "You are a technical system utility specialist. "
                "Use your tools to inspect the host OS, current date/time, or compute exact text lengths. "
                "Never guess values that can be measured with your tools."
            ),
            tools=system_tools, # type: ignore
        )

        # 3. Root Coordinator Agent (Pure Router)
        self.coordinator_agent: Agent = Agent(
            name=COORDINATOR_NAME,
            model=llm_model,
            description="Root coordinator that routes user requests to the appropriate specialist sub-agent.",
            instruction=(
                "You are the central coordinator of a multi-agent system. "
                "You do not have direct tools; instead, delegate tasks using transfer_to_agent:\n"
                "- Transfer to 'financial_analyst' for any question involving corporate expenses, "
                "departments, budgets, approval statuses, or SQL database records.\n"
                "- Transfer to 'system_utility' for questions involving current date/time, "
                "operating system details, or counting characters/words in text.\n"
                "For general greetings or follow-up clarifications already present in conversation history, "
                "answer directly and concisely."
            ),
            sub_agents=[self.financial_agent, self.system_agent],
        )

        self.session_service: InMemorySessionService = InMemorySessionService()
        self.runner: Runner = Runner(
            agent=self.coordinator_agent,
            app_name=APP_NAME,
            session_service=self.session_service,
        )
        logger.info(
            f"Google ADK Multi-Agent hierarchy initialized ('{COORDINATOR_NAME}' -> "
            f"['{self.financial_agent.name}', '{self.system_agent.name}'])."
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

    async def run(self, user_input: str, session_id: str) -> tuple[str, list[str], list[str]]:
        await self._ensure_session(session_id=session_id)

        user_message: types.Content = types.Content(
            role="user",
            parts=[types.Part(text=user_input)],
        )

        tools_used: list[str] = []
        delegated_agents: list[str] = []
        final_reply: str = ""

        async for event in self.runner.run_async(
            user_id=DEFAULT_USER_ID,
            session_id=session_id,
            new_message=user_message,
        ):
            if event.author and event.author not in {"user", COORDINATOR_NAME}:
                if event.author not in delegated_agents:
                    delegated_agents.append(event.author)
                    logger.info(f"ADK delegation active: sub-agent '{event.author}'")

            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call and part.function_call.name:
                        fn_name: str = part.function_call.name
                        if fn_name != "transfer_to_agent":
                            tools_used.append(fn_name)

            if event.is_final_response() and event.content and event.content.parts:
                text_parts: list[str] = [
                    part.text for part in event.content.parts if part.text
                ]
                final_reply = "\n".join(text_parts)

        return final_reply, tools_used, delegated_agents

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
