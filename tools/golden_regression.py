
#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    try:
        import pytest  # type: ignore  # noqa: F401
    except Exception:
        print("pytest not found. Installing is recommended: pip install pytest")
    print("Running golden regression (AST-based signature match)...")
    cmd = [sys.executable, "-m", "pytest", "-q"]
    subprocess.run(cmd, cwd=ROOT, check=False)

if __name__ == "__main__":
    main()
