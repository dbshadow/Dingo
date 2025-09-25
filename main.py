# main.py
import uvicorn
import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# --- Pre-flight checks and environment loading ---
load_dotenv()
if not os.getenv("API_TOKEN"):
    print("FATAL: API_TOKEN not found in .env file. The application cannot start.")
    exit(1)
if not os.getenv("OLLAMA_HOST") or not os.getenv("OLLAMA_MODEL"):
    print("FATAL: OLLAMA_HOST or OLLAMA_MODEL not found in .env file. The application cannot start.")
    exit(1)

# --- Local Module Imports ---
# These must come after the dotenv load
from storage import initialize_tasks_file
from worker import run_background_worker, get_running_tasks_dict
from routers import tasks, idml, live, ws, prompt

# --- App Lifecycle (Lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown events.
    """
    print("Application starting up...")
    Path("uploads").mkdir(exist_ok=True) # Ensure uploads directory exists
    # Initialize the tasks.json file if it doesn't exist
    initialize_tasks_file()
    
    # Start the background worker, passing it the WebSocket manager from the ws router
    worker_task = asyncio.create_task(run_background_worker(ws.manager))
    
    yield
    
    print("Application shutting down...")
    # --- Graceful Shutdown ---
    # 1. Cancel the main worker loop
    worker_task.cancel()
    
    # 2. Cancel all tasks that were running inside the worker
    running_tasks = get_running_tasks_dict()
    if running_tasks:
        print(f"Cancelling {len(running_tasks)} running tasks...")
        for task in running_tasks.values():
            task.cancel()
        # Wait for all cancellations to complete
        await asyncio.gather(*running_tasks.values(), return_exceptions=True)

    print("Background worker and all running tasks have been stopped.")


# --- FastAPI App Initialization ---
app = FastAPI(
    title="Dlink Translator",
    description="A tool to translate CSV and IDML files using local LLMs.",
    version="1.0.0",
    lifespan=lifespan
)

# --- Mount Static Files ---
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Include API Routers ---
app.include_router(tasks.router)
app.include_router(idml.router)
app.include_router(live.router)
app.include_router(ws.router) # Include the WebSocket router
app.include_router(prompt.router)

# --- Root Endpoint ---
@app.get("/")
async def read_root(request: Request):
    """Serves the main index.html file."""
    return FileResponse('templates/index.html')

# --- Main Entry Point ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
