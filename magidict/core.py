"""Core implementation of MagiDict, a recursive dictionary with safe attribute access
and automatic conversion of nested dictionaries into MagiDicts."""

import json
from copy import deepcopy
from typing import Any, Iterable, List, Mapping, Sequence, Union
from inspect import signature


_MISSING = object()

try:
    from ._magidict import fast_hook as _c_fast_hook
    from ._magidict import fast_hook_with_memo as _c_fast_hook_with_memo

    _has_c_hook = True
except ImportError:
    _has_c_hook = False


class MagiDict(dict):
    """A dictionary that supports attribute-style access and recursive conversion
    of nested dictionaries into MagiDicts. It also supports safe access to missing
    keys and keys with None values by returning empty MagiDicts, allowing for
    safe chaining of attribute accesses."""

    def __init__(self, *args: Union[dict, Mapping], **kwargs: Any) -> None:
        """Initialize the MagiDict, recursively converting nested dicts.
        Supports initialization with a single dict, mapping, or standard dict args/kwargs.
        """
        super().__init__()
        memo = {}
        if len(args) == 1 and not kwargs and isinstance(args[0], dict):
            input_dict = args[0]
        else:
            input_dict = dict(*args, **kwargs)
        memo[id(input_dict)] = self
        for k, v in input_dict.items():
            super().__setitem__(k, self._hook_with_memo(v, memo))

    @classmethod
    def _hook(cls, item: Any) -> Any:
        """Recursively converts dictionaries in collections to MagiDicts."""
        if _has_c_hook:
            return _c_fast_hook(item, cls)
        return cls._hook_with_memo(item, {})

    @classmethod
    def _hook_with_memo(cls, item: Any, memo: dict[int, Any]) -> Any:
        """Recursively converts dictionaries in collections to MagiDicts.
        Uses a memoization dict to handle circular references."""

        if _has_c_hook:
            return _c_fast_hook_with_memo(item, memo, cls)

        item_id = id(item)
        if item_id in memo:
            return memo[item_id]

        if isinstance(item, MagiDict):
            memo[item_id] = item
            return item

        if isinstance(item, dict):
            new_dict = cls()
            memo[item_id] = new_dict
            for k, v in item.items():
                new_dict[k] = cls._hook_with_memo(v, memo)
            return new_dict

        if isinstance(item, list):
            memo[item_id] = item
            for i, elem in enumerate(item):
                item[i] = cls._hook_with_memo(elem, memo)
            return item

        if isinstance(item, tuple):
            if hasattr(item, "_fields"):
                hooked_values = tuple(cls._hook_with_memo(elem, memo) for elem in item)
                return type(item)(*hooked_values)
            return type(item)(cls._hook_with_memo(elem, memo) for elem in item)

        if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
            try:
                memo[item_id] = item
                for i, elem in enumerate(item):
                    item[i] = cls._hook_with_memo(elem, memo)  # type: ignore[index]
                return item
            except TypeError:
                return type(item)(cls._hook_with_memo(elem, memo) for elem in item)  # type: ignore[call-arg]

        return item

    def __getitem__(self, keys: Union[Any, Iterable[Any]]) -> Any:
        """
        - Supports standard dict key access.
        - Supports list/tuple of keys for nested forgiving access.
        - Supporsts string keys with dots for nested unforgiving access.
        """
        if isinstance(keys, (list, tuple)):
            if isinstance(keys, tuple) and keys in self:
                return super().__getitem__(keys)
            obj = self
            for key in keys:
                if isinstance(obj, Mapping):
                    if key in obj:
                        obj = obj[key]
                    else:
                        md = MagiDict()
                        object.__setattr__(md, "_from_missing", True)
                        return md
                elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)):
                    try:
                        obj = obj[int(key)]
                    except (ValueError, IndexError, TypeError):
                        md = MagiDict()
                        object.__setattr__(md, "_from_missing", True)
                        return md
                else:
                    md = MagiDict()
                    object.__setattr__(md, "_from_missing", True)
                    return md
            if obj is None:
                md = MagiDict()
                object.__setattr__(md, "_from_none", True)
                return md
            return obj
        try:
            return super().__getitem__(keys)
        except KeyError:
            if isinstance(keys, str) and "." in keys:
                keys = keys.split(".")
                obj = self
                for key in keys:
                    if isinstance(obj, Mapping):
                        obj = obj[key]
                    elif isinstance(obj, Sequence) and not isinstance(
                        obj, (str, bytes)
                    ):
                        obj = obj[int(key)]
                    else:
                        raise
                return obj
            raise

    def __getattr__(self, name: str) -> Any:
        """Enables attribute-style access. Returns a safe, empty MagiDict
        for missing keys or keys with a value of None."""
        # Check for special flag attributes first
        if name in ("_from_none", "_from_missing"):
            try:
                return object.__getattribute__(self, name)
            except AttributeError:
                return False

        if super().__contains__(name):
            value = self[name]
            if value is None:
                md = MagiDict()
                object.__setattr__(md, "_from_none", True)
                return md
            if isinstance(value, dict) and not isinstance(value, MagiDict):
                value = MagiDict(value)
                self[name] = value
            return value
        try:
            return super().__getattribute__(name)
        except AttributeError:
            md = MagiDict()
            object.__setattr__(md, "_from_missing", True)
            return md

    def __setitem__(self, key, value):
        """Hook values to convert nested dicts into MagiDicts.
        Prevent setting values on MagiDicts created from missing or None keys."""
        self._raise_if_protected()
        super().__setitem__(key, self._hook(value))

    def __delitem__(self, key):
        """Prevent deleting items on MagiDicts created from missing or None keys."""
        self._raise_if_protected()
        super().__delitem__(key)

    def __dir__(self):
        """Provides keys as attributes for auto-completion in interactive environments."""
        key_attrs = sorted(k for k in self.keys() if isinstance(k, str))
        class_attrs = sorted(self.__class__.__dict__)
        instance_attrs = sorted(self.__dict__)
        dict_attrs = sorted(dir(dict))

        ordered = []
        for group in (key_attrs, class_attrs, instance_attrs, dict_attrs):
            for attr in group:
                if attr not in ordered:
                    ordered.append(attr)
        return ordered

    def __deepcopy__(self, memo: dict[int, Any]) -> "MagiDict":
        """Support deep copy of MagiDict, handling circular references."""
        copied = MagiDict()
        memo[id(self)] = copied
        # Preserve special flags using object.__setattr__ to bypass __setattr__
        if object.__getattribute__(self, "__dict__").get("_from_none", False):
            object.__setattr__(copied, "_from_none", True)
        if object.__getattribute__(self, "__dict__").get("_from_missing", False):
            object.__setattr__(copied, "_from_missing", True)
        # Deep copy the contents, bypassing protection if needed
        for k, v in self.items():
            dict.__setitem__(copied, k, deepcopy(v, memo))
        return copied

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    def __getstate__(self):
        """
        Return the state to be pickled. Include both the dict contents and special flags.
        """
        state = {
            "data": dict(self),
            "_from_none": getattr(self, "_from_none", False),
            "_from_missing": getattr(self, "_from_missing", False),
        }

        return state

    def __reduce_ex__(self, protocol):
        """Custom pickling support to preserve flags across pickle/unpickle."""

        return (self.__class__, (), self.__getstate__(), None, None)

    def __setstate__(self, state):
        """
        Restore the state from the unpickled state, preserving special flags.
        """
        if state.get("_from_none", False):
            object.__setattr__(self, "_from_none", True)
        if state.get("_from_missing", False):
            object.__setattr__(self, "_from_missing", True)
        # Use dict.update to bypass protection check during unpickling
        for k, v in state.get("data", {}).items():
            dict.__setitem__(self, k, self._hook(v))

    def update(self, *args, **kwargs):
        """Recursively convert nested dicts into MagiDicts on update."""
        self._raise_if_protected()
        for k, v in dict(*args, **kwargs).items():
            self[k] = v

    def copy(self):
        """Return a shallow copy of the MagiDict, preserving special flags."""
        new_copy = MagiDict(super().copy())
        # Preserve the special flags
        if getattr(self, "_from_none", False):
            object.__setattr__(new_copy, "_from_none", True)
        if getattr(self, "_from_missing", False):
            object.__setattr__(new_copy, "_from_missing", True)

        return new_copy

    def setdefault(self, key: Any, default: Any = None) -> Any:
        """Overrides dict.setdefault to ensure the default value is hooked."""
        self._raise_if_protected()
        return super().setdefault(key, self._hook(default))

    @classmethod
    def fromkeys(cls, seq, value=None):
        """Overrides dict.fromkeys to ensure the value is hooked."""
        d = {}
        for key in seq:
            d[key] = cls._hook(value)
        return cls(d)

    def pop(self, key: Any, *args: Any) -> Any:
        """Prevent popping items on MagiDicts created from missing or None keys."""
        self._raise_if_protected()
        return super().pop(key, *args)

    def popitem(self):
        """Prevent popping items on MagiDicts created from missing or None keys."""
        self._raise_if_protected()
        return super().popitem()

    def clear(self):
        """Prevent clearing items on MagiDicts created from missing or None keys."""
        self._raise_if_protected()
        super().clear()

    def mget(self, key: Any, default: Any = _MISSING) -> Any:
        """
        Safe get method that mimics attribute-style access.
        If the key doesn't exist, returns an empty MagiDict instead of raising KeyError.
        If the key exists but its value is None, returns an empty MagiDict for safe chaining.

        Parameters:
            key: The key to retrieve.
            default: The default value to return if the key is missing. If not provided,
                     an empty MagiDict is returned for missing keys.

        Returns:
            The value associated with the key, or an empty MagiDict if the key is missing
            or its value is None.
        """
        if default is _MISSING:
            md = MagiDict()
            object.__setattr__(md, "_from_missing", True)
            default = md
        if super().__contains__(key):
            value = self[key]
            if value is None and default is not None:
                md = MagiDict()
                object.__setattr__(md, "_from_none", True)
                return md
            return value
        return default

    def _raise_if_protected(self):
        """Raises TypeError if this MagiDict was created from a None or missing key,
        preventing modifications to. It can however be bypassed with dict methods."""
        if getattr(self, "_from_none", False) or getattr(self, "_from_missing", False):
            raise TypeError("Cannot modify NoneType or missing keys.")

    def mg(self, key: Any, default: Any = _MISSING) -> Any:
        """
        Shorthand for mget() method.
        """
        return self.mget(key, default)

    def strict_get(self, key: Any) -> Any:
        """
        Strict get method that mimics standard dict access.

        Parameters:
            key: The key to retrieve.

        Returns:
            The value associated with the key.
        """
        return super().__getitem__(key)

    def sget(self, key: Any) -> Any:
        """
        Shorthand for strict_get() method.
        """
        return self.strict_get(key)

    def sg(self, key: Any) -> Any:
        """
        Shorthand for strict_get() method.
        """
        return self.strict_get(key)

    def disenchant(self: "MagiDict") -> dict:
        """
        Convert MagiDict and all nested MagiDicts back into standard dicts,
        handling circular references gracefully.
        """
        memo: dict[int, Any] = {}

        def _disenchant_recursive(item: Any) -> Any:
            item_id = id(item)
            if item_id in memo:
                return memo[item_id]

            if isinstance(item, MagiDict):
                new_dict: dict = {}
                memo[item_id] = new_dict
                for k, v in item.items():
                    new_dict[k] = _disenchant_recursive(v)
                return new_dict

            elif isinstance(item, dict):
                new_dict = {}
                memo[item_id] = new_dict
                for k, v in item.items():
                    new_dict[_disenchant_recursive(k)] = _disenchant_recursive(v)
                return new_dict

            elif isinstance(item, tuple):
                if hasattr(item, "_fields"):
                    disenchanted_values = tuple(
                        _disenchant_recursive(elem) for elem in item
                    )
                    return type(item)(*disenchanted_values)
                return tuple(_disenchant_recursive(elem) for elem in item)

            elif isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
                new_list: list = []
                memo[item_id] = new_list
                for elem in item:
                    new_list.append(_disenchant_recursive(elem))  # type: ignore[index]

                if not isinstance(item, list):
                    try:
                        return type(item)(new_list)  # type: ignore[call-arg]
                    except TypeError:
                        return new_list
                return new_list

            elif isinstance(item, (set, frozenset)):

                new_set = type(item)(_disenchant_recursive(e) for e in item)
                memo[item_id] = new_set
                return new_set

            return item

        return _disenchant_recursive(self)

    def search_key(self, key: Any, default=None) -> Union[Any, None]:
        """
        Recursively search for a key in the MagiDict and its nested structures.
        Returns the value if found, otherwise returns None or the specified default.

        Parameters:
            key: The key to search for.
            default: The value to return if the key is not found.

        Returns:
            The value associated with the specified key, or None/default if not found.
        """
        for k, v in self.items():
            if k == key:
                return v

            def recurse(value):
                if isinstance(value, MagiDict):
                    return value.search_key(key)
                if isinstance(value, Mapping):
                    return MagiDict(value).search_key(key)
                return default

            if isinstance(v, Mapping):
                result = recurse(v)
                if result is not None:
                    return result

            if isinstance(v, Sequence) and not isinstance(v, (str, bytes)):
                for item in v:
                    if isinstance(item, Mapping):
                        result = recurse(item)
                        if result is not None:
                            return result

        return default

    def search_keys(self, key: Any) -> List[Any]:
        """
        Recursively search for all occurrences of a key in the MagiDict and its nested structures.
        Returns a list of all found values.

        Parameters:
            key: The key to search for.

        Returns:
            A list of all values associated with the specified key.
        """
        results = []

        def recurse(value):
            if isinstance(value, MagiDict):
                results.extend(value.search_keys(key))
            elif isinstance(value, Mapping):
                results.extend(MagiDict(value).search_keys(key))
            elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                for item in value:
                    recurse(item)

        for k, v in self.items():
            if k == key:
                results.append(v)
            recurse(v)

        return results

    def filter(self, function: Any, drop_empty=False) -> "MagiDict":
        """
        Returns a new MagiDict containing only the items for which the function(key) or function(key, value)
        returns True. Supports nested dicts and sequences. If drop_empty is True, empty MagiDicts and sequences
        are omitted from the result.

        Parameters:
            function: A function that takes one argument (value) or two arguments (key, value) and returns True or False.
                      If None, filters out items with value None.
            drop_empty: If True, empty MagiDicts and data structures are omitted from the result.

        Returns:
            A new MagiDict with filtered items.
        """

        if function is None:
            return self.filter(lambda x: x is not None, drop_empty=drop_empty)

        num_args = len(signature(function).parameters)

        def filter_nested_seq(
            seq: Sequence, function: Any, num_args: int, drop_empty: bool
        ) -> Union[List[Any], None]:
            """Recursively filter nested sequences while preserving structure."""
            new_seq: List[Any] = []
            for i, item in enumerate(seq):
                if isinstance(item, MagiDict):
                    nested = item.filter(function, drop_empty=drop_empty)
                    if nested or not drop_empty:
                        new_seq.append(nested)
                elif isinstance(item, Mapping):
                    nested = MagiDict(item).filter(function, drop_empty=drop_empty)
                    if nested or not drop_empty:
                        new_seq.append(nested)
                elif isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
                    nested = filter_nested_seq(item, function, num_args, drop_empty)  # type: ignore[assignment]
                    if nested or not drop_empty:
                        new_seq.append(nested)
                else:
                    if num_args == 2:
                        if function(i, item):
                            new_seq.append(item)
                    else:
                        if function(item):
                            new_seq.append(item)
            if new_seq or not drop_empty:
                try:
                    return type(seq)(new_seq)  # type: ignore
                except TypeError:
                    return new_seq
            return None

        filtered: MagiDict = MagiDict()

        for k, v in self.items():
            if isinstance(v, MagiDict):
                nested = v.filter(function, drop_empty=drop_empty)
                if nested or not drop_empty:
                    filtered[k] = nested
            elif isinstance(v, Mapping):
                nested = MagiDict(v).filter(function, drop_empty=drop_empty)
                if nested or not drop_empty:
                    filtered[k] = nested
            elif isinstance(v, Sequence) and not isinstance(v, (str, bytes)):
                new_seq: Union[List[Any], Sequence[Any]] = filter_nested_seq(
                    v, function, num_args, drop_empty  # type: ignore[assignment]
                )
                if new_seq or not drop_empty:
                    try:
                        filtered[k] = type(v)(new_seq)  # type: ignore[call-arg]
                    except TypeError:
                        filtered[k] = new_seq
            else:
                if num_args == 2:
                    if function(k, v):
                        filtered[k] = v
                else:
                    if function(v):
                        filtered[k] = v

        return filtered


def magi_loads(s: str, **kwargs: Any) -> MagiDict:
    """
    Deserialize a JSON string into a MagiDict instead of a dict.

    Parameters:
        s: The JSON string to deserialize.
        **kwargs: Additional keyword arguments to pass to json.loads.

    Returns:
        A MagiDict representing the deserialized JSON data.
    """
    return json.loads(s, object_hook=MagiDict, **kwargs)


def magi_load(fp: Any, **kwargs: Any) -> MagiDict:
    """
    Deserialize a JSON file-like object into a MagiDict instead of a dict.

    Parameters:
        fp: The file-like object to read the JSON data from.
        **kwargs: Additional keyword arguments to pass to json.load.

    Returns:
        A MagiDict representing the deserialized JSON data.
    """
    return json.load(fp, object_hook=MagiDict, **kwargs)


def enchant(d: dict) -> MagiDict:
    """
    Convert a standard dictionary into a MagiDict.

    Parameters:
        d: The standard dictionary to convert.

    Returns:
        A MagiDict representing the input dictionary.
    """
    if isinstance(d, MagiDict):
        return d
    if not isinstance(d, dict):
        raise TypeError(f"Expected dict, got {type(d).__name__}")
    return MagiDict(d)


def none(obj: Any) -> Any:
    """Convert an empty MagiDict that was created from a None or missing key into None.

    Parameters:
        obj: The object to check.

    Returns:
        None if the object is an empty MagiDict created from None or missing key, otherwise returns the object itself.
    """
    if (
        isinstance(obj, MagiDict)
        and len(obj) == 0
        and (getattr(obj, "_from_none", False) or getattr(obj, "_from_missing", False))
    ):
        return None
    return obj
