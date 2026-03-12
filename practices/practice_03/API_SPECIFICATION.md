# Weather Service API Specification

## Overview

The Weather Service API provides real-time weather information with intelligent caching and robust error handling.

**Base URL**: `http://localhost:8000`  
**API Version**: 1.0  
**Content-Type**: `application/json`

## Endpoints

### 1. Health Check

Check if the service is running and ready.

```
GET /health
```

**Response** (200 OK):
```json
{
  "status": "ok",
  "cache_available": true,
  "weather_client_ready": true
}
```

**Fields**:
- `status`: Service status ("ok" or error description)
- `cache_available`: Whether Redis cache is connected
- `weather_client_ready`: Whether OpenWeatherMap client is initialized

---

### 2. Get Current Weather

Fetch current weather for a city using cache-aside pattern.

```
GET /weather/{city}
```

**Path Parameters**:

| Parameter | Type | Required | Rules | Example |
|-----------|------|----------|-------|---------|
| `city` | string | Yes | 1-100 characters, non-empty after trim | Moscow |

**Request Headers**:
```
Content-Type: application/json
```

**Success Response** (200 OK):
```json
{
  "city": "Moscow",
  "temperature": 15.5,
  "description": "Overcast clouds",
  "humidity": 72,
  "wind_speed": 3.5
}
```

**Response Fields**:

| Field | Type | Description | Range |
|-------|------|-------------|-------|
| `city` | string | City name | 1-100 chars |
| `temperature` | float | Temperature in Celsius | > -273.15 |
| `description` | string | Weather condition | 1-200 chars |
| `humidity` | integer | Humidity percentage | 0-100 |
| `wind_speed` | float | Wind speed in m/s | ≥ 0 |

---

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Error Status Codes

#### 404 Not Found
City was not found in OpenWeatherMap database.

**Cause**: OpenWeatherMap API returned 404  
**Action**: Verify city name spelling or use another city

```json
{
  "detail": "City 'NoSuchCity' not found"
}
```

#### 422 Unprocessable Entity
Request validation failed.

**Causes**:
- City name is empty
- City name exceeds 100 characters
- Missing required parameters

```json
{
  "detail": "City cannot be empty"
}
```

#### 502 Bad Gateway
OpenWeatherMap provider returned a server error (5xx).

**Cause**: OpenWeatherMap API is experiencing issues  
**Action**: Retry after a few seconds

```json
{
  "detail": "Weather provider error"
}
```

#### 503 Service Unavailable
OpenWeatherMap is rate-limited or temporarily unavailable.

**Causes**:
- OpenWeatherMap API returned 429 (rate limit)
- Service temporarily unavailable
- Redis cache unavailable (graceful fallback)

```json
{
  "detail": "Service temporarily unavailable (rate limited)"
}
```

#### 504 Gateway Timeout
Request to OpenWeatherMap exceeded 5-second timeout.

**Cause**: Provider not responding within timeout  
**Action**: Retry the request

```json
{
  "detail": "Request timeout"
}
```

#### 500 Internal Server Error
Unexpected server error.

**Cause**: Unhandled exception in service  
**Action**: Check server logs and retry

---

## Cache-Aside Pattern

The service implements a cache-aside pattern with Redis:

```
┌─────────────────────────────────────────────────────┐
│ GET /weather/{city}                                │
└────────────────────────┬────────────────────────────┘
                         │
                         ▼
           ┌─────────────────────────┐
           │ Check Redis Cache       │
           └────┬──────────┬─────────┘
                │          │
           CACHE HIT    CACHE MISS
                │          │
                ▼          ▼
           ┌──────┐   ┌──────────────────┐
           │Return│   │Fetch from OWM    │
           │Cached│   │(5s timeout)      │
           │Data  │   └────┬──────┬──────┘
           └──────┘        │      │
                      Success   Error
                         │        │
                         ▼        ▼
                    ┌────────┐  ┌──────┐
                    │Cache   │  │Return│
                    │Result  │  │Error │
                    │TTL 10m │  │Response
                    └────┬───┘  └──────┘
                         │
                         ▼
                    Return Data
```

**Behavior**:
- First request for a city: Cache MISS → fetch from OpenWeatherMap → cache result
- Subsequent requests (within 10 min): Cache HIT → return from Redis (no provider call)
- Cache expires after 10 minutes
- If provider fails, cache is NOT updated

---

## OpenWeatherMap Error Mapping

How OpenWeatherMap (OWM) errors are mapped to API responses:

| OWM Status | API Status | Description | Retry? |
|---|---|---|---|
| 200 OK | 200 | Success, data cached | No |
| 404 Not Found | 404 | City doesn't exist | No |
| 429 Too Many Requests | 503 | Rate limited | Yes |
| 5xx Server Error | 502 | Provider error | Yes |
| Timeout (>5s) | 504 | Request timeout | Yes |

---

## Rate Limiting

Currently, the service does NOT implement client-side rate limiting. However:

- OpenWeatherMap API rate limits (429) are handled gracefully
- When rate limited, service returns 503 Service Unavailable
- No retry storms: maximum 3 internal retries with backoff

---

## Request Examples

### Example 1: Successful Request (Cache Hit)

```bash
curl -X GET "http://localhost:8000/weather/Moscow"
```

**Response**:
```json
{
  "city": "Moscow",
  "temperature": 15.5,
  "description": "Overcast clouds",
  "humidity": 72,
  "wind_speed": 3.5
}
```

### Example 2: City Not Found

```bash
curl -X GET "http://localhost:8000/weather/InvalidCityXYZ"
```

**Response** (404):
```json
{
  "detail": "City 'InvalidCityXYZ' not found"
}
```

### Example 3: Invalid City Parameter

```bash
curl -X GET "http://localhost:8000/weather/$(python -c 'print(\"A\"*101)')"
```

**Response** (422):
```json
{
  "detail": "value_error.number.not_le"
}
```

### Example 4: Provider Rate Limited

```bash
curl -X GET "http://localhost:8000/weather/Moscow"
```

**Response** (503):
```json
{
  "detail": "Service temporarily unavailable (rate limited)"
}
```

---

## Implementation Details

### Request Timeout

- **Duration**: 5 seconds
- **Applies to**: OpenWeatherMap API requests only
- **Behavior on timeout**: Return 504 Gateway Timeout

### Cache Configuration

- **Backend**: Redis
- **TTL**: 10 minutes (600 seconds)
- **Key format**: `weather:{city_normalized}`
- **Normalization**: `lowercase(trim(city))`

### Logging

All requests and errors are logged:
- Request arrival (INFO)
- Cache hits/misses (DEBUG)
- Provider calls (INFO)
- Errors (ERROR/WARNING)
- **Security**: API keys never logged

---

## Security

### API Key Protection

- API key is never exposed in responses
- API key is never logged
- API key validated at startup
- Used only for internal provider calls

### Input Validation

- City parameter: 1-100 characters
- Whitespace automatically trimmed
- Special characters allowed
- Case-insensitive for caching

### Error Information

- No sensitive details in error messages
- No stack traces exposed to clients
- All errors follow consistent format

---

## OpenAPI/Swagger Documentation

When running the service, interactive API documentation is available:

**Swagger UI**: `http://localhost:8000/docs`  
**ReDoc**: `http://localhost:8000/redoc`

These provide interactive testing and auto-generated documentation.

---

## Performance Characteristics

| Scenario | Latency | Notes |
|----------|---------|-------|
| Cache hit | 50-100ms | Redis lookup only |
| Cache miss | 5-6s | Includes provider timeout |
| Provider error | <5s | Returns error immediately |
| Rate limited | <1s | Returns 503 immediately |

**Concurrent requests**: Unlimited (async/await)

---

## Version History

### v1.0 (Current)
- GET /weather/{city} endpoint
- Cache-aside pattern with 10-minute TTL
- Comprehensive error mapping
- Pydantic v2 models
- 5-second request timeout
