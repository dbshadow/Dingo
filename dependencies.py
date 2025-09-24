# dependencies.py
import os
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED

API_TOKEN = os.getenv("API_TOKEN")
API_KEY_HEADER = APIKeyHeader(name="X-API-Token")

async def verify_api_token(api_key: str = Depends(API_KEY_HEADER)):
    if not API_TOKEN:
        # This is a server-side configuration error, so 500 is more appropriate.
        raise HTTPException(
            status_code=500, 
            detail="API_TOKEN is not configured on the server. Please check .env file."
        )
    if api_key != API_TOKEN:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, 
            detail="Invalid or missing API Token"
        )