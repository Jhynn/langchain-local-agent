from fastapi import APIRouter, Path
from app.agents.adk_agent import adk_assistant_agent
from app.agents.adk_workflow import adk_audit_workflow

from app.schemas.chat import (
    AuditRequest,
    AuditResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
    HistoryMessage,
)

router: APIRouter = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat_with_adk_agent(payload: ChatRequest) -> ChatResponse:
    """
    Sends a message to the Google ADK multi-agent coordinator within a managed session.
    """
    reply, tools_used, delegated_agents = await adk_assistant_agent.run(
        user_input=payload.message,
        session_id=payload.session_id,
    )

    return ChatResponse(
        session_id=payload.session_id,
        reply=reply,
        tools_used=tools_used,
        delegated_agents=delegated_agents,
    )


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
async def get_adk_session_history(
    session_id: str = Path(..., min_length=1, max_length=100, description="Session ID"),
) -> ChatHistoryResponse:
    """
    Retrieves the stored conversation events for a given session_id from ADK SessionService.
    """
    raw_history: list[dict[str, str]] = await adk_assistant_agent.get_history(session_id)
    formatted_messages: list[HistoryMessage] = [
        HistoryMessage(role=item["role"], content=item["content"]) for item in raw_history
    ]

    return ChatHistoryResponse(session_id=session_id, messages=formatted_messages)


@router.post("/audit", response_model=AuditResponse)
async def run_adk_audit_workflow(payload: AuditRequest) -> AuditResponse:
    """
    Executes the deterministic ADK ParallelAgent -> SequentialAgent audit pipeline.
    """
    report, executed_agents, tools_used = await adk_audit_workflow.run(
        scope=payload.scope,
        session_id=payload.session_id,
    )

    return AuditResponse(
        session_id=payload.session_id,
        report=report,
        executed_agents=executed_agents,
        tools_used=tools_used,
    )
