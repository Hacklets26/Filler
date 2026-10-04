"""Public package interface for the FILLER FastAPI backend."""
from typing import TYPE_CHECKING, Any

__all__ = ["app", "run"]

if TYPE_CHECKING:
    from .main import app, run


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from .main import app, run
    return {"app": app, "run": run}[name]
