"""MagiDict package initialization with smart C/Python fallback."""

from typing import Any, Dict

# Try to load C extension first
try:
    from ._magidict import MagiDict as _CMagiDict
    from ._magidict import magi_loads, magi_load, enchant, none

    _using_c_extension = True
    _c_extension_loaded = True

    # Try to load Python implementation for fallback
    try:
        from .core import MagiDict as _PyMagiDict

        _has_python_fallback = True
    except ImportError:
        _has_python_fallback = False

    # Create wrapper class with Python fallback for unimplemented methods
    if _has_python_fallback:

        class MagiDict(_CMagiDict):
            """MagiDict using C extension with Python fallback for unimplemented methods."""

            def filter(self, function=None, drop_empty=False):
                """Filter the MagiDict - uses Python implementation.

                The C extension doesn't implement filter(), so this method
                automatically falls back to the pure Python implementation.

                Args:
                    function: A function that takes one or two arguments and returns bool.
                              If None, filters out None values.
                    drop_empty: If True, empty MagiDicts and sequences are omitted.

                Returns:
                    A new filtered MagiDict.
                """
                try:
                    # Try C version first (in case it gets implemented later)
                    return super().filter(function, drop_empty)
                except (NotImplementedError, AttributeError):
                    # Fall back to Python implementation
                    py_md = _PyMagiDict(dict(self))
                    result = py_md.filter(function, drop_empty)
                    # Convert result back to C MagiDict
                    return MagiDict(dict(result))

    else:
        # No Python fallback available, use C version as-is
        MagiDict = _CMagiDict

except ImportError:
    # C extension not available, use pure Python
    _c_extension_loaded = False
    _using_c_extension = False
    _has_python_fallback = False

    try:
        from .core import MagiDict, magi_loads, magi_load, enchant, none
    except ImportError as e:
        raise ImportError(
            "Could not import MagiDict from either C extension or pure Python implementation. "
            "Please ensure the package is properly installed."
        ) from e


__all__ = [
    "MagiDict",
    "magi_loads",
    "magi_load",
    "enchant",
    "none",
]

__version__ = "0.1.4"

__implementation__ = "C extension" if _using_c_extension else "Pure Python"


def get_implementation_info():
    """Get detailed information about the current implementation.

    Returns:
        dict: Information about which implementation is being used.
    """
    return {
        "implementation": __implementation__,
        "c_extension_loaded": _c_extension_loaded,
        "has_python_fallback": _has_python_fallback,
        "using_c_extension": _using_c_extension,
    }
