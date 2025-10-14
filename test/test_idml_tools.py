
import requests
import os
from pathlib import Path
import time

# --- Configuration ---
BASE_URL = "http://127.0.0.1:8000"
API_TOKEN = os.getenv("API_TOKEN", "your_default_token") # Fallback to a default token if not set
HEADERS = {"X-API-Token": API_TOKEN}
EXAMPLE_DIR = Path(__file__).parent.parent / "example"
IDML_FILE = EXAMPLE_DIR / "R15_A1_Manual_v1.03(WW).idml"
CSV_FILE = EXAMPLE_DIR / "R15_A1_Manual_v1.03(WW).csv" # Assuming a translated csv for rebuild test

def test_idml_extract():
    """
    Tests the /idml/extract endpoint.
    It uploads an IDML file and expects a CSV file in response.
    """
    print("--- Running Test: IDML Extract ---")
    if not IDML_FILE.exists():
        print(f"ERROR: Test file not found at {IDML_FILE}")
        return False

    url = f"{BASE_URL}/idml/extract"
    with open(IDML_FILE, "rb") as f:
        files = {"idml_file": (IDML_FILE.name, f, "application/vnd.adobe.indesign-idml-package")}
        try:
            response = requests.post(url, headers=HEADERS, files=files, timeout=60)
            
            if response.status_code == 200:
                print("SUCCESS: Received status 200 OK.")
                if "text/csv" in response.headers.get("Content-Type", ""):
                    print("SUCCESS: Response content type is correct.")
                else:
                    print(f"FAILURE: Incorrect content type. Got {response.headers.get('Content-Type')}")
                    return False
                
                if "attachment" in response.headers.get("Content-Disposition", ""):
                     print("SUCCESS: Response has correct Content-Disposition header.")
                     return True
                else:
                    print(f"FAILURE: Incorrect Content-Disposition. Got {response.headers.get('Content-Disposition')}")
                    return False
            else:
                print(f"FAILURE: Expected status 200, but got {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except requests.RequestException as e:
            print(f"FAILURE: Request failed: {e}")
            return False

def test_idml_rebuild():
    """
    Tests the /idml/rebuild endpoint.
    It uploads an original IDML and a translated CSV, expecting a new IDML in return.
    """
    print("--- Running Test: IDML Rebuild ---")
    if not IDML_FILE.exists() or not CSV_FILE.exists():
        print(f"ERROR: Test files not found. Checked for {IDML_FILE} and {CSV_FILE}")
        return False

    url = f"{BASE_URL}/idml/rebuild"
    with open(IDML_FILE, "rb") as idml_f, open(CSV_FILE, "rb") as csv_f:
        files = {
            "original_idml": (IDML_FILE.name, idml_f, "application/vnd.adobe.indesign-idml-package"),
            "translated_csv": (CSV_FILE.name, csv_f, "text/csv")
        }
        try:
            response = requests.post(url, headers=HEADERS, files=files, timeout=60)
            
            if response.status_code == 200:
                print("SUCCESS: Received status 200 OK.")
                if "application/vnd.adobe.indesign-idml-package" in response.headers.get("Content-Type", ""):
                    print("SUCCESS: Response content type is correct.")
                else:
                    print(f"FAILURE: Incorrect content type. Got {response.headers.get('Content-Type')}")
                    return False

                if "attachment" in response.headers.get("Content-Disposition", ""):
                     print("SUCCESS: Response has correct Content-Disposition header.")
                     return True
                else:
                    print(f"FAILURE: Incorrect Content-Disposition. Got {response.headers.get('Content-Disposition')}")
                    return False
            else:
                print(f"FAILURE: Expected status 200, but got {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except requests.RequestException as e:
            print(f"FAILURE: Request failed: {e}")
            return False

if __name__ == "__main__":
    print("Starting IDML Tools Test...")
    if not API_TOKEN or API_TOKEN == "your_default_token":
        print("ERROR: API_TOKEN environment variable not set. Please set it before running tests.")
        exit(1)
        
    print(f"Using example files from: {EXAMPLE_DIR.resolve()}")
    
    extract_ok = test_idml_extract()
    rebuild_ok = test_idml_rebuild()

    print("\n--- Test Summary ---")
    print(f"IDML Extract: {'PASS' if extract_ok else 'FAIL'}")
    print(f"IDML Rebuild: {'PASS' if rebuild_ok else 'FAIL'}")

    if extract_ok and rebuild_ok:
        print("\nAll IDML tools tests passed!")
        exit(0)
    else:
        print("\nSome IDML tools tests failed.")
        exit(1)
