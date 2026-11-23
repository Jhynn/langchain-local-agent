from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique conversation thread identifier (e.g., 'user-123')",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Question or instruction for the AI agent",
    )


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tools_used: list[str] = Field(
        default_factory=list,
        description="Tools invoked autonomously by the agent during this turn",
    )


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]
