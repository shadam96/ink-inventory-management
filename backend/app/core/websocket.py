"""WebSocket connection manager for real-time updates"""
import json
from typing import Dict, Set, Optional
from uuid import UUID
from fastapi import WebSocket, WebSocketDisconnect
import asyncio


class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""
    
    def __init__(self):
        # Map of user_id -> set of websocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        
        print(f">> WebSocket connected: user {user_id} (total: {self.get_connection_count()})")
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection"""
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        
        print(f">> WebSocket disconnected: user {user_id} (total: {self.get_connection_count()})")
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(conns) for conns in self.active_connections.values())
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user (all their connections)"""
        if user_id not in self.active_connections:
            return
        
        json_message = json.dumps(message)
        disconnected = []
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(json_message)
            except Exception as e:
                print(f">> Error sending to websocket: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected websockets
        if disconnected:
            async with self._lock:
                for ws in disconnected:
                    self.active_connections[user_id].discard(ws)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
    
    async def broadcast(self, message: dict, exclude_user: Optional[str] = None):
        """Broadcast a message to all connected users"""
        json_message = json.dumps(message)
        
        for user_id, connections in list(self.active_connections.items()):
            if exclude_user and user_id == exclude_user:
                continue
            
            for websocket in list(connections):
                try:
                    await websocket.send_text(json_message)
                except Exception:
                    pass
    
    async def broadcast_to_roles(self, message: dict, roles: Set[str]):
        """Broadcast to users with specific roles (requires role info)"""
        # This would need role information passed during connection
        # For now, just broadcast to all
        await self.broadcast(message)
    
    async def send_alert(self, alert_data: dict, user_ids: Optional[Set[str]] = None):
        """Send alert notification to specific users or all"""
        message = {
            "type": "alert",
            "data": alert_data
        }
        
        if user_ids:
            for user_id in user_ids:
                await self.send_personal_message(message, user_id)
        else:
            await self.broadcast(message)
    
    async def send_inventory_update(self, update_data: dict):
        """Broadcast inventory update to all users"""
        message = {
            "type": "inventory_update",
            "data": update_data
        }
        await self.broadcast(message)
    
    async def send_batch_update(self, batch_data: dict):
        """Broadcast batch status change"""
        message = {
            "type": "batch_update",
            "data": batch_data
        }
        await self.broadcast(message)
    
    async def send_dashboard_refresh(self):
        """Trigger dashboard refresh for all users"""
        message = {
            "type": "dashboard_refresh",
            "data": {"timestamp": str(asyncio.get_event_loop().time())}
        }
        await self.broadcast(message)


# Global connection manager instance
manager = ConnectionManager()
