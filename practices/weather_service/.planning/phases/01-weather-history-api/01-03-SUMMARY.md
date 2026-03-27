---
phase: 01-weather-history-api
plan: 03
subsystem: weather-api
tags: [endpoint, history, fastapi, tdd]
dependency_graph:
  requires:
    - 01-02 (AppState.weather_history, WeatherHistoryEntry import, _record_history)
    - 01-01 (WeatherHistoryEntry model in models.py)
  provides:
    - GET /weather/{city}/history endpoint
  affects:
    - weather_service/app.py
    - tests/test_integration.py
tech_stack:
  added: []
  patterns:
    - FastAPI path parameter with min_length/max_length validation
    - list[WeatherHistoryEntry] as direct response model (no wrapper)
    - AppState.weather_history.get(normalized_city, []) for safe default
key_files:
  modified:
    - weather_service/app.py
    - tests/test_integration.py
decisions:
  - D-06 honored: response_model=list[WeatherHistoryEntry], status 200, no wrapper
  - D-07 honored: returns [] (not 404) for never-queried cities
  - D-08 honored: city normalized via city.strip().lower() for lookup
metrics:
  duration: ~5 minutes
  completed: 2026-03-27
  tasks_completed: 1
  files_modified: 2
---

# Phase 1 Plan 3: Add GET /weather/{city}/history Endpoint Summary

**One-liner:** FastAPI history endpoint returning list[WeatherHistoryEntry] from in-memory AppState with city normalization and safe empty-list default.

## What Was Implemented

Added `GET /weather/{city}/history` endpoint to `weather_service/app.py` that:

- Accepts a `city` path parameter (min_length=1, max_length=100)
- Normalizes the city name via `city.strip().lower()` before lookup
- Returns `AppState.weather_history.get(normalized_city, [])` — an empty list if no history exists
- Uses `response_model=list[WeatherHistoryEntry]` (direct array, no wrapper)
- Always returns HTTP 200 (never 404, even for unknown cities)
- Does not call OpenWeatherMap or Redis

The endpoint was inserted before the `@app.exception_handler(HTTPException)` line, after the `delete_subscribe` endpoint (around line 484 in the final file).

## Key Decisions Honored

- **D-06:** `GET /weather/{city}/history` — `response_model=list[WeatherHistoryEntry]`, status 200. No wrapper object — JSON array directly.
- **D-07:** Returns `[]` (empty list) for cities never queried. No 404 raised.
- **D-08:** City normalization is `city.strip().lower()`, identical to the existing `GET /weather/{city}` endpoint.

## Endpoint Signature

```python
@app.get(
    "/weather/{city}/history",
    response_model=list[WeatherHistoryEntry],
    status_code=200,
    tags=["Weather"],
    ...
)
async def get_weather_history(
    city: str = Path(..., min_length=1, max_length=100, examples=["Moscow"]),
) -> list[WeatherHistoryEntry]:
    normalized_city = city.strip().lower()
    return AppState.weather_history.get(normalized_city, [])
```

**Response model:** `list[WeatherHistoryEntry]` where each entry contains: `city`, `temperature`, `description`, `humidity`, `wind_speed`, `requested_at`.

## Test Class and Coverage

**Test class:** `TestWeatherHistoryEndpoint` added to `tests/test_integration.py`

**Test cases (4 total):**

1. `test_empty_list_for_never_queried_city` — verifies 200 + `[]` for a city with no history
2. `test_case_insensitive_normalization` — verifies `Moscow` and `moscow` resolve to the same history bucket
3. `test_returns_correct_entries_with_all_fields` — verifies all 6 fields are present in returned entries including `requested_at`
4. `test_no_404_for_unknown_city_always_200` — verifies multiple unknown cities all return 200

## TDD Execution

- **RED:** Tests written first; all 4 failed with `404` (route did not exist yet).
- **GREEN:** Endpoint added to `app.py`; all 4 tests passed immediately.
- **Full suite:** 74 tests passed (0 failures).

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- `weather_service/app.py`: modified, endpoint present at line 484-518
- `tests/test_integration.py`: modified, `TestWeatherHistoryEndpoint` class with 4 tests present
- Commit `81bcc0c` exists: `feat(01-endpoint): add GET /weather/{city}/history endpoint`
- Full test suite: 74 passed
