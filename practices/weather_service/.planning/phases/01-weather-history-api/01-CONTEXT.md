# Phase 1: Weather History API - Context

**Gathered:** 2026-03-27 (discuss mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Добавить хранение истории запросов погоды по городу в памяти (последние 10 записей).
Новый эндпоинт `GET /weather/{city}/history` возвращает список прошлых результатов.
Стек: FastAPI, in-memory (AppState), Pydantic v2.

Вне скоупа: персистентность истории (Redis/DB), постраничная навигация, очистка истории.
</domain>

<decisions>
## Implementation Decisions

### История хранилища
- **D-01:** Добавить `AppState.weather_history: dict[str, list[WeatherHistoryEntry]] = {}` — ключ normalized city (lowercase), паттерн идентичен существующему `AppState.subscriptions`.
- **D-02:** Лимит — **10 записей на город**. При превышении удалять самую старую (FIFO). Константа `HISTORY_MAX_SIZE = 10` в `app.py` или `models.py`.

### Модель записи истории
- **D-03:** Новая модель `WeatherHistoryEntry` расширяет `WeatherResponse` и добавляет поле `requested_at: datetime`. Pydantic v2, `Field(default_factory=datetime.utcnow)`.
- **D-04:** `WeatherHistoryEntry` объявляется в `models.py` рядом с `WeatherResponse`.

### Когда записывать
- **D-05:** Записывать в историю после **каждого успешного ответа** на `GET /weather/{city}` — как при cache hit, так и при fetch из API. Оба пути проходят через return WeatherResponse.

### Эндпоинт `/weather/{city}/history`
- **D-06:** `GET /weather/{city}/history` — response_model `list[WeatherHistoryEntry]`, статус 200. Нет враппера — список напрямую.
- **D-07:** Если история для города пуста или город никогда не запрашивался — возвращать `[]` (пустой список), не 404.
- **D-08:** Нормализация city параметра — `city.strip().lower()`, идентично `GET /weather/{city}`.

### Claude's Discretion
- Порядок сортировки результатов (предположительно: от новых к старым или наоборот)
- Точное место вставки записи в `get_weather` (до или после return)
</decisions>

<canonical_refs>
## Canonical References

No external specs — requirements fully captured in decisions above.

### Существующие файлы для чтения перед реализацией
- `weather_service/app.py` — AppState, lifespan, get_weather endpoint (место вставки логики записи истории)
- `weather_service/models.py` — WeatherResponse (базовый класс для WeatherHistoryEntry)
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AppState` (`app.py:28-34`): class-level dict pattern — `subscriptions: dict[str, Subscription] = {}`. History следует тому же паттерну.
- `WeatherResponse` (`models.py:9-53`): Pydantic v2 BaseModel с `model_config`, `Field`, `field_validator`. `WeatherHistoryEntry` наследуется от него.

### Established Patterns
- Нормализация города: `city.strip().lower()` — используется в `get_weather` и `subscribe`
- Pydantic v2: `Field(default_factory=...)`, `field_validator`, `model_config`
- Endpoint pattern: `@app.get(path, response_model=..., status_code=..., tags=[...], responses={...})`

### Integration Points
- `app.py:get_weather()` — после строк 188 (`return cached_weather`) и 200 (`return weather`) нужно добавить вызов записи в историю. Удобнее вынести логику в helper или обернуть return.
- `AppState` — добавить `weather_history: dict[str, list[WeatherHistoryEntry]] = {}` рядом с `subscriptions` (строка 34).
</code_context>

<specifics>
## Specific Ideas

- История должна работать даже если Redis недоступен (in-memory only, не зависит от cache_service)
- Запись в историю — fire-and-forget, не должна влиять на ответ `GET /weather/{city}`
</specifics>

<deferred>
## Deferred Ideas

- Персистентность истории в Redis/DB — отдельная фаза
- Постраничная навигация (pagination) в `/history` — отдельная фаза
- Параметр `?limit=N` в запросе — отдельная фаза
- Очистка/сброс истории по городу — отдельная фаза
</deferred>

---

*Phase: 01-weather-history-api*
*Context gathered: 2026-03-27*
