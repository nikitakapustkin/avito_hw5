---
name: backend-api-standards
description: >
  Comprehensive guide for RESTful API design with clear standards, checklists,
  and examples. Triggered by phrases like "design endpoint", "review API",
  "add route", "REST standards", "HTTP status", "naming convention".
---

# Backend API Standards

## URL Design
- Use **nouns**, not verbs: `/weather/{city}` not `/getWeather`
- Lowercase with hyphens: `/api/v1/subscribe-request`
- Resource collections are plural: `/subscriptions`, `/users`
- Nested resources for ownership: `/projects/{id}/tasks`

## HTTP Methods
| Method   | Use case              | Success code |
|----------|-----------------------|--------------|
| GET      | Read resource         | 200          |
| POST     | Create resource       | 201          |
| PUT      | Replace resource      | 200          |
| PATCH    | Partial update        | 200          |
| DELETE   | Remove resource       | 204          |

## Status Codes — Use Precisely
- `200` OK — general success
- `201` Created — resource created (POST)
- `204` No Content — success, no body (DELETE)
- `400` Bad Request — validation error
- `401` Unauthorized — missing/invalid auth
- `403` Forbidden — authenticated but no permission
- `404` Not Found — resource doesn't exist
- `409` Conflict — duplicate resource
- `422` Unprocessable Entity — semantic validation error
- `429` Too Many Requests — rate limited
- `500` Internal Server Error — unexpected server failure
- `502` Bad Gateway — upstream service error
- `503` Service Unavailable — upstream rate limited / down
- `504` Gateway Timeout — upstream timeout

## Request/Response Format
- Always return `Content-Type: application/json`
- Error responses: `{"detail": "human-readable message"}`
- Success with data: return the resource directly (no wrapping)
- Validate input at the boundary (Pydantic models)

## FastAPI Checklist
- [ ] Route decorated with correct HTTP method
- [ ] Path parameters typed (`city: str`)
- [ ] Response model declared (`response_model=WeatherResponse`)
- [ ] Correct `status_code` on decorator
- [ ] Error cases raise `HTTPException` with correct status
- [ ] No business logic in route handler — delegate to services
- [ ] Async handler (`async def`) for I/O operations

## Naming Conventions
- Endpoints: lowercase, hyphenated path segments
- Query params: `snake_case`
- JSON fields: `snake_case`
- Do NOT use camelCase in JSON responses
