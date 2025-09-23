import uvicorn
import asyncio
import uuid
import os
import json
import ollama

from pathlib import Path
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from fastapi import FastAPI, Request, WebSocket, UploadFile, File, Form, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_404_NOT_FOUND
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from process import process_csv, process_idml # Import the new idml processor
from idml_processor import extract_idml_to_csv, rebuild_idml_from_csv
from translator import translate_text # For Live Translator

# --- Initial Setup ---
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
if not API_TOKEN:
    print("FATAL: API_TOKEN not found. Please create a .env file.")
    exit(1)

OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
if not OLLAMA_HOST and OLLAMA_MODEL:
    print("FATAL: OLLAMA_HOST or OLLAMA_MODEL not found. Please create a .env file.")
    exit(1)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
TASKS_FILE = Path("tasks.json")

# --- Global State ---
running_async_tasks: Dict[str, asyncio.Task[Any]] = {}

# --- Data Models & State Management ---
def read_tasks() -> List[Dict]:
    if not TASKS_FILE.exists():
        return []
    with open(TASKS_FILE, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def write_tasks(tasks: List[Dict]):
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_tasks(self):
        tasks = read_tasks()
        message = {"type": "tasks_update", "payload": tasks}
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# --- Background Worker ---
async def background_worker():
    print("Background worker started.")
    while True:
        tasks = read_tasks()
        if not any(task["status"] == "running" for task in tasks):
            pending_task = next((task for task in tasks if task["status"] == "pending"), None)
            if pending_task:
                task_id = pending_task['id']
                print(f"Worker picked up task: {task_id} (type: {pending_task.get('file_type')})")

                for task in tasks:
                    if task['id'] == task_id:
                        task["status"] = "running"
                write_tasks(tasks)
                await manager.broadcast_tasks()

                async def progress_callback(processed, total):
                    current_tasks = read_tasks()
                    task_to_update = next((t for t in current_tasks if t["id"] == task_id), None)
                    if task_to_update:
                        task_to_update["progress"] = {"processed": processed, "total": total}
                        write_tasks(current_tasks)
                        await manager.broadcast_tasks()

                glossary_path_str = pending_task.get("glossary_path")
                glossary_path = Path(glossary_path_str) if glossary_path_str else None
                file_type = pending_task.get("file_type", "csv")

                # Choose the correct processing function based on file type
                if file_type == 'idml':
                    process_function = process_idml
                    path_argument = {"idml_path": Path(pending_task["filepath"])}
                else: # Default to csv
                    process_function = process_csv
                    path_argument = {"csv_path": Path(pending_task["filepath"])}

                process_task = asyncio.create_task(
                    process_function(
                        **path_argument,
                        source_lang=pending_task["source_lang"],
                        target_lang=pending_task["target_lang"],
                        overwrite=pending_task["overwrite"],
                        progress_callback=progress_callback,
                        ollama_host=pending_task.get("ollama_host"),
                        model=pending_task.get("model"),
                        batch_size=pending_task.get("batch_size", 10),
                        glossary_path=glossary_path
                    )
                )
                running_async_tasks[task_id] = process_task

                try:
                    await process_task
                    final_status = "completed"
                except asyncio.CancelledError:
                    print(f"Task {task_id} was cancelled externally.")
                    final_status = "cancelled"
                except Exception as e:
                    print(f"Task {task_id} failed: {e}")
                    final_status = "error"
                finally:
                    if task_id in running_async_tasks:
                        del running_async_tasks[task_id]
                    current_tasks = read_tasks()
                    task_exists = any(t['id'] == task_id for t in current_tasks)
                    if task_exists:
                        for task in current_tasks:
                            if task['id'] == task_id:
                                task["status"] = final_status
                        write_tasks(current_tasks)
                    await manager.broadcast_tasks()

        await asyncio.sleep(5)

# --- App Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not TASKS_FILE.exists():
        write_tasks([])
    worker_task = asyncio.create_task(background_worker())
    yield
    for task_id, task in running_async_tasks.items():
        print(f"Cancelling task {task_id} on shutdown...")
        task.cancel()
    await asyncio.gather(*running_async_tasks.values(), return_exceptions=True)
    worker_task.cancel()
    print("Background worker and all running tasks stopped.")

app = FastAPI(lifespan=lifespan)

# --- Security & Static Files ---
API_KEY_HEADER = APIKeyHeader(name="X-API-Token")
app.mount("/static", StaticFiles(directory="static"), name="static")

async def verify_api_token(api_key: str = Depends(API_KEY_HEADER)):
    if api_key != API_TOKEN:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Token")

# --- API Endpoints ---
@app.get("/")
async def read_root(request: Request):
    return FileResponse('templates/index.html')

@app.get("/tasks", dependencies=[Depends(verify_api_token)])
async def get_tasks():
    return read_tasks()

@app.post("/upload", dependencies=[Depends(verify_api_token)])
async def handle_upload(
    upload_file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    overwrite: bool = Form(False),
    glossary_file: UploadFile | None = File(None),
    note: str = Form("")
):
    original_filename = upload_file.filename
    file_extension = Path(original_filename).suffix.lower()

    if file_extension not in [".csv", ".idml"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only .csv and .idml files are accepted.")

    file_type = file_extension.strip('.')
    task_id = str(uuid.uuid4())
    filepath = UPLOAD_DIR / f"{task_id}_{original_filename}"
    with open(filepath, "wb") as buffer:
        buffer.write(await upload_file.read())

    glossary_filepath_str = None
    if glossary_file and glossary_file.filename:
        glossary_filepath = UPLOAD_DIR / f"{task_id}_glossary_{glossary_file.filename}"
        with open(glossary_filepath, "wb") as buffer:
            buffer.write(await glossary_file.read())
        glossary_filepath_str = str(glossary_filepath)
    
    new_task = {
        "id": task_id,
        "filename": original_filename,
        "filepath": str(filepath),
        "file_type": file_type,
        "status": "pending",
        "progress": {"processed": 0, "total": 0},
        "source_lang": source_lang,
        "target_lang": target_lang,
        "overwrite": overwrite,
        "glossary_path": glossary_filepath_str,
        "note": note,
        "ollama_host": OLLAMA_HOST,
        "model": OLLAMA_MODEL,
        "batch_size": 10,
    }
    tasks = read_tasks()
    tasks.append(new_task)
    write_tasks(tasks)
    await manager.broadcast_tasks()
    return JSONResponse({"message": "Task added to queue"})

@app.delete("/tasks/{task_id}", dependencies=[Depends(verify_api_token)])
async def delete_task(task_id: str):
    tasks = read_tasks()
    task_to_delete = next((t for t in tasks if t["id"] == task_id), None)

    if not task_to_delete:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")

    if task_id in running_async_tasks:
        print(f"Cancelling running task {task_id}...")
        running_async_tasks[task_id].cancel()

    remaining_tasks = [t for t in tasks if t["id"] != task_id]
    write_tasks(remaining_tasks)

    try:
        filepath = Path(task_to_delete["filepath"])
        if filepath.exists():
            filepath.unlink()
        
        file_type = task_to_delete.get("file_type", "csv")
        if file_type == 'idml':
            processed_filepath = filepath.with_name(f"{filepath.stem}_processed.idml")
        else:
            processed_filepath = filepath.with_name(f"{filepath.stem}_processed.csv")

        if processed_filepath.exists():
            processed_filepath.unlink()

    except Exception as e:
        print(f"Error during file cleanup for task {task_id}: {e}")

    await manager.broadcast_tasks()
    return JSONResponse(content={"message": f"Task {task_id} has been deleted."})

@app.get("/download/{task_id}", dependencies=[Depends(verify_api_token)])
async def download_file(task_id: str):
    tasks = read_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")

    original_filepath = Path(task["filepath"])
    file_type = task.get("file_type", "csv")
    target_lang = task.get("target_lang", "unknown")
    original_stem = Path(task['filename']).stem

    # Handle completed tasks
    if task["status"] == "completed":
        if file_type == 'idml':
            processed_filepath = original_filepath.with_name(f"{original_filepath.stem}_processed.idml")
            if processed_filepath.exists():
                download_filename = f"{original_stem}_translated_{target_lang}.idml"
                return FileResponse(
                    processed_filepath,
                    #filename=download_filename,
                    media_type="application/octet-stream",
                    headers={
                        "Content-Disposition": f'attachment; filename="{download_filename}"'
                    }
                )
        else:  # csv
            processed_filepath = original_filepath.with_name(f"{original_filepath.stem}_processed.csv")
            if processed_filepath.exists():
                download_filename = f"{original_stem}_translated_{target_lang}.csv"
                return FileResponse(
                    processed_filepath,
                    filename=download_filename,
                    media_type="text/csv"
                )

    # Handle running tasks
    if task["status"] == "running":
        if file_type == 'idml':
            processed_filepath = original_filepath.with_name(f"{original_filepath.stem}_temp_processed.csv")
            if processed_filepath.exists():
                download_filename = f"{original_stem}_inprogress_{target_lang}.csv"
                return FileResponse(
                    processed_filepath,
                    filename=download_filename,
                    media_type="text/csv"
                )
        else:  # csv
            processed_filepath = original_filepath.with_name(f"{original_filepath.stem}_processed.csv")
            if processed_filepath.exists():
                download_filename = f"{original_stem}_inprogress_{target_lang}.csv"
                return FileResponse(
                    processed_filepath,
                    filename=download_filename,
                    media_type="text/csv"
                )

    # Fallback to original file
    if original_filepath.exists():
        return FileResponse(original_filepath, filename=task["filename"])
    else:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="File not found")

# --- IDML Tools Endpoints ---
@app.post("/extract_idml", dependencies=[Depends(verify_api_token)])
async def handle_idml_extraction(idml_file: UploadFile = File(...)):
    temp_idml_path = UPLOAD_DIR / f"temp_{idml_file.filename}"
    try:
        with open(temp_idml_path, "wb") as buffer:
            buffer.write(await idml_file.read())
        csv_content = extract_idml_to_csv(temp_idml_path)
        output_filename = f"{Path(idml_file.filename).stem}.csv"
        headers = {'Content-Disposition': f'attachment; filename="{output_filename}"'}
        return Response(content=csv_content, media_type="text/csv", headers=headers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_idml_path.exists():
            temp_idml_path.unlink()

@app.post("/rebuild_idml", dependencies=[Depends(verify_api_token)])
async def handle_idml_rebuild(original_idml: UploadFile = File(...), translated_csv: UploadFile = File(...)):
    temp_idml_path = UPLOAD_DIR / f"temp_rebuild_{original_idml.filename}"
    temp_csv_path = UPLOAD_DIR / f"temp_rebuild_{translated_csv.filename}"
    try:
        with open(temp_idml_path, "wb") as buffer:
            buffer.write(await original_idml.read())
        with open(temp_csv_path, "wb") as buffer:
            buffer.write(await translated_csv.read())
        rebuilt_idml_content = rebuild_idml_from_csv(temp_idml_path, temp_csv_path)
        output_filename = f"{Path(original_idml.filename).stem}_translated.idml"
        headers = {'Content-Disposition': f'attachment; filename="{output_filename}"'}
        return Response(content=rebuilt_idml_content, media_type="application/vnd.adobe.indesign-idml-package", headers=headers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_idml_path.exists(): temp_idml_path.unlink()
        if temp_csv_path.exists(): temp_csv_path.unlink()

# --- Live Translator Endpoint ---
class LiveTranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str

@app.post("/live_translate", dependencies=[Depends(verify_api_token)])
async def live_translate(request: LiveTranslateRequest):
    try:
        client = ollama.AsyncClient(host=OLLAMA_HOST)
        translated = await translate_text(
            client=client,
            text_to_translate=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            model=OLLAMA_MODEL,
        )
        return {"translated_text": translated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)