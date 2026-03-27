"""Pydantic models for Weather Service API responses."""

from datetime import datetime
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, EmailStr

HISTORY_MAX_SIZE: int = 10


class WeatherResponse(BaseModel):
    """Weather information response model (Pydantic v2)."""

    city: str = Field(
        ...,
        description="City name",
        examples=["Moscow"],
        json_schema_extra={"minLength": 1, "maxLength": 100},
    )
    temperature: float = Field(
        ...,
        description="Temperature in Celsius",
        examples=[15.5],
        json_schema_extra={"exclusiveMinimum": -273.15},
    )
    description: str = Field(
        ...,
        description="Weather description",
        examples=["Overcast clouds"],
        json_schema_extra={"minLength": 1, "maxLength": 200},
    )
    humidity: int = Field(
        ...,
        description="Humidity percentage (0-100)",
        examples=[72],
        json_schema_extra={"minimum": 0, "maximum": 100},
    )
    wind_speed: float = Field(
        ...,
        description="Wind speed in m/s",
        examples=[3.5],
        json_schema_extra={"minimum": 0},
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "city": "Moscow",
                "temperature": 15.5,
                "description": "Overcast clouds",
                "humidity": 72,
                "wind_speed": 3.5,
            }
        }
    }

    @field_validator("humidity")
    @classmethod
    def validate_humidity(cls, v):
        """Validate humidity is between 0 and 100."""
        if not (0 <= v <= 100):
            raise ValueError("Humidity must be between 0 and 100")
        return v

    @field_validator("city")
    @classmethod
    def validate_city(cls, v):
        """Validate city name is not empty."""
        if not v or not v.strip():
            raise ValueError("City name cannot be empty")
        return v


class SubscribeRequest(BaseModel):
    """Request model for POST /subscribe endpoint (Pydantic v2)."""

    city: str = Field(
        ...,
        description="City name",
        min_length=1,
        max_length=100,
        examples=["Moscow"],
    )
    email: EmailStr = Field(
        ...,
        description="Valid email address",
        examples=["user@example.com"],
    )
    channel: Literal["email"] = Field(
        default="email",
        description="Subscription channel (only 'email' is supported)",
        examples=["email"],
    )

    @field_validator("city", mode="before")
    @classmethod
    def validate_and_normalize_city(cls, v):
        """Validate and normalize city name: trim, not empty, max 100."""
        if not isinstance(v, str):
            raise ValueError("City must be a string")
        v = v.strip()
        if not v:
            raise ValueError("City cannot be empty after trim")
        if len(v) > 100:
            raise ValueError("City must be at most 100 characters")
        return v


class SubscriptionResponse(BaseModel):
    """Response model for POST /subscribe endpoint (201 Created)."""

    id: str = Field(
        ...,
        description="Subscription unique identifier (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    city: str = Field(
        ...,
        description="City name (trimmed, not normalized to lowercase)",
        examples=["Moscow"],
    )
    email: str = Field(
        ...,
        description="Email address",
        examples=["user@example.com"],
    )
    channel: Literal["email"] = Field(
        ...,
        description="Subscription channel",
        examples=["email"],
    )
    created_at: datetime = Field(
        ...,
        description="Subscription creation timestamp (ISO 8601)",
        examples=["2026-03-06T08:02:51.562000"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "city": "Moscow",
                "email": "user@example.com",
                "channel": "email",
                "created_at": "2026-03-06T08:02:51.562000",
            }
        }
    }


class Subscription(BaseModel):
    """Internal subscription model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    city: str  # Normalized city (trimmed)
    city_normalized: str  # Lowercase normalized for uniqueness check
    email: str  # Stored as-is from request (will be lowercased for comparison)
    channel: Literal["email"]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WeatherHistoryEntry(WeatherResponse):
    """Single weather history record extending WeatherResponse with a timestamp."""

    requested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of when the weather was requested",
        examples=["2026-03-27T10:00:00"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "city": "Moscow",
                "temperature": 15.5,
                "description": "Overcast clouds",
                "humidity": 72,
                "wind_speed": 3.5,
                "requested_at": "2026-03-27T10:00:00",
            }
        }
    }
