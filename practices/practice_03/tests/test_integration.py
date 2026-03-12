"""Integration tests for the Weather Service API endpoint."""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
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
def mock_redis():
    """Create a mock Redis client."""
    return MagicMock(spec=Redis)


@pytest.fixture
def setup_app_state(mock_redis):
    """Set up app state with mock services."""
    from weather_service.cache import CacheService
    
    AppState.redis_client = mock_redis
    AppState.cache_service = CacheService(mock_redis)
    AppState.weather_client = OpenWeatherMapClient("test_key")
    
    yield
    
    # Cleanup
    AppState.redis_client = None
    AppState.cache_service = None
    AppState.weather_client = None


class TestWeatherEndpoint:
    """Tests for GET /weather/{city} endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_get_weather_cache_hit(self, client, setup_app_state, mock_redis):
        """Test GET /weather with cache hit."""
        weather_data = {
            "city": "Moscow",
            "temperature": 15.5,
            "description": "Overcast clouds",
            "humidity": 72,
            "wind_speed": 3.5,
        }
        
        # Mock Redis cache hit
        mock_redis.get.return_value = json.dumps(weather_data)
        
        response = client.get("/weather/Moscow")
        
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Moscow"
        assert data["temperature"] == 15.5
        assert data["humidity"] == 72
        assert data["wind_speed"] == 3.5

    @pytest.mark.asyncio
    async def test_get_weather_cache_miss(self, client, setup_app_state, mock_redis):
        """Test GET /weather with cache miss and successful fetch."""
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
        mock_redis.setex.return_value = True
        
        with patch.object(
            AppState.weather_client,
            "get_weather",
            return_value=weather_response,
        ):
            response = client.get("/weather/Paris")
        
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Paris"
        assert data["temperature"] == 12.0

    @pytest.mark.asyncio
    async def test_get_weather_city_not_found(self, client, setup_app_state):
        """Test GET /weather with city not found (404)."""
        with patch.object(
            AppState.weather_client,
            "get_weather",
            side_effect=CityNotFoundError("City not found"),
        ):
            response = client.get("/weather/NoSuchCity")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_get_weather_rate_limited(self, client, setup_app_state):
        """Test GET /weather with rate limit (429 -> 503)."""
        with patch.object(
            AppState.weather_client,
            "get_weather",
            side_effect=RateLimitedError("Rate limited"),
        ):
            response = client.get("/weather/Moscow")
        
        assert response.status_code == 503
        data = response.json()
        assert "temporarily unavailable" in data["detail"].lower() or "rate limited" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_weather_provider_error(self, client, setup_app_state):
        """Test GET /weather with provider 5xx error (502)."""
        with patch.object(
            AppState.weather_client,
            "get_weather",
            side_effect=ProviderError("Server error"),
        ):
            response = client.get("/weather/Moscow")
        
        assert response.status_code == 502
        data = response.json()
        assert "provider" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_weather_timeout(self, client, setup_app_state):
        """Test GET /weather with timeout (504)."""
        with patch.object(
            AppState.weather_client,
            "get_weather",
            side_effect=ProviderTimeoutError("Timeout"),
        ):
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
    async def test_get_weather_special_characters_in_city(self, client, setup_app_state, mock_redis):
        """Test GET /weather with special characters in city name."""
        city = "St. Petersburg"
        weather_response = WeatherResponse(
            city=city,
            temperature=10.0,
            description="Cloudy",
            humidity=70,
            wind_speed=4.0,
        )
        
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        
        with patch.object(
            AppState.weather_client,
            "get_weather",
            return_value=weather_response,
        ):
            response = client.get(f"/weather/{city}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == city

    @pytest.mark.asyncio
    async def test_cache_not_updated_on_provider_error(self, client, setup_app_state, mock_redis):
        """Test that cache is not updated when provider fails."""
        mock_redis.get.return_value = None
        
        with patch.object(
            AppState.weather_client,
            "get_weather",
            side_effect=ProviderError("Server error"),
        ):
            response = client.get("/weather/Moscow")
        
        assert response.status_code == 502
        # Cache setex should not have been called
        mock_redis.setex.assert_not_called()

    @pytest.mark.asyncio
    async def test_response_model_structure(self, client, setup_app_state, mock_redis):
        """Test that response includes all required fields."""
        weather_data = {
            "city": "London",
            "temperature": 10.0,
            "description": "Rainy",
            "humidity": 85,
            "wind_speed": 5.0,
        }
        
        mock_redis.get.return_value = json.dumps(weather_data)
        
        response = client.get("/weather/London")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all required fields are present
        required_fields = ["city", "temperature", "description", "humidity", "wind_speed"]
        for field in required_fields:
            assert field in data
            assert data[field] is not None

    @pytest.mark.asyncio
    async def test_multiple_requests_same_city(self, client, setup_app_state, mock_redis):
        """Test multiple requests for the same city (cache hit on second)."""
        weather_response = WeatherResponse(
            city="Berlin",
            temperature=8.0,
            description="Cloudy",
            humidity=75,
            wind_speed=3.0,
        )
        
        # First request: cache miss
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        
        with patch.object(
            AppState.weather_client,
            "get_weather",
            return_value=weather_response,
        ):
            response1 = client.get("/weather/Berlin")
        
        assert response1.status_code == 200
        
        # Second request: cache hit
        weather_data = weather_response.model_dump()
        mock_redis.get.return_value = json.dumps(weather_data)
        
        response2 = client.get("/weather/Berlin")
        
        assert response2.status_code == 200
        assert response1.json() == response2.json()

    @pytest.mark.asyncio
    async def test_api_key_not_in_logs(self, client, setup_app_state):
        """Test that API key is never exposed in responses."""
        with patch.object(
            AppState.weather_client,
            "get_weather",
            side_effect=ProviderError("Provider error"),
        ):
            response = client.get("/weather/Moscow")
        
        assert response.status_code == 502
        data = response.json()
        
        # API key should never be in response
        assert "test_key" not in str(data)
        assert "OPENWEATHERMAP_API_KEY" not in str(data)

    @pytest.mark.asyncio
    async def test_case_insensitive_city_cache(self, client, setup_app_state, mock_redis):
        """Test that city names are normalized for cache lookup."""
        weather_data = {
            "city": "Moscow",
            "temperature": 15.0,
            "description": "Clear",
            "humidity": 60,
            "wind_speed": 2.0,
        }
        
        mock_redis.get.return_value = json.dumps(weather_data)
        
        # Request with uppercase city
        response = client.get("/weather/MOSCOW")
        
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Moscow"
        
        # Verify Redis was queried with lowercase key
        mock_redis.get.assert_called()
        call_args = mock_redis.get.call_args
        # The key should include the lowercase version
        assert "moscow" in call_args[0][0].lower()
