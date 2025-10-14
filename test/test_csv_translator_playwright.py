# IMPORTANT: Before running this test, you must install Playwright and its dependencies:
# pip install pytest-playwright
# playwright install

import pytest
import os
import re
import csv
from pathlib import Path
from playwright.sync_api import Page, expect

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000"
API_TOKEN = os.getenv("API_TOKEN", "your_default_token")
EXAMPLE_DIR = Path(__file__).parent.parent / "example"
CSV_FILE = str((EXAMPLE_DIR / "test.csv").resolve())
GLOSSARY_FILE = str((EXAMPLE_DIR / "glossary_example.csv").resolve())

# --- Helper Function ---
def set_token_and_navigate(page: Page):
    """Navigates to the base URL and sets the API token in localStorage."""
    # --- DEBUG: Add a listener to capture ALL console messages ---
    console_messages = []
    page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))

    page.goto(BASE_URL)
    modal = page.locator("#token-modal")
    expect(modal).to_be_visible(timeout=5000)
    page.locator("#token-input").fill(API_TOKEN)

    with page.expect_console_message(
        lambda msg: "Task queue connection established." in msg.text,
        timeout=10000
    ):
        page.locator("#token-submit").click()

    expect(modal).not_to_be_visible()

    try:
        # Now that the WebSocket is confirmed to be open, the "No tasks" message
        # should have been rendered by the onopen event.
        expect(page.locator('#task-list-body:has-text("No tasks in the queue")')).to_be_visible()
    except AssertionError as e:
        # --- DEBUGGING BLOCK on failure ---
        print("\n\n" + "="*20 + " DEBUGGING INFO " + "="*20)
        
        # 1. Take a screenshot
        screenshot_path = "failed_test_screenshot.png"
        page.screenshot(path=screenshot_path)
        print(f"DEBUG: Screenshot of the failure saved to: {screenshot_path}")

        # 2. Print inner HTML of the task list body
        try:
            body_html = page.locator("#task-list-body").inner_html(timeout=1000)
            print(f"DEBUG: innerHTML of #task-list-body:\n---\n{body_html}\n---")
        except Exception as html_err:
            print(f"DEBUG: Could not get innerHTML of #task-list-body: {html_err}")

        # 3. Print all captured console messages
        print("\nDEBUG: Captured Console Logs:")
        if console_messages:
            for msg in console_messages:
                print(msg)
        else:
            print("No console messages were captured.")
        
        print("="*56 + "\n")
        
        # Re-raise the original exception to fail the test
        raise e

# --- Test Cases ---

@pytest.mark.parametrize(
    "test_id, use_glossary, note_text",
    [
        ("no_options", False, None),
        ("with_glossary", True, None),
        ("with_note", False, "This is a test note."),
        ("with_glossary_and_note", True, "Another test note with glossary."),
    ]
)
def test_csv_upload_scenarios(page: Page, test_id, use_glossary, note_text):
    """
    Tests the CSV translator form with different combinations of optional inputs.
    """
    print(f"--- Running Playwright Test: {test_id} ---")

    if not API_TOKEN or API_TOKEN == "your_default_token":
        pytest.fail("API_TOKEN environment variable not set.")

    set_token_and_navigate(page)

    # Ensure we are on the correct tab
    csv_tab = page.locator(".tab-link[data-tab='csv-translator']")
    expect(csv_tab).to_have_class(re.compile(r'\bactive\b'))

    # Fill out the form
    page.locator("#upload-file").set_input_files(CSV_FILE)
    if use_glossary:
        page.locator("#glossary-file").set_input_files(GLOSSARY_FILE)
    if note_text:
        page.locator("#note").fill(note_text)

    # Submit and wait for the task to appear in the list
    submit_button = page.locator("#upload-form button[type='submit']")
    submit_button.click()

    # The task list should update via WebSocket. We expect the filename to appear.
    task_row = page.locator(f'#task-list-body tr:has-text("{Path(CSV_FILE).name}")')
    expect(task_row).to_be_visible(timeout=10000) # Wait up to 10s for WS update
    print(f"SUCCESS: Task for '{Path(CSV_FILE).name}' appeared in the queue.")

    # If a note was added, check if it's rendered correctly
    if note_text:
        # Find the toggle link and click it
        toggle_link = task_row.locator(f'.filename-toggle:has-text("{Path(CSV_FILE).name}")')
        expect(toggle_link).to_be_visible()
        toggle_link.click()
        
        # Check if the note content is visible
        # We need to find the note row associated with the task row
        note_row = page.locator(f'tr.note-row[data-task-id="{toggle_link.get_attribute("data-task-id")}"]')
        expect(note_row.locator(".note-content")).to_have_text(note_text)
        print(f"SUCCESS: Note '{note_text}' was correctly displayed.")

    # --- NEW: Wait for translation to complete ---
    print("Waiting for translation to complete (up to 5 minutes)...")
    progress_text = task_row.locator(".progress-text")
    expect(progress_text).to_have_text("100%", timeout=300000) # 5 minutes timeout
    print("SUCCESS: Task reached 100%.")

    # --- NEW: Download the result and verify it ---
    print("Downloading result file...")
    download_path = None
    try:
        with page.expect_download() as download_info:
            task_row.locator(".download-btn").click()
        download = download_info.value
        
        # Save the download to a known location for inspection
        download_path = Path(f"./{download.suggested_filename}")
        download.save_as(download_path)
        print(f"SUCCESS: Downloaded result file to {download_path}")

        # Verify the content of the downloaded CSV
        with open(download_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            header = reader.fieldnames
            # From test.csv, we know the source is 'en' and one target is 'zh-Hant'
            source_lang_code = 'en'
            target_lang_code = 'zh-Hant'

            assert target_lang_code in header, f"CSV header should contain target language '{target_lang_code}'"
            
            first_row = next(reader)
            
            assert first_row[target_lang_code], f"Target column '{target_lang_code}' in the first row should not be empty"
            assert first_row[target_lang_code] != first_row[source_lang_code], f"Target '{target_lang_code}' should be different from source '{source_lang_code}'"
        print("SUCCESS: Verified content of the downloaded file.")

    finally:
        # Clean up the downloaded file
        if download_path and download_path.exists():
            download_path.unlink()
            print(f"Cleaned up downloaded file: {download_path}")

# To run this test:
# 1. Make sure the FastAPI server is running.
# 2. Set the API_TOKEN environment variable: export API_TOKEN='your_token'
# 3. Run pytest from your terminal in the project root: pytest test/test_csv_translator_playwright.py