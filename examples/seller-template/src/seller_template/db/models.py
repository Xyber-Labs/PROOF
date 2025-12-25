import datetime
from typing import Any
import uuid

from pydantic import BaseModel, Field

from xy_market.models.execution import ExecutionRequest, ExecutionResult


class Task(BaseModel):
    """Represents a task in the system."""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    buyer_secret: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "in_progress"
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    expires_at: datetime.datetime
    execution_request: ExecutionRequest
    result: Any | None = None
    error: dict[str, Any] | None = None
    execution_time_ms: int | None = None
    tools_used: list[str] = Field(default_factory=list)

    def to_execution_result(self) -> ExecutionResult:
        """Converts the Task model to an ExecutionResult model."""
        # ExecutionResult uses 'data' instead of 'result' and 'deadline_at' instead of 'expires_at'
        data = self.result if self.result else {}
        if isinstance(data, dict) and "tools_used" not in data:
            data["tools_used"] = self.tools_used
        
        return ExecutionResult(
            task_id=self.task_id,
            buyer_secret=self.buyer_secret,
            status=self.status,
            created_at=self.created_at.isoformat().replace("+00:00", "Z"),
            deadline_at=self.expires_at.isoformat().replace("+00:00", "Z"),
            data=data,
            error=self.error,
            execution_time_ms=self.execution_time_ms,
        )
