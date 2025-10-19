"""MagiDict package initialization."""

from typing import Any

try:
    from .core import MagiDict

    _using_c_extension = True
except ImportError:
    try:
        from .core import MagiDict

        _using_c_extension = False
    except ImportError as e:
        raise ImportError(
            "Could not import MagiDict from either C extension or pure Python implementation. "
            "Please ensure the package is properly installed."
        ) from e

try:
    from .core import magi_loads, magi_load, enchant, none
except ImportError:

    def magi_loads(s: str, **kwargs: Any) -> MagiDict:
        """Fallback magi_loads - requires core module"""
        raise ImportError("magi_loads requires the core module to be available")

    def magi_load(fp: Any, **kwargs: Any) -> MagiDict:
        """Fallback magi_load - requires core module"""
        raise ImportError("magi_load requires the core module to be available")

    def enchant(d: dict) -> MagiDict:
        """Fallback enchant - requires core module"""
        raise ImportError("enchant requires the core module to be available")

    def none(obj: Any) -> Any:
        """Fallback none - requires core module"""
        raise ImportError("none requires the core module to be available")


__all__ = [
    "MagiDict",
    "magi_loads",
    "magi_load",
    "enchant",
    "none",
]

__version__ = "0.1.4"

__implementation__ = "C extension" if _using_c_extension else "Pure Python"
