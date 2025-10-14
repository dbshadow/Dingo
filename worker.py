# worker.py
import asyncio
from pathlib import Path
from typing import Dict, Any

from process import process_csv
from storage import read_tasks, write_tasks

# This state is now local to the worker
running_async_tasks: Dict[str, asyncio.Task[Any]] = {}

async def run_background_worker(manager):
    """
    The main background worker loop.
    """
    print("Background worker started.")
    while True:
        tasks = read_tasks()

        # --- Task Cancellation Check ---
        # If a task is in our running list but not in storage anymore (e.g., deleted by user), cancel it.
        running_ids = set(running_async_tasks.keys())
        task_ids_in_storage = {t['id'] for t in tasks}
        
        for task_id in running_ids - task_ids_in_storage:
            print(f"Task {task_id} not found in storage, requesting cancellation.")
            if task_id in running_async_tasks:
                running_async_tasks[task_id].cancel()
                # The main try/except/finally block below will handle the cleanup.

        # --- New Task Execution ---
        # Check if any task is currently running
        is_task_running = any(task["status"] == "running" for task in tasks)

        if not is_task_running:
            pending_task = next((task for task in tasks if task["status"] == "pending"), None)
            
            if pending_task:
                task_id = pending_task['id']
                print(f"Worker picked up task: {task_id} (type: {pending_task.get('file_type')})")

                # Update task status to "running"
                for task in tasks:
                    if task['id'] == task_id:
                        task["status"] = "running"
                write_tasks(tasks)
                await manager.broadcast_tasks()

                async def progress_callback(processed, total):
                    current_tasks = read_tasks()
                    task_to_update = next((t for t in current_tasks if t["id"] == task_id), None)
                    if task_to_update:
                        task_to_update["progress"] = {"processed": processed, "total": total}
                        write_tasks(current_tasks)
                        await manager.broadcast_tasks()

                glossary_path_str = pending_task.get("glossary_path")
                glossary_path = Path(glossary_path_str) if glossary_path_str else None

                # Create and store the asyncio task
                process_task = asyncio.create_task(
                    process_csv(
                        csv_path=Path(pending_task["filepath"]),
                        progress_callback=progress_callback,
                        ollama_host=pending_task.get("ollama_host"),
                        model=pending_task.get("model"),
                        batch_size=pending_task.get("batch_size", 10),
                        glossary_path=glossary_path
                    )
                )
                running_async_tasks[task_id] = process_task

                final_status = ""
                try:
                    await process_task
                    final_status = "completed"
                except asyncio.CancelledError:
                    print(f"Task {task_id} was cancelled.")
                    final_status = "cancelled"
                except Exception as e:
                    print(f"Task {task_id} failed: {e}")
                    final_status = "error"
                finally:
                    # Clean up the task from the running list
                    if task_id in running_async_tasks:
                        del running_async_tasks[task_id]
                    
                    # Update the final status in storage, but only if the task hasn't been deleted
                    current_tasks = read_tasks()
                    task_exists = any(t['id'] == task_id for t in current_tasks)
                    if task_exists:
                        for task in current_tasks:
                            if task['id'] == task_id:
                                task["status"] = final_status
                        write_tasks(current_tasks)
                    
                    # Notify clients of the final status
                    await manager.broadcast_tasks()

        await asyncio.sleep(5)

def get_running_tasks_dict():
    """Returns the dictionary of running asyncio tasks for cancellation."""
    return running_async_tasks
