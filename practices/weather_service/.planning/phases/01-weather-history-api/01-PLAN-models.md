---
phase: 01-weather-history-api
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - weather_service/models.py
autonomous: true
requirements:
  - HIST-01
must_haves:
  truths:
    - "WeatherHistoryEntry class exists in models.py and is importable"
    - "WeatherHistoryEntry inherits from WeatherResponse"
    - "WeatherHistoryEntry has a requested_at field with default_factory=datetime.utcnow"
    - "HISTORY_MAX_SIZE constant equals 10 and is exported from models.py"
  artifacts:
    - path: "weather_service/models.py"
      provides: "WeatherHistoryEntry model and HISTORY_MAX_SIZE constant"
      contains: "class WeatherHistoryEntry(WeatherResponse)"
  key_links:
    - from: "weather_service/models.py"
      to: "weather_service/app.py"
      via: "import WeatherHistoryEntry, HISTORY_MAX_SIZE"
      pattern: "class WeatherHistoryEntry"
---

<objective>
Add the `WeatherHistoryEntry` Pydantic v2 model to `models.py`, inheriting from `WeatherResponse` and adding `requested_at: datetime`. Also define the `HISTORY_MAX_SIZE = 10` constant.

Purpose: Establish the data contract for history entries that AppState will store and the history endpoint will return.
Output: Updated `weather_service/models.py` with `WeatherHistoryEntry` and `HISTORY_MAX_SIZE` exported.
</objective>

<execution_context>
@/Users/nikitakapustkin/.claude/get-shit-done/workflows/execute-plan.md
@/Users/nikitakapustkin/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@weather_service/models.py
@.planning/phases/01-weather-history-api/01-CONTEXT.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add WeatherHistoryEntry model and HISTORY_MAX_SIZE to models.py</name>
  <files>weather_service/models.py, tests/test_models.py</files>

  <read_first>
    - weather_service/models.py — read the full file to understand current WeatherResponse definition (line 9), existing imports (line 1-7), and Pydantic v2 patterns in use (field_validator, Field, model_config)
    - .planning/phases/01-weather-history-api/01-CONTEXT.md — confirm decisions D-03 and D-04
  </read_first>

  <behavior>
    - WeatherHistoryEntry(WeatherResponse) can be instantiated with only WeatherResponse fields — requested_at auto-populates
    - WeatherHistoryEntry(WeatherResponse) explicitly passing requested_at stores the given value
    - WeatherHistoryEntry is a subclass of WeatherResponse (isinstance check passes)
    - HISTORY_MAX_SIZE == 10
    - WeatherHistoryEntry.model_fields contains "city", "temperature", "description", "humidity", "wind_speed", "requested_at"
  </behavior>

  <action>
Append the following to `weather_service/models.py` after the existing `Subscription` class (line 158). Do NOT modify any existing class.

1. Add `HISTORY_MAX_SIZE: int = 10` as a module-level constant directly after the imports block (after line 7, before `class WeatherResponse`). This places it near the top for visibility. Per D-02.

2. Append `WeatherHistoryEntry` class at the end of the file (after `Subscription`). Per D-03 and D-04:

```python
HISTORY_MAX_SIZE: int = 10


class WeatherHistoryEntry(WeatherResponse):
    """Single weather history record extending WeatherResponse with a timestamp."""

    requested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of when the weather was requested",
        examples=["2026-03-27T10:00:00"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "city": "Moscow",
                "temperature": 15.5,
                "description": "Overcast clouds",
                "humidity": 72,
                "wind_speed": 3.5,
                "requested_at": "2026-03-27T10:00:00",
            }
        }
    }
```

Note: `datetime` is already imported at line 3. No new imports needed.

In `tests/test_models.py`, write tests covering the behavior block above before implementing. Run tests (they must fail RED), then add the class to models.py (GREEN).
  </action>

  <verify>
    <automated>cd /Users/nikitakapustkin/Documents/GitHub/itmo-practice-nikitakapustkin/practices/weather_service && python -m pytest tests/test_models.py -x -q 2>&1 | tail -20</automated>
  </verify>

  <acceptance_criteria>
    - `grep -n "class WeatherHistoryEntry" weather_service/models.py` returns a line with `WeatherHistoryEntry(WeatherResponse)`
    - `grep -n "requested_at" weather_service/models.py` returns a line with `default_factory=datetime.utcnow`
    - `grep -n "HISTORY_MAX_SIZE" weather_service/models.py` returns a line with `HISTORY_MAX_SIZE: int = 10`
    - `python -c "from weather_service.models import WeatherHistoryEntry, HISTORY_MAX_SIZE; assert HISTORY_MAX_SIZE == 10; e = WeatherHistoryEntry(city='Moscow', temperature=1.0, description='x', humidity=50, wind_speed=1.0); assert hasattr(e, 'requested_at'); print('OK')"` prints `OK`
    - `python -m pytest tests/test_models.py -x -q` exits with code 0
  </acceptance_criteria>

  <done>WeatherHistoryEntry and HISTORY_MAX_SIZE are in models.py, importable, and all model tests pass.</done>
</task>

</tasks>

<verification>
```bash
cd /Users/nikitakapustkin/Documents/GitHub/itmo-practice-nikitakapustkin/practices/weather_service
python -c "from weather_service.models import WeatherHistoryEntry, HISTORY_MAX_SIZE; print('HISTORY_MAX_SIZE:', HISTORY_MAX_SIZE); e = WeatherHistoryEntry(city='Test', temperature=0.0, description='x', humidity=50, wind_speed=0.0); print('requested_at auto-set:', e.requested_at is not None)"
python -m pytest tests/test_models.py -q
```
</verification>

<success_criteria>
- `WeatherHistoryEntry` inherits from `WeatherResponse` (is-a check passes)
- `requested_at` auto-populates from `datetime.utcnow` when not provided
- `HISTORY_MAX_SIZE == 10`
- All tests in `tests/test_models.py` pass
</success_criteria>

<output>
After completion, create `.planning/phases/01-weather-history-api/01-01-SUMMARY.md` with:
- What was implemented
- Key decisions honored (D-03, D-04, D-02)
- Exact class signature and constant value
</output>
