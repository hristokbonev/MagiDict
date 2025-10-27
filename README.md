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
When you're out in public, do you constantly have the feeling that Keanu Reeves is judging you from behind the corner for your inability to elegantly access nested dictionary keys?<br>
And when you go to sleep at night, do you lie awake thinking about how much better your life would be if you took that course in JavaScript that your friend gave you a voucher for, before they moved to a different country and you lost contact with them, so you could finally use optional chaining and nullish coalescing operators to safely access nested properties without all the drama?

If you answered "yes" to any of these questions - don't worry! There's finally a solution that doesn't involve learning a whole new programming language or changing your religion to JavaScript! It's called ✨MagiDict✨ and it's here to make your dicts work like magic!

MagiDict is a powerful Python dictionary subclass that provides simple, safe and convenient attribute-style access to nested data structures, with recursive conversion and graceful failure handling. Designed to ease working with complex, deeply nested dictionaries, it reduces errors and improves code readability. Optimized and memoized for better performance.

Stop chaining `get()`'s and brackets like it's 2003 and start living your best life, where `Dicts.Just.Work`!

## Installation

You can install MagiDict via pip:

```bash
pip install magidict
```

## Quick Start

```python
from magidict import MagiDict

# Create from dict
md = MagiDict({'user': {'name': 'Keanu', 'nickname': None}})

# Dot notation access
print(md.user.name)  # 'Keanu'

# Bracket access with dot notation
print(md['user.name'])  # 'Keanu'

# Safe chaining - no errors!
print(md.user.settings.theme)  # MagiDict({}) - not a KeyError!
print(md['user.settings.theme'])  # None - safe!

# Works with None values too
print(md.user.nickname.stage_name)  # MagiDict({}) - safe!
print(md['user.nickname.stage_name'])  # None - safe!
```

### Access Styles Map

```ascii
d = MagiDict({})

         ┌───────────────────┐
         │   Access Styles   │
         └─────────┬─────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌────────────────┐
│ Attribute Style │  │ Bracket Style  │
│        .        │  │       []       │
└───────┬─────────┘  └────────┬───────┘
        │              ┌──────┴──────┐
        ▼              ▼             ▼
  ┌──────────┐   ┌──────────┐   ┌─────────┐
  │   Safe   │   │   Safe   │   │ Strict  │
  └────┬─────┘   └─────┬────┘   └────┬────┘
       │               │             │
       ▼               ▼             ▼
   ┌───────┐   ┌──────────────┐ ┌──────────┐
   │ d.bar │   │ d["foo.bar"] │ │ d["foo"] │
   └───────┘   └──────────────┘ └──────────┘
       │               │             │
       ▼               ▼             ▼
   MagiDict({})       None        KeyError
```

## Documentation

Full documentation available in the GitHub [Wiki](https://github.com/hristokbonev/MagiDict/wiki)

## Key Features

### 1. Attribute-Style Access

Access dictionary keys using dot notation instead of bracket notation. Missing keys and keys with `None` values return an empty `MagiDict`:

```python
md = MagiDict({'user': {'name': 'Keanu', 'nickname': None}})

# Existing key:
print(md.user.name) # 'Keanu'
# None value key:
print(md.user.nickname) # MagiDict({})
# Missing key:
print(md.user.email) # MagiDict({})
# Chaining onto none value key:
print(md.user.nickname.stage_name)  # MagiDict({})
# Chaining onto missing key:
print(md.user.email.address)  # MagiDict({})
```

### 2. Dot Notation in Brackets

Access nested keys using dot notation within brackets. Supports list access via indices and invalid Python identifiers as keys.
Missing keys and keys with `None` values return `None`:

```python
md = MagiDict({
    'users': [
        {'name': 'Keanu'},
        {'name': 'Alice'}
    ],
    'settings': {'theme': None, "key-with-dash": "value" , 1: "One"}
})

# Existing key:
print(md['users.0.name']) # 'Keanu'
# Index out of range:
print(md['users.2.name']) # None - safe!
# Missing key:
print(md['users.0.email']) # None
# None value:
print(md['settings.theme']) # None
# Chaining onto none value:
print(md['settings.theme.color'])  # None
# Chaining onto missing key:
print(md['settings.language.code'])  # None
# Invalid identifier keys
print(md['settings.key-with-dash'])  # 'value'
print(md['settings.1'])  # 'One'

# Direct access still raises KeyError as expected
print(md['nonexistent'])  # KeyError
```

**Automatic Type Conversion**

When using dot notation in brackets, MagiDict intelligently converts key segments to their appropriate types. To prevent conversion and treat the segment as a string, enclose it in quotes, like you would with standard single key dictionary access.

```python
md = MagiDict({'items': {0: 'int zero', True: 'yes', 3.14: 'pi', '0': 'string zero'}})

print(md['items.0'])    # 'int zero'
print(md['items.True'])  # 'yes'
# Use comma for float access
print(md['items.3,14'])   # 'pi'

# Prevent conversion with quotes
print(md['items."0"'])   # 'string zero' (stays as string)
```

**Keys with Dots Parsing**

Quotes can also be used to parse keys that contain dots:

```python
md = MagiDict({"settings": {"config.version": "1.0","config": {"version": "2.0"}}})

print(md['settings."config.version"'])  # '1.0'
print(md['settings.config.version'])    # '2.0'
```

### 3. Recursive Conversion

Nested dictionaries are automatically converted to `MagiDict` instances:

### 4. Standard Dictionary Behavior Preserved

All standard `dict` methods and behaviors work as expected. For example missing keys with brackets raise `KeyError` as expected

### 5. Safe `mget()` Method

`mget` or `mg` is MagiDict's native `get` method. Unless a custom default is provided, it returns an empty `MagiDict` for missing keys or `None` values:

```python
md = MagiDict({'key': 'value', 'second_key': None})

# Existing key
print(md.mget('key'))  # 'value'

# Returns empty MagiDict for None values and missing keys
print(md.mget('second_key'))  # MagiDict({})
print(md.mget('missing'))      # MagiDict({})

# Custom default value
print(md.mget('missing', default='Not Found'))  # 'Not Found'
```

### 6. Convert Back to Standard Dict

Use `disenchant()` to convert back to a standard Python `dict`:

```python
md = MagiDict({'user': {'name': 'Keanu'}})
standard_dict = md.disenchant()
```

### 7. Convert empty MagiDict to None

Use `none()` to convert empty `MagiDict` instances that were created from `None` or missing keys back to `None`. Other values are returned unchanged:

```python
md = MagiDict({'user': None, 'age': 25})
print(none(md.user))      # None
print(none(md.user.name))  # None
print(none(md.age))       # 25
```

## API Reference

### Constructor

**`MagiDict(\*args, **kwargs)`** - Creates a new instance. Accepts same arguments as built-in `dict`.

### Core Methods

- **`mget(key, default=...)`** / **`mg(key, default=...)`** - Safe get that returns empty `MagiDict` for missing keys or `None` values (unless custom default provided)
- **`strict_get(key)`** / **`sg(key)`** / **`sget(key)`** - Strict get that raises `KeyError` for missing keys, returns `None` for `None` values
- **`disenchant()`** - Converts `MagiDict` and all nested instances back to standard `dict`. Handles circular references
- **`filter(function, drop_empty=False)`** - Returns new `MagiDict` with items where function returns `True`
- **`search_key(key)`** - Finds first occurrence of key in nested structures
- **`search_keys(key)`** - Returns list of all values for key in nested structures

All standard `dict` methods are fully supported (`get`, `update`, `copy`, `keys`, `values`, `items`, etc.)

### Utility Functions

- **`enchant(d)`** - Converts standard `dict` to `MagiDict`
- **`magi_loads(s, **kwargs)`** - Deserializes JSON string to `MagiDict`
- **`magi_load(fp, **kwargs)`** - Deserializes JSON file to `MagiDict`
- **`none(obj)`** - Converts empty `MagiDict` (from `None`/missing key) back to `None`

## Important Caveats

### 1. Key Conflicts with Dict Methods

Keys that conflict with standard `dict` methods must be accessed using brackets, `mget` or `get`:

```python
md = MagiDict({'keys': 'my_value', 'items': 'another_value'})

# These return dict methods, not your values
print(md.keys)   # <built-in method keys...>

# Use bracket access instead
print(md['keys'])   # 'my_value'
# Or use mget()
print(md.mget('keys'))  # 'my_value'
```

### 2. Invalid Python Identifiers and Non-String Keys

Keys that aren't valid Python identifiers must use bracket access or `mget()`:

```python
md = MagiDict({
    '1-key': 'value1',
    2: 'value2',
})

# Must use brackets or mget()
print(md['1-key'])  # 'value1'
print(md[2])        # 'value2'
print(md.mget('1-key'))  # 'value1'

# These won't work
print(md.1-key)  # SyntaxError
print(md.2)      # SyntaxError

```

### 3. Setting attributes

Setting or updating keys using dot notation is not supported. Use bracket notation instead like standard dicts. This is purposely restricted to avoid confusion and potential bugs.

## Advanced Features

`MagiDict` supports:

- Pickling and unpickling
- Deep copying
- In-place updates with `|=` operator (Python 3.9+)
- Circular reference handling
- Auto-completion support in IPython, Jupyter and IDE's

## Performance

`Magidict`'s initialization and recursive conversion are very fast due to the core hooks being implemented in C.
`Magidict` is extensively tested with 800+ test cases and 98% code coverage.

[Benchmarks](https://hristokbonev.github.io/magidict/)

## Comparison with Alternatives

### vs. Regular Dict

```python
d = {'user': {'profile': {'name': 'Keanu'}}}
md = MagiDict(d)

# Regular dict
name = d.get('user', {}).get('profile', {}).get('name', 'Unknown')
# MagiDict
name = md.user.profile.name or 'Unknown'
```

### vs. DotDict, Bunch, AttrDict and Similar Libraries

MagiDict provides additional features:

- Safe chaining with missing keys (returns empty `MagiDict`)
- Safe chaining with None values
- Dot notation in bracket access
- Built-in `mget()` and `strict_get()` methods
- Search and filter methods
- Protected empty instances
- Circular reference handling
- Memoization
- Type preservation for all non-dict values
- In-place mutation

## Troubleshooting

If you encounter any issues or have questions, please check the Troubleshooting section in the [Wiki](https://github.com/hristokbonev/MagiDict/wiki/Troubleshooting) or [GitHub Issues](https://github.com/hristokbonev/MagiDict/issues)

---

## Contributing

Contributions are welcome and appreciated! Please see the [CONTRIBUTING.md](https://github.com/hristokbonev/MagiDict/blob/main/CONTRIBUTING.md) for more information.

## License

MagiDict is licensed under the [MIT License](https://github.com/hristokbonev/MagiDict/blob/main/LICENSE).

## Links

For documentation and source code, visit the project on GitHub: <br>
Documentation: [GitHub Wiki](https://github.com/hristokbonev/MagiDict/wiki)<br>
PyPI: [magidict](https://pypi.org/project/magidict/)<br>
Source Code: [MagiDict](https://github.com/hristokbonev/MagiDict)<br>
Issue Tracker: [GitHub Issues](https://github.com/hristokbonev/MagiDict/issues)<br>
Benchmarks: [Performance Results](https://hristokbonev.github.io/magidict/)
