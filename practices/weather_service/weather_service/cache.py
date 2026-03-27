"""Redis cache service with TTL support for weather data."""

import json
import logging
from typing import Optional
from redis import Redis, ConnectionError as RedisConnectionError
from .models import WeatherResponse

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = 10 * 60  # 10 minutes
CACHE_KEY_PREFIX = "weather:"


class CacheService:
    """
    Redis cache service for weather data with cache-aside pattern.
    
    Features:
    - Get weather data from cache
    - Set weather data with TTL=10 minutes
    - Handle cache misses gracefully
    - No secrets in logs
    """

    def __init__(self, redis_client: Redis, ttl_seconds: int = CACHE_TTL_SECONDS):
        """
        Initialize cache service.

        Args:
            redis_client: Redis client instance
            ttl_seconds: Cache TTL in seconds (default: 10 minutes)
        """
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds

    @staticmethod
    def _build_key(city: str) -> str:
        """
        Build cache key for city (use normalized city name).

        Args:
            city: Normalized city name (lowercase, trimmed)

        Returns:
            Cache key string
        """
        return f"{CACHE_KEY_PREFIX}{city.lower()}"

    async def get(self, city: str) -> Optional[WeatherResponse]:
        """
        Get weather data from cache.

        Args:
            city: City name (should be normalized by caller)

        Returns:
            WeatherResponse if found, None if cache miss or error
        """
        key = self._build_key(city)
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"Cache hit for city: {city}")
                return WeatherResponse(**data)
            logger.debug(f"Cache miss for city: {city}")
            return None
        except (RedisConnectionError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for city: {city}. Error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected cache error for city: {city}. Error: {e}")
            return None

    async def set(self, city: str, weather: WeatherResponse) -> bool:
        """
        Set weather data in cache with TTL.

        Args:
            city: City name (should be normalized by caller)
            weather: WeatherResponse object to cache

        Returns:
            True if successful, False otherwise
        """
        key = self._build_key(city)
        try:
            # Convert WeatherResponse to JSON-serializable dict
            data = weather.model_dump()
            json_data = json.dumps(data)
            
            # Set with TTL in seconds
            self.redis_client.setex(key, self.ttl_seconds, json_data)
            logger.debug(f"Cached weather for city: {city} with TTL={self.ttl_seconds}s")
            return True
        except RedisConnectionError as e:
            logger.warning(f"Cache set error for city: {city}. Connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected cache set error for city: {city}. Error: {e}")
            return False

    async def clear(self, city: str) -> bool:
        """
        Clear cache entry for a city.

        Args:
            city: City name (should be normalized by caller)

        Returns:
            True if deleted, False otherwise or if not found
        """
        key = self._build_key(city)
        try:
            result = self.redis_client.delete(key)
            logger.debug(f"Cleared cache for city: {city}")
            return bool(result)
        except Exception as e:
            logger.error(f"Cache clear error for city: {city}. Error: {e}")
            return False

    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if Redis is reachable, False otherwise
        """
        try:
            self.redis_client.ping()
            logger.debug("Redis health check passed")
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
