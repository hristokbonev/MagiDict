import json
from copy import deepcopy
from typing import Mapping, Sequence


class MagicDict(dict):
    """
    A dictionary subclass that allows for deep, safe, and convenient attribute-style access.

    This class provides the following "magic" features:

    1.  Attribute-style Access:
        Keys can be accessed and traversed as attributes (e.g., `md.key.subkey`).

    2.  Dot Notation Access in Brackets:
        Bracket access supports dot-separated strings for deep access, including list indices
        (e.g., `md['key.subkey']` and `md['items.0.name']`).

    3.  Recursive Conversion:
        When initialized, it recursively converts any nested dictionaries into `MagicDict`
        instances, including those inside lists, tuples, and other sequences. This enables
        deep attribute-style access throughout the structure.

    4.  Graceful Failure on Attribute Access:
        Accessing a non-existent key via an attribute (e.g., `md.non_existent_key`)
        returns an empty `MagicDict` instead of raising an `AttributeError` or `KeyError`,
        allowing for safe chaining (e.g., `md.non_existent.key.chain`).

    5.  Safe Chaining for `None` Values:
        Accessing a key whose value is `None` via an attribute (e.g., `md.key_with_none`)
        also returns an empty `MagicDict`, allowing for safe chaining. Standard bracket
        access (`md['key_with_none']`) will correctly return `None`.

    6.  Standard `dict` Behavior Preservation:
        It retains all standard dictionary functionality. Accessing a non-existent
        key with bracket notation (`md['missing']`) will still raise a `KeyError`,
        as expected from a standard `dict`.

    7.  Safe `mget()` Method:
        The `mget()` method provides the "graceful failure" behavior of attribute access
        for any key, including those that are not valid Python identifiers.

    8.  Conversion Back to Standard `dict`:
        The `disenchant()` method converts the `MagicDict` and all nested `MagicDict`
        instances back into standard dictionaries.


    Examples:
        >>> data = {'user': {'name': 'Alice', 'id': 1, 'nickname': None}, 'permissions': ['read']}
        >>> md = MagicDict(data)

        # Attribute-style access
        >>> md.user.name
        'Alice'

        # Dot notation for nested keys
        >>> md["user.id"]
        1

        # Standard access still works
        >>> md['user']['id']
        1

        # Accessing a non-existent key returns empty MagicDict:
        >>> md.user.email
        MagicDict({})

        # Accessing a non-existent nested key with dot notation raises KeyError:
        >>> md["user.email.address"]
        KeyError: 'email'

        # Behavior with None values:
        >>> md.user.nickname  # Attribute access is safe for chaining
        MagicDict({})
        >>> print(md.user['nickname']) # Bracket access returns the actual value
        None

        # Standard access for a non-existent key raises KeyError
        >>> md.user["email"]
        KeyError: 'email'

        # Chaining non-existent keys with attribute access is safe
        >>> md.user.address.city
        MagicDict({})


        # Chaining a key with a value of None is also safe
        >>> md.user.nickname.stagename
        MagicDict({})

        # Converting back to a standard dict
        >>> md.disenchant()
        {'user': {'name': 'Alice', 'id': 1, 'nickname': None}, 'permissions': ['read']}


        # --- USAGE NOTES & CAVEATS ---

        1.  Key Conflicts:

            Keys that conflict with standard `dict` methods must be accessed using brackets.
            >>> md = MagicDict({'keys': 'custom_value'})
            >>> md.keys
            <built-in method keys of MagicDict object at ...>
            >>> md['keys'] # Use bracket access to get the value
            'custom_value'

        2.  Invalid Identifiers:

            Keys that aren't valid Python identifiers (e.g., start with a number, contain spaces)
            must also use bracket access or the `mget()` method.
            >>> md = MagicDict({'1-key': 'value'})
            >>> md['1-key']
            'value'
            >>> md.mget('1-key')
            'value'

        3.  Non-String Keys:

            Non-string keys can only be accessed using standard bracket notation or `mget()`.
            >>> class MyKey: pass
            >>> k = MyKey()
            >>> md = MagicDict({k: 'value'})
            >>> md[k]
            'value'
            >>> md.k
            MagicDict({})

        Summary:
        - MagicDict allows convenient deep attribute-style access to nested dictionaries.
        - Missing keys and None values are handled safely without raising errors.
        - Be careful with key naming to avoid conflicts (e.g., dict methods) and invalid identifiers.
        - All standard dict methods, behaviors and bracket notation are preserved
    """

    def __init__(self, *args, **kwargs):
        """Initialize the MagicDict, recursively converting nested dicts.
        Supports initialization with a single dict, mapping, or standard dict args/kwargs."""
        super().__init__()
        # Create memo ONCE for the entire initialization to handle circular references
        memo = {}
        # Support initialization with either a single dict or standard dict args/kwargs
        # Get the input dict. If a single dict positional argument was passed,
        # use it directly (do NOT copy) so we preserve object identity for
        # circular references. For other inputs, fall back to creating a dict
        # (this preserves previous behavior for mappings/kwargs).
        if len(args) == 1 and not kwargs and isinstance(args[0], dict):
            input_dict = args[0]
        else:
            input_dict = dict(*args, **kwargs)
        # Register that MagicDict as the converted version of the input dict
        # This is crucial for circular references where the dict references itself
        memo[id(input_dict)] = self
        # Recursively convert nested dicts into MagicDicts
        # which would call _hook() with a fresh memo
        for k, v in input_dict.items():
            # Use super().__setitem__ directly to bypass __setitem__ override
            super().__setitem__(k, self._hook_with_memo(v, memo))

    @classmethod
    def _hook(cls, item):
        """Recursively converts dictionaries in collections to MagicDicts."""
        return cls._hook_with_memo(item, {})

    @classmethod
    def _hook_with_memo(cls, item, memo):
        """Recursively converts dictionaries in collections to MagicDicts.
        Uses a memoization dict to handle circular references."""
        item_id = id(item)  # Unique identifier for the object
        # Check memo FIRST, before any isinstance checks
        if item_id in memo:
            return memo[item_id]  # Return already processed object to handle circular refs

        if isinstance(item, MagicDict):
            # Already a MagicDict, but still need to register it in memo for circular refs
            memo[item_id] = item
            return item

        if isinstance(item, dict):
            new_dict = cls()
            memo[item_id] = new_dict
            for k, v in item.items():
                # Recursively hook nested items.
                new_dict[k] = cls._hook_with_memo(v, memo)
            return new_dict

        # Handle lists specifically. We modify in place to preserve references.
        if isinstance(item, list):
            memo[item_id] = item  # Prevent infinite recursion on self-referential lists.
            for i, elem in enumerate(item):
                item[i] = cls._hook_with_memo(elem, memo)
            return item

        # For tuples, which are immutable, we must create a new one.
        if isinstance(item, tuple):
            # Special handling for namedtuples to preserve their type.
            if hasattr(item, "_fields"):  # Check for namedtuple
                hooked_values = tuple(cls._hook_with_memo(elem, memo) for elem in item)
                return type(item)(*hooked_values)
            return type(item)(cls._hook_with_memo(elem, memo) for elem in item)

        # Handle other rare sequence types.
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
            try:
                memo[item_id] = item
                for i, elem in enumerate(item):
                    item[i] = cls._hook_with_memo(elem, memo)
                return item
            except TypeError:
                # Immutable sequence, create a new one.
                return type(item)(cls._hook_with_memo(elem, memo) for elem in item)

        return item

    def __getitem__(self, keys):
        """Support dot notation for nested keys in addition to standard dict access."""
        try:
            # First try standard dict access
            return super().__getitem__(keys)
        except KeyError:
            # Check if keys are ["a.b.c"] format
            if isinstance(keys, str) and "." in keys:
                keys = keys.split(".")
                obj = self
                for key in keys:
                    # If obj is a MagicDict or dict, do standard access
                    if isinstance(obj, Mapping):
                        obj = obj[key]
                    # If obj is a sequence (like list/tuple), try to access by index
                    elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes)):
                        obj = obj[int(key)]
                    # Otherwise, we cannot traverse further and raise KeyError
                    else:
                        raise
                return obj
            # Neither standard nor dot notation works, reraise
            raise

    def __getattr__(self, name):
        """Enables attribute-style access. Returns a safe, empty MagicDict
        for missing keys or keys with a value of None."""
        # Use super().__contains__ to avoid recursion with __getattr__
        if super().__contains__(name):
            value = self[name]
            if value is None:
                # Return an empty, temporary MagicDict for safe chaining.
                md = MagicDict()
                # Mark it so we can prevent modifications.
                object.__setattr__(md, "_from_none", True)
                return md
            # Ensure any plain dicts are hooked, in case they were added after initialization.
            if isinstance(value, dict) and not isinstance(value, MagicDict):
                value = MagicDict(value)
                self[name] = value
            return value
        try:
            # Fallback to standard attribute access for dict methods, etc.
            return super().__getattribute__(name)
        # If key doesn't exist, return an empty MagicDict for safe chaining.
        except AttributeError:
            md = MagicDict()
            # Mark it so we can prevent modifications.
            object.__setattr__(md, "_from_missing", True)
            return md

    def __setitem__(self, key, value):
        """Hook values to convert nested dicts into MagicDicts.
        Prevent setting values on MagicDicts created from missing or None keys."""
        self._raise_if_protected()
        super().__setitem__(key, self._hook(value))

    def __delitem__(self, key):
        """Prevent deleting items on MagicDicts created from missing or None keys."""
        self._raise_if_protected()
        super().__delitem__(key)

    def update(self, *args, **kwargs):
        """Recursively convert nested dicts into MagicDicts on update."""
        self._raise_if_protected()
        for k, v in dict(*args, **kwargs).items():
            self[k] = v

    def copy(self):
        """Return a shallow copy of the MagicDict."""
        return MagicDict(super().copy())

    def setdefault(self, key, default=None):
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

    def __deepcopy__(self, memo):
        """Support deep copy of MagicDict, handling circular references."""
        copied = MagicDict()
        memo[id(self)] = copied
        for k, v in self.items():
            copied[k] = deepcopy(v, memo)
        return copied

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    def __ior__(self, other):
        """Support the |= operator for in-place updates."""
        self.update(other)
        return self

    def pop(self, key, *args):
        """Prevent popping items on MagicDicts created from missing or None keys."""
        self._raise_if_protected()
        return super().pop(key, *args)

    def popitem(self):
        """Prevent popping items on MagicDicts created from missing or None keys."""
        self._raise_if_protected()
        return super().popitem()

    def clear(self):
        """Prevent clearing items on MagicDicts created from missing or None keys."""
        self._raise_if_protected()
        super().clear()

    def __getstate__(self):
        """
        Return the state to be pickled. It's just the dictionary's contents.
        pickle will handle the rest, including circular references.
        """
        return dict(self)

    def __setstate__(self, state):
        """
        Restore the state from the unpickled state. The `update` method
        is perfect for this as it already calls the `_hook` method to
        recursively convert nested dicts back to MagicDicts.
        """
        self.update(state)

    def mget(self, key, default=Ellipsis):
        """
        Safe get method that mimics attribute-style access.
        If the key doesn't exist, returns an empty MagicDict instead of raising KeyError.
        If the key exists but its value is None, returns an empty MagicDict for safe chaining.
        """
        # If default is not provided, return a MagicDict for missing keys.
        if default is Ellipsis:
            md = MagicDict()
            # Mark it so we can prevent modifications.
            object.__setattr__(md, "_from_missing", True)
            default = md
        # Use super().__contains__ to avoid recursion with __getattr__
        if super().__contains__(key):
            value = self[key]
            # If the value is None and default is not explicitly set to None,
            if value is None and default is not None:
                md = MagicDict()
                # Mark it so we can prevent modifications.
                object.__setattr__(md, "_from_none", True)
                return md
            return value
        return default

    def _raise_if_protected(self):
        """Raises TypeError if this MagicDict was created from a None or missing key,
        preventing modifications to. It can however be bypassed with dict methods."""
        if getattr(self, "_from_none", False) or getattr(self, "_from_missing", False):
            raise TypeError("Cannot modify NoneType or missing keys.")

    def mg(self, key, default=Ellipsis):
        """
        Shorthand for mget() method.
        """
        return self.mget(key, default)

    def disenchant(self):
        """
        Convert MagicDict and all nested MagicDicts back into standard dicts,
        handling circular references gracefully.
        """
        memo = {}  # Memoization dict to track visited object IDs

        def _disenchant_recursive(item):
            # If we've seen this object before, return its converted counterpart.
            item_id = id(item)
            if item_id in memo:
                return memo[item_id]

            # Use elif instead of separate if statements to avoid double-processing
            if isinstance(item, MagicDict):
                # Create a new dict, store it in memo *before* recursing.
                new_dict = {}
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
                # Special handling for namedtuples to preserve their type.
                if hasattr(item, "_fields"):  # Check if it's a namedtuple
                    disenchanted_values = tuple(_disenchant_recursive(elem) for elem in item)
                    # Recreate the namedtuple with its original class and disenchanted values.
                    return type(item)(*disenchanted_values)
                # It's a regular tuple, so just convert its contents.
                return tuple(_disenchant_recursive(elem) for elem in item)

            elif isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
                # Handle lists and other sequences.
                # Create a new list, store it in the memo *before* recursing.
                new_list = []
                memo[item_id] = new_list
                for elem in item:
                    new_list.append(_disenchant_recursive(elem))

                # Try to convert back to original type if it's not a plain list
                if not isinstance(item, list):
                    try:
                        return type(item)(new_list)
                    except TypeError:
                        return new_list  # Fallback to list
                return new_list

            elif isinstance(item, (set, frozenset)):

                new_set = type(item)(_disenchant_recursive(e) for e in item)
                memo[item_id] = new_set
                return new_set

            return item

        return _disenchant_recursive(self)


def magic_loads(s: str, **kwargs) -> MagicDict:
    """Deserialize a JSON string into a MagicDict instead of a dict."""
    return json.loads(s, object_hook=MagicDict)


def enchant(d: dict) -> MagicDict:
    """Convert a standard dictionary into a MagicDict."""
    if isinstance(d, MagicDict):
        return d
    if not isinstance(d, dict):
        raise TypeError(f"Expected dict, got {type(d).__name__}")
    return MagicDict(d)
