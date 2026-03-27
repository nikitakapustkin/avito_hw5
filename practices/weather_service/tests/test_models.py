"""Unit tests for Pydantic models."""

import pytest
from datetime import datetime
from weather_service.models import WeatherResponse, WeatherHistoryEntry, HISTORY_MAX_SIZE


class TestWeatherResponse:
    """Tests for WeatherResponse model."""

    def test_valid_weather_response(self):
        """Test creating a valid WeatherResponse."""
        response = WeatherResponse(
            city="Moscow",
            temperature=15.5,
            description="Overcast clouds",
            humidity=72,
            wind_speed=3.5,
        )
        
        assert response.city == "Moscow"
        assert response.temperature == 15.5
        assert response.description == "Overcast clouds"
        assert response.humidity == 72
        assert response.wind_speed == 3.5

    def test_weather_response_serialization(self):
        """Test WeatherResponse JSON serialization."""
        response = WeatherResponse(
            city="London",
            temperature=10.0,
            description="Rainy",
            humidity=85,
            wind_speed=5.2,
        )
        
        data = response.model_dump()
        assert data["city"] == "London"
        assert data["temperature"] == 10.0
        assert data["humidity"] == 85

    def test_weather_response_from_dict(self):
        """Test creating WeatherResponse from dict."""
        data = {
            "city": "Paris",
            "temperature": 12.5,
            "description": "Partly cloudy",
            "humidity": 60,
            "wind_speed": 2.1,
        }
        
        response = WeatherResponse(**data)
        assert response.city == "Paris"
        assert response.temperature == 12.5

    def test_weather_response_missing_field(self):
        """Test that missing required field raises error."""
        with pytest.raises(ValueError):
            WeatherResponse(
                city="Moscow",
                temperature=15.5,
                description="Overcast clouds",
                humidity=72,
                # missing wind_speed
            )

    def test_weather_response_invalid_humidity(self):
        """Test that invalid humidity range raises error."""
        with pytest.raises(ValueError):
            WeatherResponse(
                city="Moscow",
                temperature=15.5,
                description="Overcast clouds",
                humidity=150,  # Invalid: > 100
                wind_speed=3.5,
            )

    def test_weather_response_negative_temperature(self):
        """Test that very low temperature is allowed (valid case)."""
        response = WeatherResponse(
            city="Siberia",
            temperature=-40.0,
            description="Very cold",
            humidity=20,
            wind_speed=10.0,
        )
        assert response.temperature == -40.0

    def test_weather_response_zero_wind_speed(self):
        """Test that zero wind speed is allowed."""
        response = WeatherResponse(
            city="Windless",
            temperature=20.0,
            description="Calm",
            humidity=50,
            wind_speed=0.0,
        )
        assert response.wind_speed == 0.0

    def test_weather_response_empty_city_name(self):
        """Test that empty city name raises error."""
        with pytest.raises(ValueError):
            WeatherResponse(
                city="",
                temperature=15.5,
                description="Overcast",
                humidity=72,
                wind_speed=3.5,
            )

    def test_weather_response_long_description(self):
        """Test that long description is allowed."""
        long_desc = "A" * 200
        response = WeatherResponse(
            city="Test",
            temperature=15.0,
            description=long_desc,
            humidity=50,
            wind_speed=2.0,
        )
        assert len(response.description) == 200


class TestWeatherHistoryEntry:
    """Tests for WeatherHistoryEntry model."""

    def _make_entry(self, **kwargs):
        defaults = dict(
            city="Moscow",
            temperature=15.5,
            description="Overcast clouds",
            humidity=72,
            wind_speed=3.5,
        )
        defaults.update(kwargs)
        return WeatherHistoryEntry(**defaults)

    def test_history_entry_inherits_weather_response(self):
        """WeatherHistoryEntry is a subclass of WeatherResponse."""
        entry = self._make_entry()
        assert isinstance(entry, WeatherResponse)

    def test_history_entry_auto_populates_requested_at(self):
        """requested_at is automatically set when not provided."""
        entry = self._make_entry()
        assert entry.requested_at is not None
        assert isinstance(entry.requested_at, datetime)

    def test_history_entry_explicit_requested_at(self):
        """Explicitly passed requested_at is stored as given."""
        ts = datetime(2026, 3, 27, 10, 0, 0)
        entry = self._make_entry(requested_at=ts)
        assert entry.requested_at == ts

    def test_history_entry_has_all_weather_fields(self):
        """WeatherHistoryEntry.model_fields contains all expected fields."""
        fields = WeatherHistoryEntry.model_fields
        for field in ("city", "temperature", "description", "humidity", "wind_speed", "requested_at"):
            assert field in fields, f"Missing field: {field}"

    def test_history_entry_serialization_includes_requested_at(self):
        """model_dump() includes requested_at."""
        entry = self._make_entry()
        data = entry.model_dump()
        assert "requested_at" in data
        assert data["city"] == "Moscow"

    def test_history_max_size_constant(self):
        """HISTORY_MAX_SIZE equals 10."""
        assert HISTORY_MAX_SIZE == 10
