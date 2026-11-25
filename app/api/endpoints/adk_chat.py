from fastapi import APIRouter, Path
from app.agents.adk_agent import adk_assistant_agent
from app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse, HistoryMessage

router: APIRouter = APIRouter()


@router.post("/", response_model=ChatResponse)
async def chat_with_adk_agent(payload: ChatRequest) -> ChatResponse:
    """
    Sends a message to the Google ADK agent within a managed session.
    """
    reply, tools_used = await adk_assistant_agent.run(
        user_input=payload.message,
        session_id=payload.session_id,
    )

    return ChatResponse(
        session_id=payload.session_id,
        reply=reply,
        tools_used=tools_used,
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
