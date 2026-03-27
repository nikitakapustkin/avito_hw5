---
phase: 01-weather-history-api
plan: 03
type: execute
wave: 3
depends_on:
  - 01-PLAN-models
  - 01-PLAN-appstate
files_modified:
  - weather_service/app.py
  - tests/test_integration.py
autonomous: true
requirements:
  - HIST-04
  - HIST-05
must_haves:
  truths:
    - "GET /weather/{city}/history returns 200 with a JSON array"
    - "Returned array contains WeatherHistoryEntry objects with city, temperature, description, humidity, wind_speed, requested_at fields"
    - "GET /weather/{city}/history for a never-requested city returns 200 with []"
    - "City normalization matches GET /weather/{city}: strip + lowercase"
    - "After N successful /weather/{city} requests, /weather/{city}/history returns N entries (up to 10)"
  artifacts:
    - path: "weather_service/app.py"
      provides: "GET /weather/{city}/history endpoint"
      contains: "async def get_weather_history"
  key_links:
    - from: "GET /weather/{city}/history"
      to: "AppState.weather_history"
      via: "normalized_city = city.strip().lower()"
      pattern: "AppState.weather_history.get"
---

<objective>
Add the `GET /weather/{city}/history` endpoint to `app.py` that reads from `AppState.weather_history` and returns a `list[WeatherHistoryEntry]` — empty list if no history exists for the city. Add comprehensive integration tests.

Purpose: Expose the in-memory history via a REST endpoint (D-06, D-07, D-08).
Output: New endpoint in `app.py` and full test coverage in `tests/test_integration.py`.
</objective>

<execution_context>
@/Users/nikitakapustkin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/nikitakapustkin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@weather_service/app.py
@weather_service/models.py
@tests/test_integration.py
@.planning/phases/01-weather-history-api/01-CONTEXT.md
@.planning/phases/01-weather-history-api/01-02-SUMMARY.md
</context>

<interfaces>
<!-- Key contracts the executor needs. Extracted from plan 01 and plan 02 output. -->

From weather_service/models.py (after plan 01):
```python
HISTORY_MAX_SIZE: int = 10

class WeatherHistoryEntry(WeatherResponse):
    requested_at: datetime = Field(default_factory=datetime.utcnow, ...)
```

From weather_service/app.py (after plan 02):
```python
class AppState:
    weather_history: dict[str, list[WeatherHistoryEntry]] = {}

def _record_history(normalized_city: str, weather: WeatherResponse) -> None: ...
```

Existing endpoint pattern (from app.py):
```python
@app.get(
    "/weather/{city}",
    response_model=WeatherResponse,
    status_code=200,
    tags=["Weather"],
    responses={...},
)
async def get_weather(city: str = Path(..., min_length=1, max_length=100)) -> WeatherResponse:
    normalized_city = city.strip().lower()
    ...
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add GET /weather/{city}/history endpoint</name>
  <files>weather_service/app.py, tests/test_integration.py</files>

  <read_first>
    - weather_service/app.py — read fully. Confirm `_record_history` is present and `WeatherHistoryEntry` is imported. Note the last endpoint (delete_subscribe ends around line 462) and the exception_handler at line 465. Insert new endpoint BEFORE the exception_handler.
    - tests/test_integration.py — read fully. Note the `setup_app_state` fixture pattern and `TestWeatherHistory` class added in plan 02. The new tests go in a new class `TestWeatherHistoryEndpoint`.
    - .planning/phases/01-weather-history-api/01-CONTEXT.md — confirm D-06, D-07, D-08
  </read_first>

  <behavior>
    - GET /weather/moscow/history with no prior requests returns 200 and body `[]`
    - GET /weather/Moscow/history and GET /weather/moscow/history resolve to same history (city normalized)
    - GET /weather/moscow/history after 3 successful GET /weather/moscow calls returns array of length 3
    - Each entry in the array has keys: city, temperature, description, humidity, wind_speed, requested_at
    - GET /weather/moscow/history after 11 successful GET /weather/moscow calls returns array of length 10
    - GET /weather/moscow/history does NOT trigger weather API or cache lookup
    - Response schema matches list[WeatherHistoryEntry] — no wrapper object
  </behavior>

  <action>
Add the history endpoint to `weather_service/app.py`. Insert it BEFORE the `@app.exception_handler` line (currently around line 465), after the `delete_subscribe` endpoint.

```python
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
```

Note: `WeatherHistoryEntry` is already imported (done in plan 02). No additional imports needed.

In `tests/test_integration.py`, add class `TestWeatherHistoryEndpoint` with tests covering the behavior block. Use the existing `setup_app_state` fixture. Reset `AppState.weather_history = {}` in each test using `monkeypatch.setattr("weather_service.app.AppState.weather_history", {})`. Write tests first (RED), then implement endpoint (GREEN).

Typical test structure for history population:
```python
# Populate history by patching AppState directly
monkeypatch.setattr(
    "weather_service.app.AppState.weather_history",
    {"moscow": [WeatherHistoryEntry(city="Moscow", temperature=1.0, description="x", humidity=50, wind_speed=1.0)]},
)
response = client.get("/weather/Moscow/history")
assert response.status_code == 200
data = response.json()
assert len(data) == 1
assert data[0]["city"] == "Moscow"
assert "requested_at" in data[0]
```
  </action>

  <verify>
    <automated>cd /Users/nikitakapustkin/Documents/GitHub/itmo-practice-nikitakapustkin/practices/weather_service && python -m pytest tests/test_integration.py -x -q -k "TestWeatherHistoryEndpoint" 2>&1 | tail -20</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "weather/{city}/history" weather_service/app.py` returns the route decorator line
    - `grep -n "async def get_weather_history" weather_service/app.py` returns a match
    - `grep -n "response_model=list\[WeatherHistoryEntry\]" weather_service/app.py` returns a match
    - `grep -n "AppState.weather_history.get" weather_service/app.py` returns a match
    - `python -m pytest tests/test_integration.py -x -q -k "TestWeatherHistoryEndpoint"` exits with code 0
    - `python -m pytest tests/test_integration.py -x -q` exits with code 0 (all tests including previous classes pass)
    - `python -m pytest tests/ -x -q` exits with code 0 (full suite passes)
  </acceptance_criteria>

  <done>GET /weather/{city}/history endpoint is live, returns list[WeatherHistoryEntry] (or []), city is normalized, and all tests across the full test suite pass.</done>
</task>

</tasks>

<verification>
```bash
cd /Users/nikitakapustkin/Documents/GitHub/itmo-practice-nikitakapustkin/practices/weather_service
python -m pytest tests/ -q
```
Full suite passes. Then manual smoke test:
```bash
# Start the app locally (requires OPENWEATHERMAP_API_KEY) or use TestClient in test
# Verify /weather/moscow/history returns [] before any request
# Verify /weather/MOSCOW/history and /weather/moscow/history are equivalent
```
</verification>

<success_criteria>
- `GET /weather/{city}/history` endpoint registered in FastAPI app
- Returns `200` + `list[WeatherHistoryEntry]` in all cases
- Returns `[]` for unknown city (no 404)
- City normalized via `city.strip().lower()`
- Full test suite (`tests/`) passes
</success_criteria>

<output>
After completion, create `.planning/phases/01-weather-history-api/01-03-SUMMARY.md` with:
- What was implemented
- Key decisions honored (D-06, D-07, D-08)
- Endpoint signature and response model
- Test class name and count of test cases added
</output>
