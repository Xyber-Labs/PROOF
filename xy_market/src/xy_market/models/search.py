"""Search models for marketplace integration."""

from pydantic import BaseModel, Field, field_validator

from xy_market.utils.validation import validate_uuid


class SearchRequest(BaseModel):
    """Search request for filtering sellers."""

    task_description: str = Field(
        ..., description="Task description for semantic search"
    )
    tags: list[str] | None = Field(
        default=None, description="Optional tags for targeted search"
    )
    limit: int = Field(default=5, ge=1, le=20, description="Maximum number of results")
    budget_range: tuple[float, float] | None = Field(
        default=None,
        description="Optional budget range (min, max) in smallest currency unit. Second value must be >= first.",
    )

    @field_validator("budget_range")
    @classmethod
    def validate_budget_range(
        cls, v: tuple[float, float] | None
    ) -> tuple[float, float] | None:
        """Validate that budget_range[1] >= budget_range[0]."""
        if v is not None:
            min_budget, max_budget = v
            if max_budget < min_budget:
                raise ValueError(
                    f"budget_range max ({max_budget}) must be >= min ({min_budget})"
                )
            if min_budget < 0:
                raise ValueError(f"budget_range min ({min_budget}) must be >= 0")
        return v


class SellerProfile(BaseModel):
    """Seller profile returned by marketplace."""

    seller_id: str = Field(..., description="Seller UUID")
    base_url: str = Field(..., description="Seller HTTPS base URL")
    description: str = Field(..., description="Seller description")
    tags: list[str] = Field(
        default_factory=list, description="Optional tags for categorization"
    )
    version: int = Field(default=1, description="Profile version")
    registered_at: str = Field(..., description="Registration timestamp (ISO 8601)")

    @field_validator("seller_id")
    @classmethod
    def validate_seller_id(cls, v: str) -> str:
        """Validate UUID format."""
        if not validate_uuid(v):
            raise ValueError(f"Invalid UUID format: {v}")
        return v

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate HTTPS URL."""
        from xy_market.utils.validation import validate_https_url

        if not validate_https_url(v):
            raise ValueError(f"Invalid HTTPS URL: {v}")
        return v


class SearchResponse(BaseModel):
    """
    Search response from marketplace.

    Synchronous response containing relevant sellers.
    """

    sellers: list[SellerProfile] = Field(
        ..., description="List of relevant Seller profiles"
    )
    search_id: str | None = Field(
        default=None, description="Optional ID for tracking the search request"
    )
