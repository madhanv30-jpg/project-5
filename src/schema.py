from typing import Optional
from pydantic import BaseModel, Field


class AgentResponse(BaseModel):
    """Structured response contract the model must emit at the end of a run."""

    answer: str = Field(description="The final answer/reply to Madhan.")
    escalated: bool = Field(
        description="True if the query was escalated to Madhan for review."
    )
    escalate_reason: Optional[str] = Field(
        default=None, description="Why it was escalated, if applicable."
    )
    fact_learned: Optional[str] = Field(
        default=None, description="A new durable fact about Madhan that was stored."
    )
    preference_learned: Optional[str] = Field(
        default=None, description="A new durable preference about Madhan that was stored."
    )
    reminder_set: Optional[str] = Field(
        default=None, description="A reminder that was created for Madhan, if any."
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Document sources (file names) the answer was based on.",
    )
    confidence: str = Field(
        default="medium",
        description="Confidence in the answer: low, medium, or high.",
    )
    needs_human: bool = Field(
        default=False,
        description="True if a human (Madhan) should be alerted about this.",
    )


class ToolCallRecord(BaseModel):
    """Instrumentation record for a single tool invocation inside a step."""

    tool: str
    args: dict
    ok: bool
    error: Optional[str] = None
