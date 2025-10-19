"""Type stubs for magidict package."""

from typing import Any, Dict

# Import from the stub files - both have identical signatures now
from magidict._magidict import (
    MagiDict as MagiDict,
    enchant as enchant,
    magi_load as magi_load,
    magi_loads as magi_loads,
    none as none,
)

__version__: str
__all__: list[str]