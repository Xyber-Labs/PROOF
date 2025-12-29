from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from xy_market.utils.validation import validate_uuid, validate_https_url


class AgentRegistrationRequest(BaseModel):
    """Request model for agent registration."""
    agent_name: str = Field(..., description="Human-readable agent name")
    agent_id: str | None = Field(default=None, description="Optional Agent UUID. If not provided, one will be generated.")
    base_url: str = Field(..., description="HTTPS webhook URL")
    description: str = Field(..., description="Agent description")
    tags: list[str] = Field(default_factory=list, description="Optional tags for categorization")

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id_opt(cls, v: str | None) -> str | None:
        """Validate UUID format if provided."""
        if v is not None and not validate_uuid(v):
            raise ValueError(f"Invalid UUID format: {v}")
        return v

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate HTTPS URL."""
        if not validate_https_url(v):
            raise ValueError(f"Invalid HTTPS URL: {v}")
        return v


class AgentProfile(BaseModel):
    """Agent profile for registration with MarketplaceBK."""

    agent_id: str = Field(..., description="Agent UUID")
    agent_name: str = Field(default="", description="Human-readable agent name")
    base_url: str = Field(..., description="HTTPS webhook URL")
    description: str = Field(..., description="Agent description")
    tags: list[str] = Field(default_factory=list, description="Optional tags for categorization")
    version: int = Field(default=1, description="Profile version")
    registered_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Registration timestamp (ISO 8601)",
    )
    last_updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z",
        description="Last update timestamp (ISO 8601)",
    )

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        """Validate UUID format."""
        if not validate_uuid(v):
            raise ValueError(f"Invalid UUID format: {v}")
        return v

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate HTTPS URL."""
        if not validate_https_url(v):
            raise ValueError(f"Invalid HTTPS URL: {v}")
        return v

    model_config = {"json_schema_extra": {"examples": [{"agent_id": "550e8400-e29b-41d4-a716-446655440000", "agent_name": "NewsAgent", "base_url": "https://agent.example.com", "description": "News retrieval agent"}]}}


class RegistrationResponse(BaseModel):
    """Response from agent registration."""

    status: Literal["success"] = "success"
    agent_id: str
    version: int
