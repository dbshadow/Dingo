import uvicorn
import asyncio
import uuid
import os
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, Request, WebSocket, UploadFile, File, Form, WebSocketDisconnect, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.status import HTTP_401_UNAUTHORIZED
from fastapi.security import APIKeyHeader

from process import process_csv

# 載入 .env 文件中的環境變數
load_dotenv()

# 從環境變數讀取 API Token
API_TOKEN = os.getenv("API_TOKEN")

# --- 啟動時檢查 ---
if not API_TOKEN:
    print("\033[91mFATAL: API_TOKEN not found in environment variables or .env file.\033[0m")
    print("Please create a .env file and add a line like: API_TOKEN=\"your-secret-token\"")
    exit(1)
# --- 檢查結束 ---

app = FastAPI()

API_KEY_HEADER = APIKeyHeader(name="X-API-Token")

# 設置模板和靜態文件目錄
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 臨時上傳文件的存放位置
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# 用於追蹤背景任務和 WebSocket 連線
active_tasks = {}
active_websockets = {}

# API Token 驗證函式 (FastAPI Dependency)
async def verify_api_token(api_key: str = Depends(API_KEY_HEADER)):
    if api_key != API_TOKEN:
        raise HTTPException(status_code=HTTP_401_UNAUTHORIZED, detail="Invalid or missing API Token")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 保護 /upload 端點
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
        "status": "pending"
    }

    return JSONResponse({"task_id": task_id})

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
                
                await process_csv(
                    csv_path=task_info["file_path"],
                    source_lang=task_info["source_lang"],
                    target_lang=task_info["target_lang"],
                    ollama_host=task_info["ollama_host"],
                    model=task_info["model"],
                    batch_size=task_info["batch_size"],
                    overwrite=task_info["overwrite"],
                    websocket=websocket
                )
                
                if task_id in active_tasks:
                    active_tasks[task_id]["file_path"].unlink(missing_ok=True)
                    del active_tasks[task_id]

    except WebSocketDisconnect:
        print(f"WebSocket {ws_id} disconnected.")
    except Exception as e:
        print(f"An error occurred in WebSocket: {e}")
    finally:
        if ws_id in active_websockets:
            del active_websockets[ws_id]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
