import pytest
from xy_market.utils.validation import validate_uuid, validate_https_url

def test_validate_uuid_valid():
    assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True
    assert validate_uuid("00000000-0000-0000-0000-000000000000") is True

def test_validate_uuid_invalid():
    assert validate_uuid("not-a-uuid") is False
    assert validate_uuid("550e8400-e29b-41d4-a716-44665544000") is False  # too short
    assert validate_uuid("550e8400-e29b-41d4-a716-4466554400000") is False # too long
    assert validate_uuid("") is False

def test_validate_https_url_valid_https():
    assert validate_https_url("https://example.com") is True
    assert validate_https_url("https://sub.example.com/path") is True

def test_validate_https_url_valid_localhost():
    assert validate_https_url("http://localhost") is True
    assert validate_https_url("http://localhost:8000") is True
    assert validate_https_url("http://127.0.0.1:8000") is True

def test_validate_https_url_valid_docker_service():
    assert validate_https_url("http://search_engine:8002") is True
    assert validate_https_url("http://marketplace") is True

def test_validate_https_url_invalid():
    assert validate_https_url("ftp://example.com") is False
    assert validate_https_url("not-a-url") is False
    assert validate_https_url("") is False
    # HTTP not allowed for public domains
    assert validate_https_url("http://example.com") is False

