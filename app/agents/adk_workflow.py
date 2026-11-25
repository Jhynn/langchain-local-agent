from collections.abc import Callable
from typing import Any

from google.adk.agents import Agent, ParallelAgent, SequentialAgent
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


AUDIT_APP_NAME: str = "corporate_audit_workflow_adk"
DEFAULT_USER_ID: str = "audit_operator"


def _extract_plain_tools(wrapped_tools: list[StructuredTool]) -> list[Callable[..., Any]]:
    return [tool_obj.func for tool_obj in wrapped_tools if tool_obj.func is not None]


class AdkAuditWorkflow:
    def __init__(self) -> None:
        llm_model: LiteLlm = LiteLlm(
            model=f"ollama_chat/{settings.LLM_MODEL}",
            api_base=settings.OLLAMA_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
        )

        # Branch 1: Financial database collector (writes to session.state["financial_findings"])
        financial_tools: list[Callable[..., Any]] = _extract_plain_tools([
            get_expenses_by_status,
            get_department_spending_summary,
            execute_readonly_sql,
        ]) # type: ignore

        self.financial_collector: Agent = Agent(
            name="financial_collector",
            model=llm_model,
            description="Queries MariaDB for corporate expense metrics and approval statuses.",
            instruction=(
                "You are a financial data extraction agent. Query the MariaDB expenses database "
                "using your tools to gather department spending totals and expense records matching "
                "the user's audit scope. Return a concise, factual summary with exact numbers."
            ),
            tools=financial_tools, # type: ignore
            output_key="financial_findings",
        )

        # Branch 2: Host diagnostics collector (writes to session.state["system_diagnostics"])
        system_tools: list[Callable[..., Any]] = _extract_plain_tools([
            get_current_datetime,
            get_system_platform,
        ]) # type: ignore
        self.system_collector: Agent = Agent(
            name="system_collector",
            model=llm_model,
            description="Collects current system timestamp and host platform metadata.",
            instruction=(
                "You are a system telemetry collector. Call your tools to retrieve the exact "
                "current system date/time and host OS/architecture details. Return only verified facts."
            ),
            tools=system_tools, # type: ignore
            output_key="system_diagnostics",
        )

        # Stage 1: Execute both data collection branches concurrently
        self.parallel_gathering: ParallelAgent = ParallelAgent(
            name="parallel_data_gathering",
            description="Runs financial and system data collection concurrently.",
            sub_agents=[self.financial_collector, self.system_collector],
        )

        # Stage 2: Pure synthesis agent reading state keys populated by Stage 1
        self.report_synthesizer: Agent = Agent(
            name="report_synthesizer",
            model=llm_model,
            description="Consolidates parallel findings from session state into a structured audit report.",
            instruction=(
                "You are a senior corporate audit reporter. Write a clear, structured audit report "
                "based strictly on the verified findings below. Do not invent any additional figures.\n\n"
                "### Verified Financial Data (MariaDB)\n"
                "{financial_findings}\n\n"
                "### Execution Environment Metadata\n"
                "{system_diagnostics}\n\n"
                "Structure the report into three sections: "
                "1) Executive Summary, 2) Financial Breakdown, and 3) Audit Metadata."
            ),
        )

        # Root deterministic pipeline: Parallel Gathering -> Sequential Synthesis
        self.pipeline: SequentialAgent = SequentialAgent(
            name="corporate_audit_pipeline",
            description="Deterministic two-stage corporate audit workflow.",
            sub_agents=[self.parallel_gathering, self.report_synthesizer],
        )

        self.session_service: InMemorySessionService = InMemorySessionService()
        self.runner: Runner = Runner(
            agent=self.pipeline,
            app_name=AUDIT_APP_NAME,
            session_service=self.session_service,
        )
        logger.info("Google ADK deterministic audit workflow initialized (Parallel -> Sequential).")

    async def run(
        self,
        scope: str,
        session_id: str,
    ) -> tuple[str, list[str], list[str]]:
        # Create a fresh session per audit run to guarantee clean state keys
        existing: Session | None = await self.session_service.get_session(
            app_name=AUDIT_APP_NAME,
            user_id=DEFAULT_USER_ID,
            session_id=session_id,
        )

        if existing is not None:
            await self.session_service.delete_session(
                app_name=AUDIT_APP_NAME,
                user_id=DEFAULT_USER_ID,
                session_id=session_id,
            )

        await self.session_service.create_session(
            app_name=AUDIT_APP_NAME,
            user_id=DEFAULT_USER_ID,
            session_id=session_id,
        )

        user_message: types.Content = types.Content(
            role="user",
            parts=[types.Part(text=scope)],
        )

        executed_agents: list[str] = []
        tools_used: list[str] = []
        final_report: str = ""

        async for event in self.runner.run_async(
            user_id=DEFAULT_USER_ID,
            session_id=session_id,
            new_message=user_message,
        ):
            if event.author and event.author != "user":
                if event.author not in executed_agents:
                    executed_agents.append(event.author)
                    logger.info(f"ADK workflow stage active: '{event.author}'")

            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call and part.function_call.name:
                        tools_used.append(part.function_call.name)

            if (
                event.author == self.report_synthesizer.name
                and event.is_final_response()
                and event.content
                and event.content.parts
            ):
                text_parts: list[str] = [
                    part.text for part in event.content.parts if part.text
                ]
                final_report = "\n".join(text_parts)

        return final_report, executed_agents, tools_used


adk_audit_workflow: AdkAuditWorkflow = AdkAuditWorkflow()
