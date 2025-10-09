# dependencies.py
from typing import List
from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_500_INTERNAL_SERVER_ERROR

from token_manager import get_tokens

API_KEY_HEADER = APIKeyHeader(name="X-API-Token", auto_error=False)

def get_valid_tokens() -> List[str]:
    """
    Reads tokens from api_tokens.json via the token_manager.
    This runs on each request, ensuring the token list is always fresh.
    """
    tokens = get_tokens()
    if not tokens:
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No API tokens found in api_tokens.json or the file is invalid."
        )
    return tokens

async def get_current_api_token(api_key: str = Depends(API_KEY_HEADER), valid_tokens: List[str] = Depends(get_valid_tokens)) -> str:
    """
    Validates the provided API key against the list of valid tokens.
    Returns the valid API key if it exists.
    """
    if api_key is None or api_key not in valid_tokens:
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED, 
            detail="Invalid or missing API Token"
        )
    return api_key

# For backward compatibility, we can have a simple verification dependency
async def verify_api_token(api_key: str = Depends(get_current_api_token)):
    """
    A simple dependency that just verifies the token without returning it.
    Useful for routes that need protection but don't need the token itself.
    """
    pass
