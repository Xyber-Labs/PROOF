from typing import Literal

from pydantic import BaseModel, Field, field_validator

from xy_market.utils.validation import validate_uuid


class ExecutionRequest(BaseModel):
    """Task execution request from Buyer to Seller."""

    task_description: str = Field(..., description="Task description")
    context: dict | None = Field(default=None, description="Optional context data")
    secrets: dict | None = Field(
        default=None,
        description="Sensitive data (API keys, credentials) - NEVER logged",
    )


class ExecutionResult(BaseModel):
    """Task execution result from Seller to Buyer.
    
    For async execution pattern:
    - Initial response: status='in_progress', task_id and buyer_secret provided
    - Polling response: status='in_progress' (still working) or 'done'/'failed' (complete)
    """

    task_id: str = Field(..., description="Task UUID assigned by Seller for tracking")
    buyer_secret: str = Field(..., description="Secret UUID for polling task status (assigned by Seller)")
    status: Literal["in_progress", "done", "failed"] = Field(
        ..., description="Execution status - 'in_progress' for async operations, 'done' when complete, 'failed' on error"
    )
    data: dict = Field(default_factory=dict, description="Result data (only populated when status='done')")
    execution_time_ms: int | None = Field(default=None, description="Execution time in milliseconds")
    error: dict | None = Field(
        default=None,
        description="Error details if status is 'failed'",
    )
    created_at: str = Field(..., description="Task creation timestamp (ISO 8601)")
    deadline_at: str | None = Field(
        default=None, description="Deadline timestamp (ISO 8601) - when task must be completed by"
    )

    @field_validator("task_id", "buyer_secret")
    @classmethod
    def validate_uuid_fields(cls, v: str) -> str:
        """Validate UUID format."""
        if not validate_uuid(v):
            raise ValueError(f"Invalid UUID format: {v}")
        return v
