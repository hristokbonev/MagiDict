[![GitHub Repo](https://img.shields.io/badge/GitHub-MagiDict-181717?logo=github)](https://github.com/hristokbonev/MagiDict)
[![PyPI version](https://img.shields.io/pypi/v/magidict.svg?color=blue&label=PyPI)](https://pypi.org/project/magidict/)
[![Python versions](https://img.shields.io/pypi/pyversions/magidict.svg?color=informational)](https://pypi.org/project/magidict/)
[![Build Status](https://github.com/hristokbonev/MagiDict/actions/workflows/ci.yml/badge.svg)](https://github.com/hristokbonev/MagiDict/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/hristokbonev/MagiDict/branch/main/graph/badge.svg?token=YOUR_CODECOV_TOKEN)](https://codecov.io/gh/hristokbonev/MagiDict)
[![Benchmarks](https://img.shields.io/badge/Benchmarks-View%20Results-blueviolet?logo=python&logoColor=white)](https://hristokbonev.github.io/magidict/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<p align="center">
  <img src="http://raw.githubusercontent.com/hristokbonev/MagiDict/refs/heads/main/docs/assets/MagiDictLogo.png" alt="MagiDict Logo" width="200">
</p>

<h1 align="center">MagiDict</h1>

Do you find yourself chaining `.get()`'s like there's no tomorrow, then praying to the Gods of Safety that you didn't miss a single `{}`?<br>
Has your partner left you because whenever they ask you to do something, you always reply, "I'll try, except `KeyError` as e"?<br>
Do your kids get annoyed with you because you've called them "`None`" one too many times.<br>
And did your friends stop hanging out with you because every time you're together, you keep going to the bathroom to check your production logs for any TypeErrors named "`real_friends`"?<br>
How often do you seek imaginary guidance from Guido, begging him to teach you the mystical ways of safely navigating nested Python dictionaries?<br>
When you're out in public, do you constantly have the feeling that Keanu Reeves is judging you from behind the corner for your inability to elegantly access nested dictionary keys?<br>
And when you go to sleep at night, do you lie awake thinking about how much better your life would be if you took that course in JavaScript that your friend gave you a voucher for, before they moved to a different country and you lost contact with them, so you could finally use optional chaining and nullish coalescing operators to safely access nested properties without all the drama?

If you answered "yes" to any of these questions, you're not alone!
But don't worry anymore, because there's finally a solution that doesn't involve learning a whole new programming language or changing your religion to JavaScript! It's called ✨MagiDict✨ and it's here to save your sanity!

MagiDict is a powerful Python dictionary subclass that provides simple, safe and convenient attribute-style access to nested data structures, with recursive conversion and graceful failure handling. Designed to ease working with complex, deeply nested dictionaries, it reduces errors and improves code readability. Optimized and memoized for better performance.

Stop chaining `get()`'s and brackets like it's 2003 and start living your best life, where `Dicts.Just.Work`!

## Overview

`MagiDict` extends Python's built-in `dict` to offer a more convenient and forgiving way to work with nested dictionaries. It's particularly useful when working with JSON data, API responses, configuration files, or any deeply nested data structures where safe navigation is important.

## Installation

You can install MagiDict via pip:

```bash
pip install magidict
```

## Quick Start

```python
from magidict import MagiDict

# Create from dict
md = MagiDict({
    'user': {
        'name': 'Alice',
        'profile': {
            'bio': 'Software Engineer',
            'location': 'NYC'
        }
    }
})

# Dot notation access
print(md.user.name)  # 'Alice'
print(md.user.profile.bio)  # 'Software Engineer'

# Safe chaining - no errors!
print(md.user.settings.theme)  # MagiDict({}) - not a KeyError!
print(md.user.email or 'no-email')  # 'no-email'

# Works with None values too
md = MagiDict({'value': None})
print(md.value.nested.key)  # MagiDict({}) - safe!
```

## Documentation

Full documentation available in the GitHub [Wiki](https://github.com/hristokbonev/MagiDict/wiki)

## Key Features

```ascii
         ┌───────────────────┐
         │   Access Styles   │
         └─────────┬─────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌────────────────┐
│ Attribute Style │  │ Bracket Style  │
│        .        │  │       []       ├──────┐
└─────────┬───────┘  └───────┬────────┘      │
          │                  │               │
          ▼                  ▼               ▼
    ┌──────────┐       ┌──────────┐     ┌─────────┐
    │   Safe   │       │   Safe   │     │ Strict  ├──────────┐
    └─────┬────┘       └─────┬────┘     └────┬────┘          │
          │                  │               │               │
          ▼                  ▼               ▼               ▼
      ┌───────┐     ┌────────────────┐  ┌──────────┐  ┌──────────────┐
      │ d.bar │     │ d["foo","bar"] │  │ d["foo"] │  │ d["foo.bar"] │
      └───────┘     └────────────────┘  └──────────┘  └──────────────┘


*Safe* returns empty MagiDict for missing keys or None values.
*Strict* raises KeyError for missing keys and returns None for None values.
```

### 1. Attribute-Style Access

Access dictionary keys using dot notation instead of bracket notation. Missing keys and keys with `None` values return an empty `MagiDict`:

```python
md = MagiDict({'user': {'name': 'Alice', 'age': 30, 'nickname': None}})
md.user.name # 'Alice'
md.user.age  # 30
md.user.nickname # MagiDict({})
md.user.email # MagiDict({})
```

### 2. Dot Notation in Brackets

Use dot-separated strings for deep access, including list indices.
Missing keys raise `KeyError` and out-of-bounds indices raise `IndexError` as expected from standard dict/list behavior:

```python
md = MagiDict({
    'users': [
        {'name': 'Alice', 'id': 1},
        {'name': 'Keanu', 'id': 2}
    ]
})

md['users.0.name']  # 'Alice'
md['users.1.id']    # 2
md['users.2.name']  # IndexError
md['users.0.email'] # KeyError
```

### 3. List or Tuple of Keys in Brackets

Use a list or tuple of keys for deep sefe access.
Missing keys and keys with `None` values return an empty `MagiDict`. If the entire tuple is an actual key in the dict, it prioritizes and returns that value. The caveat of this is that you cannot strictly access tuple keys that don't exist, as it will return an empty `MagiDict` instead of raising `KeyError`. For that, use the strict `strict_get()` method.

```python
md = MagiDict({
    'users': [
        {'name': 'Alice', 'id': 1},
        {'name': 'Keanu', 'id': 2}
    ]
})
md['users', 0, 'name']  # 'Alice'
md['users', 1, 'id']    # 2
md['users', 2, 'name']  # MagiDict({})
md['users', 0, 'email'] # MagiDict({})

md['users', 0, 'name'] = "Overridden"
# It returns the the actual tuple key value
md['users', 0, 'name']  # 'Overridden'
```

### 4. Recursive Conversion

Nested dictionaries are automatically converted to `MagiDict` instances:

```python
data = {
    'company': {
        'departments': {
            'engineering': {
                'employees': 50
            }
        }
    }
}
md = MagiDict(data)
md.company.departments.engineering.employees  # 50
```

### 5. Graceful Failure

Accessing non-existent keys or keys with `None` values via dot notation or tuple/list of keys returns an empty `MagiDict` instead of raising errors:

```python
md = MagiDict({'user': {'name': 'Alice'}})

# No error, returns empty MagiDict
md.user.email.address.street # MagiDict({})
md["user", "email", "address", "street"] # MagiDict({})

# Safe chaining
if md.settings.theme.dark_mode:
    # This won't cause an error even if 'settings' doesn't exist
    pass
```

### 6. Safe None Handling

Keys with `None` values can be safely chained:

```python
md = MagiDict({'user': {'nickname': None}})

md.user.nickname.stage_name  # MagiDict({})

# Bracket access returns the actual None value
md.user['nickname']  # None
# Safe access with conversion back to None
none(md.user.nickname)  # None
```

### 7. Standard Dictionary Behavior Preserved

All standard `dict` methods and behaviors work as expected. For example missing keys with brackets raise `KeyError` as expected

### 8. Safe `mget()` Method

`mget` is MagiDict's native `get` method. Unless a custom default is provided, it returns an empty `MagiDict` for missing keys or `None` values:

```python
md = MagiDict({'1-invalid': 'value', 'valid': None})

# Works with invalid identifiers
md.mget('1-invalid')  # 'value'

# Returns empty MagiDict for missing keys
md.mget('missing')  # MagiDict({})

# Shorthand version
md.mg('1-invalid')  # 'value'

# Provide custom default
md.mget('missing', 'default')  # 'default'
```

### 9. Strict `strict_get()` Method

`strict_get` is a strict version of `mget` that behaves like standard `dict` bracket access, raising `KeyError` for missing keys and returning `None` for keys with `None` values.
The main usage is to strictly access tuple keys, where if they don't exist, it raises a `KeyError`, instead of returning an empty `MagiDict`.

```python
md = MagiDict({'user': {'name': 'Alice', ('tuple', 'key'): 'value'}, 'valid': None})
# Raises KeyError for missing keys
md.sg('missing')  # KeyError
md.sg('valid')    # None
# Raises KeyError for missing nested keys
md.sg('user').sg('email')  # KeyError
# Raises KeyError for missing tuple keys
md.sg(('tuple', 'missing'))  # KeyError
md.sg(('tuple', 'key'))      # 'value'
```

### 10. Convert Back to Standard Dict

Use `disenchant()` to convert back to a standard Python `dict`:

```python
md = MagiDict({'user': {'name': 'Alice'}})
standard_dict = md.disenchant()
type(standard_dict)  # <class 'dict'>
```

### 11. Convert empty MagiDict to None

Use `none()` to convert empty `MagiDict` instances that were created from `None` or missing keys back to `None`:

```python
md = MagiDict({'user': None, 'age': 25})
none(md.user)       # None
none(md.user.name)  # None
none(md.age)        # 25
```

## API Reference

### Constructor

```python
MagiDict(*args, **kwargs)
```

Creates a new `MagiDict` instance. Accepts the same arguments as the built-in `dict`.

**Examples:**

```python
MagiDict(*args, **kwargs)
```

or

```python
d = {"key": "value"}

md = MagiDict(d)
```

### Methods

#### `mget(key, default=...)`

Safe get method that mimics `dict`'s `get()`, but returns an empty `MagiDict` for missing keys or `None` values unless a custom default is provided.

**Parameters:**

- `key`: The key to retrieve
- `default`: Value to return if key doesn't exist (optional)

**Returns:**

- The value if key exists and is not `None`
- Empty `MagiDict` if key doesn't exist (unless custom default provided)
- Empty `MagiDict` if value is `None` (unless default explicitly set to `None`)

#### `mg(key, default=...)`

Shorthand alias for `mget()`.

#### `strict_get(key)`

Strict get method that raises `KeyError` for missing keys and returns `None` for keys with `None` values, mimicking standard `dict` bracket access behavior.

**Parameters:**

- `key`: The key to retrieve

**Returns:**

- The value if key exists (including `None`)
- Raises `KeyError` if key doesn't exist

#### `sg(key)` and `sget(key)`

Shorthand aliasese for `strict_get()`.

#### `disenchant()`

Converts the `MagiDict` and all nested `MagiDict` instances back to standard Python dictionaries. Handles circular references gracefully.

**Returns:** A standard Python `dict`

**Example:**

```python
md = MagiDict({'nested': {'data': [1, 2, 3]}})
regular_dict = md.disenchant()
type(regular_dict)  # <class 'dict'>
```

#### `filter(function, drop_empty=False)`

Returns a new `MagiDict` containing only the items for which the provided function returns `True`.

**Parameters:**

- `function`: A function that takes either one argument (value) or two arguments (key, value) and returns `True` or `False`. If function is `None`,
  it defaults to filtering out items with `None` values.
- `drop_empty`: If `True`, removes empty data structures from the result (default: `False`)

**Returns:** A new `MagiDict` with filtered items

**Example:**

```python
md = MagiDict({'a': 1, 'b': 2, 'c': 3})
filtered_md = md.filter(lambda k, v: v % 2 == 1)
# filtered_md is MagiDict({'a': 1, 'c': 3})
```

#### `search_key(key)`

Searches for the first occurrence of the specified key in the `MagiDict` and its nested structures, returning the corresponding value if found.

**Parameters:**

- `key`: The key to search for

**Returns:** The value associated with the key or `None` if not found

**Example:**

```python
md = MagiDict({'level1': {'level2': {'target_key': 'found_value'}}})
value = md.search_key('target_key')  # 'found_value'
```

#### `search_keys(keys)`

Searches for all occurrences of the specified key in the `MagiDict` and its nested structures, returning a list of values corresponding to the found keys.

**Parameters:**

- `keys`: The key to search for

**Returns:** A list of values associated with the keys or an empty list if none found

**Example:**

```python
md = MagiDict({
    'level1': {'target_key': 'value1'},
    'level2': {'nested': {'target_key': 'value2'}}
})
values = md.search_keys('target_key')  # ['value1', 'value2']
```

### Standard Dict Methods

All standard dictionary methods are supported:

- `update()` - Update with key-value pairs
- `copy()` - Return a shallow copy
- `setdefault()` - Get value or set default
- `fromkeys()` - Create dict from sequence of keys
- `pop()` - Remove and return value
- `popitem()` - Remove and return arbitrary item
- `clear()` - Remove all items
- `keys()` - Return dict keys
- `values()` - Return dict values
- `items()` - Return dict items
- `get()` - Get value with optional default
- `__contains__()` - Check if key exists (via `in`)
- and more

## Utility Functions

### `enchant(d)`

Converts a standard dictionary into a `MagiDict`.

**Parameters:**

- `d`: A standard Python dictionary

**Returns:** A `MagiDict` instance

### `magi_loads(s, **kwargs)`

Deserializes a JSON string directly into a `MagiDict` instead of a standard dict.

**Parameters:**

- `s`: JSON string to parse
- `**kwargs`: Additional arguments passed to `json.loads()`

**Returns:** A `MagiDict` instance

**Example:**

```python

json_string = '{"user": {"name": "Alice", "age": 30}}'
md = magi_loads(json_string)
md.user.name  # 'Alice'
```

### `magi_load(fp, **kwargs)`

Deserializes a JSON file-like object into a `MagiDict` instead of a standard dict.

**Parameters:**

- `fp`: A file-like object containing JSON data
- `**kwargs`: Additional arguments passed to `json.load()`

**Returns:** A `MagiDict` instance

### `none(obj)`

Converts an empty `MagiDict` that was created from a `None` or missing key into `None`. Otherwise, returns the object as is.

**Parameters:**

- `obj`: The object to check

**Returns:**

- `None` if `obj` is an empty `MagiDict` created from `None` or missing key
- `obj` otherwise

## Important Caveats

### 1. Key Conflicts with Dict Methods

Keys that conflict with standard `dict` methods must be accessed using brackets, `mget` or `get`:

```python
md = MagiDict({'keys': 'my_value', 'items': 'another_value'})

# These return dict methods, not your values
md.keys   # <built-in method keys...>
md.items  # <built-in method items...>

# Use bracket access instead
md['keys']   # 'my_value'
md['items']  # 'another_value'

# Or use mget()
md.mget('keys')  # 'my_value'
```

**Common conflicting keys:** `keys`, `values`, `items`, `get`, `pop`, `update`, `clear`, `copy`, `setdefault`, `fromkeys`

### 2. Invalid Python Identifiers

Keys that aren't valid Python identifiers must use bracket access or `mget()`:

```python
md = MagiDict({
    '1-key': 'value1',
    'my key': 'value2',
    'my-key': 'value3'
})

# Must use brackets or mget()
md['1-key']       # 'value1'
md.mget('my key') # 'value2'
md['my-key']      # 'value3'

# These won't work
print(md.1-key)        # SyntaxError
print(md.my key)       # SyntaxError
```

### 3. Non-String Keys

Non-string keys can only be accessed using standard bracket notation or `mget()`:

```python
md = MagiDict({1: 'one', (2, 3): 'tuple_key'})

md[1]        # 'one'
md[(2, 3)]   # 'tuple_key'
md.mget(1)   # 'one'

print(md.1)  # SyntaxError
```

### 4. Protected Empty MagiDicts

Empty `MagiDict` instances returned from missing keys or `None` values are protected from modification:

```python
md = MagiDict({'user': None})

md.user["name"] = 'Alice'  # TypeError

# Same for missing keys
md["missing"]["key"] = 'value'  # TypeError
```

This protection prevents silent bugs where you might accidentally try to modify a non-existent path.

### 5. Setting attributes

Setting or updating keys using dot notation is not supported. Use bracket notation instead. As with standard dicts, this is purposely restricted to avoid confusion and potential bugs.

```python
md = MagiDict({'user': {'name': 'Alice'}})

md.user.name = 'Keanu'  # AttributeError
md.user.age = 30      # AttributeError
# Use bracket notation instead
md['user']['name'] = 'Keanu'
md['user']['age'] = 30
```

### 6. Accessing Tuple Keys

When accessing tuple keys, if the tuple does not exist as a key in the dictionary, it will return an empty `MagiDict` instead of raising a `KeyError`. To strictly access tuple keys and raise `KeyError` if they don't exist, use the `strict_get()` method.

```python
md = MagiDict({('tuple', 'key'): 'value'})
md[('tuple', 'key')]      # 'value'
md[('tuple', 'missing')]  # MagiDict({}) - does not raise KeyError
md.sg(('tuple', 'missing'))  # KeyError - raises KeyError
```

## Advanced Features

### Pickle Support

`MagiDict` supports pickling and unpickling:

```python

md = MagiDict({'data': {'nested': 'value'}})
pickled = pickle.dumps(md)
restored = pickle.loads(pickled)
restored.data.nested  # 'value'
```

### Deep Copy Support

```python

md1 = MagiDict({'user': {'name': 'Alice'}})
md2 = deepcopy(md1)
md2.user.name = 'Keanu'

md1.user.name  # 'Alice' (unchanged)
md2.user.name  # 'Keanu'
```

### In-Place Updates with `|=` Operator

Python 3.9+ dict merge operator is supported:

```python
md = MagiDict({'a': 1})
md |= {'b': 2, 'c': 3}
md  # MagiDict({'a': 1, 'b': 2, 'c': 3})
```

### Circular Reference Handling

`MagiDict` gracefully handles circular references:

```python
md = MagiDict({'name': 'root'})
md['self'] = md  # Circular reference

# Access works
md.self.name  # 'root'
md.self.self.name  # 'root'

# Safely converts back to dict
regular = md.disenchant()
```

### Auto-completion Support

`MagiDict` provides intelligent auto-completion in IPython, Jupyter notebooks and IDE's.

## Performance Considerations

### Tested:

- All standard and custom functionality
- Circular and self references through pickle/deepcopy/disenchant
- Concurrent access patterns (multi-threaded reads/writes)
- Protected MagiDict mutation attempts
- Deep nesting with recursion limits and stack overflow prevention
- Type preservation through operations

### Performance

Magidict's initialization and recursive conversion are very fast due to the core hooks being implemented in C.

[Benchmarks](https://hristokbonev.github.io/magidict/)

### Best Practices

**Good use cases:**

- Configuration files
- API response processing
- Data exploration
- One-time data transformations
- Interactive development

**Avoid for:**

- High-performance inner loops
- Large-scale data processing
- Memory-constrained environments
- When you need maximum speed

### Optimization Tips

```python
# If you need standard dict for performance-critical code
if need_speed:
    regular_dict = md.disenchant()
    # Use regular_dict in hot loop

# Convert back when done
md = enchant(regular_dict)
```

## Comparison with Alternatives

### vs. Regular Dict

```python
# Regular dict - verbose and error-prone
regular = {'user': {'profile': {'name': 'Alice'}}}
name = regular.get('user', {}).get('profile', {}).get('name', 'Unknown')

# MagiDict - clean and safe
md = MagiDict({'user': {'profile': {'name': 'Alice'}}})
name = md.user.profile.name or 'Unknown'
```

### vs. DotDict, Bunch, AttrDict and Similar Libraries

MagiDict provides additional features:

- Safe chaining with missing keys (returns empty `MagiDict`)
- Safe chaining with None values
- Dot notation in bracket access
- List/tuple of keys in bracket access with safe chaining
- Built-in `mget()` and `strict_get()` methods
- Protected empty instances
- Circular reference handling
- Memoization
- Type preservation for all non-dict values
- In-place mutation

## Troubleshooting

### `KeyError` on Dot Notation Access

```python
md = MagiDict({'user': {'name': 'Alice'}})

email = md['user']['email'] #KeyError
email = md['user.email'] #KeyError

# This is safe
email = md.user.email or 'no-email'
email = md['user', 'email'] or 'no-email'
```

### Cannot Modify Error

```python
md = MagiDict({'user': None})

md.user.name = 'Alice' #TypeError
```

### Unexpected Empty `MagiDict`

```python
md = MagiDict({'value': None})

md.value  # MagiDict({})

# Use bracket access to get actual None
md['value']  # None
```

### Empty `MagiDict` on Missing Tuple Key

```python
md = MagiDict({('tuple', 'key'): 'value'})
md[('tuple', 'missing')]  # MagiDict({}) - does not raise KeyError
md.sg(('tuple', 'missing'))  # KeyError - raises KeyError
```

---

## Contributing

Contributions are welcome and appreciated! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) for more information.

## License

MagiDict is licensed under the [MIT License](https://github.com/hristokbonev/MagiDict/blob/main/LICENSE).

## Links

For documentation and source code, visit the project on GitHub: <br>
Documentation: [GitHub Wiki](https://github.com/hristokbonev/MagiDict/wiki)<br>
PyPI: [magidict](https://pypi.org/project/magidict/)<br>
Source Code: [MagiDict](https://github.com/hristokbonev/MagiDict)<br>
Issue Tracker: [GitHub Issues](https://github.com/hristokbonev/MagiDict/issues)<br>
Benchmarks: [Performance Results](https://hristokbonev.github.io/magidict/)
