# token_manager.py
import json
import secrets
import sys
from pathlib import Path
from typing import List, Dict, Any

TOKEN_FILE = Path("api_tokens.json")

def initialize_token_file():
    """Creates a default token file if it doesn't exist."""
    if not TOKEN_FILE.exists():
        print(f"Creating default token file at: {TOKEN_FILE}")
        default_token = {"name": "default-user", "token": "replace-with-your-real-api-token"}
        save_token_objects([default_token])

def get_token_objects() -> List[Dict[str, Any]]:
    """Reads the list of token objects from the JSON file."""
    if not TOKEN_FILE.exists():
        return []
    try:
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except (json.JSONDecodeError, IOError):
        return []

def get_tokens() -> List[str]:
    """Extracts just the token strings from the token objects."""
    token_objects = get_token_objects()
    return [obj["token"] for obj in token_objects if isinstance(obj, dict) and "token" in obj]

def save_token_objects(tokens: List[Dict[str, Any]]):
    """Saves a list of token objects to the JSON file."""
    try:
        with open(TOKEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(tokens, f, indent=2)
    except IOError as e:
        print(f"Error saving token file: {e}")

def add_token(username: str):
    """Generates a new token for a user and adds it to the file."""
    if not username:
        print("Error: Username cannot be empty.", file=sys.stderr)
        return

    token_objects = get_token_objects()
    
    # Check if username already exists
    if any(obj.get("name") == username for obj in token_objects):
        print(f"Error: User '{username}' already exists.", file=sys.stderr)
        return

    # Generate a new, URL-safe token
    new_token = secrets.token_urlsafe(32)
    
    token_objects.append({"name": username, "token": new_token})
    save_token_objects(token_objects)
    print(f"Successfully added token for user '{username}'.")
    print(f"New Token: {new_token}")

if __name__ == "__main__":
    # Allows running as a script: python -m token_manager add <username>
    if len(sys.argv) == 3 and sys.argv[1] == 'add':
        username_to_add = sys.argv[2]
        # Ensure the file exists before trying to add to it
        if not TOKEN_FILE.exists():
            initialize_token_file()
        add_token(username_to_add)
    else:
        print("Usage: python -m token_manager add <username>", file=sys.stderr)
        sys.exit(1)