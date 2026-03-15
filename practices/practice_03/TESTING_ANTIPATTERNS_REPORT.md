# Testing Anti-Patterns Report: tests/test_integration.py

## Executive Summary
Found **5 critical anti-patterns** and **3 code quality issues** in the integration tests. All are fixable without changing production code.

---

## Anti-Pattern #1: Mock-Checking Instead of Behavior Verification ⚠️ CRITICAL

### Location
Lines 223, 320-323

### Issue
```python
# Line 223: BAD - tests mock behavior, not actual functionality
mock_redis.setex.assert_not_called()

# Lines 320-323: BAD - assertion depends on mock implementation details
mock_redis.get.assert_called()
call_args = mock_redis.get.call_args
assert "moscow" in call_args[0][0].lower()
```

### Why It's Wrong
- **Iron Law #1 Violation**: "Never test mock behavior — verify actual component functionality"
- Line 223 tests that the mock wasn't called, not that cache-aside logic works correctly
- Lines 320-323 verify mock was called and inspect its arguments — this tests the mock, not the actual cache lookup behavior
- If cache implementation changes but behavior is correct, test fails

### Correct Approach
```python
# GOOD - verify the actual behavior: response is still successful
assert response.status_code == 502
assert response.json()["detail"]  # Error message is present

# GOOD - verify behavior without inspecting mock internals
response_uppercase = client.get("/weather/MOSCOW")
response_lowercase = client.get("/weather/moscow")
# Both should work if normalization is implemented correctly
assert response_uppercase.status_code == 200
assert response_lowercase.status_code == 200
```

### Fix
**Remove lines 223** (mock assertion).
**Remove lines 320-323** (mock inspection) — the test already verifies the response.

---

## Anti-Pattern #2: Incomplete Mock Structures ⚠️ CRITICAL

### Location
Lines 72, 236, 302-308

### Issue
```python
# Lines 72, 236, 302-308: BAD - JSON dict doesn't match WeatherResponse model
weather_data = {
    "city": "Moscow",
    "temperature": 15.5,
    "description": "Overcast clouds",
    "humidity": 72,
    "wind_speed": 3.5,
}
mock_redis.get.return_value = json.dumps(weather_data)
```

### Why It's Wrong
- Real code may deserialize this as `WeatherResponse` — if model has new fields, tests don't catch issues
- When `WeatherResponse` schema changes (e.g., add `timestamp`), cached data silently mismatches
- Tests pass but production breaks with `ValidationError`

### Correct Approach
```python
# GOOD - use actual model, ensures type safety
weather_response = WeatherResponse(
    city="Moscow",
    temperature=15.5,
    description="Overcast clouds",
    humidity=72,
    wind_speed=3.5,
)
mock_redis.get.return_value = json.dumps(weather_response.model_dump())
```

### Fix
Replace all raw dicts in lines 72, 236, 302-308 with `WeatherResponse` model instantiation + `model_dump()`.

---

## Anti-Pattern #3: Test-Only Mutation of Production State ⚠️ CRITICAL

### Location
Lines 36-45

### Issue
```python
# BAD - directly modifying class attributes in fixture
AppState.redis_client = mock_redis
AppState.cache_service = CacheService(mock_redis)
AppState.weather_client = OpenWeatherMapClient("test_key")

yield

# Cleanup attempt
AppState.redis_client = None
AppState.cache_service = None
AppState.weather_client = None
```

### Why It's Wrong
- **Iron Law #2 Violation**: "Never add test-only methods to production code"
- `setup_app_state` mutates `AppState` class attributes, polluting global state
- If test fails or pytest stops unexpectedly, cleanup doesn't run → subsequent tests fail
- Tests are not isolated; one test's cleanup affects another
- No protection against concurrent test execution

### Correct Approach
Use dependency injection via `app.dependency_overrides` (FastAPI best practice):

```python
@pytest.fixture
def app_with_mocks(mock_redis, mock_weather_client):
    """Create app with mocked dependencies."""
    app.dependency_overrides = {
        get_redis: lambda: mock_redis,
        get_weather_client: lambda: mock_weather_client,
    }
    yield app
    app.dependency_overrides = {}  # Always cleanup
```

Or use `monkeypatch` (pytest built-in):

```python
@pytest.fixture
def setup_app_state(mock_redis, monkeypatch):
    """Set up app state with mock services."""
    monkeypatch.setattr("weather_service.app.AppState.redis_client", mock_redis)
    monkeypatch.setattr("weather_service.app.AppState.cache_service", 
                       CacheService(mock_redis))
    # No manual cleanup needed — monkeypatch restores automatically
```

### Fix
Replace lines 36-45 with `monkeypatch` fixture (requires `conftest.py` update).

---

## Anti-Pattern #4: Blind Mocking (Mocking Too Much) ⚠️ MODERATE

### Location
Lines 26-28, 84-97

### Issue
```python
# BAD - mock Redis unconditionally, even in health check test
@pytest.fixture
def mock_redis():
    return MagicMock(spec=Redis)

# Line 52: test_health_check doesn't need mock_redis but it's in setup_app_state
@pytest.mark.asyncio
async def test_health_check(self, client):
    response = client.get("/health")
```

### Why It's Wrong
- Health check endpoint doesn't use Redis or weather client
- Unnecessary mocking adds cognitive load and test setup overhead
- Test becomes fragile: changes to mock behavior affect unrelated tests
- Mock setup > 50% of test code (Red Flag #1)

### Correct Approach
```python
# GOOD - fixture that does nothing for tests that don't need it
@pytest.fixture
def app_with_services(monkeypatch):
    """Only patch what the test actually needs."""
    # Health check test won't use this fixture
    pass

# test_health_check doesn't depend on setup_app_state or mock_redis
async def test_health_check(self, client):  # No unnecessary fixtures
    response = client.get("/health")
```

### Fix
Remove `setup_app_state` from `test_health_check` (line 52).
Make mocking conditional: only mock what each test needs.

---

## Anti-Pattern #5: Overly Broad Mock Scopes ⚠️ MODERATE

### Location
Lines 99-103, 114-118, etc. (all `with patch.object(AppState.weather_client...)`)

### Issue
```python
# Problematic: patches AppState.weather_client globally
with patch.object(AppState.weather_client, "get_weather", ...):
    response = client.get("/weather/Paris")
```

### Why It's Wrong
- `AppState.weather_client` is a class attribute shared across all tests
- If one test's patch fails or hangs, it affects subsequent tests
- Patches are not automatically scoped to the test
- Context managers don't guarantee cleanup if test raises exception

### Correct Approach
```python
# GOOD - use pytest-mock for automatic cleanup
def test_get_weather_cache_miss(self, mocker):
    mocker.patch.object(
        AppState.weather_client,
        "get_weather",
        return_value=weather_response,
    )
    response = client.get("/weather/Paris")
    assert response.status_code == 200
```

Or use dependency injection as mentioned in Anti-Pattern #3.

### Fix
Replace all `patch.object(AppState.weather_client...)` with `mocker.patch.object()` 
(requires adding `pytest-mock` to `pyproject.toml` — it's already there).

---

## Code Quality Issues

### Issue #1: Redundant Assertions on Response Structure (Lines 243-247)

```python
# BAD - redundant loop
for field in required_fields:
    assert field in data
    assert data[field] is not None
```

**Fix**: Use `model_validate()` to verify schema in one line:
```python
# GOOD - FastAPI/Pydantic validates response automatically
WeatherResponse(**data)  # Raises ValidationError if fields missing
```

---

### Issue #2: Weak Error Message Assertions (Lines 137, 151, 165)

```python
# BAD - loose string matching, case-insensitive
assert "temporarily unavailable" in data["detail"].lower() or "rate limited" in data["detail"].lower()
```

**Fix**: Use exact assertions:
```python
# GOOD - verify exact error response
assert "temporarily unavailable" in data["detail"]
```

---

### Issue #3: Test Coupling via Shared Fixtures (Lines 61, 84, etc.)

Multiple tests depend on `setup_app_state`, creating hidden coupling.

**Fix**: Create test-specific fixtures:
```python
@pytest.fixture
def weather_response_moscow():
    return WeatherResponse(city="Moscow", temperature=15.5, ...)
```

---

## Summary Table

| Anti-Pattern | Location | Severity | Fix |
|---|---|---|---|
| Mock-checking behavior | 223, 320-323 | 🔴 Critical | Remove mock assertions, verify behavior |
| Incomplete mock structures | 72, 236, 302-308 | 🔴 Critical | Use `WeatherResponse.model_dump()` |
| Test-only state mutation | 36-45 | 🔴 Critical | Use `monkeypatch` fixture |
| Blind mocking | 26-28, 52 | 🟡 Moderate | Remove unnecessary mocks |
| Broad patch scopes | 99-103, 114+  | 🟡 Moderate | Use `pytest-mock` (mocker fixture) |
| Redundant assertions | 243-247 | 🟢 Minor | Trust Pydantic validation |
| Weak error messages | 137, 151, 165 | 🟢 Minor | Use exact string matching |

---

## Implementation Priority

**Phase 1 (Blocking)**: Fix anti-patterns #1-3 (critical)
**Phase 2 (Recommended)**: Fix anti-patterns #4-5 (moderate)
**Phase 3 (Nice-to-have)**: Fix code quality issues

---

## Testing the Fixes

After applying fixes:

```bash
pytest tests/test_integration.py -v
pytest tests/test_integration.py --tb=short -x  # Stop on first failure
pytest --cov=weather_service tests/  # Coverage report
```

Expected: All tests pass with 100% coverage, no mock assertions.
