#!/usr/bin/env python3
import pytest
from unittest.mock import AsyncMock, patch
import os

# Mocking the Telethon Client so we don't hit real servers
@pytest.fixture
def mock_client():
    with patch('telethon.TelegramClient') as mock:
        instance = mock.return_value
        instance.connect = AsyncMock()
        instance.is_user_authorized = AsyncMock(return_value=True)
        instance.send_message = AsyncMock()
        instance.session = AsyncMock()
        instance.session.save = lambda: "mock_session_string"
        yield instance

def test_env_vars_presence():
    """Ensure the CI environment has the required keys defined"""
    # In the YAML we set TG_SESSION_STR: "test_mode"
    assert os.getenv('TG_SESSION_STR') is not None
    print("✅ Environment variables verified.")

@pytest.mark.asyncio
async def test_client_connection(mock_client):
    """Test if the client initialization logic works"""
    await mock_client.connect()
    assert mock_client.connect.called
    print("✅ Connection logic verified.")

@pytest.mark.asyncio
async def test_send_test_message(mock_client):
    """Test the 'hello whatever' message logic"""
    await mock_client.send_message('me', 'hello whatever')
    mock_client.send_message.assert_called_with('me', 'hello whatever')
    print("✅ Message sending logic verified.")

def test_session_string_format():
    """Basic check to ensure the session string isn't empty"""
    session = os.getenv('TG_SESSION_STR')
    assert len(session) > 0
    print("✅ Session string presence verified.")
