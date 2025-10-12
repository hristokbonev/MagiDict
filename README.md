[magicdict_docs.md](https://github.com/user-attachments/files/22863846/magicdict_docs.md)
# MagicDict

Do you often find yourself chaining get()'s like there's no tomorrow, and then pray to the gods of safety that you didn't miss a { } in one of them? Has your partner already left you because when they ask you to do something you always reply "I'll try, except KeyError as e"? Do you kids get annoyed with you because you've called them "None" one too many times. And do your friends avoid you because when you hang out with them, you keep going to the bathroom to check your production logs for any TypeErrors named "real_friends"? How often do you seek imaginary guidance from Guido, begging him to teach you the mystical ways of safely navigating nested Python dictionaries? When you go out in public, do you constantly have the feeling that Keanu Reeves is judging you from behind the corner for not being able to safely access nested dictionary keys?

And when you go to sleep at night, do you lie awake thinking about how much better your life would be if you took a that course in JavaScript that your friend gave you a voucher for, before they moved to a different country and you lost contact with them, so you could finally use optional chaining and nullish coalescing operators to safely access nested properties without all the drama?

If you answered "yes" to any of these questions, then MagicDict is the library for you!

MagicDict is a powerful Python dictionary subclass that provides simple, safe and convenient attribute-style access to nested data structures, with automatic conversion and graceful failure handling. Designed to ease working with complex, deeply nested dictionaries, it reduces errors and improves code readability. Optimized and memoized for better performance.

Stop chaining get calls and brackets like it's 2003 and start living your best life, where `Dicts.Just.Work`!

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
- [Key Features](#key-features)
- [API Reference](#api-reference)
- [Utility Functions](#utility-functions)
- [Important Caveats](#important-caveats)
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
md.user.name # 'Alice'
md.user.age  # 30
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

md['users.0.name']  # 'Alice'
md['users.1.id']    # 2
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
md.company.departments.engineering.employees  # 50
```

### 4. Graceful Failure

Accessing non-existent keys returns an empty `MagicDict` instead of raising errors:

```python
md = MagicDict({'user': {'name': 'Alice'}})

# No error, returns empty MagicDict
md.user.email.address.street # MagicDict({})

# Safe chaining
if md.settings.theme.dark_mode:
    # This won't cause an error even if 'settings' doesn't exist
    pass
```

### 5. Safe None Handling

Keys with `None` values can be safely chained:

```python
md = MagicDict({'user': {'nickname': None}})

md.user.nickname.stage_name  # MagicDict({})

# Bracket access returns the actual None value
md.user['nickname']  # None
```

### 6. Standard Dictionary Behavior Preserved

All standard `dict` methods and behaviors work as expected. For example missing keys with brackets raise KeyError as expected

### 7. Safe `mget()` Method

`mget` is MagicDict's native `get` method. Unless a custom default is provided, it returns an empty `MagicDict` for missing keys or `None` values:

```python
md = MagicDict({'1-invalid': 'value', 'valid': None})

# Works with invalid identifiers
md.mget('1-invalid')  # 'value'

# Returns empty MagicDict for missing keys
md.mget('missing')  # MagicDict({})

# Shorthand version
md.mg('1-invalid')  # 'value'

# Provide custom default
md.mget('missing', 'default')  # 'default'
```

### 8. Convert Back to Standard Dict

Use `disenchant()` to convert back to a standard Python `dict`:

```python
md = MagicDict({'user': {'name': 'Alice'}})
standard_dict = md.disenchant()
type(standard_dict)  # <class 'dict'>
```

### 9. Convert empty MagicDict to None
Use `none()` to convert empty MagicDict instances that were created from `None` or missing keys back to `None`:

```python
md = MagicDict({'user': None, 'age': 25})
none(md.user)       # None
none(md.user.name)  # None
none(md.age)        # 25
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

#### `mget(key, default=...)`

Safe get method that mimics `dict`'s `get()`, but returns an empty `MagicDict` for missing keys or `None` values unless a custom default is provided.

**Parameters:**

- `key`: The key to retrieve
- `default`: Value to return if key doesn't exist (optional)

**Returns:**

- The value if key exists and is not `None`
- Empty `MagicDict` if key doesn't exist (unless custom default provided)
- Empty `MagicDict` if value is `None` (unless default explicitly set to `None`)

#### `mg(key, default=...)`

Shorthand alias for `mget()`.

#### `disenchant()`

Converts the `MagicDict` and all nested `MagicDict` instances back to standard Python dictionaries. Handles circular references gracefully.

**Returns:** A standard Python `dict`

**Example:**

```python
md = MagicDict({'nested': {'data': [1, 2, 3]}})
regular_dict = md.disenchant()
type(regular_dict)  # <class 'dict'>
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

json_string = '{"user": {"name": "Alice", "age": 30}}'
md = magic_loads(json_string)
md.user.name  # 'Alice'
```

### `none(obj)`

Converts an empty `MagicDict` that was created from a `None` or missing key into `None`. Otherwise, returns the object as is.

**Parameters:**

- `obj`: The object to check

**Returns:**

- `None` if `obj` is an empty `MagicDict` created from `None` or missing keyFtest
- `obj` otherwise

## Important Caveats

### 1. Key Conflicts with Dict Methods

Keys that conflict with standard `dict` methods must be accessed using brackets, `mget` or `get`:

```python
md = MagicDict({'keys': 'my_value', 'items': 'another_value'})

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
md = MagicDict({
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
md = MagicDict({1: 'one', (2, 3): 'tuple_key'})

md[1]        # 'one'
md[(2, 3)]   # 'tuple_key'
md.mget(1)   # 'one'

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

## Advanced Features

### Pickle Support

`MagicDict` supports pickling and unpickling:

```python

md = MagicDict({'data': {'nested': 'value'}})
pickled = pickle.dumps(md)
restored = pickle.loads(pickled)
restored.data.nested  # 'value'
```

### Deep Copy Support

```python

md1 = MagicDict({'user': {'name': 'Alice'}})
md2 = deepcopy(md1)
md2.user.name = 'Bob'

md1.user.name  # 'Alice' (unchanged)
md2.user.name  # 'Bob'
```

### In-Place Updates with `|=` Operator

Python 3.9+ dict merge operator is supported:

```python
md = MagicDict({'a': 1})
md |= {'b': 2, 'c': 3}
md  # MagicDict({'a': 1, 'b': 2, 'c': 3})
```

### Circular Reference Handling

`MagicDict` gracefully handles circular references:

```python
md = MagicDict({'name': 'root'})
md['self'] = md  # Circular reference

# Access works
md.self.name  # 'root'
md.self.self.name  # 'root'

# Safely converts back to dict
regular = md.disenchant()
```

### Auto-completion Support

`MagicDict` provides intelligent auto-completion in IPython, Jupyter notebooks and IDE's.

## Performance Considerations

### Tested:
- All standard and custom functionality
- Circular and self references through pickle/deepcopy/disenchant
- Concurrent access patterns (multi-threaded reads/writes)
- Protected MagicDict mutation attempts
- Deep nesting with recursion limits and stack overflow prevention
- Type preservation through operations



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

md.value  # MagicDict({})

# Use bracket access to get actual None
md['value']  # None
```
