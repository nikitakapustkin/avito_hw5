# Rules — WeatherService (Practice 03)

## Стек
- Python 3.10+, FastAPI, Pydantic v2, httpx, Redis, poetry

## Код

- Используй **Pydantic v2**: `@field_validator`, не `@validator`; `model_config`, не `class Config`
- Используй **httpx** для HTTP-запросов, не requests
- Все эндпоинты FastAPI — `async def`
- Форматирование: **black** + **ruff** (запускай перед коммитом)
- Типизация обязательна: аннотации на всех функциях

## Структура проекта

```
weather_service/
  app.py              # FastAPI app, lifespan, роутер
  models.py           # Pydantic модели (только models, никакой логики)
  openweather_client.py  # HTTP-клиент к OWM, маппинг ошибок
  cache.py            # CacheService (Redis)
tests/
  conftest.py
  test_*.py
```

- Не добавляй новые модули без необходимости — сначала проверь, нет ли подходящего места
- Бизнес-логику не пиши в `app.py` — только роутинг и обработка ошибок

## Безопасность

- **НИКОГДА** не логируй `OPENWEATHERMAP_API_KEY` и другие секреты
- Конфиг читать только из переменных окружения (`os.getenv`)
- `.env` в `.rooignore` — не читай и не изменяй его

## Обработка ошибок OWM

Всегда маппи ошибки провайдера строго по этой таблице:

| Ошибка клиента     | HTTP-код |
|--------------------|----------|
| CityNotFoundError  | 404      |
| RateLimitedError   | 503      |
| ProviderError      | 502      |
| TimeoutError       | 504      |

- Не возвращай 500 для ошибок провайдера
- В `detail` ответа не раскрывай внутренние детали (стектрейс, ключи)

## Cache-aside (Redis)

- Всегда сначала читать из Redis → при cache hit вернуть ответ, OWM не вызывать
- При cache miss → запросить OWM → записать в Redis TTL=10 минут → вернуть ответ
- Если Redis недоступен — не падать, работать без кэша (graceful degradation)
- Ключ кэша: нормализованное имя города (`city.strip().lower()`)

## Тесты

- Фреймворк: **pytest + pytest-asyncio + pytest-mock**
- Моки для OWM — через `respx` или `pytest-mock`, не поднимай реальный сервер
- Для каждого нового эндпоинта: хотя бы happy path + ошибка провайдера + 404
- Не пиши тесты, которые ходят в настоящий OWM или Redis

## Запрещено

- Не используй `requests` (только `httpx`)
- Не используй Pydantic v1 синтаксис (`@validator`, `class Config`)
- Не добавляй зависимости без обновления `pyproject.toml`
- Не изменяй файлы в `docs/` — это reference-реализация
