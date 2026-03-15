---
name: code-review
description: >
  Review FastAPI endpoint code for correctness, style, and compliance with
  project rules (Pydantic v2, async, error mapping, cache-aside, no secrets in logs).
  Triggered by phrases like "review", "проверь код", "code review", "найди проблемы".
---

# Code Review Skill — weather_service

## Purpose
Perform a structured code review of FastAPI endpoints in `weather_service/`.
Check compliance with the rules defined in `.roo/rules.md` and `AGENTS.md`.

## Review Checklist

### 1. Pydantic v2 Compliance
- [ ] Uses `model_config = ConfigDict(...)` instead of `class Config`
- [ ] Uses `@field_validator` instead of `@validator`
- [ ] Uses `model_validator` for cross-field validation if needed

### 2. Async Correctness
- [ ] All endpoint handlers use `async def`
- [ ] All I/O calls (Redis, HTTP) are `await`-ed
- [ ] No blocking calls (`requests`, `time.sleep`, etc.)

### 3. HTTP Client
- [ ] Uses `httpx.AsyncClient` (not `requests`)
- [ ] Client is reused via `AppState`, not recreated per request
- [ ] Timeout is set (5 seconds for OWM)

### 4. Error Mapping
| Exception             | HTTP Status |
|-----------------------|-------------|
| `CityNotFoundError`   | 404         |
| `RateLimitedError`    | 503         |
| `ProviderError`       | 502         |
| `TimeoutError`        | 504         |

- [ ] Each exception maps to the correct HTTP status
- [ ] Error response includes `{"detail": "..."}` body

### 5. Cache-Aside Pattern
- [ ] GET /weather/{city} checks Redis before calling OWM
- [ ] Cache key format: `weather:{city.lower()}`
- [ ] TTL = 600 seconds
- [ ] Redis failure is handled gracefully (log warning, continue)

### 6. Security
- [ ] No API keys in logs or error messages
- [ ] No secrets in response bodies

### 7. Code Style
- [ ] `black` formatting compliant
- [ ] `ruff` linting compliant
- [ ] Imports are sorted

## Output Format

For each issue found:
```
[SEVERITY] File:Line — Description
Suggestion: ...
```

Severity levels: `ERROR` | `WARNING` | `INFO`

## Example Usage

> "Review app.py for compliance with project rules"
> "Проверь код weather_service на соответствие правилам"
> "Найди проблемы в реализации GET /weather/{city}"
