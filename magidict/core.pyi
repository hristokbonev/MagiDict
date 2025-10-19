"""Type stubs for magidict.core module - mirrors _magidict.pyi"""

from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    SupportsIndex,
    Tuple,
    TypeVar,
    Union,
    overload,
)
from typing_extensions import Self

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")
_T = TypeVar("_T")
_KT_co = TypeVar("_KT_co")
_VT_co = TypeVar("_VT_co")

class MagiDict(Dict[_KT, _VT]):
    """A dictionary that supports attribute-style access and recursive conversion
    of nested dictionaries into MagiDicts."""

    _from_none: bool
    _from_missing: bool

    @overload
    def __init__(self) -> None: ...
    @overload
    def __init__(self, __map: Mapping[_KT, _VT]) -> None: ...
    @overload
    def __init__(self, __iterable: Iterable[Tuple[_KT, _VT]]) -> None: ...
    @overload
    def __init__(self, **kwargs: _VT) -> None: ...
    @classmethod
    def _hook(cls, item: Any) -> Any:
        """Recursively converts dictionaries in collections to MagiDicts."""
        ...

    @classmethod
    def _hook_with_memo(cls, item: Any, memo: Dict[int, Any]) -> Any:
        """Recursively converts dictionaries in collections to MagiDicts.
        Uses a memoization dict to handle circular references."""
        ...

    @overload
    def __getitem__(self, key: _KT) -> _VT: ...
    @overload
    def __getitem__(self, key: Union[List[Any], Tuple[Any, ...]]) -> Any: ...
    @overload
    def __getitem__(self, key: str) -> Any: ...
    def __setitem__(self, key: _KT, value: _VT) -> None: ...
    def __delitem__(self, key: _KT) -> None: ...
    def __getattr__(self, name: str) -> Any: ...
    def __dir__(self) -> List[str]: ...
    def __repr__(self) -> str: ...
    def __deepcopy__(self, memo: Dict[int, Any]) -> Self: ...
    def __getstate__(self) -> Dict[str, Any]: ...
    def __setstate__(self, state: Dict[str, Any]) -> None: ...
    def __reduce_ex__(
        self, protocol: SupportsIndex
    ) -> Tuple[type, Tuple[()], Dict[str, Any], None, None]: ...
    def update(self, *args: Any, **kwargs: Any) -> None:
        """Recursively convert nested dicts into MagiDicts on update."""
        ...

    def copy(self) -> Self:
        """Return a shallow copy of the MagiDict, preserving special flags."""
        ...

    def setdefault(self, key: _KT, default: _VT = ...) -> _VT:
        """Overrides dict.setdefault to ensure the default value is hooked."""
        ...

    @overload
    @classmethod
    def fromkeys(
        cls, __iterable: Iterable[_KT_co], __value: None = ...
    ) -> MagiDict[_KT_co, Optional[Any]]: ...
    @overload
    @classmethod
    def fromkeys(
        cls, __iterable: Iterable[_KT_co], __value: _VT_co
    ) -> MagiDict[_KT_co, _VT_co]: ...
    @overload
    def pop(self, __key: _KT) -> _VT: ...
    @overload
    def pop(self, __key: _KT, __default: _VT) -> _VT: ...
    @overload
    def pop(self, __key: _KT, __default: _T) -> Union[_VT, _T]: ...
    def popitem(self) -> Tuple[_KT, _VT]: ...
    def clear(self) -> None: ...
    @overload
    def mget(self, key: _KT) -> Union[_VT, Self]: ...
    @overload
    def mget(self, key: _KT, default: _T) -> Union[_VT, _T]: ...
    @overload
    def mg(self, key: _KT) -> Union[_VT, Self]: ...
    @overload
    def mg(self, key: _KT, default: _T) -> Union[_VT, _T]: ...
    def strict_get(self, key: _KT) -> _VT:
        """Strict get method that mimics standard dict access.

        Parameters:
            key: The key to retrieve.

        Returns:
            The value associated with the key.

        Raises:
            KeyError: If the key is not found.
        """
        ...

    def sget(self, key: _KT) -> _VT:
        """Shorthand for strict_get() method."""
        ...

    def sg(self, key: _KT) -> _VT:
        """Shorthand for strict_get() method."""
        ...

    def disenchant(self) -> Dict[Any, Any]:
        """Convert MagiDict and all nested MagiDicts back into standard dicts,
        handling circular references gracefully."""
        ...

    def _raise_if_protected(self) -> None:
        """Raises TypeError if this MagiDict was created from a None or missing key."""
        ...

    def search_key(self, key: Any, default: Optional[Any] = None) -> Any:
        """Recursively search for a key in the MagiDict and its nested structures.
        Returns the value if found, otherwise returns None or the specified default.

        Parameters:
            key: The key to search for.
            default: The value to return if the key is not found.

        Returns:
            The value associated with the specified key, or None/default if not found.
        """
        ...

    def search_keys(self, key: Any) -> List[Any]:
        """Recursively search for all occurrences of a key in the MagiDict and its nested structures.
        Returns a list of all found values.

        Parameters:
            key: The key to search for.

        Returns:
            A list of all values associated with the specified key.
        """
        ...

    def filter(
        self, function: Optional[Callable[..., bool]] = None, drop_empty: bool = False
    ) -> Self:
        """Returns a new MagiDict containing only the items for which the function
        returns True. Supports nested dicts and sequences.

        Parameters:
            function: A function that takes one argument (value) or two arguments
                     (key, value) and returns True or False. If None, filters out
                     None values.
            drop_empty: If True, empty MagiDicts and sequences are omitted from
                       the result.

        Returns:
            A new MagiDict with filtered items.
        """
        ...

def magi_loads(s: str, **kwargs: Any) -> MagiDict:
    """Deserialize a JSON string into a MagiDict instead of a dict.

    Parameters:
        s: The JSON string to deserialize.
        **kwargs: Additional keyword arguments to pass to json.loads.

    Returns:
        A MagiDict representing the deserialized JSON data.
    """
    ...

def magi_load(fp: Any, **kwargs: Any) -> MagiDict:
    """Deserialize a JSON file-like object into a MagiDict instead of a dict.

    Parameters:
        fp: The file-like object to read the JSON data from.
        **kwargs: Additional keyword arguments to pass to json.load.

    Returns:
        A MagiDict representing the deserialized JSON data.
    """
    ...

def enchant(d: Dict[Any, Any]) -> MagiDict:
    """Convert a standard dictionary into a MagiDict.

    Parameters:
        d: The standard dictionary to convert.

    Returns:
        A MagiDict representing the input dictionary.

    Raises:
        TypeError: If the input is not a dictionary.
    """
    ...

def none(obj: Any) -> Any:
    """Convert an empty MagiDict that was created from a None or missing key into None.

    Parameters:
        obj: The object to check.

    Returns:
        None if the object is an empty MagiDict created from None or missing key,
        otherwise returns the object itself.
    """
    ...
