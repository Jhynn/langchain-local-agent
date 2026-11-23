from fastapi import APIRouter, Path
from app.agents.assistant_agent import assistant_agent
from app.schemas.chat import ChatHistoryResponse, ChatRequest, ChatResponse, HistoryMessage

router: APIRouter = APIRouter()


@router.post("/", response_model=ChatResponse)
def chat_with_agent(payload: ChatRequest) -> ChatResponse:
    """
    Sends a message to the LangGraph ReAct agent within a persistent session thread.
    """
    reply, tools_used = assistant_agent.run(
        user_input=payload.message,
        session_id=payload.session_id,
    )

    return ChatResponse(
        session_id=payload.session_id,
        reply=reply,
        tools_used=tools_used,
    )


@router.get("/{session_id}/history", response_model=ChatHistoryResponse)
def get_session_history(
    session_id: str = Path(..., min_length=1, max_length=100, description="Session thread ID"),
) -> ChatHistoryResponse:
    """
    Retrieves the stored conversation history for a given session_id from MemorySaver.
    """
    raw_history: list[dict[str, str]] = assistant_agent.get_history(session_id)
    formatted_messages: list[HistoryMessage] = [
        HistoryMessage(role=item["role"], content=item["content"]) for item in raw_history
    ]

    return ChatHistoryResponse(session_id=session_id, messages=formatted_messages)
