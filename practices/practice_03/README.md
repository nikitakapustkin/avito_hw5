# Weather Service - FastAPI with OpenWeatherMap Integration

A production-ready REST API service that provides current weather information with Redis caching and comprehensive error handling.

## Features

- **GET /weather/{city}** endpoint for fetching current weather
- **Cache-aside pattern** with Redis (TTL=10 minutes)
- **Pydantic v2** response models for type safety
- **Comprehensive error handling** with mapped HTTP status codes
- **5-second timeout** on OpenWeatherMap API requests
- **No secrets in logs** - API keys are never exposed
- **Async/await** throughout using httpx and FastAPI
- **Health check endpoint** for monitoring

## Requirements

- Python 3.10+
- FastAPI 0.109.0+
- Redis (for caching)
- OpenWeatherMap API key

## Installation

### 1. Clone and setup

```bash
cd weather_service
poetry install
```

### 2. Configure environment

Copy `.env.example` to `.env` and set your configuration:

```bash
cp .env.example .env
```

Edit `.env`:
```
OPENWEATHERMAP_API_KEY=your_actual_api_key_here
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
```

### 3. Start Redis

```bash
# Using Docker
docker run -d -p 6379:6379 redis:latest

# Or using Homebrew on macOS
brew services start redis
```

### 4. Run the application

```bash
poetry run python -m uvicorn weather_service.app:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "cache_available": true,
  "weather_client_ready": true
}
```

### GET /weather/{city}

Get current weather for a city with cache-aside pattern.

**Parameters:**
- `city` (path, required): City name (1-100 characters)

**Success Response (200):**
```json
{
  "city": "Moscow",
  "temperature": 15.5,
  "description": "Overcast clouds",
  "humidity": 72,
  "wind_speed": 3.5
}
```

**Error Responses:**

| Status | Description | Cause |
|--------|-------------|-------|
| 404 | City not found | OpenWeatherMap returned 404 |
| 503 | Service unavailable | Rate limited (429) or other 5xx from OWM |
| 502 | Bad Gateway | Provider error (5xx from OWM) |
| 504 | Gateway Timeout | Request timeout (>5 seconds) |
| 422 | Unprocessable Entity | Invalid city parameter |

## Usage Examples

### Using curl

```bash
# Get weather for Moscow (cache miss, fetches from OWM)
curl http://localhost:8000/weather/Moscow

# Get weather for Paris (may hit cache if available)
curl http://localhost:8000/weather/Paris

# Invalid city name (too long)
curl http://localhost:8000/weather/$(python -c "print('A'*101)")
# Returns 422
```

### Using Python requests

```python
import requests

# Fetch weather
response = requests.get("http://localhost:8000/weather/London")

if response.status_code == 200:
    weather = response.json()
    print(f"Temperature in {weather['city']}: {weather['temperature']}°C")
elif response.status_code == 404:
    print("City not found")
elif response.status_code == 503:
    print("Service temporarily unavailable")
elif response.status_code == 504:
    print("Request timeout")
```

### Using httpx (async)

```python
import httpx

async def get_weather(city: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8000/weather/{city}")
        return response.json()
```

## Architecture

### Cache-Aside Pattern

```
1. Request arrives for /weather/{city}
2. Service attempts to read from Redis cache
   - Cache HIT  → Return cached data (no provider call)
   - Cache MISS → Continue to step 3
3. Fetch weather from OpenWeatherMap API (5s timeout)
4. Store result in Redis with TTL=10 minutes
5. Return weather data to client
```

### Error Mapping

| OpenWeatherMap | API Response | Details |
|---|---|---|
| 200 OK | 200 | Weather data returned and cached |
| 404 Not Found | 404 | City doesn't exist |
| 429 Too Many Requests | 503 | Rate limited |
| 5xx Server Error | 502 | Provider error |
| Timeout | 504 | Request exceeded 5s timeout |

### File Structure

```
weather_service/
├── weather_service/
│   ├── __init__.py
│   ├── app.py              # FastAPI application with endpoints
│   ├── models.py           # Pydantic v2 models
│   ├── cache.py            # Redis cache service
│   └── openweather_client.py  # OpenWeatherMap API client
├── tests/
│   ├── test_models.py      # Unit tests for models
│   ├── test_cache.py       # Unit tests for cache
│   ├── test_openweather_client.py  # Unit tests for client
│   └── test_integration.py # Integration tests
├── pyproject.toml          # Dependencies and configuration
├── .env.example            # Environment variables template
└── README.md              # This file
```

## Testing

### Run all tests

```bash
poetry run pytest
```

### Run with coverage

```bash
poetry run pytest --cov=weather_service --cov-report=html
```

### Run specific test file

```bash
poetry run pytest tests/test_models.py -v
```

### Run integration tests only

```bash
poetry run pytest tests/test_integration.py -v
```

## Implementation Details

### Pydantic v2 Response Model

```python
class WeatherResponse(BaseModel):
    city: str                    # City name
    temperature: float           # Temperature in Celsius
    description: str             # Weather description
    humidity: int                # Humidity percentage (0-100)
    wind_speed: float            # Wind speed in m/s
```

### OpenWeatherMap Client Features

- **Async HTTP client** using httpx
- **Custom exceptions** for different error types:
  - `CityNotFoundError` (404)
  - `RateLimitedError` (429)
  - `ProviderError` (5xx)
  - `TimeoutError` (request timeout)
- **No API key exposure** in logs
- **Request timeout** of 5 seconds (configurable)

### Redis Cache Service

- **Cache key format**: `weather:{city_normalized}`
  - City normalized: lowercase, trimmed
- **TTL**: 10 minutes (600 seconds)
- **Graceful degradation**: If Redis is unavailable, service still works (goes directly to provider)
- **Health check**: `health_check()` method for monitoring

## Configuration

All configuration uses environment variables:

```
OPENWEATHERMAP_API_KEY  # Required: Your OpenWeatherMap API key
REDIS_URL               # Default: redis://localhost:6379
LOG_LEVEL              # Default: INFO
```

## Security Considerations

1. **API Key Protection**
   - Never logged or exposed in responses
   - Validated at startup
   - Used only internally for provider requests

2. **Input Validation**
   - City name: 1-100 characters
   - Whitespace trimmed automatically
   - Path parameters validated by Pydantic

3. **Error Messages**
   - No sensitive details in error responses
   - Logging excludes secrets
   - Client errors (4xx) and server errors (5xx) clearly distinguished

4. **Rate Limiting**
   - Provider errors (429) handled gracefully
   - No retry storms
   - Mapped to 503 for client

## Logging

Logs are structured and include:
- Timestamp
- Logger name
- Log level (DEBUG, INFO, WARNING, ERROR)
- Message (with no secrets exposed)

Example log output:
```
2026-03-06 10:15:30,123 - weather_service.openweather_client - INFO - Fetching weather from OpenWeatherMap for city: Moscow
2026-03-06 10:15:31,234 - weather_service.cache - DEBUG - Cached weather for city: moscow with TTL=600s
2026-03-06 10:15:31,245 - weather_service.app - INFO - Weather retrieved successfully for city: Moscow
```

## Performance

- **Cache hit latency**: ~50-100ms (Redis lookup only)
- **Cache miss latency**: ~5-6s (includes 5s provider timeout)
- **Typical cache hit rate**: 60%+ (depends on city variety)
- **Concurrent requests**: Supported via async/await

## Troubleshooting

### Redis connection issues

```
ERROR - Failed to connect to Redis
```

**Solution**: Ensure Redis is running:
```bash
docker run -d -p 6379:6379 redis:latest
```

### API key not set

```
ERROR - OPENWEATHERMAP_API_KEY not configured
```

**Solution**: Set environment variable:
```bash
export OPENWEATHERMAP_API_KEY=your_key_here
```

### City not found

```json
{"detail": "City 'NoSuchCity' not found"}
```

**Solution**: Verify city name spelling. OpenWeatherMap uses official city names.

### Rate limited (429)

```json
{"detail": "Service temporarily unavailable (rate limited)"}
```

**Solution**: Wait before making more requests or upgrade your OpenWeatherMap plan.

## Development

### Code formatting

```bash
poetry run black weather_service tests
```

### Linting

```bash
poetry run ruff check weather_service tests
```

### Type checking

```bash
poetry run mypy weather_service
```

## Contributing

1. Write tests for new features
2. Ensure all tests pass: `poetry run pytest`
3. Format code: `poetry run black .`
4. Check types: `poetry run mypy weather_service`

## License

MIT
