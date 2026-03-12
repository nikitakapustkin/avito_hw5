# Weather Service - Quick Start Guide

Get the Weather Service up and running in 5 minutes.

## Prerequisites

- Python 3.10+
- Docker & Docker Compose (optional, for Redis)
- OpenWeatherMap API key (free at https://openweathermap.org/api)

## Option 1: Quick Start with Docker Compose (Recommended)

### 1. Clone and setup
```bash
cd weather_service
cp .env.example .env
```

### 2. Add your API key
Edit `.env` and set:
```
OPENWEATHERMAP_API_KEY=your_api_key_here
```

### 3. Start everything
```bash
docker-compose up
```

The API will be available at `http://localhost:8000`

### 4. Test it
```bash
curl http://localhost:8000/weather/Moscow
```

You should see:
```json
{
  "city": "Moscow",
  "temperature": 15.5,
  "description": "Overcast clouds",
  "humidity": 72,
  "wind_speed": 3.5
}
```

---

## Option 2: Local Development Setup

### 1. Install dependencies
```bash
cd weather_service
poetry install
```

### 2. Start Redis
```bash
# Using Docker (if you have it)
docker run -d -p 6379:6379 redis:latest

# Or using Homebrew on macOS
brew services start redis

# Or using apt on Ubuntu/Debian
sudo apt-get install redis-server
sudo service redis-server start
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your API key
export $(cat .env | xargs)
```

### 4. Run the application
```bash
poetry run python -m uvicorn weather_service.app:app --reload
```

The API will be available at `http://localhost:8000`

### 5. Test it
```bash
curl http://localhost:8000/weather/London
```

---

## Interactive API Documentation

Once running, visit these URLs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

You can test endpoints directly in the Swagger UI!

---

## Running Tests

### Run all tests
```bash
poetry run pytest -v
```

### Run with coverage
```bash
poetry run pytest --cov=weather_service --cov-report=html
# Open htmlcov/index.html to view coverage report
```

### Run specific test file
```bash
poetry run pytest tests/test_models.py -v
```

---

## Common API Calls

### Get weather for a city
```bash
curl http://localhost:8000/weather/Paris
```

### Get weather with special characters
```bash
curl "http://localhost:8000/weather/St.%20Petersburg"
```

### Check service health
```bash
curl http://localhost:8000/health
```

### Using Python
```python
import requests

response = requests.get("http://localhost:8000/weather/Berlin")
if response.status_code == 200:
    data = response.json()
    print(f"Temperature in {data['city']}: {data['temperature']}°C")
else:
    print(f"Error: {response.status_code}")
```

### Using httpx (async)
```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/weather/Tokyo")
        print(response.json())

asyncio.run(main())
```

---

## Troubleshooting

### Redis connection error
**Error**: `Failed to connect to Redis`

**Fix**: Ensure Redis is running
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running, start it
docker run -d -p 6379:6379 redis:latest
```

### API key not configured
**Error**: `OPENWEATHERMAP_API_KEY not configured`

**Fix**: Set your API key
```bash
export OPENWEATHERMAP_API_KEY=your_key_here
# or add to .env file
```

### City not found (404)
**Error**: `{"detail": "City 'XYZ' not found"}`

**Fix**: Verify city name. OpenWeatherMap uses official city names
```bash
curl http://localhost:8000/weather/Moscow      # ✓ Works
curl http://localhost:8000/weather/Moskva      # ✗ Doesn't work
```

### Rate limited (503)
**Error**: `{"detail": "Service temporarily unavailable (rate limited)"}`

**Fix**: Wait before making more requests or upgrade your OpenWeatherMap plan

### Timeout (504)
**Error**: `{"detail": "Request timeout"}`

**Fix**: OpenWeatherMap is slow. Try again in a moment

---

## Key Features to Try

### 1. Cache Hit
```bash
# First request (cache miss, slow ~5s)
time curl http://localhost:8000/weather/Moscow

# Second request (cache hit, fast ~0.1s)
time curl http://localhost:8000/weather/Moscow
```

### 2. Error Handling
```bash
# City not found (404)
curl http://localhost:8000/weather/NonExistentCity

# Invalid parameter (422)
curl "http://localhost:8000/weather/$(python3 -c 'print("A"*101)')"
```

### 3. Multiple Cities
```bash
curl http://localhost:8000/weather/Moscow
curl http://localhost:8000/weather/London
curl http://localhost:8000/weather/Tokyo
```

---

## Production Deployment

### Using Docker
```bash
docker build -t weather-service .
docker run -p 8000:8000 \
  -e OPENWEATHERMAP_API_KEY=your_key \
  -e REDIS_URL=redis://redis:6379 \
  weather-service
```

### Using Kubernetes
```bash
kubectl create configmap weather-config \
  --from-literal=REDIS_URL=redis://redis:6379
kubectl create secret generic weather-secrets \
  --from-literal=OPENWEATHERMAP_API_KEY=your_key
kubectl apply -f k8s/deployment.yaml
```

### Environment Variables
```
OPENWEATHERMAP_API_KEY    # Required
REDIS_URL                 # Default: redis://localhost:6379
LOG_LEVEL                 # Default: INFO
```

---

## Architecture Overview

```
Client Request
    ↓
FastAPI Endpoint (/weather/{city})
    ↓
Check Redis Cache
    ├─ HIT  → Return cached data (50-100ms)
    └─ MISS → Fetch from OpenWeatherMap
                ├─ Success → Cache + Return (5-6s)
                └─ Error   → Return error response
```

---

## Development Commands

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

### Run full quality check
```bash
poetry run black . && \
poetry run ruff check . && \
poetry run mypy weather_service && \
poetry run pytest
```

---

## API Response Examples

### Success (200)
```json
{
  "city": "Moscow",
  "temperature": 15.5,
  "description": "Overcast clouds",
  "humidity": 72,
  "wind_speed": 3.5
}
```

### City Not Found (404)
```json
{
  "detail": "City 'NoSuchCity' not found"
}
```

### Rate Limited (503)
```json
{
  "detail": "Service temporarily unavailable (rate limited)"
}
```

### Provider Error (502)
```json
{
  "detail": "Weather provider error"
}
```

### Timeout (504)
```json
{
  "detail": "Request timeout"
}
```

### Invalid Parameter (422)
```json
{
  "detail": "City cannot be empty"
}
```

---

## Performance Tips

1. **Cache reuse**: Request the same cities to hit cache (much faster)
2. **Batch requests**: Use async clients for multiple concurrent requests
3. **Monitor logs**: Watch logs to understand cache hit rate

---

## Next Steps

- Read [`README.md`](README.md) for detailed documentation
- Read [`API_SPECIFICATION.md`](API_SPECIFICATION.md) for complete API details
- Check [`IMPLEMENTATION_SUMMARY.md`](IMPLEMENTATION_SUMMARY.md) for technical overview
- Run tests: `poetry run pytest -v`
- Try the interactive docs: http://localhost:8000/docs

---

## Support

For issues, check:
1. `.env` file has `OPENWEATHERMAP_API_KEY` set
2. Redis is running (`redis-cli ping`)
3. Port 8000 is not in use
4. Python 3.10+ is installed

For more details, see the full [README.md](README.md)
