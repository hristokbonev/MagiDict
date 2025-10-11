[magicdict_docs.md](https://github.com/user-attachments/files/22863846/magicdict_docs.md)
# MagicDict Documentation

A powerful Python dictionary subclass that provides safe and convenient attribute-style access to nested data structures, with automatic conversion and graceful failure handling. Designed to simplify working with complex, deeply nested dictionaries, it reduces errors and improves code readability. Optimized and memoized for better performance.

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Utility Functions](#utility-functions)
- [Important Caveats](#important-caveats)
- [Common Use Cases](#common-use-cases)
- [Advanced Features](#advanced-features)
- [Performance Considerations](#performance-considerations)

## Overview

`MagicDict` extends Python's built-in `dict` to offer a more convenient and forgiving way to work with nested dictionaries. It's particularly useful when working with JSON data, API responses, configuration files, or any deeply nested data structures where safe navigation is important.

## Installation

Simply copy the `MagicDict` class into your project.

## Key Features

### 1. Attribute-Style Access

Access dictionary keys using dot notation instead of bracket notation:

```python
md = MagicDict({'user': {'name': 'Alice', 'age': 30}})
print(md.user.name)  # 'Alice'
print(md.user.age)   # 30
```

### 2. Dot Notation in Brackets

Use dot-separated strings for deep access, including list indices:

```python
md = MagicDict({
    'users': [
        {'name': 'Alice', 'id': 1},
        {'name': 'Bob', 'id': 2}
    ]
})

print(md['users.0.name'])  # 'Alice'
print(md['users.1.id'])    # 2
```

### 3. Recursive Conversion

Nested dictionaries are automatically converted to `MagicDict` instances:

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
md = MagicDict(data)
print(md.company.departments.engineering.employees)  # 50
```

### 4. Graceful Failure

Accessing non-existent keys returns an empty `MagicDict` instead of raising errors:

```python
md = MagicDict({'user': {'name': 'Alice'}})

# No error, returns empty MagicDict
result = md.user.email.address.street
print(result)  # MagicDict({})

# Safe chaining
if md.settings.theme.dark_mode:
    # This won't cause an error even if 'settings' doesn't exist
    pass
```

### 5. Safe None Handling

Keys with `None` values can be safely chained:

```python
md = MagicDict({'user': {'nickname': None}})

print(md.user.nickname.stage_name)  # MagicDict({})

# Bracket access returns the actual None value
print(md.user['nickname'])  # None
```

### 6. Standard Dictionary Behavior Preserved

All standard `dict` methods and behaviors work as expected. For example missing keys with brackets raise KeyError as expected

### 7. Safe `mget()` Method

`mget` is MagicDict's native `get` method. Unless a custom default is provided, it returns an empty `MagicDict` for missing keys or `None` values:

```python
md = MagicDict({'1-invalid': 'value', 'valid': None})

# Works with invalid identifiers
print(md.mget('1-invalid'))  # 'value'

# Returns empty MagicDict for missing keys
print(md.mget('missing'))  # MagicDict({})

# Shorthand version
print(md.mg('1-invalid'))  # 'value'

# Provide custom default
print(md.mget('missing', 'default'))  # 'default'
```

### 8. Convert Back to Standard Dict

Use `disenchant()` to convert back to a standard Python `dict`:

```python
md = MagicDict({'user': {'name': 'Alice'}})
standard_dict = md.disenchant()
print(type(standard_dict))  # <class 'dict'>
```

## API Reference

### Constructor

```python
MagicDict(*args, **kwargs)
```

Creates a new `MagicDict` instance. Accepts the same arguments as the built-in `dict`.

**Examples:**

```python
MagicDict(*args, **kwargs)
```
or
```python
d = {"key": "value"}

md = MagicDict(d)
```

### Methods

#### `mget(key, default=Ellipsis)`

Safe get method that mimics attribute-style access.

**Parameters:**

- `key`: The key to retrieve
- `default`: Value to return if key doesn't exist (optional)

**Returns:**

- The value if key exists and is not `None`
- Empty `MagicDict` if key doesn't exist (unless custom default provided)
- Empty `MagicDict` if value is `None` (unless default explicitly set to `None`)

#### `mg(key, default=Ellipsis)`

Shorthand alias for `mget()`.

#### `disenchant()`

Converts the `MagicDict` and all nested `MagicDict` instances back to standard Python dictionaries. Handles circular references gracefully.

**Returns:** A standard Python `dict`

**Example:**

```python
md = MagicDict({'nested': {'data': [1, 2, 3]}})
regular_dict = md.disenchant()
print(type(regular_dict))  # <class 'dict'>
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

Converts a standard dictionary into a `MagicDict`.

**Parameters:**

- `d`: A standard Python dictionary

**Returns:** A `MagicDict` instance

### `magic_loads(s, **kwargs)`

Deserializes a JSON string directly into a `MagicDict` instead of a standard dict.

**Parameters:**

- `s`: JSON string to parse
- `**kwargs`: Additional arguments passed to `json.loads()`

**Returns:** A `MagicDict` instance

**Example:**

```python
import json

json_string = '{"user": {"name": "Alice", "age": 30}}'
md = magic_loads(json_string)
print(md.user.name)  # 'Alice'
```

## Important Caveats

### 1. Key Conflicts with Dict Methods

Keys that conflict with standard `dict` methods must be accessed using brackets, `mget` or `get`:

```python
md = MagicDict({'keys': 'my_value', 'items': 'another_value'})

# These return dict methods, not your values
print(md.keys)   # <built-in method keys...>
print(md.items)  # <built-in method items...>

# Use bracket access instead
print(md['keys'])   # 'my_value'
print(md['items'])  # 'another_value'

# Or use mget()
print(md.mget('keys'))  # 'my_value'
```

**Common conflicting keys:** `keys`, `values`, `items`, `get`, `pop`, `update`, `clear`, `copy`, `setdefault`, `fromkeys`

### 2. Invalid Python Identifiers

Keys that aren't valid Python identifiers must use bracket access or `mget()`:

```python
md = MagicDict({
    '1-key': 'value1',
    'my key': 'value2',
    'my-key': 'value3'
})

# Must use brackets or mget()
print(md['1-key'])       # 'value1'
print(md.mget('my key')) # 'value2'
print(md['my-key'])      # 'value3'

# These won't work
print(md.1-key)        # SyntaxError
print(md.my key)       # SyntaxError
```

### 3. Non-String Keys

Non-string keys can only be accessed using standard bracket notation or `mget()`:

```python
md = MagicDict({1: 'one', (2, 3): 'tuple_key'})

print(md[1])        # 'one'
print(md[(2, 3)])   # 'tuple_key'
print(md.mget(1))   # 'one'

print(md.1)  # SyntaxError
```

### 4. Protected Empty MagicDicts

Empty `MagicDict` instances returned from missing keys or `None` values are protected from modification:

```python
md = MagicDict({'user': None})

md.user["name"] = 'Alice'  # TypeError

# Same for missing keys
md["missing"]["key"] = 'value'  # TypeError
```

This protection prevents silent bugs where you might accidentally try to modify a non-existent path.

### 5. Setting attributes
Setting or updating keys using dot notation is not supported. Use bracket notation instead. As with standard dicts, this is purposely restricted to avoid confusion and potential bugs.

```python
md = MagicDict({'user': {'name': 'Alice'}})

md.user.name = 'Bob'  # AttributeError
md.user.age = 30      # AttributeError
# Use bracket notation instead
md['user']['name'] = 'Bob'
md['user']['age'] = 30
```

## Common Use Cases

JSON APIs; Configuration Files; Nested Data Structures; Safe Data Exploration; Data Transformation

## Advanced Features

### Pickle Support

`MagicDict` supports pickling and unpickling:

```python
import pickle

md = MagicDict({'data': {'nested': 'value'}})
pickled = pickle.dumps(md)
restored = pickle.loads(pickled)
print(restored.data.nested)  # 'value'
```

### Deep Copy Support

```python
from copy import deepcopy

md1 = MagicDict({'user': {'name': 'Alice'}})
md2 = deepcopy(md1)
md2.user.name = 'Bob'

print(md1.user.name)  # 'Alice' (unchanged)
print(md2.user.name)  # 'Bob'
```

### In-Place Updates with `|=` Operator

Python 3.9+ dict merge operator is supported:

```python
md = MagicDict({'a': 1})
md |= {'b': 2, 'c': 3}
print(md)  # MagicDict({'a': 1, 'b': 2, 'c': 3})
```

### Circular Reference Handling

`MagicDict` gracefully handles circular references:

```python
md = MagicDict({'name': 'root'})
md['self'] = md  # Circular reference

# Access works
print(md.self.name)  # 'root'
print(md.self.self.name)  # 'root'

# Safely converts back to dict
regular = md.disenchant()
```

### Auto-completion Support

`MagicDict` provides intelligent auto-completion in IPython, Jupyter notebooks and IDE's.

## Performance Considerations

### Initialization Overhead

Converting nested structures has a one-time cost proportional to the depth and size of the structure:

```python
import time

large_dict = {'level1': {f'key{i}': {'nested': 'value'} for i in range(1000)}}

start = time.time()
md = MagicDict(large_dict)
print(f"Conversion took: {time.time() - start:.4f}s")
```

### Memory Usage

`MagicDict` uses slightly more memory than standard dicts due to:

- Additional object instances for nested dicts
- Small overhead for the class itself

### Access Speed

- Attribute access: Marginally slower than bracket notation (negligible for most use cases)
- Bracket notation: Comparable to standard dict
- Dot notation in brackets: Additional parsing overhead

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

# MagicDict - clean and safe
md = MagicDict({'user': {'profile': {'name': 'Alice'}}})
name = md.user.profile.name or 'Unknown'
```

### vs. DotDict/AttrDict Libraries

MagicDict provides additional features:

- Safe chaining with missing keys (returns empty MagicDict)
- Safe chaining with None values
- Dot notation in bracket access
- Built-in `mget()` for safe access
- Protected empty instances
- Circular reference handling

## Troubleshooting

### KeyError on Dot Notation Access

```python
md = MagicDict({'user': {'name': 'Alice'}})

email = md['user']['email'] #KeyError
email = md['user.email'] #KeyError

# This is safe
email = md.user.email or 'no-email'
```

### Cannot Modify Error

```python
md = MagicDict({'user': None})

md.user.name = 'Alice' #TypeError
```

### Unexpected Empty MagicDict

```python
md = MagicDict({'value': None})

print(md.value)  # MagicDict({})

# Use bracket access to get actual None
print(md['value'])  # None
```
