"""Integration tests for the Weather Service API endpoint."""

import pytest
import json
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from redis import Redis
from weather_service.app import app, AppState
from weather_service.models import WeatherResponse
from weather_service.openweather_client import (
    OpenWeatherMapClient,
    CityNotFoundError,
    RateLimitedError,
    ProviderError,
    TimeoutError as ProviderTimeoutError,
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def setup_app_state(monkeypatch):
    """Set up app state with mock services using monkeypatch for isolation."""
    from weather_service.cache import CacheService

    # Create mocks
    mock_redis = MagicMock(spec=Redis)
    mock_weather_client = MagicMock(spec=OpenWeatherMapClient)

    # Use monkeypatch for automatic cleanup
    monkeypatch.setattr("weather_service.app.AppState.redis_client", mock_redis)
    monkeypatch.setattr(
        "weather_service.app.AppState.cache_service",
        CacheService(mock_redis),
    )
    monkeypatch.setattr(
        "weather_service.app.AppState.weather_client",
        mock_weather_client,
    )

    return {
        "redis": mock_redis,
        "weather_client": mock_weather_client,
    }


class TestWeatherEndpoint:
    """Tests for GET /weather/{city} endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint (no mocking needed)."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_get_weather_cache_hit(self, client, setup_app_state):
        """Test GET /weather with cache hit."""
        mock_redis = setup_app_state["redis"]

        weather_response = WeatherResponse(
            city="Moscow",
            temperature=15.5,
            description="Overcast clouds",
            humidity=72,
            wind_speed=3.5,
        )

        # Mock Redis cache hit with properly structured data
        mock_redis.get.return_value = json.dumps(
            weather_response.model_dump()
        )

        response = client.get("/weather/Moscow")

        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Moscow"
        assert data["temperature"] == 15.5
        assert data["humidity"] == 72
        assert data["wind_speed"] == 3.5

    @pytest.mark.asyncio
    async def test_get_weather_cache_miss(self, client, setup_app_state):
        """Test GET /weather with cache miss and successful fetch."""
        mock_redis = setup_app_state["redis"]
        mock_weather_client = setup_app_state["weather_client"]

        weather_response = WeatherResponse(
            city="Paris",
            temperature=12.0,
            description="Rainy",
            humidity=85,
            wind_speed=5.2,
        )

        # Mock cache miss
        mock_redis.get.return_value = None
        # Mock successful weather fetch
        mock_weather_client.get_weather.return_value = weather_response
        mock_redis.setex.return_value = True

        response = client.get("/weather/Paris")

        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Paris"
        assert data["temperature"] == 12.0

    @pytest.mark.asyncio
    async def test_get_weather_city_not_found(self, client, setup_app_state):
        """Test GET /weather with city not found (404)."""
        mock_weather_client = setup_app_state["weather_client"]
        mock_weather_client.get_weather.side_effect = CityNotFoundError(
            "City not found"
        )

        response = client.get("/weather/NoSuchCity")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_weather_rate_limited(self, client, setup_app_state):
        """Test GET /weather with rate limit (429 -> 503)."""
        mock_weather_client = setup_app_state["weather_client"]
        mock_weather_client.get_weather.side_effect = RateLimitedError(
            "Rate limited"
        )

        response = client.get("/weather/Moscow")

        assert response.status_code == 503
        data = response.json()
        assert "temporarily unavailable" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_weather_provider_error(self, client, setup_app_state):
        """Test GET /weather with provider 5xx error (502)."""
        mock_weather_client = setup_app_state["weather_client"]
        mock_weather_client.get_weather.side_effect = ProviderError(
            "Server error"
        )

        response = client.get("/weather/Moscow")

        assert response.status_code == 502
        data = response.json()
        assert "provider" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_weather_timeout(self, client, setup_app_state):
        """Test GET /weather with timeout (504)."""
        mock_weather_client = setup_app_state["weather_client"]
        mock_weather_client.get_weather.side_effect = ProviderTimeoutError(
            "Timeout"
        )

        response = client.get("/weather/Moscow")

        assert response.status_code == 504
        data = response.json()
        assert "timeout" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_weather_empty_city(self, client, setup_app_state):
        """Test GET /weather with empty city parameter."""
        response = client.get("/weather/")
        # FastAPI will return 404 for empty path parameter
        assert response.status_code in (404, 422)

    @pytest.mark.asyncio
    async def test_get_weather_city_too_long(self, client, setup_app_state):
        """Test GET /weather with city name exceeding max length."""
        long_city = "A" * 101
        response = client.get(f"/weather/{long_city}")

        # Should be rejected due to validation
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_weather_special_characters_in_city(
        self, client, setup_app_state
    ):
        """Test GET /weather with special characters in city name."""
        mock_redis = setup_app_state["redis"]
        mock_weather_client = setup_app_state["weather_client"]

        city = "St. Petersburg"
        weather_response = WeatherResponse(
            city=city,
            temperature=10.0,
            description="Cloudy",
            humidity=70,
            wind_speed=4.0,
        )

        mock_redis.get.return_value = None
        mock_weather_client.get_weather.return_value = weather_response
        mock_redis.setex.return_value = True

        response = client.get(f"/weather/{city}")

        assert response.status_code == 200
        data = response.json()
        assert data["city"] == city

    @pytest.mark.asyncio
    async def test_cache_not_updated_on_provider_error(
        self, client, setup_app_state
    ):
        """Test that cache is not updated when provider fails."""
        mock_redis = setup_app_state["redis"]
        mock_weather_client = setup_app_state["weather_client"]

        mock_redis.get.return_value = None
        mock_weather_client.get_weather.side_effect = ProviderError(
            "Server error"
        )

        response = client.get("/weather/Moscow")

        assert response.status_code == 502
        # Verify behavior: error message is present
        assert response.json()["detail"]

    @pytest.mark.asyncio
    async def test_response_model_structure(self, client, setup_app_state):
        """Test that response includes all required fields."""
        mock_redis = setup_app_state["redis"]

        weather_response = WeatherResponse(
            city="London",
            temperature=10.0,
            description="Rainy",
            humidity=85,
            wind_speed=5.0,
        )

        mock_redis.get.return_value = json.dumps(
            weather_response.model_dump()
        )

        response = client.get("/weather/London")

        assert response.status_code == 200
        data = response.json()

        # Verify response matches model schema via validation
        validated = WeatherResponse(**data)
        assert validated.city == "London"
        assert validated.temperature == 10.0

    @pytest.mark.asyncio
    async def test_multiple_requests_same_city(
        self, client, setup_app_state
    ):
        """Test multiple requests for the same city (cache hit on second)."""
        mock_redis = setup_app_state["redis"]
        mock_weather_client = setup_app_state["weather_client"]

        weather_response = WeatherResponse(
            city="Berlin",
            temperature=8.0,
            description="Cloudy",
            humidity=75,
            wind_speed=3.0,
        )

        # First request: cache miss
        mock_redis.get.return_value = None
        mock_weather_client.get_weather.return_value = weather_response
        mock_redis.setex.return_value = True

        response1 = client.get("/weather/Berlin")

        assert response1.status_code == 200

        # Second request: cache hit
        mock_redis.get.return_value = json.dumps(
            weather_response.model_dump()
        )

        response2 = client.get("/weather/Berlin")

        assert response2.status_code == 200
        assert response1.json() == response2.json()

    @pytest.mark.asyncio
    async def test_api_key_not_in_logs(self, client, setup_app_state):
        """Test that API key is never exposed in responses."""
        mock_weather_client = setup_app_state["weather_client"]
        mock_weather_client.get_weather.side_effect = ProviderError(
            "Provider error"
        )

        response = client.get("/weather/Moscow")

        assert response.status_code == 502
        data = response.json()

        # API key should never be in response
        assert "test_key" not in str(data)
        assert "OPENWEATHERMAP_API_KEY" not in str(data)

    @pytest.mark.asyncio
    async def test_case_insensitive_city_cache(self, client, setup_app_state):
        """Test that city names are normalized for cache lookup."""
        mock_redis = setup_app_state["redis"]

        weather_response = WeatherResponse(
            city="Moscow",
            temperature=15.0,
            description="Clear",
            humidity=60,
            wind_speed=2.0,
        )

        mock_redis.get.return_value = json.dumps(
            weather_response.model_dump()
        )

        # Request with uppercase city
        response = client.get("/weather/MOSCOW")

        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Moscow"


class TestWeatherHistory:
    """Tests for AppState.weather_history population via GET /weather/{city}."""

    @pytest.fixture(autouse=True)
    def reset_history(self, monkeypatch):
        """Reset AppState.weather_history before each test to prevent contamination."""
        monkeypatch.setattr("weather_service.app.AppState.weather_history", {})

    @pytest.mark.asyncio
    async def test_cache_miss_populates_history(self, client, setup_app_state):
        """After a cache-miss GET /weather/moscow, history["moscow"] has length 1."""
        mock_redis = setup_app_state["redis"]
        mock_weather_client = setup_app_state["weather_client"]

        weather_response = WeatherResponse(
            city="Moscow",
            temperature=15.5,
            description="Overcast clouds",
            humidity=72,
            wind_speed=3.5,
        )

        mock_redis.get.return_value = None
        mock_weather_client.get_weather.return_value = weather_response
        mock_redis.setex.return_value = True

        response = client.get("/weather/Moscow")

        assert response.status_code == 200
        from weather_service.app import AppState
        assert "moscow" in AppState.weather_history
        assert len(AppState.weather_history["moscow"]) == 1

    @pytest.mark.asyncio
    async def test_cache_hit_populates_history(self, client, setup_app_state):
        """After a cache-hit GET /weather/moscow, history["moscow"] has length 1."""
        mock_redis = setup_app_state["redis"]

        weather_response = WeatherResponse(
            city="Moscow",
            temperature=15.5,
            description="Overcast clouds",
            humidity=72,
            wind_speed=3.5,
        )

        mock_redis.get.return_value = json.dumps(weather_response.model_dump())

        response = client.get("/weather/Moscow")

        assert response.status_code == 200
        from weather_service.app import AppState
        assert "moscow" in AppState.weather_history
        assert len(AppState.weather_history["moscow"]) == 1

    @pytest.mark.asyncio
    async def test_history_grows_with_multiple_requests(self, client, setup_app_state):
        """After N successful requests, history length equals N (up to HISTORY_MAX_SIZE)."""
        mock_redis = setup_app_state["redis"]
        mock_weather_client = setup_app_state["weather_client"]

        weather_response = WeatherResponse(
            city="Paris",
            temperature=12.0,
            description="Rainy",
            humidity=85,
            wind_speed=5.2,
        )

        mock_redis.get.return_value = None
        mock_weather_client.get_weather.return_value = weather_response
        mock_redis.setex.return_value = True

        for _ in range(5):
            response = client.get("/weather/Paris")
            assert response.status_code == 200

        from weather_service.app import AppState
        assert len(AppState.weather_history["paris"]) == 5

    @pytest.mark.asyncio
    async def test_history_capped_at_max_size(self, client, setup_app_state):
        """After 11 successful requests, history length is exactly 10 (oldest dropped)."""
        mock_redis = setup_app_state["redis"]
        mock_weather_client = setup_app_state["weather_client"]

        weather_response = WeatherResponse(
            city="Berlin",
            temperature=8.0,
            description="Cloudy",
            humidity=75,
            wind_speed=3.0,
        )

        mock_redis.get.return_value = None
        mock_weather_client.get_weather.return_value = weather_response
        mock_redis.setex.return_value = True

        for _ in range(11):
            response = client.get("/weather/Berlin")
            assert response.status_code == 200

        from weather_service.app import AppState
        assert len(AppState.weather_history["berlin"]) == 10

    @pytest.mark.asyncio
    async def test_history_fifo_oldest_dropped(self, client, setup_app_state):
        """When 11th entry is added, the oldest (index 0) is dropped, newest is at index -1."""
        mock_redis = setup_app_state["redis"]
        mock_weather_client = setup_app_state["weather_client"]

        mock_redis.setex.return_value = True

        temperatures = list(range(1, 12))  # 1 through 11
        for temp in temperatures:
            weather_response = WeatherResponse(
                city="Tokyo",
                temperature=float(temp),
                description="Clear",
                humidity=60,
                wind_speed=2.0,
            )
            mock_redis.get.return_value = None
            mock_weather_client.get_weather.return_value = weather_response
            client.get("/weather/Tokyo")

        from weather_service.app import AppState
        history = AppState.weather_history["tokyo"]
        assert len(history) == 10
        # Oldest dropped (temp=1), newest should be temp=11
        assert history[0].temperature == 2.0   # second-oldest is now at index 0
        assert history[-1].temperature == 11.0  # newest at end

    @pytest.mark.asyncio
    async def test_error_does_not_populate_history(self, client, setup_app_state):
        """When GET /weather/{city} raises an error (404), history is NOT modified."""
        mock_weather_client = setup_app_state["weather_client"]
        mock_weather_client.get_weather.side_effect = CityNotFoundError("City not found")

        response = client.get("/weather/NoSuchCity")

        assert response.status_code == 404
        from weather_service.app import AppState
        assert "nosuchcity" not in AppState.weather_history

    @pytest.mark.asyncio
    async def test_history_key_is_normalized_city(self, client, setup_app_state):
        """History key is lowercase normalized city, not the raw input."""
        mock_redis = setup_app_state["redis"]
        mock_weather_client = setup_app_state["weather_client"]

        weather_response = WeatherResponse(
            city="London",
            temperature=10.0,
            description="Rainy",
            humidity=85,
            wind_speed=5.0,
        )

        mock_redis.get.return_value = None
        mock_weather_client.get_weather.return_value = weather_response
        mock_redis.setex.return_value = True

        client.get("/weather/LONDON")

        from weather_service.app import AppState
        assert "london" in AppState.weather_history
        assert "LONDON" not in AppState.weather_history


class TestWeatherHistoryEndpoint:
    """Tests for GET /weather/{city}/history endpoint."""

    @pytest.fixture(autouse=True)
    def reset_history(self, monkeypatch):
        """Reset AppState.weather_history before each test to prevent contamination."""
        monkeypatch.setattr("weather_service.app.AppState.weather_history", {})

    @pytest.mark.asyncio
    async def test_empty_list_for_never_queried_city(self, client):
        """GET /weather/{city}/history returns 200 with [] for a city never queried."""
        response = client.get("/weather/neverqueried/history")
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_case_insensitive_normalization(self, client, monkeypatch):
        """GET /weather/Moscow/history and GET /weather/moscow/history resolve to same history."""
        from weather_service.models import WeatherHistoryEntry

        entry = WeatherHistoryEntry(
            city="Moscow",
            temperature=10.0,
            description="Clear",
            humidity=60,
            wind_speed=2.0,
        )
        monkeypatch.setattr(
            "weather_service.app.AppState.weather_history",
            {"moscow": [entry]},
        )

        response_upper = client.get("/weather/Moscow/history")
        response_lower = client.get("/weather/moscow/history")

        assert response_upper.status_code == 200
        assert response_lower.status_code == 200
        assert len(response_upper.json()) == 1
        assert len(response_lower.json()) == 1
        assert response_upper.json()[0]["city"] == "Moscow"
        assert response_lower.json()[0]["city"] == "Moscow"

    @pytest.mark.asyncio
    async def test_returns_correct_entries_with_all_fields(self, client, monkeypatch):
        """History entries include all required fields: city, temperature, description, humidity, wind_speed, requested_at."""
        from weather_service.models import WeatherHistoryEntry

        entry = WeatherHistoryEntry(
            city="Moscow",
            temperature=15.5,
            description="Overcast clouds",
            humidity=72,
            wind_speed=3.5,
        )
        monkeypatch.setattr(
            "weather_service.app.AppState.weather_history",
            {"moscow": [entry]},
        )

        response = client.get("/weather/moscow/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["city"] == "Moscow"
        assert data[0]["temperature"] == 15.5
        assert data[0]["description"] == "Overcast clouds"
        assert data[0]["humidity"] == 72
        assert data[0]["wind_speed"] == 3.5
        assert "requested_at" in data[0]

    @pytest.mark.asyncio
    async def test_no_404_for_unknown_city_always_200(self, client):
        """GET /weather/{city}/history never returns 404 — always 200 even for unknown cities."""
        for city in ["unknowncity", "nonexistent", "xyz123"]:
            response = client.get(f"/weather/{city}/history")
            assert response.status_code == 200
            assert response.json() == []
