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
        description="Tools invoked autonomously during this turn",
    )

    delegated_agents: list[str] = Field(
        default_factory=list,
        description="Specialist sub-agents invoked during multi-agent routing",
    )


class HistoryMessage(BaseModel):
    role: str
    content: str


class ChatHistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]

class AuditRequest(BaseModel):
    session_id: str = Field(
        default="audit-run-01",
        min_length=1,
        max_length=100,
        description="Unique session identifier for the audit workflow run",
    )
    scope: str = Field(
        default="Generate a complete corporate expense audit report covering department totals and pending approvals.",
        min_length=1,
        description="Audit scope or instructions passed to the parallel collectors",
    )


class AuditResponse(BaseModel):
    session_id: str
    report: str
    executed_agents: list[str] = Field(
        default_factory=list,
        description="Agents executed across the parallel and sequential stages",
    )
    tools_used: list[str] = Field(
        default_factory=list,
        description="Tools invoked across the parallel data collection branches",
    )
