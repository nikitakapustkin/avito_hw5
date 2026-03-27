"""Pytest configuration and shared fixtures."""

import pytest
import asyncio
from unittest.mock import MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis():
    """Fixture for mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=None)
    redis_mock.set = MagicMock(return_value=True)
    redis_mock.setex = MagicMock(return_value=True)
    redis_mock.delete = MagicMock(return_value=1)
    redis_mock.ping = MagicMock(return_value=True)
    return redis_mock


@pytest.fixture
def sample_weather_dict():
    """Fixture for sample weather data as dict."""
    return {
        "main": {
            "temp": 15.5,
            "humidity": 72,
        },
        "weather": [
            {"main": "Overcast clouds"},
        ],
        "wind": {
            "speed": 3.5,
        },
    }
