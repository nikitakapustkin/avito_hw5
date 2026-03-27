"""OpenWeatherMap API client with error handling and timeout management."""

import logging
from typing import Optional
from httpx import AsyncClient, TimeoutException, HTTPStatusError
from .models import WeatherResponse

logger = logging.getLogger(__name__)


class OpenWeatherMapError(Exception):
    """Base exception for OpenWeatherMap client."""

    pass


class CityNotFoundError(OpenWeatherMapError):
    """Raised when city is not found (404 from provider)."""

    pass


class RateLimitedError(OpenWeatherMapError):
    """Raised when rate limit is exceeded (429 from provider)."""

    pass


class ProviderError(OpenWeatherMapError):
    """Raised when provider returns 5xx error."""

    pass


class TimeoutError(OpenWeatherMapError):
    """Raised when provider request times out."""

    pass


class OpenWeatherMapClient:
    """
    Async client for OpenWeatherMap API.
    
    Handles:
    - 404 (city not found) -> CityNotFoundError
    - 429 (rate limited) -> RateLimitedError
    - 5xx (server error) -> ProviderError
    - Timeout -> TimeoutError
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openweathermap.org/data/2.5",
        timeout_seconds: float = 5.0,
    ):
        """
        Initialize OpenWeatherMap client.

        Args:
            api_key: OpenWeatherMap API key (from OPENWEATHERMAP_API_KEY env var)
            base_url: Base URL for OpenWeatherMap API
            timeout_seconds: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds
        self._client: Optional[AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = AsyncClient(timeout=self.timeout_seconds)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def get_weather(self, city: str) -> WeatherResponse:
        """
        Fetch weather for a city from OpenWeatherMap API.

        Args:
            city: City name

        Returns:
            WeatherResponse with weather data

        Raises:
            CityNotFoundError: If city not found (404)
            RateLimitedError: If rate limited (429)
            ProviderError: If provider returns 5xx
            TimeoutError: If request times out
            OpenWeatherMapError: For other errors
        """
        if not self._client:
            self._client = AsyncClient(timeout=self.timeout_seconds)

        endpoint = f"{self.base_url}/weather"
        params = {
            "q": city,
            "appid": self.api_key,
            "units": "metric",
        }

        try:
            response = await self._client.get(endpoint, params=params)

            # Handle specific status codes
            if response.status_code == 404:
                logger.warning(f"City not found: {city}")
                raise CityNotFoundError(f"City '{city}' not found")

            if response.status_code == 429:
                logger.warning(
                    f"Rate limit exceeded for city: {city}. "
                    "Details not logged to prevent spam."
                )
                raise RateLimitedError("OpenWeatherMap API rate limit exceeded")

            if response.status_code >= 500:
                logger.error(
                    f"OpenWeatherMap provider error. Status: {response.status_code}. "
                    f"City: {city}"
                )
                raise ProviderError(
                    f"OpenWeatherMap API error: {response.status_code}"
                )

            # Raise for other 4xx/5xx
            response.raise_for_status()

            # Parse successful response
            data = response.json()
            return self._parse_weather_response(city, data)

        except TimeoutException as e:
            logger.error(f"Timeout fetching weather for city: {city}")
            raise TimeoutError(f"Request timeout for city '{city}'") from e
        except (CityNotFoundError, RateLimitedError, ProviderError, TimeoutError):
            # Re-raise custom exceptions
            raise
        except HTTPStatusError as e:
            # Already logged above, re-raise as generic error
            logger.error(f"HTTP error for city: {city}. Status: {e.response.status_code}")
            raise OpenWeatherMapError(f"HTTP error: {e.response.status_code}") from e
        except Exception as e:
            logger.error(f"Unexpected error fetching weather for city: {city}. Error: {e}")
            raise OpenWeatherMapError(f"Unexpected error: {str(e)}") from e

    @staticmethod
    def _parse_weather_response(city: str, data: dict) -> WeatherResponse:
        """
        Parse OpenWeatherMap JSON response into WeatherResponse model.

        Args:
            city: City name (already normalized by caller)
            data: JSON response from OpenWeatherMap API

        Returns:
            WeatherResponse model instance

        Raises:
            OpenWeatherMapError: If response schema is unexpected
        """
        try:
            main = data.get("main", {})
            weather_list = data.get("weather", [])
            wind = data.get("wind", {})

            # Check if weather list is empty or missing
            if not weather_list:
                raise ValueError("Missing 'weather' field in provider response")
            
            weather = weather_list[0]

            temperature = main.get("temp")
            description = weather.get("main", "")
            humidity = main.get("humidity")
            wind_speed = wind.get("speed")

            if any(v is None for v in [temperature, description, humidity, wind_speed]):
                raise ValueError("Missing required fields in provider response")

            return WeatherResponse(
                city=city,
                temperature=float(temperature),
                description=str(description),
                humidity=int(humidity),
                wind_speed=float(wind_speed),
            )
        except (KeyError, ValueError, IndexError) as e:
            logger.error(
                f"Failed to parse weather response for city: {city}. Error: {e}"
            )
            raise OpenWeatherMapError(
                f"Invalid response schema from provider: {str(e)}"
            ) from e
