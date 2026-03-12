# AGENTS.md — WeatherService (Practice 03)

Инструкции для AI-агентов по работе с проектом WeatherService.
Универсальный формат, совместимый с Roo Code, Cursor, Claude Code и другими AI IDE.

---

## Структура проекта

```
practice_03/
├── weather_service/
│   ├── app.py                  # FastAPI app, lifespan, роутер, AppState
│   ├── models.py               # Pydantic v2 модели (только схемы, без логики)
│   ├── openweather_client.py   # HTTP-клиент к OWM, классы ошибок
│   └── cache.py                # CacheService (Redis, cache-aside)
├── tests/
│   ├── conftest.py             # Фикстуры pytest
│   └── test_*.py               # Тесты по модулям
├── docs/
│   └── report_p2.md            # Архитектурные артефакты (только для чтения)
├── .roo/
│   └── rules.md                # Правила для Roo Code
├── .roomodes                   # Кастомные агенты Roo Code
├── .rooignore                  # Исключения из контекста Roo Code
├── .env                        # Секреты (не читать, не изменять)
├── .env.example                # Шаблон переменных окружения
└── pyproject.toml              # Зависимости (poetry)
```

---

## Технологический стек

- Python 3.10+
- FastAPI + uvicorn
- Pydantic v2
- httpx (HTTP-клиент)
- Redis (кэш, cache-aside паттерн)
- pytest + pytest-asyncio + pytest-mock
- ruff + black (линтинг и форматирование)
- poetry (управление зависимостями)

---

## Правила для агентов

### Код

- Используй **Pydantic v2**: `@field_validator`, не `@validator`; `model_config`, не `class Config`
- Используй **httpx** для HTTP-запросов, не requests
- Все эндпоинты FastAPI — `async def`
- Типизация обязательна: аннотации на всех функциях
- Форматирование: black + ruff

### Структура

- Бизнес-логику не писать в `app.py` — только роутинг и обработка ошибок
- Не добавляй новые модули без необходимости — сначала найди подходящее место
- Не изменяй файлы в `docs/` — это reference-материалы

### Безопасность

- **Никогда** не логировать `OPENWEATHERMAP_API_KEY` и другие секреты
- Конфиг читать только из переменных окружения (`os.getenv`)
- Не читать и не изменять `.env`

### Обработка ошибок OpenWeatherMap

| Исключение клиента | HTTP-код |
|--------------------|----------|
| CityNotFoundError  | 404      |
| RateLimitedError   | 503      |
| ProviderError      | 502      |
| TimeoutError       | 504      |

- Не возвращать 500 для ошибок провайдера
- В `detail` ответа не раскрывать внутренние детали

### Cache-aside (Redis)

- Всегда сначала читать из Redis → при cache hit вернуть ответ, OWM не вызывать
- При cache miss → запросить OWM → записать в Redis TTL=10 минут → вернуть ответ
- Если Redis недоступен — не падать, работать без кэша (graceful degradation)
- Ключ кэша: `weather:{city.strip().lower()}`

### Тесты

- Мокать OpenWeatherMap через pytest-mock — никогда не вызывать реальный API
- Мокать Redis — не требовать запущенного Redis
- Для каждого эндпоинта: минимум happy path + 404 + одна ошибка провайдера
- Не добавлять зависимости — использовать только то, что есть в `pyproject.toml`
- Не изменять исходный код — только файлы в `tests/`

### Запрещено

- Использовать `requests` (только `httpx`)
- Использовать Pydantic v1 синтаксис (`@validator`, `class Config`)
- Добавлять зависимости без обновления `pyproject.toml`
- Изменять файлы в `docs/`
