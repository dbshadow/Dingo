# routers/ws.py
from typing import List, Tuple
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from storage import read_tasks
from token_manager import get_tokens

class ConnectionManager:
    def __init__(self):
        # Store tuples of (websocket, api_token)
        self.active_connections: List[Tuple[WebSocket, str]] = []

    async def connect(self, websocket: WebSocket, token: str):
        await websocket.accept()
        self.active_connections.append((websocket, token))

    def disconnect(self, websocket: WebSocket):
        connection_to_remove = next((conn for conn in self.active_connections if conn[0] == websocket), None)
        if connection_to_remove:
            self.active_connections.remove(connection_to_remove)

    async def send_tasks_to_connection(self, connection: Tuple[WebSocket, str]):
        websocket, token = connection
        all_tasks = read_tasks()
        
        # Create a personalized list of tasks with ownership info
        tasks_with_ownership = []
        for task in all_tasks:
            task_copy = task.copy()
            task_copy["is_owner"] = task_copy.get("api_token") == token
            tasks_with_ownership.append(task_copy)

        message = {"type": "tasks_update", "payload": tasks_with_ownership}
        try:
            await websocket.send_json(message)
        except (WebSocketDisconnect, RuntimeError):
            self.disconnect(websocket)

    async def broadcast_tasks(self):
        if not self.active_connections:
            return
        # Create a copy for safe iteration
        for connection in list(self.active_connections):
            await self.send_tasks_to_connection(connection)

manager = ConnectionManager()
router = APIRouter()

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    # --- Authenticate WebSocket connection using the token manager ---
    valid_tokens = get_tokens()
    if token not in valid_tokens:
        await websocket.close(code=1008) # Policy Violation
        return

    await manager.connect(websocket, token)
    # Send initial state to the newly connected client
    await manager.send_tasks_to_connection((websocket, token))
    try:
        while True:
            # Keep connection alive. We are not expecting any client messages.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client disconnected from WebSocket.")
