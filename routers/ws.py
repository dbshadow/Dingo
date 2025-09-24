# routers/ws.py
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from storage import read_tasks

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_tasks(self):
        if not self.active_connections:
            return
        tasks = read_tasks()
        message = {"type": "tasks_update", "payload": tasks}
        # Create a copy of the list for safe iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except (WebSocketDisconnect, RuntimeError):
                # Handle cases where connection is closed but not yet removed
                self.disconnect(connection)

manager = ConnectionManager()
router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.broadcast_tasks() # Send initial state
    try:
        while True:
            # Keep connection alive. We are not expecting any client messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected from WebSocket.")
