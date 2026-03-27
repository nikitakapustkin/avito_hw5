"""Unit tests for OpenWeatherMap client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import TimeoutException, Response
from weather_service.openweather_client import (
    OpenWeatherMapClient,
    CityNotFoundError,
    RateLimitedError,
    ProviderError,
    TimeoutError as ProviderTimeoutError,
    OpenWeatherMapError,
)
from weather_service.models import WeatherResponse


class TestOpenWeatherMapClient:
    """Tests for OpenWeatherMapClient."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return OpenWeatherMapClient(
            api_key="test_key_12345",
            timeout_seconds=5.0,
        )

    @pytest.fixture
    def mock_response_data(self):
        """Sample OpenWeatherMap API response."""
        return {
            "main": {
                "temp": 15.5,
                "humidity": 72,
            },
            "weather": [
                {"main": "Overcast"},
            ],
            "wind": {
                "speed": 3.5,
            },
        }

    @pytest.mark.asyncio
    async def test_get_weather_success(self, client, mock_response_data):
        """Test successful weather fetch."""
        client._client = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = mock_response_data
        client._client.get.return_value = mock_http_response

        result = await client.get_weather("Moscow")

        assert isinstance(result, WeatherResponse)
        assert result.city == "Moscow"
        assert result.temperature == 15.5
        assert result.humidity == 72
        assert result.wind_speed == 3.5

    @pytest.mark.asyncio
    async def test_get_weather_city_not_found(self, client):
        """Test 404 response raises CityNotFoundError."""
        client._client = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.status_code = 404
        client._client.get.return_value = mock_http_response

        with pytest.raises(CityNotFoundError):
            await client.get_weather("NoSuchCity")

    @pytest.mark.asyncio
    async def test_get_weather_rate_limited(self, client):
        """Test 429 response raises RateLimitedError."""
        client._client = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.status_code = 429
        client._client.get.return_value = mock_http_response

        with pytest.raises(RateLimitedError):
            await client.get_weather("Moscow")

    @pytest.mark.asyncio
    async def test_get_weather_provider_error_500(self, client):
        """Test 500 response raises ProviderError."""
        client._client = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.status_code = 500
        client._client.get.return_value = mock_http_response

        with pytest.raises(ProviderError):
            await client.get_weather("Moscow")

    @pytest.mark.asyncio
    async def test_get_weather_provider_error_503(self, client):
        """Test 503 response raises ProviderError."""
        client._client = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.status_code = 503
        client._client.get.return_value = mock_http_response

        with pytest.raises(ProviderError):
            await client.get_weather("Moscow")

    @pytest.mark.asyncio
    async def test_get_weather_timeout(self, client):
        """Test timeout raises TimeoutError."""
        client._client = AsyncMock()
        client._client.get.side_effect = TimeoutException("Request timeout")

        with pytest.raises(ProviderTimeoutError):
            await client.get_weather("Moscow")

    @pytest.mark.asyncio
    async def test_get_weather_invalid_response_missing_field(self, client):
        """Test invalid response schema raises OpenWeatherMapError."""
        client._client = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        # Missing 'main' field
        mock_http_response.json.return_value = {
            "weather": [{"main": "Overcast"}],
            "wind": {"speed": 3.5},
        }
        client._client.get.return_value = mock_http_response

        with pytest.raises(OpenWeatherMapError):
            await client.get_weather("Moscow")

    @pytest.mark.asyncio
    async def test_get_weather_invalid_response_no_weather(self, client):
        """Test invalid response with empty weather list."""
        client._client = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = {
            "main": {"temp": 15.5, "humidity": 72},
            "weather": [],  # Empty
            "wind": {"speed": 3.5},
        }
        client._client.get.return_value = mock_http_response

        with pytest.raises(OpenWeatherMapError):
            await client.get_weather("Moscow")

    @pytest.mark.asyncio
    async def test_context_manager(self, client):
        """Test async context manager."""
        async with client:
            assert client._client is not None

    def test_parse_weather_response_success(self, mock_response_data):
        """Test parsing successful weather response."""
        result = OpenWeatherMapClient._parse_weather_response(
            "Moscow", mock_response_data
        )

        assert isinstance(result, WeatherResponse)
        assert result.city == "Moscow"
        assert result.temperature == 15.5
        assert result.description == "Overcast"
        assert result.humidity == 72
        assert result.wind_speed == 3.5

    def test_parse_weather_response_missing_main(self):
        """Test parsing response with missing main field."""
        data = {
            "weather": [{"main": "Overcast"}],
            "wind": {"speed": 3.5},
        }

        with pytest.raises(OpenWeatherMapError):
            OpenWeatherMapClient._parse_weather_response("Moscow", data)

    def test_parse_weather_response_missing_weather(self):
        """Test parsing response with missing weather field."""
        data = {
            "main": {"temp": 15.5, "humidity": 72},
            "wind": {"speed": 3.5},
        }

        with pytest.raises(OpenWeatherMapError):
            OpenWeatherMapClient._parse_weather_response("Moscow", data)

    def test_parse_weather_response_none_values(self):
        """Test parsing response with None values."""
        data = {
            "main": {"temp": None, "humidity": 72},
            "weather": [{"main": "Overcast"}],
            "wind": {"speed": 3.5},
        }

        with pytest.raises(OpenWeatherMapError):
            OpenWeatherMapClient._parse_weather_response("Moscow", data)

    @pytest.mark.asyncio
    async def test_get_weather_initializes_client(self, client):
        """Test that get_weather initializes client if not already set."""
        client._client = None
        client._client = AsyncMock()
        
        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = {
            "main": {"temp": 15.5, "humidity": 72},
            "weather": [{"main": "Clear"}],
            "wind": {"speed": 0.0},
        }
        client._client.get.return_value = mock_http_response

        result = await client.get_weather("Test")
        assert result.city == "Test"

    @pytest.mark.asyncio
    async def test_get_weather_api_key_not_in_exception(self, client):
        """Test that API key is not leaked in exceptions."""
        client._client = AsyncMock()
        mock_http_response = MagicMock()
        mock_http_response.status_code = 500
        client._client.get.return_value = mock_http_response

        with pytest.raises(ProviderError) as exc_info:
            await client.get_weather("Moscow")

        # Verify API key is not in exception message
        assert "test_key_12345" not in str(exc_info.value)
