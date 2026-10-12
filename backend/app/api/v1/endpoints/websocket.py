"""WebSocket endpoint for real-time updates"""
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional

from app.core.websocket import manager
from app.core.security import decode_access_token


router = APIRouter()


async def get_user_id_from_token(token: Optional[str] = Query(None)) -> Optional[str]:
    """Extract user ID from JWT token"""
    if not token:
        return None
    
    try:
        payload = decode_access_token(token)
        return payload.get("sub")
    except Exception:
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time updates
    
    Connect with: ws://localhost:8000/api/v1/ws?token=YOUR_JWT_TOKEN
    
    Message types received:
    - {"type": "alert", "data": {...}}
    - {"type": "inventory_update", "data": {...}}
    - {"type": "batch_update", "data": {...}}
    - {"type": "dashboard_refresh", "data": {...}}
    
    Client can send:
    - {"type": "ping"} - Keep-alive
    - {"type": "subscribe", "channel": "alerts"}
    """
    # Extract user ID from token; reject connections without a valid token
    # instead of allowing anonymous access to live inventory/alert broadcasts.
    user_id = await get_user_id_from_token(token)

    if not user_id:
        await websocket.close(code=4401)
        return

    # Connect
    await manager.connect(websocket, user_id)
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "data": {
                "user_id": user_id,
                "message": "Connected to Ink Inventory WebSocket"
            }
        })
        
        # Listen for messages
        while True:
            try:
                # Wait for message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle ping/pong
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                # Handle subscribe requests (future feature)
                elif message.get("type") == "subscribe":
                    channel = message.get("channel", "all")
                    await websocket.send_json({
                        "type": "subscribed",
                        "data": {"channel": channel}
                    })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON"}
                })
                
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user_id)
    except Exception as e:
        print(f">> WebSocket error: {e}")
        await manager.disconnect(websocket, user_id)
