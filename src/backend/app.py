import sys
from pathlib import Path

root = next((p for p in Path(__file__).resolve().parents if (p / "src" / "backend" / "main.py").is_file()), None)
if root is None:
    raise ModuleNotFoundError("Run app.py from inside the full repository (src/backend/main.py is missing).")
sys.path.insert(0, str(root))
from src.backend.main import run  # noqa: E402

if __name__ == "__main__":
    run()
