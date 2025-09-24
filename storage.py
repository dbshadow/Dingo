# storage.py
import json
from pathlib import Path
from typing import List, Dict

TASKS_FILE = Path("tasks.json")

def read_tasks() -> List[Dict]:
    if not TASKS_FILE.exists():
        return []
    # TODO: Consider adding a file lock to prevent race conditions on concurrent writes
    with open(TASKS_FILE, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def write_tasks(tasks: List[Dict]):
    with open(TASKS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=4, ensure_ascii=False)

def initialize_tasks_file():
    if not TASKS_FILE.exists():
        write_tasks([])
