"""FastAPI application with weather endpoints."""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Path, Body
from fastapi.responses import JSONResponse
from redis import Redis
from .models import WeatherResponse, SubscribeRequest, SubscriptionResponse, Subscription, WeatherHistoryEntry, HISTORY_MAX_SIZE
from .openweather_client import (
    OpenWeatherMapClient,
    CityNotFoundError,
    RateLimitedError,
    ProviderError,
    TimeoutError as ProviderTimeoutError,
    OpenWeatherMapError,
)
from .cache import CacheService

# Configure logging without exposing secrets
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AppState:
    """Application state container."""

    cache_service: CacheService | None = None
    weather_client: OpenWeatherMapClient | None = None
    redis_client: Redis | None = None
    subscriptions: dict[str, Subscription] = {}
    weather_history: dict[str, list[WeatherHistoryEntry]] = {}


def _record_history(normalized_city: str, weather: WeatherResponse) -> None:
    """Record a successful weather response in in-memory history (FIFO, max HISTORY_MAX_SIZE per city).

    Fire-and-forget: errors are logged but never propagate to the caller.
    Per D-01, D-02, D-05.
    """
    try:
        entry = WeatherHistoryEntry(**weather.model_dump())
        history = AppState.weather_history.setdefault(normalized_city, [])
        history.append(entry)
        if len(history) > HISTORY_MAX_SIZE:
            history.pop(0)  # Remove oldest entry (FIFO per D-02)
    except Exception as exc:
        logger.warning(f"Failed to record weather history for city '{normalized_city}': {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup/shutdown.
    
    Startup:
    - Initialize Redis connection
    - Initialize cache service
    - Initialize OpenWeatherMap client
    
    Shutdown:
    - Clean up resources
    """
    # Startup
    logger.info("Starting up Weather Service...")
    
    try:
        # Get configuration from environment
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        
        if not api_key:
            logger.error("OPENWEATHERMAP_API_KEY environment variable not set")
            raise RuntimeError("OPENWEATHERMAP_API_KEY not configured")
        
        # Initialize Redis
        try:
            redis_client = Redis.from_url(redis_url, decode_responses=True)
            redis_client.ping()
            logger.info("Redis connection established")
            AppState.redis_client = redis_client
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Cache will be unavailable.")
            AppState.redis_client = None
        
        # Initialize cache service
        if AppState.redis_client:
            AppState.cache_service = CacheService(AppState.redis_client)
        
        # Initialize OpenWeatherMap client
        AppState.weather_client = OpenWeatherMapClient(
            api_key=api_key,
            timeout_seconds=5.0,
        )
        
        logger.info("Weather Service startup complete")
    
    except Exception as e:
        logger.error(f"Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Weather Service...")
    try:
        if AppState.redis_client:
            AppState.redis_client.close()
        logger.info("Cleanup complete")
    except Exception as e:
        logger.error(f"Shutdown error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Weather Service",
    description="REST API for current weather with Redis cache-aside pattern",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    health_status = {
        "status": "ok",
        "cache_available": bool(AppState.cache_service),
        "weather_client_ready": bool(AppState.weather_client),
    }
    return health_status


@app.get(
    "/weather/{city}",
    response_model=WeatherResponse,
    status_code=200,
    tags=["Weather"],
    responses={
        200: {"description": "Weather data retrieved successfully"},
        404: {"description": "City not found"},
        503: {"description": "OpenWeatherMap service unavailable or rate limited"},
        504: {"description": "Request timeout"},
        422: {"description": "Invalid city parameter"},
    },
)
async def get_weather(
    city: str = Path(
        ...,
        description="City name",
        min_length=1,
        max_length=100,
        examples=["Moscow"],
    ),
) -> WeatherResponse:
    """
    Get current weather for a city using cache-aside pattern.
    
    **Cache-aside pattern:**
    1. Try to read from Redis cache
    2. On cache miss, fetch from OpenWeatherMap API
    3. Cache the result with TTL=10 minutes
    4. Return the weather data
    
    **Error handling:**
    - City not found (404 from OWM) → 404 Not Found
    - Rate limited (429 from OWM) → 503 Service Unavailable
    - Server error (5xx from OWM) → 502 Bad Gateway
    - Timeout → 504 Gateway Timeout
    
    **Security:**
    - API_KEY is not exposed in responses or logs
    - Only normalized city name in cache keys
    
    Args:
        city: City name to get weather for
    
    Returns:
        WeatherResponse with weather data
    
    Raises:
        HTTPException: For various error conditions
    """
    
    # Validate inputs
    if not city or not city.strip():
        logger.warning("Empty city parameter in request")
        raise HTTPException(
            status_code=422,
            detail="City cannot be empty",
        )
    
    # Normalize city for cache lookup
    normalized_city = city.strip().lower()
    
    try:
        # Step 1: Try cache-aside - read from cache first
        if AppState.cache_service:
            cached_weather = await AppState.cache_service.get(normalized_city)
            if cached_weather:
                logger.info(f"Returning cached weather for city: {city}")
                _record_history(normalized_city, cached_weather)
                return cached_weather
        
        # Step 2: Cache miss - fetch from OpenWeatherMap
        if not AppState.weather_client:
            logger.error("Weather client not initialized")
            raise HTTPException(
                status_code=503,
                detail="Weather service temporarily unavailable",
            )
        
        logger.info(f"Fetching weather from OpenWeatherMap for city: {city}")
        weather = await AppState.weather_client.get_weather(city)
        
        # Step 3: Cache the result (fire and forget - don't fail if cache fails)
        if AppState.cache_service:
            await AppState.cache_service.set(normalized_city, weather)
        
        logger.info(f"Weather retrieved successfully for city: {city}")
        _record_history(normalized_city, weather)
        return weather
    
    except CityNotFoundError:
        logger.info(f"City not found: {city}")
        raise HTTPException(
            status_code=404,
            detail=f"City '{city}' not found",
        )
    
    except RateLimitedError:
        logger.warning(f"Rate limited by OpenWeatherMap for city: {city}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable (rate limited)",
        )
    
    except ProviderError:
        logger.error(f"OpenWeatherMap server error for city: {city}")
        raise HTTPException(
            status_code=502,
            detail="Weather provider error",
        )
    
    except ProviderTimeoutError:
        logger.error(f"Timeout fetching weather for city: {city}")
        raise HTTPException(
            status_code=504,
            detail="Request timeout",
        )
    
    except OpenWeatherMapError as e:
        logger.error(f"OpenWeatherMap error for city: {city}. Error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Weather service error",
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (already handled above)
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error fetching weather for city: {city}. Error: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@app.post(
    "/subscribe",
    response_model=SubscriptionResponse,
    status_code=201,
    tags=["Subscriptions"],
    responses={
        201: {"description": "Subscription created successfully"},
        404: {"description": "City not found"},
        409: {"description": "Subscription already exists for this email and city"},
        502: {"description": "Weather provider error"},
        503: {"description": "Service unavailable or rate limited"},
        504: {"description": "Request timeout"},
        422: {"description": "Invalid request body"},
    },
)
async def subscribe(
    request_body: SubscribeRequest = Body(
        ...,
        description="Subscription request with city, email, and channel",
    ),
) -> SubscriptionResponse:
    """
    Subscribe to weather updates for a city (POST /subscribe).
    
    **Request validation (Pydantic v2):**
    - city: trim + not empty + max 100 chars
    - email: valid email address
    - channel: Literal["email"] (only "email" is supported)
    
    **Logic:**
    1. Normalize city: city.strip()
    2. Check city existence via AppState.weather_client.get_weather(city)
       - CityNotFoundError → 404
       - RateLimitedError → 503
       - ProviderError → 502
       - TimeoutError → 504
    3. Check subscription uniqueness by (email, city_normalized)
       - If exists → 409 Conflict
    4. Save subscription in AppState.subscriptions
    5. Return 201 with {id, city, email, channel, created_at}
    
    Args:
        request_body: SubscribeRequest with city, email, channel
    
    Returns:
        SubscriptionResponse (201 Created) with subscription details
    
    Raises:
        HTTPException: For various error conditions
    """
    
    # Step 1: Normalize city (trim whitespace)
    normalized_city = request_body.city.strip()
    city_normalized_lower = normalized_city.lower()
    email_lower = request_body.email.lower()
    
    try:
        # Step 2: Verify city exists via OpenWeatherMap API
        if not AppState.weather_client:
            logger.error("Weather client not initialized")
            raise HTTPException(
                status_code=503,
                detail="Weather service temporarily unavailable",
            )
        
        logger.info(f"Verifying city existence for subscription: {normalized_city}")
        await AppState.weather_client.get_weather(normalized_city)
        
        # Step 3: Check if subscription already exists by (email, city_normalized)
        for sub in AppState.subscriptions.values():
            if (
                sub.email.lower() == email_lower
                and sub.city_normalized.lower() == city_normalized_lower
            ):
                logger.warning(
                    f"Subscription already exists for city_normalized: {city_normalized_lower}"
                )
                raise HTTPException(
                    status_code=409,
                    detail="Subscription already exists for this email and city",
                )
        
        # Step 4: Create subscription
        subscription = Subscription(
            city=normalized_city,
            city_normalized=city_normalized_lower,
            email=email_lower,
            channel=request_body.channel,
        )
        
        # Step 5: Store subscription in AppState
        AppState.subscriptions[subscription.id] = subscription
        logger.info(
            f"Subscription created: id={subscription.id}, city={normalized_city}, "
            f"city_normalized={city_normalized_lower}"
        )
        
        # Return subscription response
        return SubscriptionResponse(
            id=subscription.id,
            city=subscription.city,
            email=subscription.email,
            channel=subscription.channel,
            created_at=subscription.created_at,
        )
    
    except CityNotFoundError:
        logger.info(f"City not found in subscription request: {normalized_city}")
        raise HTTPException(
            status_code=404,
            detail=f"City '{normalized_city}' not found",
        )
    
    except RateLimitedError:
        logger.warning(f"Rate limited by OpenWeatherMap: {normalized_city}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable (rate limited)",
        )
    
    except ProviderError:
        logger.error(f"OpenWeatherMap server error: {normalized_city}")
        raise HTTPException(
            status_code=502,
            detail="Weather provider error",
        )
    
    except ProviderTimeoutError:
        logger.error(f"Timeout verifying city for subscription: {normalized_city}")
        raise HTTPException(
            status_code=504,
            detail="Request timeout",
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions (already handled above)
        raise
    
    except OpenWeatherMapError as e:
        logger.error(
            f"OpenWeatherMap error for subscription: {normalized_city}. Error: {e}"
        )
        raise HTTPException(
            status_code=503,
            detail="Weather service error",
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in subscription: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )


@app.delete(
    "/subscribe/{id}",
    status_code=204,
    tags=["Subscriptions"],
    responses={
        204: {"description": "Subscription deleted successfully"},
        404: {"description": "Subscription not found"},
    },
)
async def delete_subscribe(
    subscription_id: str = Path(
        ...,
        alias="id",
        description="Subscription unique identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    ),
):
    """
    Delete a subscription by ID (DELETE /subscribe/{id}).
    
    **Logic:**
    1. Find subscription by id in AppState.subscriptions
       - If not found → 404 Not Found
    2. Delete from AppState.subscriptions
    3. Return 204 No Content
    
    Args:
        id: Subscription ID to delete
    
    Returns:
        204 No Content on success
    
    Raises:
        HTTPException: 404 if subscription not found
    """
    
    # Step 1: Check if subscription exists
    if subscription_id not in AppState.subscriptions:
        logger.warning(f"Subscription not found for deletion: id={subscription_id}")
        raise HTTPException(
            status_code=404,
            detail=f"Subscription with id '{subscription_id}' not found",
        )

    # Step 2: Delete subscription
    subscription = AppState.subscriptions.pop(subscription_id)
    logger.info(
        f"Subscription deleted: id={id}, city={subscription.city}, "
        f"email={subscription.email}"
    )
    
    # Step 3: Return 204 No Content
    return None


@app.get(
    "/weather/{city}/history",
    response_model=list[WeatherHistoryEntry],
    status_code=200,
    tags=["Weather"],
    responses={
        200: {"description": "Weather history for city (empty list if no history)"},
        422: {"description": "Invalid city parameter"},
    },
)
async def get_weather_history(
    city: str = Path(
        ...,
        description="City name",
        min_length=1,
        max_length=100,
        examples=["Moscow"],
    ),
) -> list[WeatherHistoryEntry]:
    """
    Return in-memory history of weather requests for a city (last HISTORY_MAX_SIZE entries).

    **Behavior:**
    - Returns [] if the city has never been queried (per D-07)
    - City is normalized (strip + lowercase) for lookup (per D-08)
    - Does not call OpenWeatherMap or Redis

    Args:
        city: City name

    Returns:
        list[WeatherHistoryEntry] — from oldest to newest, max HISTORY_MAX_SIZE entries
    """
    normalized_city = city.strip().lower()
    return AppState.weather_history.get(normalized_city, [])


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom HTTP exception handler to ensure consistent error responses."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "weather_service.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
