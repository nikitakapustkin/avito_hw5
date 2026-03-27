---
phase: 01-weather-history-api
plan: 02
type: execute
wave: 2
depends_on:
  - 01-PLAN-models
files_modified:
  - weather_service/app.py
autonomous: true
requirements:
  - HIST-02
  - HIST-03
must_haves:
  truths:
    - "AppState has a weather_history class-level dict attribute"
    - "After a successful GET /weather/{city} response, the city's history grows by 1 entry"
    - "History never exceeds 10 entries per city (oldest is dropped when 11th is added)"
    - "History is recorded for both cache-hit and cache-miss paths"
    - "Recording history does not raise exceptions and does not affect the HTTP response"
  artifacts:
    - path: "weather_service/app.py"
      provides: "AppState.weather_history and _record_history helper"
      contains: "weather_history: dict[str, list[WeatherHistoryEntry]] = {}"
  key_links:
    - from: "weather_service/app.py get_weather()"
      to: "AppState.weather_history"
      via: "_record_history(normalized_city, weather)"
      pattern: "_record_history"
---

<objective>
Add `weather_history` to `AppState` and a `_record_history` helper that appends a `WeatherHistoryEntry` after every successful `GET /weather/{city}` response — both cache-hit and cache-miss paths — enforcing the 10-entry FIFO cap per city.

Purpose: Implement in-memory history storage (D-01, D-02, D-05) without touching the HTTP response or raising exceptions that would degrade weather requests.
Output: Updated `weather_service/app.py` with `AppState.weather_history`, `_record_history`, and two call sites in `get_weather`.
</objective>

<execution_context>
@/Users/nikitakapustkin/.claire/get-shit-done/workflows/execute-plan.md
@/Users/nikitakapustkin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@weather_service/app.py
@weather_service/models.py
@.planning/phases/01-weather-history-api/01-CONTEXT.md
@.planning/phases/01-weather-history-api/01-01-SUMMARY.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add weather_history to AppState and implement _record_history helper</name>
  <files>weather_service/app.py, tests/test_integration.py</files>

  <read_first>
    - weather_service/app.py — read fully. Key lines: AppState class (28-34), get_weather endpoint (133-252), specifically the two return statements at line 188 (`return cached_weather`) and line 206 (`return weather`)
    - weather_service/models.py — confirm WeatherHistoryEntry and HISTORY_MAX_SIZE are present (from plan 01)
    - .planning/phases/01-weather-history-api/01-CONTEXT.md — confirm D-01, D-02, D-05
  </read_first>

  <behavior>
    - After GET /weather/moscow (cache miss) returns 200, AppState.weather_history["moscow"] has length 1
    - After GET /weather/moscow (cache hit) returns 200, AppState.weather_history["moscow"] has length 1 (increments)
    - After 11 successful requests for the same city, history length is exactly 10 (oldest entry dropped)
    - history[city][0] is the oldest entry, history[city][-1] is the newest (insertion order)
    - When get_weather raises HTTPException (404, 503, etc.), history is NOT modified
    - _record_history wraps logic in try/except; any internal error is logged but does not propagate
  </behavior>

  <action>
Make three targeted edits to `weather_service/app.py`:

**Edit 1 — Update the import line (line 9):**
Change:
```python
from .models import WeatherResponse, SubscribeRequest, SubscriptionResponse, Subscription
```
To:
```python
from .models import WeatherResponse, SubscribeRequest, SubscriptionResponse, Subscription, WeatherHistoryEntry, HISTORY_MAX_SIZE
```

**Edit 2 — Add field to AppState class (after line 34, inside class body):**
Add after `subscriptions: dict[str, Subscription] = {}`:
```python
    weather_history: dict[str, list[WeatherHistoryEntry]] = {}
```
Per D-01: same pattern as `subscriptions`.

**Edit 3 — Add `_record_history` helper function** after the `AppState` class definition and before the `lifespan` function (after line 35, before line 37):
```python
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
```

**Edit 4 — Call `_record_history` at the two return points in `get_weather`:**

At the cache-hit path (currently line 188):
```python
# Before:
                return cached_weather
# After:
                _record_history(normalized_city, cached_weather)
                return cached_weather
```

At the cache-miss path (currently line 206):
```python
# Before:
        return weather
# After:
        _record_history(normalized_city, weather)
        return weather
```

Both inserts are BEFORE the return statement so the entry is recorded before the response is sent. Per D-05.

Add tests to `tests/test_integration.py` in a new class `TestWeatherHistory` covering the behavior block. Use `monkeypatch` to reset `AppState.weather_history = {}` in setup to prevent cross-test contamination. Write tests first (RED), then implement (GREEN).
  </action>

  <verify>
    <automated>cd /Users/nikitakapustkin/Documents/GitHub/itmo-practice-nikitakapustkin/practices/weather_service && python -m pytest tests/test_integration.py -x -q -k "TestWeatherHistory" 2>&1 | tail -20</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "weather_history" weather_service/app.py` returns at least 3 matches: class field, _record_history body, and call sites
    - `grep -n "_record_history" weather_service/app.py` returns at least 3 lines: definition + 2 call sites
    - `grep -n "WeatherHistoryEntry, HISTORY_MAX_SIZE" weather_service/app.py` returns a match on the import line
    - `grep -n "history.pop(0)" weather_service/app.py` returns a match (FIFO enforcement)
    - `python -m pytest tests/test_integration.py -x -q -k "TestWeatherHistory"` exits with code 0
    - `python -m pytest tests/test_integration.py -x -q` exits with code 0 (existing tests still pass)
  </acceptance_criteria>

  <done>AppState.weather_history is populated after each successful GET /weather/{city}, capped at 10, and all integration tests pass including the new TestWeatherHistory class.</done>
</task>

</tasks>

<verification>
```bash
cd /Users/nikitakapustkin/Documents/GitHub/itmo-practice-nikitakapustkin/practices/weather_service
python -m pytest tests/test_integration.py -q
```
All tests pass including new `TestWeatherHistory` tests.
</verification>

<success_criteria>
- `AppState.weather_history: dict[str, list[WeatherHistoryEntry]] = {}` present in class body
- `_record_history` function defined and called from both return paths in `get_weather`
- FIFO cap enforced: `history.pop(0)` when `len(history) > HISTORY_MAX_SIZE`
- History recording wrapped in try/except — never raises
- All existing integration tests continue to pass
</success_criteria>

<output>
After completion, create `.planning/phases/01-weather-history-api/01-02-SUMMARY.md` with:
- What was implemented
- Key decisions honored (D-01, D-02, D-05)
- Exact location of _record_history definition and call sites (line numbers)
</output>
