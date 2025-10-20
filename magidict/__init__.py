"""MagiDict package initialization."""

from typing import Any, Dict

from .core import MagiDict, magi_loads, magi_load, enchant, none

try:
    from ._magidict import fast_hook, fast_hook_with_memo

    _c_extension_loaded = True
except ImportError:
    _c_extension_loaded = False

__all__ = [
    "MagiDict",
    "magi_loads",
    "magi_load",
    "enchant",
    "none",
]

__version__ = "0.1.7"

__implementation__ = "Python + C hook" if _c_extension_loaded else "Pure Python"


def get_implementation_info():
    """Get detailed information about the current implementation."""
    return {
        "implementation": __implementation__,
        "c_extension_loaded": _c_extension_loaded,
        "c_hook_available": _c_extension_loaded,
    }
