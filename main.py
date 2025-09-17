import asyncio
import os
import uuid
from pathlib import Path

import ollama
import uvicorn
from dotenv import load_dotenv
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.status import HTTP_401_UNAUTHORIZED

from idml_processor import extract_idml_to_csv, rebuild_idml_from_csv
from process import process_csv
from translator import translate_text

# Load environment variables from .env file
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    print("\033[91mFATAL: API_TOKEN not found in environment variables or .env file.\033[0m")
    print('Please create a .env file and add a line like: API_TOKEN="your-secret-token"'
    )
    exit(1)

app = FastAPI()

API_KEY_HEADER = APIKeyHeader(name="X-API-Token")

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

active_tasks = {}
active_websockets = {}


async def verify_api_token(api_key: str = Depends(API_KEY_HEADER)):
    if api_key != API_TOKEN:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Token"
        )


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# --- CSV Translator Endpoints ---
@app.post("/upload", dependencies=[Depends(verify_api_token)])
async def handle_upload(
    csv_file: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
    overwrite: bool = Form(False),
    ollama_host: str = Form("http://192.168.7.149:11434"),
    model: str = Form("gpt-oss:20b"),
    batch_size: int = Form(10),
):
    task_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{task_id}_{csv_file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(await csv_file.read())
    active_tasks[task_id] = {
        "file_path": file_path,
        "source_lang": source_lang,
        "target_lang": target_lang,
        "ollama_host": ollama_host,
        "model": model,
        "batch_size": batch_size,
        "overwrite": overwrite,
        "status": "pending",
    }
    return JSONResponse({"task_id": task_id})


# --- IDML Tools Endpoints ---
@app.post("/extract_idml", dependencies=[Depends(verify_api_token)])
async def handle_idml_extraction(idml_file: UploadFile = File(...)):
    temp_idml_path = UPLOAD_DIR / f"temp_{idml_file.filename}"
    try:
        with open(temp_idml_path, "wb") as buffer:
            buffer.write(await idml_file.read())
        csv_content = extract_idml_to_csv(temp_idml_path)
        output_filename = f"{Path(idml_file.filename).stem}.csv"
        headers = {"Content-Disposition": f'attachment; filename="{output_filename}"'}
        return Response(content=csv_content, media_type="text/csv", headers=headers)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_idml_path.exists():
            temp_idml_path.unlink()


@app.post("/rebuild_idml", dependencies=[Depends(verify_api_token)])
async def handle_idml_rebuild(
    original_idml: UploadFile = File(...), translated_csv: UploadFile = File(...)
):
    temp_idml_path = UPLOAD_DIR / f"temp_rebuild_{original_idml.filename}"
    temp_csv_path = UPLOAD_DIR / f"temp_rebuild_{translated_csv.filename}"
    try:
        with open(temp_idml_path, "wb") as buffer:
            buffer.write(await original_idml.read())
        with open(temp_csv_path, "wb") as buffer:
            buffer.write(await translated_csv.read())
        rebuilt_idml_content = rebuild_idml_from_csv(temp_idml_path, temp_csv_path)
        output_filename = f"{Path(original_idml.filename).stem}_translated.idml"
        headers = {"Content-Disposition": f'attachment; filename="{output_filename}"'}
        return Response(
            content=rebuilt_idml_content,
            media_type="application/vnd.adobe.indesign-idml-package",
            headers=headers,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if temp_idml_path.exists():
            temp_idml_path.unlink()
        if temp_csv_path.exists():
            temp_csv_path.unlink()


# --- Live Translator Endpoint ---
class LiveTranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str
    model: str = "gpt-oss:20b"
    ollama_host: str = "http://192.168.7.149:11434"


@app.post("/live_translate", dependencies=[Depends(verify_api_token)])
async def handle_live_translation(request: LiveTranslateRequest):
    try:
        client = ollama.AsyncClient(host=request.ollama_host)
        translated_text = await translate_text(
            client=client,
            text_to_translate=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang,
            model=request.model,
        )
        return {"translated_text": translated_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- WebSocket Handler ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    ws_id = str(uuid.uuid4())
    active_websockets[ws_id] = websocket
    try:
        message = await websocket.receive_json()
        task_id = message.get("task_id")
        if task_id and task_id in active_tasks:
            task_info = active_tasks[task_id]
            if task_info["status"] == "pending":
                task_info["status"] = "running"
                await process_csv(websocket=websocket, **task_info)
                if task_id in active_tasks:
                    active_tasks[task_id]["file_path"].unlink(missing_ok=True)
                    del active_tasks[task_id]
    except WebSocketDisconnect:
        print(f"WebSocket {ws_id} disconnected.")
    finally:
        if ws_id in active_websockets:
            del active_websockets[ws_id]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
