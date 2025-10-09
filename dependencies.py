# dependencies.py
import os
from typing import List
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED

API_TOKENS_STR = os.getenv("API_TOKENS")
VALID_TOKENS: List[str] = API_TOKENS_STR.split(',') if API_TOKENS_STR else []

API_KEY_HEADER = APIKeyHeader(name="X-API-Token", auto_error=False)

async def get_current_api_token(api_key: str = Depends(API_KEY_HEADER)) -> str:
    if not VALID_TOKENS:
        raise HTTPException(
            status_code=500, 
            detail="API_TOKENS are not configured on the server. Please check .env file."
        )
    if api_key is None or api_key not in VALID_TOKENS:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, 
            detail="Invalid or missing API Token"
        )
    return api_key

# For backward compatibility, we can have a simple verification dependency
async def verify_api_token(api_key: str = Depends(get_current_api_token)):
    pass
