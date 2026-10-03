import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import ModuleType


app_path = Path(__file__).resolve()
project_root = next(
    (
        parent
        for parent in app_path.parents
        if (parent / "src" / "backend" / "main.py").is_file()
    ),
    None,
)
if project_root is not None:
    sys.path.insert(0, str(project_root))
    from src.backend.main import run
else:
    colocated_main = app_path.with_name("main.py")
    if not colocated_main.is_file():
        raise ModuleNotFoundError(
            "Cannot find the backend main.py. Run app.py with the src/backend "
            "package available, or place its backend modules beside app.py."
        )

    package_name = "_gittok_backend"
    package = ModuleType(package_name)
    package.__path__ = [str(app_path.parent)]
    sys.modules[package_name] = package

    module_name = f"{package_name}.main"
    spec = spec_from_file_location(module_name, colocated_main)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load backend entry point from {colocated_main}")
    main_module = module_from_spec(spec)
    sys.modules[module_name] = main_module
    spec.loader.exec_module(main_module)
    run = main_module.run


if __name__ == "__main__":
    run()