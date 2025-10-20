#!/usr/bin/env python3
"""Verify MagiDict implementation and test all features."""

import sys
from typing import Any


def test_basic_import():
    """Test 1: Basic import and implementation check."""
    print("\n" + "=" * 70)
    print("TEST 1: Basic Import and Implementation")
    print("=" * 70)

    try:
        import magidict
        from magidict import MagiDict, magi_loads, enchant, none

        print("✓ Import successful")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

    # Check implementation
    print(f"\nImplementation: {magidict.__implementation__}")
    print(f"Version: {magidict.__version__}")

    # Get detailed info
    info = magidict.get_implementation_info()
    print(f"\nDetailed Info:")
    for key, value in info.items():
        print(f"  {key}: {value}")

    return True


def test_module_sources():
    """Test 2: Verify where functions come from."""
    print("\n" + "=" * 70)
    print("TEST 2: Module Sources")
    print("=" * 70)

    from magidict import MagiDict, magi_loads, magi_load, enchant, none

    components = {
        "MagiDict": MagiDict,
        "magi_loads": magi_loads,
        "magi_load": magi_load,
        "enchant": enchant,
        "none": none,
    }

    for name, obj in components.items():
        module = getattr(obj, "__module__", "unknown")
        print(f"{name:15} -> {module}")

    # Check if all from same source
    modules = {getattr(obj, "__module__", None) for obj in components.values()}

    if "_magidict" in str(modules):
        print("\n✓ Using C extension for utility functions")
        return True
    elif "core" in str(modules):
        print("\n✓ Using Python implementation for utility functions")
        return True
    else:
        print(f"\n⚠ Mixed sources: {modules}")
        return True


def test_basic_functionality():
    """Test 3: Basic MagiDict functionality."""
    print("\n" + "=" * 70)
    print("TEST 3: Basic Functionality")
    print("=" * 70)

    from magidict import MagiDict

    # Test creation
    md = MagiDict({"user": {"name": "John", "age": 30}})
    print(f"✓ Created: {md}")

    # Test attribute access
    assert md.user.name == "John", "Attribute access failed"
    print(f"✓ Attribute access: md.user.name = {md.user.name}")

    # Test safe chaining
    missing = md.user.missing.deeply.nested
    assert hasattr(missing, "_from_missing"), "Safe chaining failed"
    print(f"✓ Safe chaining: md.user.missing.deeply.nested = {missing}")

    # Test None value
    md.user.phone = None
    phone = md.user.phone
    assert hasattr(phone, "_from_none"), "None handling failed"
    print(f"✓ None handling: md.user.phone (None) = {phone}")

    return True


def test_methods():
    """Test 4: Test all methods."""
    print("\n" + "=" * 70)
    print("TEST 4: Method Tests")
    print("=" * 70)

    from magidict import MagiDict

    md = MagiDict({"a": 1, "b": 2, "c": {"d": 3}})

    tests = {
        "mget": lambda: md.mget("a"),
        "mg": lambda: md.mg("missing", "default"),
        "strict_get": lambda: md.strict_get("a"),
        "sget": lambda: md.sget("b"),
        "sg": lambda: md.sg("c"),
        "disenchant": lambda: md.disenchant(),
        "copy": lambda: md.copy(),
        "search_key": lambda: md.search_key("d"),
        "search_keys": lambda: md.search_keys("a"),
    }

    results = {}
    for name, test_func in tests.items():
        try:
            result = test_func()
            results[name] = "✓"
            print(f"✓ {name:15} works")
        except Exception as e:
            results[name] = f"✗ {e}"
            print(f"✗ {name:15} failed: {e}")

    return all(v == "✓" for v in results.values())


def test_utility_functions():
    """Test 5: Test utility functions."""
    print("\n" + "=" * 70)
    print("TEST 5: Utility Functions")
    print("=" * 70)

    from magidict import MagiDict, enchant, none, magi_loads

    # Test enchant
    regular_dict = {"a": {"b": 1}}
    md = enchant(regular_dict)
    assert isinstance(md, MagiDict), "enchant failed"
    print(f"✓ enchant: {type(md).__name__}")

    # Test none
    empty = md.missing.key
    result = none(empty)
    assert result is None, "none failed"
    print(f"✓ none: empty MagiDict -> None")

    # Test magi_loads
    json_str = '{"x": {"y": 42}}'
    md_json = magi_loads(json_str)
    assert md_json.x.y == 42, "magi_loads failed"
    print(f"✓ magi_loads: JSON -> MagiDict")

    return True


def test_filter_fallback():
    """Test 6: Test filter() method with fallback."""
    print("\n" + "=" * 70)
    print("TEST 6: Filter Method (Python Fallback)")
    print("=" * 70)

    import magidict
    from magidict import MagiDict

    md = MagiDict({"a": 1, "b": None, "c": 3, "d": None})

    try:
        # This should work via Python fallback if C extension is loaded
        filtered = md.filter(lambda v: v is not None)

        print(f"✓ filter() works")
        print(f"  Original: {dict(md)}")
        print(f"  Filtered: {dict(filtered)}")

        assert "a" in filtered, "filter failed"
        assert "c" in filtered, "filter failed"
        assert "b" not in filtered, "filter failed"
        assert "d" not in filtered, "filter failed"

        # Check if result is still C MagiDict
        if magidict._using_c_extension:
            print(f"  Result type: {type(filtered).__module__}")
            if "_magidict" in type(filtered).__module__:
                print(f"  ✓ Result is C MagiDict (fallback worked correctly)")
            else:
                print(f"  ⚠ Result is Python MagiDict")

        return True

    except NotImplementedError as e:
        print(f"✗ filter() not implemented: {e}")
        return False
    except Exception as e:
        print(f"✗ filter() failed: {e}")
        return False


def test_pickle():
    """Test 7: Test pickle support."""
    print("\n" + "=" * 70)
    print("TEST 7: Pickle Support")
    print("=" * 70)

    import pickle
    from magidict import MagiDict

    md = MagiDict({"a": {"b": 1}})

    try:
        # Pickle and unpickle
        pickled = pickle.dumps(md)
        restored = pickle.loads(pickled)

        assert restored.a.b == 1, "Pickle failed"
        print(f"✓ Pickle works")
        print(f"  Original: {md}")
        print(f"  Restored: {restored}")

        return True
    except Exception as e:
        print(f"✗ Pickle failed: {e}")
        return False


def test_deepcopy():
    """Test 8: Test deepcopy with circular references."""
    print("\n" + "=" * 70)
    print("TEST 8: Deep Copy (Circular References)")
    print("=" * 70)

    from copy import deepcopy
    from magidict import MagiDict

    md = MagiDict({"a": 1})
    md["self"] = md  # Circular reference

    try:
        copied = deepcopy(md)

        assert copied is not md, "deepcopy didn't create new object"
        assert copied is copied["self"], "deepcopy didn't preserve circular ref"
        print(f"✓ Deep copy with circular references works")

        return True
    except Exception as e:
        print(f"✗ Deep copy failed: {e}")
        return False


def test_performance():
    """Test 9: Quick performance comparison."""
    print("\n" + "=" * 70)
    print("TEST 9: Performance Check")
    print("=" * 70)

    import timeit
    from magidict import MagiDict
    import magidict

    if not magidict._using_c_extension:
        print("⚠ Skipping (not using C extension)")
        return True

    # Create test data
    data = {f"k{i}": {f"v{j}": j for j in range(10)} for i in range(50)}

    # Test initialization
    time = timeit.timeit(lambda: MagiDict(data), number=1000)
    print(f"Initialization (1000x): {time:.4f}s")

    # Test attribute access
    md = MagiDict(data)
    time = timeit.timeit(lambda: md.k25.v5, number=100000)
    print(f"Attribute access (100000x): {time:.4f}s")

    if time < 0.5:
        print("✓ Performance looks good (C extension speed)")
    else:
        print("⚠ Performance seems slow (might be Python fallback)")

    return True


def main():
    """Run all tests."""
    print("=" * 70)
    print("MagiDict Implementation Verification")
    print("=" * 70)

    tests = [
        test_basic_import,
        test_module_sources,
        test_basic_functionality,
        test_methods,
        test_utility_functions,
        test_filter_fallback,
        test_pickle,
        test_deepcopy,
        test_performance,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n✗ Test failed with exception: {e}")
            import traceback

            traceback.print_exc()
            results.append(False)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if all(results):
        print("\n✓ ALL TESTS PASSED")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
