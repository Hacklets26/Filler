import importlib
import importlib.util
import sys
from pathlib import Path

backend_root = Path(__file__).resolve().parent
package_name = "_filler_backend"
spec = importlib.util.spec_from_file_location(
    package_name,
    backend_root / "__init__.py",
    submodule_search_locations=[str(backend_root)],
)
if spec is None or spec.loader is None:
    raise ModuleNotFoundError(f"Could not load the backend package from {backend_root}")
package = importlib.util.module_from_spec(spec)
sys.modules[package_name] = package
spec.loader.exec_module(package)
run = importlib.import_module(f"{package_name}.main").run

if __name__ == "__main__":
    run()
