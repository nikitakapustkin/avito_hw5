---
status: complete
phase: 01-weather-history-api
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md]
started: 2026-03-27T14:00:00Z
updated: 2026-03-27T14:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. История пуста до первого запроса
expected: GET /weather/testcity/history возвращает HTTP 200 и тело `[]` до того, как был сделан хотя бы один GET /weather/testcity.
result: pass

### 2. История заполняется после GET /weather/{city}
expected: После одного успешного GET /weather/moscow GET /weather/moscow/history возвращает массив из 1 элемента с полями city, temperature, description, humidity, wind_speed, requested_at.
result: pass

### 3. История ограничена 10 записями
expected: После 11+ успешных запросов GET /weather/berlin/history возвращает ровно 10 элементов. Самый старый удалён, самый новый — последний.
result: pass

### 4. Нормализация города (case-insensitive)
expected: GET /weather/Moscow/history и GET /weather/moscow/history возвращают одинаковые данные — один и тот же bucket истории.
result: pass

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none]
