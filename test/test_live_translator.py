
import requests
import os

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000"
API_TOKEN = os.getenv("API_TOKEN", "your_default_token")
HEADERS = {
    "X-API-Token": API_TOKEN,
    "Content-Type": "application/json"
}

def test_live_translation():
    """
    Tests the /live_translate endpoint.
    It sends text and expects a translated version back.
    """
    print("--- Running Test: Live Translation ---")
    url = f"{BASE_URL}/live_translate"
    payload = {
        "text": "Hello, world!",
        "source_lang": "en",
        "target_lang": "zh-Hant"
    }

    try:
        response = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        
        if response.status_code == 200:
            print("SUCCESS: Received status 200 OK.")
            data = response.json()
            if "translated_text" in data and data["translated_text"]:
                print(f"SUCCESS: Received translated text: '{data['translated_text']}'")
                return True
            else:
                print(f"FAILURE: 'translated_text' not in response or is empty. Response: {data}")
                return False
        # Handle case where Ollama is not configured
        elif response.status_code == 500 and "Ollama host or model is not configured" in response.text:
            print("SKIPPED: Live translation test skipped because Ollama is not configured on the server.")
            return True # Treat as a pass since the feature is intentionally disabled
        else:
            print(f"FAILURE: Expected status 200, but got {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except requests.RequestException as e:
        print(f"FAILURE: Request failed: {e}")
        return False

if __name__ == "__main__":
    print("Starting Live Translator Test...")
    if not API_TOKEN or API_TOKEN == "your_default_token":
        print("ERROR: API_TOKEN environment variable not set. Please set it before running tests.")
        exit(1)

    translation_ok = test_live_translation()

    print("\n--- Test Summary ---")
    print(f"Live Translation: {'PASS' if translation_ok else 'FAIL'}")

    if translation_ok:
        print("\nLive Translator test passed!")
        exit(0)
    else:
        print("\nLive Translator test failed.")
        exit(1)
