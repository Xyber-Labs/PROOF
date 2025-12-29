import httpx
import logging

from xy_market.clients.base import BaseClient
from xy_market.models.search import SearchRequest, SearchResponse

logger = logging.getLogger(__name__)


class SearchEngineClient(BaseClient):
    """Client for interacting with SearchEngineBK."""

    def __init__(self, base_url: str, http_client: httpx.AsyncClient | None = None):
        """Initialize SearchEngineClient.

        Args:
            base_url: Base URL of SearchEngineBK
            http_client: Optional HTTP client
        """
        super().__init__(base_url, http_client)

    async def search_sellers(self, search_request: SearchRequest) -> SearchResponse:
        """Search for sellers synchronously.

        Args:
            search_request: Search parameters

        Returns:
            SearchResponse containing list of sellers
        """
        try:
            response = await self.post(
                "/search",
                json=search_request.model_dump(exclude_none=True),
            )
            return SearchResponse.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise ValueError(f"Invalid search request: {e.response.text}") from e
            if e.response.status_code == 429:
                from xy_market.errors.exceptions import RateLimitError
                raise RateLimitError(f"Rate limit exceeded: {e.response.text}") from e
            raise
