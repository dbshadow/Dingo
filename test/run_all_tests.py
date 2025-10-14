
import subprocess
import sys
from pathlib import Path

def run_test(script_path):
    """Runs a python script and returns its exit code."""
    print(f"\n{'='*20} RUNNING TEST: {script_path.name} {'='*20}")
    try:
        # For pytest, we need to call it via the pytest module
        if 'playwright' in script_path.name:
            command = [sys.executable, "-m", "pytest", str(script_path)]
        else:
            command = [sys.executable, str(script_path)]
            
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False, # Don't raise exception on non-zero exit code
            encoding='utf-8'
        )
        
        # Print stdout and stderr
        if process.stdout:
            print("--- STDOUT ---")
            print(process.stdout)
        if process.stderr:
            print("--- STDERR ---")
            print(process.stderr)
        
        if process.returncode == 0:
            print(f"-----> RESULT: PASS ({script_path.name}) <-----")
            return True
        else:
            print(f"-----> RESULT: FAIL ({script_path.name}) - Exit Code: {process.returncode} <-----")
            return False
            
    except FileNotFoundError:
        print(f"Error: Could not find the script at {script_path}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while running {script_path.name}: {e}")
        return False

def main():
    """Finds and runs all test scripts."""
    test_dir = Path(__file__).parent
    test_scripts = [
        test_dir / "test_idml_tools.py",
        test_dir / "test_live_translator.py",
        test_dir / "test_csv_translator_playwright.py",
    ]
    
    results = {}
    all_passed = True

    for script in test_scripts:
        if not script.exists():
            print(f"WARNING: Test script not found, skipping: {script}")
            continue
        success = run_test(script)
        results[script.name] = "PASS" if success else "FAIL"
        if not success:
            all_passed = False

    print(f"\n{'='*20} OVERALL TEST SUMMARY {'='*20}")
    for name, result in results.items():
        print(f"{name:<40} {result}")
    print("="*62)

    if all_passed:
        print("\nCongratulations! All tests passed successfully.")
        sys.exit(0)
    else:
        print("\nSome tests failed. Please review the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
