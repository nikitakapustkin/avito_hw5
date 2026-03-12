"""Unit tests for Redis cache service."""

import json
import pytest
from unittest.mock import MagicMock, AsyncMock
from redis import ConnectionError as RedisConnectionError
from weather_service.cache import CacheService, CACHE_KEY_PREFIX, CACHE_TTL_SECONDS
from weather_service.models import WeatherResponse


class TestCacheService:
    """Tests for CacheService."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        return MagicMock()

    @pytest.fixture
    def cache_service(self, mock_redis):
        """Create a cache service with mock Redis."""
        return CacheService(mock_redis, ttl_seconds=600)

    @pytest.fixture
    def sample_weather(self):
        """Sample weather response."""
        return WeatherResponse(
            city="Moscow",
            temperature=15.5,
            description="Overcast clouds",
            humidity=72,
            wind_speed=3.5,
        )

    def test_build_key(self):
        """Test cache key generation."""
        key = CacheService._build_key("Moscow")
        assert key == f"{CACHE_KEY_PREFIX}moscow"

    def test_build_key_case_insensitive(self):
        """Test cache key is lowercase."""
        key1 = CacheService._build_key("MOSCOW")
        key2 = CacheService._build_key("moscow")
        assert key1 == key2

    @pytest.mark.asyncio
    async def test_get_cache_hit(self, cache_service, mock_redis, sample_weather):
        """Test successful cache get (cache hit)."""
        data = sample_weather.model_dump()
        mock_redis.get.return_value = json.dumps(data)

        result = await cache_service.get("Moscow")

        assert result is not None
        assert result.city == "Moscow"
        assert result.temperature == 15.5
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cache_miss(self, cache_service, mock_redis):
        """Test cache get on miss (no data in cache)."""
        mock_redis.get.return_value = None

        result = await cache_service.get("Moscow")

        assert result is None
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection_error(self, cache_service, mock_redis):
        """Test cache get with Redis connection error."""
        mock_redis.get.side_effect = RedisConnectionError("Connection refused")

        result = await cache_service.get("Moscow")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_json_decode_error(self, cache_service, mock_redis):
        """Test cache get with invalid JSON."""
        mock_redis.get.return_value = "invalid json {["

        result = await cache_service.get("Moscow")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_unexpected_error(self, cache_service, mock_redis):
        """Test cache get with unexpected error."""
        mock_redis.get.side_effect = Exception("Unexpected error")

        result = await cache_service.get("Moscow")

        assert result is None

    @pytest.mark.asyncio
    async def test_set_success(self, cache_service, mock_redis, sample_weather):
        """Test successful cache set."""
        mock_redis.setex.return_value = True

        result = await cache_service.set("Moscow", sample_weather)

        assert result is True
        mock_redis.setex.assert_called_once()
        
        # Verify TTL is set correctly
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 600  # TTL in seconds

    @pytest.mark.asyncio
    async def test_set_connection_error(self, cache_service, mock_redis, sample_weather):
        """Test cache set with Redis connection error."""
        mock_redis.setex.side_effect = RedisConnectionError("Connection refused")

        result = await cache_service.set("Moscow", sample_weather)

        assert result is False

    @pytest.mark.asyncio
    async def test_set_unexpected_error(self, cache_service, mock_redis, sample_weather):
        """Test cache set with unexpected error."""
        mock_redis.setex.side_effect = Exception("Unexpected error")

        result = await cache_service.set("Moscow", sample_weather)

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_success(self, cache_service, mock_redis):
        """Test successful cache clear."""
        mock_redis.delete.return_value = 1

        result = await cache_service.clear("Moscow")

        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_not_found(self, cache_service, mock_redis):
        """Test cache clear when key doesn't exist."""
        mock_redis.delete.return_value = 0

        result = await cache_service.clear("Moscow")

        assert result is False

    @pytest.mark.asyncio
    async def test_clear_error(self, cache_service, mock_redis):
        """Test cache clear with error."""
        mock_redis.delete.side_effect = Exception("Error")

        result = await cache_service.clear("Moscow")

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_success(self, cache_service, mock_redis):
        """Test successful health check."""
        mock_redis.ping.return_value = True

        result = await cache_service.health_check()

        assert result is True
        mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, cache_service, mock_redis):
        """Test health check failure."""
        mock_redis.ping.side_effect = Exception("Connection error")

        result = await cache_service.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_round_trip_cache_set_get(self, cache_service, mock_redis, sample_weather):
        """Test setting and then getting from cache."""
        data = sample_weather.model_dump()
        
        # First set in cache
        await cache_service.set("Moscow", sample_weather)
        
        # Then mock return on get
        mock_redis.get.return_value = json.dumps(data)
        result = await cache_service.get("Moscow")

        assert result is not None
        assert result.city == "Moscow"
        assert result.temperature == 15.5

    @pytest.mark.asyncio
    async def test_ttl_configuration(self, mock_redis):
        """Test custom TTL configuration."""
        custom_ttl = 3600
        cache_service = CacheService(mock_redis, ttl_seconds=custom_ttl)
        sample_weather = WeatherResponse(
            city="Moscow",
            temperature=15.5,
            description="Overcast",
            humidity=72,
            wind_speed=3.5,
        )

        await cache_service.set("Moscow", sample_weather)

        # Verify TTL is custom value
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600

    @pytest.mark.asyncio
    async def test_normalized_city_handling(self, cache_service, mock_redis):
        """Test that city names are normalized in cache keys."""
        data = WeatherResponse(
            city="St. Petersburg",
            temperature=10.0,
            description="Rain",
            humidity=80,
            wind_speed=4.0,
        )
        
        # All these should map to the same cache key
        key1 = CacheService._build_key("St. Petersburg")
        key2 = CacheService._build_key("ST. PETERSBURG")
        key3 = CacheService._build_key("st. petersburg")
        
        assert key1 == key2 == key3
