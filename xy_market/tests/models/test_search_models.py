
import pytest

from xy_market.models.search import SearchRequest, SearchResponse, SellerProfile


def test_search_request_validation():
    """Test SearchRequest validation."""
    request = SearchRequest(
        task_description="Find news articles about AI",
        limit=10,
    )
    assert request.task_description == "Find news articles about AI"
    assert request.limit == 10
    assert request.budget_range is None

    # Test with tags and budget
    request_with_details = SearchRequest(
        task_description="Find news articles",
        tags=["news", "ai"],
        limit=5,
        budget_range=(10.0, 100.0),
    )
    assert request_with_details.tags == ["news", "ai"]
    assert request_with_details.budget_range == (10.0, 100.0)

    # Test invalid budget_range (max < min)
    with pytest.raises(ValueError, match="must be >= min"):
        SearchRequest(task_description="Test", budget_range=(100.0, 10.0))

    # Test invalid budget_range (min < 0)
    with pytest.raises(ValueError, match="must be >= 0"):
        SearchRequest(task_description="Test", budget_range=(-1.0, 10.0))


def test_seller_profile_validation():
    """Test SellerProfile validation."""
    profile = SellerProfile(
        seller_id="770e8400-e29b-41d4-a716-446655440002",
        base_url="https://seller.example.com",
        description="Test seller",
        tags=["news"],
        version=1,
        registered_at="2024-01-01T00:00:00Z",
    )
    assert profile.seller_id == "770e8400-e29b-41d4-a716-446655440002"
    assert profile.base_url == "https://seller.example.com"
    assert profile.tags == ["news"]

    # Test invalid seller_id
    with pytest.raises(ValueError):
        SellerProfile(
            seller_id="invalid",
            base_url="https://seller.example.com",
            description="Test",
            registered_at="2024-01-01T00:00:00Z",
        )

    # Test invalid HTTPS URL
    with pytest.raises(ValueError):
        SellerProfile(
            seller_id="770e8400-e29b-41d4-a716-446655440002",
            base_url="http://seller.example.com",  # Not HTTPS
            description="Test",
            registered_at="2024-01-01T00:00:00Z",
        )


def test_search_response_validation():
    """Test SearchResponse validation."""
    sellers = [
        SellerProfile(
            seller_id="770e8400-e29b-41d4-a716-446655440002",
            base_url="https://seller.example.com",
            description="Test seller",
            registered_at="2024-01-01T00:00:00Z",
        )
    ]

    response = SearchResponse(
        sellers=sellers,
        search_id="550e8400-e29b-41d4-a716-446655440000",
    )
    assert len(response.sellers) == 1
    assert response.search_id == "550e8400-e29b-41d4-a716-446655440000"
    assert response.sellers[0].seller_id == "770e8400-e29b-41d4-a716-446655440002"

    # Test with empty sellers
    empty_response = SearchResponse(sellers=[])
    assert len(empty_response.sellers) == 0
    assert empty_response.search_id is None

    # Test with None search_id
    response_no_id = SearchResponse(sellers=sellers, search_id=None)
    assert response_no_id.search_id is None
