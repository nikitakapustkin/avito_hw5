---
phase: 01-weather-history-api
plan: 02
subsystem: app-state
tags: [weather-history, appstate, tdd, in-memory]
dependency_graph:
  requires:
    - 01-01-SUMMARY.md (WeatherHistoryEntry, HISTORY_MAX_SIZE models)
  provides:
    - AppState.weather_history in-memory storage
    - _record_history helper (called by get_weather)
  affects:
    - weather_service/app.py
    - tests/test_integration.py
tech_stack:
  added: []
  patterns:
    - FIFO capped list via list.pop(0) when len > HISTORY_MAX_SIZE
    - fire-and-forget try/except wrapping in _record_history
    - monkeypatch fixture for AppState class-level attribute reset
key_files:
  created: []
  modified:
    - weather_service/app.py
    - tests/test_integration.py
decisions:
  - "D-01: AppState.weather_history mirrors subscriptions pattern (class-level dict)"
  - "D-02: FIFO cap at HISTORY_MAX_SIZE=10; history.pop(0) drops oldest when 11th added"
  - "D-05: history recorded for both cache-hit and cache-miss return paths in get_weather"
metrics:
  duration: ~5min
  completed: 2026-03-27
  tasks: 1
  files_modified: 2
---

# Phase 01 Plan 02: AppState Weather History Storage Summary

**One-liner:** In-memory FIFO weather history per city via AppState.weather_history with _record_history helper wired into both get_weather return paths.

## What Was Implemented

Added in-memory weather history storage to `weather_service/app.py`:

1. **Import update** (line 9): Added `WeatherHistoryEntry, HISTORY_MAX_SIZE` to the models import.

2. **AppState.weather_history field** (line 35): Class-level dict `weather_history: dict[str, list[WeatherHistoryEntry]] = {}` following the same pattern as the existing `subscriptions` attribute (D-01).

3. **`_record_history` helper function** (lines 38-51): Standalone function defined after AppState class and before lifespan. Wraps all logic in try/except — errors are logged via `logger.warning` but never propagate to callers (fire-and-forget per D-05). Enforces FIFO cap: `history.pop(0)` when `len(history) > HISTORY_MAX_SIZE` (D-02).

4. **Call sites in `get_weather`**:
   - Line 205: cache-hit path — `_record_history(normalized_city, cached_weather)` before `return cached_weather`
   - Line 224: cache-miss path — `_record_history(normalized_city, weather)` before `return weather`

## Key Decisions Honored

- **D-01:** `AppState.weather_history` uses identical class-level dict pattern as `AppState.subscriptions`. Key is `normalized_city` (lowercase).
- **D-02:** FIFO cap at `HISTORY_MAX_SIZE=10`. When 11th entry is added, `history.pop(0)` removes the oldest, keeping the list at exactly 10.
- **D-05:** History recorded after every successful `GET /weather/{city}` response — both cache-hit and cache-miss paths call `_record_history` before their return statement.

## _record_history Location and Call Sites

| Item | File | Line |
|------|------|------|
| `_record_history` definition | weather_service/app.py | 38 |
| `AppState.weather_history` field | weather_service/app.py | 35 |
| Call site (cache-hit path) | weather_service/app.py | 205 |
| Call site (cache-miss path) | weather_service/app.py | 224 |

## Test Class Added

**Class:** `TestWeatherHistory` in `tests/test_integration.py`

**Tests added (7):**

| Test | Behavior Covered |
|------|-----------------|
| `test_cache_miss_populates_history` | Cache-miss GET records 1 entry in history |
| `test_cache_hit_populates_history` | Cache-hit GET records 1 entry in history |
| `test_history_grows_with_multiple_requests` | 5 requests → history length 5 |
| `test_history_capped_at_max_size` | 11 requests → history length exactly 10 |
| `test_history_fifo_oldest_dropped` | After 11 requests, oldest (temp=1) is dropped; newest (temp=11) is at index -1 |
| `test_error_does_not_populate_history` | 404 error does NOT modify history |
| `test_history_key_is_normalized_city` | Key stored as lowercase normalized city |

Each test uses `autouse=True` fixture with `monkeypatch.setattr("weather_service.app.AppState.weather_history", {})` to prevent cross-test contamination.

## TDD Execution

- **RED:** Tests written first; all failed with `AttributeError: 'type' object at weather_service.app.AppState has no attribute 'weather_history'`
- **GREEN:** 4 edits to app.py; 7/7 tests pass; 22/22 total integration tests pass

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — `AppState.weather_history` is live in-memory storage; `_record_history` is fully wired. The history endpoint (`GET /weather/{city}/history`) is deferred to a subsequent plan.

## Self-Check: PASSED

- `weather_service/app.py` modified and committed at 2eac7cf
- `tests/test_integration.py` modified and committed at 2eac7cf
- `python3 -m pytest tests/test_integration.py -x -q` exits 0 (22 passed)
- All acceptance criteria grep patterns verified
