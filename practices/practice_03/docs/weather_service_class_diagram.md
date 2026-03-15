# Weather Service - UML Class Diagram

## Диаграмма классов (PlantUML)

Ниже представлена диаграмма классов для проекта WeatherService:

![Weather Service Class Diagram](https://www.plantuml.com/plantuml/svg/nLZRRXit47tNLx3gGsqaIfGqVQZG1b5LfJQgs88aD0-1iQ2uOudmBhabkR9TLq2V-W7zX7vQlgH3xiLxeIv92tGDs19dvkpSP-Wtsb1bqZWYjq3D6bIWGMquWu15L6lGdI_mD0QIH9IBZhxX8g6AncH9sSrAoLI48nb9HRvyExO_5Gu7y4EBhMz_McnIXQ1obg_TKs6XIidREh6J831T0UaszEwIXmx1n_twYdplUSYxon_7axcNviHAx5Y64Ea2qZvEM_8-U-SCT2A5XWhTFZt2kBaV46rKuzn0d82Y9bKm8DUHfAR1489cYYU6I-6JNwSn3nqs5qtHMox2G2S0eHUwL_lwX6nen4Dg82WmJpQdRTWA7ojugcfjoqyD3ytJfRLa2JFuDGLjZdOHn9H70pAsV-OjAbjJ8G3f4sxGaT67hkFlNXrfB4KV2QbY_FxRPvhaWhCpyZpq6NN0MFsvTXAcC1CX3AWP46kWuJ5ycYN_qW9x_kZHyFyoSdkmvY-duultu-7YR3mZeydv-69nHFtB14JHNrZ4GPXsBxX4dhmVlAF965kLQlZqWIxHUChCzd1eHkZF2sdUsexPnDefD4EdJ7YCNZnUPghaXcFFFLfWWLwNgJcQl-wNaVDUAzbemeCRy6RMace8KkND79FfWZsVIH5gVo_D8pP0JMoYOtuDzRrWcIO76aOGK6J2g0SdfmElAHw1EsuiVuEo0XFaENHILX62DcP8KtcSV6X_aNmgvtf4U6fBWM91S6Rse1rR7gFXw6nyH4KmojRGBeAHFPvd4xWLP0KXrsKqPlPRCvucUenbQxJrsXwjURACRyC9LmqvNPLxMYmyBTyXubBAg27C8g3r07gOra0ZimxG5-pcnCU2WLscF0fjqjV0sXFeSCo6q-aH4QD9qexNC4dc1hj6irFXDcWusn8NvcAbgdYu6kShlsYzNrPaVLMq0wEUCIM2IvqT8heoqtHM5XzScAl3xkfmstfBjHbEpz51hJmst4JWQqS7jhODABs35F5hp3gAD6fx4rQ0WJiJKu6XKmUh8CZopMQQjVS_Q3nF2ZykuKHbcrkmb27ADXUwqu5t8MgWuVeCk7OzWkRRnUad9_jiF1akpYylvcVdqpshUmunlcEGhJThZgk5OkjxH_4Dw-z-x_NQStS_UtFYxkUkpThzhDKfMpN8EqrJl9zvm-dbVlRiTUlYCY1T1NWT4RgxMx3NUqqgezCAsJTtg_hL1a2MltxLQemMsQEIDX87tdFKJ77O56zgIRfsuDMcR6-seF3UgadUohB1Kv8jIWqMmTOo2dEq6f_NDNluI-rsCTIsyDBgcXsLPkHYNSWxSeNe8bHW8nHbQ6hfb0hZCJdGO6_Tv1m_0xw1lGBrUzA1b_ZgOM2t3OF1gViaL-Dv2PrTqXsrfMjJ7mVghXCvQ8tOZ4fLUymaxED64oExdMsd8oIwMl7LsX1vxSdqwNr81KucidcPQOXdl-JNK5rUvCb9l_UYtp-j4OKKFOWJfDgstG4H4lksvZjtRAMkKidPOZ4bh3XpETwZ6fiGBWO65rk1fvcROrmGk5WDyE3Z7t-JL_rNvEEVVtaRegE__DRHFHtGah-vktFaPikpj7nhT_HQdzjbORKq4IEhABUQa5jkrcIncE3npt1FhkqD55U5uhz1WmVhkgsDCJ8Do8i-YRb8ZMi0F-5T3AxJ2AVJIb7qEOPwfmwLaiEF4MUEdUXgUt6Z-bnmmxDRC0bJXIujfpjIvskAImsXJ4bSCl3Y6qQu5LJU-WO_fd7K-GS0)

## Описание компонентов

### 📦 **models** — Pydantic v2 модели

| Класс | Описание |
|-------|----------|
| [`WeatherResponse`](../weather_service/models.py:9) | Ответ API с данными о погоде (Pydantic v2) |
| [`SubscribeRequest`](../weather_service/models.py:72) | Запрос на создание подписки |
| [`SubscriptionResponse`](../weather_service/models.py:107) | Ответ с данными подписки (201 Created) |
| [`Subscription`](../weather_service/models.py:149) | Внутренняя модель подписки (с ID, временем создания) |

**Ключевые валидаторы:**
- `WeatherResponse.validate_humidity()` — проверка 0-100%
- `WeatherResponse.validate_city()` — не пусто
- `SubscribeRequest.validate_and_normalize_city()` — trim + валидация

### 🌐 **openweather_client** — HTTP-клиент к OpenWeatherMap API

| Класс | Описание |
|-------|----------|
| [`OpenWeatherMapClient`](../weather_service/openweather_client.py:41) | Async клиент с поддержкой context manager |

**Методы:**
- `async get_weather(city: str) → WeatherResponse` — получить погоду
- `async __aenter__()` / `__aexit__()` — context manager для httpx.AsyncClient

**Иерархия исключений:**
```
OpenWeatherMapError (base)
├── CityNotFoundError     (404 from provider)
├── RateLimitedError      (429 from provider)
├── ProviderError         (5xx from provider)
└── TimeoutError          (connection timeout)
```

**Обработка ошибок:**
- 404 → `CityNotFoundError` → HTTP 404
- 429 → `RateLimitedError` → HTTP 503
- 5xx → `ProviderError` → HTTP 502
- Timeout → `TimeoutError` → HTTP 504

### 💾 **cache** — Redis кэш с паттерном cache-aside

| Класс | Описание |
|-------|----------|
| [`CacheService`](../weather_service/cache.py:16) | Сервис кэширования с TTL |

**Методы:**
- `async get(city: str) → Optional[WeatherResponse]` — чтение из кэша
- `async set(city: str, weather: WeatherResponse) → bool` — запись в кэш с TTL
- `async clear(city: str) → bool` — удаление из кэша
- `async health_check() → bool` — проверка Redis

**Параметры:**
- TTL: 10 минут
- Ключ: `weather:{city.lower()}`
- Graceful degradation при недоступности Redis

### 🚀 **app** — FastAPI приложение

| Класс | Описание |
|-------|----------|
| [`AppState`](../weather_service/app.py:28) | Контейнер состояния приложения (синглтон) |

**Поля AppState:**
- `cache_service: Optional[CacheService]` — сервис кэша
- `weather_client: Optional[OpenWeatherMapClient]` — клиент OWM
- `redis_client: Optional[Redis]` — Redis клиент
- `subscriptions: dict[str, Subscription]` — хранилище подписок

**Эндпоинты:**
1. `GET /health` — проверка здоровья
2. `GET /weather/{city}` — получить погоду (с cache-aside)
3. `POST /subscribe` — создать подписку
4. `DELETE /subscribe/{id}` — удалить подписку

**Lifespan:**
- **Startup**: инициализация Redis, CacheService, OpenWeatherMapClient
- **Shutdown**: закрытие Redis соединения

## Паттерны и принципы

### 1. **Cache-Aside (Lazy Loading)**
```
GET /weather/{city}:
  1. Проверить Redis
  2. На cache hit → вернуть ответ
  3. На cache miss → запросить OWM
  4. Сохранить в Redis с TTL=10 min
  5. Вернуть ответ
```

### 2. **Graceful Degradation**
- Если Redis недоступен → работаем без кэша
- Если OpenWeatherMap недоступен → возвращаем ошибку

### 3. **Pydantic v2**
- Используется `@field_validator` (не `@validator`)
- Используется `model_config` (не `class Config`)
- Типизация обязательна

### 4. **Async/Await**
- Все методы API — `async def`
- Используется `httpx.AsyncClient` (не `requests`)
- Redis операции обёрнуты в `async def`

### 5. **Безопасность**
- API_KEY не логируется
- Конфиг читается только из переменных окружения
- Не раскрываются внутренние детали в ошибках

## Зависимости между классами

```
FastAPIApp
  ├── AppState (держит все сервисы)
  │   ├── CacheService (управляет WeatherResponse)
  │   ├── OpenWeatherMapClient (возвращает WeatherResponse)
  │   └── Redis (хранилище для CacheService)
  │
  ├── WeatherResponse (ответ /weather/{city})
  ├── SubscribeRequest (запрос /subscribe)
  ├── SubscriptionResponse (ответ /subscribe)
  └── OpenWeatherMapError иерархия (обработка ошибок)
```

