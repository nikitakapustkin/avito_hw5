# Weather Service - CURL Examples

The Weather Service API is now running at `http://localhost:8000`

## Quick Test Commands

### 1. Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
    "status": "ok",
    "cache_available": false,
    "weather_client_ready": true
}
```

---

### 2. Get Weather for Tokyo
```bash
curl http://localhost:8000/weather/Tokyo
```

**Response:**
```json
{
    "city": "Tokyo",
    "temperature": 13.82,
    "description": "Clouds",
    "humidity": 55,
    "wind_speed": 1.54
}
```

---

### 3. Get Weather for London
```bash
curl http://localhost:8000/weather/London
```

**Response:**
```json
{
    "city": "London",
    "temperature": 8.75,
    "description": "Clouds",
    "humidity": 89,
    "wind_speed": 1.79
}
```

---

### 4. Get Weather for Berlin
```bash
curl http://localhost:8000/weather/Berlin
```

**Response:**
```json
{
    "city": "Berlin",
    "temperature": 3.9,
    "description": "Clear",
    "humidity": 77,
    "wind_speed": 1.79
}
```

---

### 5. Get Weather for Moscow
```bash
curl http://localhost:8000/weather/Moscow
```

**Response:**
```json
{
    "city": "Moscow",
    "temperature": -2.63,
    "description": "Clouds",
    "humidity": 64,
    "wind_speed": 3.5
}
```

---

### 6. City Not Found (404 Error)
```bash
curl http://localhost:8000/weather/XYZNonExistent
```

**Response (404):**
```json
{
    "detail": "City 'XYZNonExistent' not found"
}
```

---

### 7. Pretty Print JSON (using jq or python)
```bash
# Using python
curl -s http://localhost:8000/weather/Paris | python3 -m json.tool

# Or using jq (if installed)
curl -s http://localhost:8000/weather/Paris | jq .
```

---

## Testing Error Scenarios

### Invalid City Parameter (too long - 422)
```bash
curl "http://localhost:8000/weather/$(python3 -c 'print("A"*101)')"
```

**Response (422):**
```json
{
    "detail": "value_error.string.max_length"
}
```

---

### Multiple Cities (Sequential)
```bash
for city in Tokyo London Berlin Moscow Paris; do
  echo "=== $city ===" 
  curl -s http://localhost:8000/weather/$city | python3 -m json.tool
done
```

---

## Performance Testing

### Test Cache Hit (Second Request is Faster)
```bash
# First request (cache miss - slower, ~5s)
time curl -s http://localhost:8000/weather/TestCity > /dev/null

# Second request (cache hit - faster, ~0.1s)
time curl -s http://localhost:8000/weather/TestCity > /dev/null
```

---

## Full URL Format

```
GET http://localhost:8000/weather/{city}
```

**Parameters:**
- `city` (path, required): City name (1-100 characters)

---

## Response Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | `{"city": "Tokyo", ...}` |
| 404 | City not found | `{"detail": "City 'XYZ' not found"}` |
| 503 | Rate limited or service unavailable | `{"detail": "Service temporarily unavailable..."}` |
| 502 | Provider error (5xx from OWM) | `{"detail": "Weather provider error"}` |
| 504 | Request timeout | `{"detail": "Request timeout"}` |
| 422 | Invalid parameter | `{"detail": "value_error..."}` |

---

## Interactive API Documentation

Visit these URLs in your browser for interactive testing:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

You can test endpoints directly in the browser!

---

## Using with Other Tools

### HTTPie
```bash
http GET http://localhost:8000/weather/Tokyo
```

### Python Requests
```python
import requests
response = requests.get("http://localhost:8000/weather/Tokyo")
print(response.json())
```

### Postman
- Import URL: `http://localhost:8000/docs`
- Method: GET
- URL: `http://localhost:8000/weather/Tokyo`

---

## Logs

Watch the application logs to see:
- Cache hits/misses (DEBUG level)
- Provider requests (INFO level)
- Errors (ERROR/WARNING level)
- API key is **never logged**

Example log output:
```
2026-03-06 10:30:37,276 - weather_service.app - INFO - Fetching weather from OpenWeatherMap for city: London
2026-03-06 10:30:37,935 - httpx - INFO - HTTP Request: GET https://api.openweathermap.org/data/2.5/weather?q=London&... "HTTP/1.1 200 OK"
2026-03-06 10:30:37,936 - weather_service.app - INFO - Weather retrieved successfully for city: London
```

---

## Common Issues

### Connection Refused
```
curl: (7) Failed to connect to localhost port 8000: Connection refused
```
**Fix**: Ensure server is running: `python3 -m uvicorn weather_service.app:app --host 0.0.0.0 --port 8000`

### Invalid JSON
Try using `python3 -m json.tool` to pretty-print:
```bash
curl -s http://localhost:8000/weather/Tokyo | python3 -m json.tool
```

---

## All Cities Tested ✅

| City | Status | Temperature | Description |
|------|--------|-------------|-------------|
| Tokyo | ✅ | 13.82°C | Clouds |
| London | ✅ | 8.75°C | Clouds |
| Berlin | ✅ | 3.9°C | Clear |
| Moscow | ✅ | -2.63°C | Clouds |
| Paris | ✅ | 10.04°C | Clear |
| XYZNonExistent | ❌ 404 | — | City not found |

---

**Server Status**: Running at http://localhost:8000 ✅
**Cache**: Available when Redis is connected ⚠️ (currently disconnected)
**Weather API**: OpenWeatherMap ✅
