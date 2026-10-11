"""
DevPilot AI - Unified Test Runner Script.
Executes both the Backend and Sample API test suites with full coverage reporting.
"""

import sys
import subprocess

def run_suite(name: str, args: list) -> int:
    print("\n" + "=" * 60)
    print(f"RUNNING {name.upper()}")
    print("=" * 60)
    result = subprocess.run([sys.executable, "-m", "pytest"] + args)
    return result.returncode

def main() -> None:
    code1 = run_suite("Backend Tests", ["backend/tests", "-v", "--cov=backend/app", "--cov-report=term-missing"])
    code2 = run_suite("Sample Target API Tests", ["sample-api/tests", "-v", "--cov=sample-api/app", "--cov-report=term-missing"])

    print("\n" + "=" * 60)
    print("TEST SUITE SUMMARY")
    print("=" * 60)
    print(f"Backend Tests:       {'PASS' if code1 == 0 else 'FAIL'}")
    print(f"Sample API Tests:    {'PASS' if code2 == 0 else 'FAIL'}")

    if code1 != 0 or code2 != 0:
        sys.exit(1)
    print("\nAll tests across the entire platform passed successfully!")

if __name__ == "__main__":
    main()
