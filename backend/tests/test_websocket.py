"""Tests for WebSocket functionality"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from fastapi import WebSocket

from app.core.websocket import ConnectionManager


@pytest.fixture
def connection_manager():
    """Create connection manager instance"""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket"""
    ws = AsyncMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connection_manager_initialization(connection_manager):
    """Test connection manager initializes correctly"""
    assert connection_manager.active_connections == {}
    assert connection_manager.get_connection_count() == 0


@pytest.mark.asyncio
async def test_connect_user(connection_manager, mock_websocket):
    """Test connecting a user"""
    user_id = "test-user-123"
    
    await connection_manager.connect(mock_websocket, user_id)
    
    assert user_id in connection_manager.active_connections
    assert mock_websocket in connection_manager.active_connections[user_id]
    assert connection_manager.get_connection_count() == 1
    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_connect_multiple_users(connection_manager, mock_websocket):
    """Test connecting multiple users"""
    ws1 = mock_websocket
    ws2 = AsyncMock(spec=WebSocket)
    ws2.accept = AsyncMock()
    
    await connection_manager.connect(ws1, "user1")
    await connection_manager.connect(ws2, "user2")
    
    assert connection_manager.get_connection_count() == 2
    assert "user1" in connection_manager.active_connections
    assert "user2" in connection_manager.active_connections


@pytest.mark.asyncio
async def test_connect_same_user_multiple_connections(connection_manager):
    """Test same user with multiple connections"""
    ws1 = AsyncMock(spec=WebSocket)
    ws1.accept = AsyncMock()
    ws2 = AsyncMock(spec=WebSocket)
    ws2.accept = AsyncMock()
    
    user_id = "user1"
    await connection_manager.connect(ws1, user_id)
    await connection_manager.connect(ws2, user_id)
    
    assert connection_manager.get_connection_count() == 2
    assert len(connection_manager.active_connections[user_id]) == 2


@pytest.mark.asyncio
async def test_disconnect_user(connection_manager, mock_websocket):
    """Test disconnecting a user"""
    user_id = "user1"
    await connection_manager.connect(mock_websocket, user_id)
    
    await connection_manager.disconnect(mock_websocket, user_id)
    
    assert user_id not in connection_manager.active_connections
    assert connection_manager.get_connection_count() == 0


@pytest.mark.asyncio
async def test_send_personal_message(connection_manager, mock_websocket):
    """Test sending personal message to user"""
    user_id = "user1"
    await connection_manager.connect(mock_websocket, user_id)
    
    message = {"type": "test", "data": "Hello"}
    await connection_manager.send_personal_message(message, user_id)
    
    mock_websocket.send_text.assert_called_once()
    call_args = mock_websocket.send_text.call_args[0][0]
    assert "test" in call_args
    assert "Hello" in call_args


@pytest.mark.asyncio
async def test_send_personal_message_nonexistent_user(connection_manager):
    """Test sending message to non-existent user"""
    message = {"type": "test", "data": "Hello"}
    
    # Should not raise error
    await connection_manager.send_personal_message(message, "nonexistent")


@pytest.mark.asyncio
async def test_broadcast_message(connection_manager):
    """Test broadcasting message to all users"""
    ws1 = AsyncMock(spec=WebSocket)
    ws1.accept = AsyncMock()
    ws1.send_text = AsyncMock()
    
    ws2 = AsyncMock(spec=WebSocket)
    ws2.accept = AsyncMock()
    ws2.send_text = AsyncMock()
    
    await connection_manager.connect(ws1, "user1")
    await connection_manager.connect(ws2, "user2")
    
    message = {"type": "broadcast", "data": "Hello everyone"}
    await connection_manager.broadcast(message)
    
    ws1.send_text.assert_called_once()
    ws2.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_broadcast_exclude_user(connection_manager):
    """Test broadcasting with user exclusion"""
    ws1 = AsyncMock(spec=WebSocket)
    ws1.accept = AsyncMock()
    ws1.send_text = AsyncMock()
    
    ws2 = AsyncMock(spec=WebSocket)
    ws2.accept = AsyncMock()
    ws2.send_text = AsyncMock()
    
    await connection_manager.connect(ws1, "user1")
    await connection_manager.connect(ws2, "user2")
    
    message = {"type": "broadcast", "data": "Hello"}
    await connection_manager.broadcast(message, exclude_user="user1")
    
    ws1.send_text.assert_not_called()
    ws2.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_send_alert(connection_manager, mock_websocket):
    """Test sending alert notification"""
    await connection_manager.connect(mock_websocket, "user1")
    
    alert_data = {
        "id": "alert-123",
        "title": "Test Alert",
        "severity": "CRITICAL"
    }
    
    await connection_manager.send_alert(alert_data)
    
    mock_websocket.send_text.assert_called_once()
    call_args = mock_websocket.send_text.call_args[0][0]
    assert "alert" in call_args
    assert "alert-123" in call_args


@pytest.mark.asyncio
async def test_send_inventory_update(connection_manager, mock_websocket):
    """Test sending inventory update"""
    await connection_manager.connect(mock_websocket, "user1")
    
    update_data = {"item_id": "item-123", "new_quantity": 50}
    await connection_manager.send_inventory_update(update_data)
    
    mock_websocket.send_text.assert_called_once()
    call_args = mock_websocket.send_text.call_args[0][0]
    assert "inventory_update" in call_args


@pytest.mark.asyncio
async def test_send_batch_update(connection_manager, mock_websocket):
    """Test sending batch update"""
    await connection_manager.connect(mock_websocket, "user1")
    
    batch_data = {"batch_id": "batch-123", "status": "SCRAP"}
    await connection_manager.send_batch_update(batch_data)
    
    mock_websocket.send_text.assert_called_once()
    call_args = mock_websocket.send_text.call_args[0][0]
    assert "batch_update" in call_args


@pytest.mark.asyncio
async def test_send_dashboard_refresh(connection_manager, mock_websocket):
    """Test sending dashboard refresh"""
    await connection_manager.connect(mock_websocket, "user1")
    
    await connection_manager.send_dashboard_refresh()
    
    mock_websocket.send_text.assert_called_once()
    call_args = mock_websocket.send_text.call_args[0][0]
    assert "dashboard_refresh" in call_args


@pytest.mark.asyncio
async def test_websocket_error_handling(connection_manager):
    """Test WebSocket handles errors gracefully"""
    ws = AsyncMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock(side_effect=Exception("Connection error"))
    
    await connection_manager.connect(ws, "user1")
    
    # Should not raise error
    message = {"type": "test", "data": "test"}
    await connection_manager.send_personal_message(message, "user1")
    
    # Connection should be cleaned up
    assert connection_manager.get_connection_count() == 0
