
import pytest
import os
from pathlib import Path

# This fixture will be automatically used by tests in the same directory or subdirectories.
@pytest.fixture(autouse=True)
def clean_tasks_before_test():
    """
    A pytest fixture that automatically runs before each test.
    It ensures the testing environment is clean by deleting the tasks.json file.
    """
    # Define the path to the tasks.json file relative to the project root
    tasks_file = Path(__file__).parent.parent / "tasks.json"
    
    # --- SETUP ---
    # This code runs before each test
    if tasks_file.exists():
        try:
            os.remove(tasks_file)
            print(f"\n[Setup] Cleared old '{tasks_file.name}' for a clean test run.")
        except OSError as e:
            print(f"\n[Setup] Error removing file {tasks_file.name}: {e}")

    # 'yield' passes control to the test function.
    yield

    # --- TEARDOWN ---
    # This code runs after each test is finished
    # You could add cleanup here if needed, for now, we'll just re-clear
    if tasks_file.exists():
        try:
            os.remove(tasks_file)
            # print(f"\n[Teardown] Cleared '{tasks_file.name}' after test.")
        except OSError as e:
            print(f"\n[Teardown] Error removing file {tasks_file.name}: {e}")
