# routers/tasks.py
import uuid
import os
from pathlib import Path

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form
)
from fastapi.responses import FileResponse, JSONResponse
from starlette.status import HTTP_404_NOT_FOUND

from dependencies import verify_api_token
from storage import read_tasks, write_tasks
from worker import get_running_tasks_dict
# Import the WebSocket manager from the ws router to notify it of changes
from routers.ws import manager as ws_manager

# --- Router Setup ---
router = APIRouter(
    prefix="/tasks",
    tags=["Task Management"],
    dependencies=[Depends(verify_api_token)]
)

# --- Constants ---
UPLOAD_DIR = Path("uploads")
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

# --- Endpoints ---

@router.get("/")
async def get_tasks():
    """Get the list of all tasks."""
    return read_tasks()

@router.post("/upload")
async def handle_upload(
    upload_file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    overwrite: bool = Form(False),
    glossary_file: UploadFile | None = File(None),
    note: str = Form("")
):
    """Handles file upload and creates a new translation task."""
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
    await ws_manager.broadcast_tasks()
    return JSONResponse({"message": "Task added to queue"})

@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """Deletes a task and its associated files."""
    tasks = read_tasks()
    task_to_delete = next((t for t in tasks if t["id"] == task_id), None)

    if not task_to_delete:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")

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
async def download_file(task_id: str):
    """Downloads the output file for a given task."""
    task = next((t for t in read_tasks() if t["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Task not found")

    original_filepath = Path(task["filepath"])
    original_stem = Path(task['filename']).stem
    target_lang = task.get("target_lang", "unknown")
    file_type = task.get("file_type", "csv")

    final_idml = original_filepath.with_name(f"{original_filepath.stem}_processed.idml")
    final_csv = original_filepath.with_name(f"{original_filepath.stem}_processed.csv")
    if file_type == 'csv' and final_csv.exists():
        if task["status"] == "completed":
            filename = f"{original_stem}_translated_{target_lang}.csv"
        else:
            filename = f"{original_stem}_inprogress_{target_lang}.csv"
        return FileResponse(
            final_csv,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    if task["status"] == "completed" and file_type == 'idml' and final_idml.exists():
        filename = f"{original_stem}_translated_{target_lang}.idml"
        return FileResponse(
            final_idml,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    print(f"{final_csv}")
    if task["status"] != "completed" and file_type == 'idml' and final_csv.exists():
        filename = f"{original_stem}_inprogress_{target_lang}.csv"
        print(f"{filename}")
        return FileResponse(
            final_csv,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    if original_filepath.exists():
        return FileResponse(original_filepath, filename=task["filename"])

    raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="No downloadable file found for this task.")