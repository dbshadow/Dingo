# routers/tasks.py
import uuid
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form
)
from fastapi.responses import FileResponse, JSONResponse
from starlette.status import HTTP_403_FORBIDDEN, HTTP_404_NOT_FOUND

from dependencies import get_current_api_token
from storage import read_tasks, write_tasks
from worker import get_running_tasks_dict
# Import the WebSocket manager from the ws router to notify it of changes
from routers.ws import manager as ws_manager

# --- Router Setup ---
router = APIRouter(
    prefix="/tasks",
    tags=["Task Management"],
)

# --- Constants ---
UPLOAD_DIR = Path("uploads")
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

# --- Endpoints ---

@router.get("/")
async def get_tasks(api_token: str = Depends(get_current_api_token)):
    """Get the list of all tasks and indicate ownership."""
    all_tasks = read_tasks()
    for task in all_tasks:
        task["is_owner"] = task.get("api_token") == api_token
    return all_tasks

@router.post("/upload")
async def handle_upload(
    upload_file: UploadFile = File(...),
    glossary_file: UploadFile | None = File(None),
    note: str = Form(""),
    api_token: str = Depends(get_current_api_token)
):
    """Handles file upload and creates a new translation task."""
    original_filename = upload_file.filename
    file_extension = Path(original_filename).suffix.lower()

    if file_extension not in [".csv"]:
        raise HTTPException(status_code=400, detail="Invalid file type. Only .csv files are accepted.")

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
        "file_type": "csv",
        "status": "pending",
        "progress": {"processed": 0, "total": 0},
        "glossary_path": glossary_filepath_str,
        "note": note,
        "ollama_host": OLLAMA_HOST,
        "model": OLLAMA_MODEL,
        "batch_size": 10,
        "api_token": api_token  # Associate task with the user's token
    }
    tasks = read_tasks()
    tasks.append(new_task)
    write_tasks(tasks)
    await ws_manager.broadcast_tasks()
    return JSONResponse({"message": "Task added to queue"})

@router.delete("/{task_id}")
async def delete_task(task_id: str, api_token: str = Depends(get_current_api_token)):
    """Deletes a task and its associated files."""
    tasks = read_tasks()
    task_to_delete = next((t for t in tasks if t["id"] == task_id), None)

    if not task_to_delete:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")

    # --- NEW: Ownership Verification ---
    if task_to_delete.get("api_token") != api_token:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="You do not have permission to delete this task.")

    running_tasks = get_running_tasks_dict()
    if task_id in running_tasks:
        print(f"Cancelling running task {task_id} via API delete...")
        running_tasks[task_id].cancel()

    remaining_tasks = [t for t in tasks if t["id"] != task_id]
    write_tasks(remaining_tasks)

    # --- Robust File Cleanup ---
    try:
        files_to_delete = []
        
        # 1. Original uploaded file
        original_filepath = Path(task_to_delete["filepath"])
        files_to_delete.append(original_filepath)

        # 2. Glossary file
        if task_to_delete.get("glossary_path"):
            files_to_delete.append(Path(task_to_delete["glossary_path"]))

        file_type = task_to_delete.get("file_type", "csv")
        
        if file_type == 'idml':
            # 3. Final processed IDML
            files_to_delete.append(original_filepath.with_name(f"{original_filepath.stem}_processed.idml"))
            
            # 4. Intermediate temporary files for IDML process
            # Note: These names must match the ones created in `processor.py`
            temp_csv_path = original_filepath.with_name(f"{original_filepath.stem}.csv")
            translated_temp_csv_path = temp_csv_path.with_name(f"{temp_csv_path.stem}_processed.csv")
            files_to_delete.append(temp_csv_path)
            files_to_delete.append(translated_temp_csv_path)
        else: # csv
            # 3. Final processed CSV
            files_to_delete.append(original_filepath.with_name(f"{original_filepath.stem}_processed.csv"))

        # 5. Perform deletion
        for path in files_to_delete:
            if path and path.exists():
                try:
                    path.unlink()
                    print(f"Deleted file: {path}")
                except OSError as e:
                    print(f"Error deleting file {path}: {e}")

    except Exception as e:
        print(f"An unexpected error occurred during file cleanup for task {task_id}: {e}")

    await ws_manager.broadcast_tasks()
    return JSONResponse(content={"message": f"Task {task_id} has been deleted."})

@router.get("/download/{task_id}")
async def download_file(task_id: str, api_token: str = Depends(get_current_api_token)):
    """Downloads the output file for a given task."""
    task = next((t for t in read_tasks() if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")

    # --- NEW: Ownership Verification ---
    if task.get("api_token") != api_token:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="You do not have permission to download this file.")

    original_filepath = Path(task["filepath"])
    original_stem = Path(task['filename']).stem
    file_type = task.get("file_type", "csv")

    final_idml = original_filepath.with_name(f"{original_filepath.stem}_processed.idml")
    final_csv = original_filepath.with_name(f"{original_filepath.stem}_processed.csv")

    def create_file_response(path, filename):
        ascii_filename = Path(filename).stem.encode('ascii', 'ignore').decode('ascii') + Path(filename).suffix
        utf8_filename = quote(filename)
        headers = {
            "Content-Disposition": f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{utf8_filename}"
        }
        return FileResponse(path, media_type="application/octet-stream", headers=headers)

    # Handle CSV file download
    if file_type == 'csv' and final_csv.exists():
        if task["status"] == "completed":
            filename = f"{original_stem}_translated.csv"
        else:
            filename = f"{original_stem}_inprogress.csv"
        return create_file_response(final_csv, filename)

    # Handle IDML file download (for completed tasks)
    if task["status"] == "completed" and file_type == 'idml' and final_idml.exists():
        filename = f"{original_stem}_translated.idml"
        return create_file_response(final_idml, filename)

    # Handle in-progress IDML download (which serves the intermediate CSV)
    if task["status"] != "completed" and file_type == 'idml' and final_csv.exists():
        filename = f"{original_stem}_inprogress.csv"
        return create_file_response(final_csv, filename)

    # Fallback to original file if no processed file is found
    if original_filepath.exists():
        return create_file_response(original_filepath, task["filename"])

    raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No downloadable file found for this task.")