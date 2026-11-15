"""Trusted fixed worker; accepts parameters only, never code or file paths."""
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.science import simulate
if __name__ == '__main__': print(json.dumps(simulate(json.loads(sys.stdin.read(4096))), allow_nan=False))
