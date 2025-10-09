# routers/translator.py
import os
import ollama
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from dependencies import verify_api_token
from translator import translate_text

# --- Router Setup ---
router = APIRouter(
    tags=["Live Translation"],
)

# --- Environment & Constants ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

# --- Data Models ---
class LiveTranslateRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str

# --- Endpoint ---
@router.post("/live_translate", dependencies=[Depends(verify_api_token)])
async def live_translate(request: LiveTranslateRequest):
    if not OLLAMA_HOST or not OLLAMA_MODEL:
        raise HTTPException(
            status_code=500, 
            detail="Ollama host or model is not configured on the server."
        )
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
