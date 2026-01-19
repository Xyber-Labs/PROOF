"""
This module should be changed to match the request and response shapes of your own MCP tools and REST endpoints, while keeping the pattern of small, focused Pydantic models.

Main responsibility: Define shared Pydantic schemas for input and output payloads used across routers and tools.
"""

from typing import Literal

from pydantic import BaseModel, Field


class LocationRequest(BaseModel):
    """Input schema for location-based queries with unit preferences."""

    latitude: str = Field(
        ...,
        pattern=r"^-?\d{1,2}\.\d+$",
        description="Location latitude as a string, e.g., '37.7749'. Format: decimal degrees with optional negative sign",
    )
    longitude: str = Field(
        ...,
        pattern=r"^-?\d{1,3}\.\d+$",
        description="Location longitude as a string, e.g., '-122.4194'. Format: decimal degrees with optional negative sign",
    )
    units: Literal["metric", "imperial"] | None = Field(
        default=None,
        description="Unit system for temperature and other measures: 'metric' or 'imperial'. Defaults to configuration.",
    )


class WeatherResponse(BaseModel):
    """Response model for weather data."""

    state: str = Field(description="Weather state/condition description")
    temperature: str = Field(description="Temperature with unit suffix (e.g., '25C' or '77F')")
    humidity: str = Field(description="Humidity percentage (e.g., '65%')")


class ForecastDayResponse(BaseModel):
    """Response model for a single day in a weather forecast."""

    day: int = Field(description="Day number (1-indexed)")
    condition: str = Field(description="Weather condition for the day")
    high: int = Field(description="High temperature")
    low: int = Field(description="Low temperature")


class ForecastResponse(BaseModel):
    """Response model for weather forecast data."""

    location: str = Field(description="Location name")
    days: int = Field(description="Number of forecast days")
    forecast: list[ForecastDayResponse] = Field(description="List of daily forecast data")