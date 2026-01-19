"""Custom exceptions for Agent Swarms ecosystem."""

from xy_market.errors.codes import ErrorCode


class MarketplaceError(Exception):
    """Base exception for MarketplaceBK errors."""

    def __init__(self, message: str, error_code: ErrorCode):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class RateLimitError(MarketplaceError):
    """Rate limit exceeded error."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, ErrorCode.RATE_LIMIT_EXCEEDED)


class AgentNotFoundError(MarketplaceError):
    """Agent not found error."""

    def __init__(self, agent_id: str):
        super().__init__(f"Agent not found: {agent_id}", ErrorCode.AGENT_NOT_FOUND)
        self.agent_id = agent_id


class AgentAlreadyRegisteredError(MarketplaceError):
    """Agent already registered error."""

    def __init__(self, message: str):
        super().__init__(message, ErrorCode.AGENT_ALREADY_REGISTERED)


class InvalidPaymentProofError(MarketplaceError):
    """Invalid payment proof error."""

    def __init__(self, message: str = "Invalid payment proof"):
        super().__init__(message, ErrorCode.INVALID_PAYMENT_PROOF)


class ExecutionFailedError(MarketplaceError):
    """Task execution failed error."""

    def __init__(self, message: str):
        super().__init__(message, ErrorCode.EXECUTION_FAILED)


class NegotiationError(MarketplaceError):
    """Base exception for negotiation-related errors."""

    pass


class NegotiationExhaustedError(NegotiationError):
    """Negotiation revision count exceeded max_revisions."""

    def __init__(self, revision: int, max_revisions: int):
        super().__init__(
            f"Negotiation exhausted: revision {revision} exceeds maximum {max_revisions}",
            ErrorCode.NEGOTIATION_EXHAUSTED,
        )
        self.revision = revision
        self.max_revisions = max_revisions
