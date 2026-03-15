---
name: testing-anti-patterns
description: >
  Identifies common testing mistakes and provides detection rules and fixes.
  Triggered by phrases like "write test", "check test", "test coverage",
  "mock", "pytest", "тест", "проверь тест".
---

# Testing Anti-Patterns

## Iron Laws
1. **Never test mock behavior** — verify actual component functionality
2. **Never add test-only methods to production code** — use test utilities
3. **Never mock without understanding dependencies** — know side effects first

## Core Principle
> "Test what the code does, not what the mocks do."

Mocks are isolation tools, not the subject of assertions.

## Five Anti-Patterns to Avoid

### 1. Checking Mock Existence
```python
# BAD
mock_client.get_weather.assert_called_once()  # tests the mock, not behaviour

# GOOD
assert response.status_code == 200
assert response.json()["city"] == "London"
```

### 2. Test-Only Methods in Production Code
```python
# BAD — adding _reset() to AppState just for tests
def _reset(self): self.subscriptions.clear()

# GOOD — reset state in conftest fixture
@pytest.fixture(autouse=True)
def clear_state(app):
    app.state.subscriptions.clear()
```

### 3. Blind Mocking
```python
# BAD — mock everything "to be safe"
@patch("weather_service.cache.redis")
@patch("weather_service.client.httpx")
@patch("weather_service.app.logger")

# GOOD — mock only external I/O boundaries
@patch("weather_service.openweather_client.httpx.AsyncClient")
```

### 4. Incomplete Mock Structures
```python
# BAD — partial response missing required fields
mock_client.get_weather.return_value = {"temp": 20}

# GOOD — mirror the real response model
mock_client.get_weather.return_value = WeatherResponse(
    city="London", temperature=20.0, description="clear sky", humidity=60
)
```

### 5. Tests Written After Implementation (no TDD)
- Write the test first, watch it fail, then implement
- If you can't write a test before coding — the design is too coupled

## Red Flags
- Mock setup > 50% of test code
- Phrases like "mock this to be safe"
- Test IDs containing "mock" (e.g., `test_mock_cache`)
- `assert mock_x.called` as the only assertion

## pytest Checklist
- [ ] Each test has one clear assertion goal
- [ ] Fixtures in `conftest.py`, not repeated per test
- [ ] Parametrize similar cases with `@pytest.mark.parametrize`
- [ ] External calls (HTTP, Redis) are mocked at the boundary
- [ ] Test names describe behaviour: `test_returns_404_for_unknown_city`
