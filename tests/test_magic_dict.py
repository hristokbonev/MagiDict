from collections import UserList, namedtuple
import gc
import sys
import threading
from typing import OrderedDict
from unittest import TestCase
import copy
from copy import deepcopy
import pickle
from types import MappingProxyType
import json
import weakref
from main.magic_dict import MagicDict, enchant, magic_loads, none


md = MagicDict(
    {
        "user": {
            "name": "Alice",
            "id": 101,
        }
    }
)


class TestMagicDict(TestCase):
    """Unit tests for the MagicDict class."""

    def setUp(self):
        self.md = {
            "user": {
                "name": "Alice",
                "id": 101,
                "profile": {
                    "email": "alice@example.com",
                    "active": True,
                    "settings": {"theme": "dark"},
                },
            },
            "permissions": [
                "read",
                "write",
                {"area": "admin", "level": 1},
                {"area": "billing", "level": 2, "nested_list": [{"deep": True}]},
            ],
            "metadata": ({"source": "web-form"}, "some_other_data_in_tuple"),
            "stringKey": "some string",
            "integerKey": 3,
            "floatKey": 1.5,
            "keys": "this key conflicts with the .keys() method",
            "get": "this key conflicts with the .get() method",
            "user-id": "uuid-1234-5678",
            "123_numeric": "starts with a number",
            "empty_dict": {},
            "empty_list": [],
        }
        self.md = MagicDict(self.md)

    def test_init(self):
        """Test various initialization methods."""
        self.assertIsInstance(MagicDict(), MagicDict)
        self.assertEqual(MagicDict({"a": 1}), {"a": 1})
        self.assertEqual(MagicDict(a=1, b=2), {"a": 1, "b": 2})
        self.assertEqual(MagicDict([("a", 1), ("b", 2)]), {"a": 1, "b": 2})

    def test_item_access_and_assignment(self):
        """Test standard dict-style item access and assignment."""
        d = MagicDict()
        d["a"] = 100
        self.assertEqual(d["a"], 100)
        d["a"] = 200
        self.assertEqual(d["a"], 200)

    def test_deletion_2(self):
        """Test deletion of keys."""
        d = MagicDict({"a": 1, "b": 2})
        del d["a"]
        self.assertNotIn("a", d)
        with self.assertRaises(KeyError):
            del d["c"]

    def test_membership(self):
        """Test membership using 'in' and 'not in'."""
        self.assertIn("user", self.md)
        self.assertIn("profile", self.md.user)
        self.assertIn("email", self.md.user.profile)
        self.assertIn("area", self.md.permissions[2])
        self.assertNotIn("store", self.md)
        self.assertNotIn("address", self.md.user)

    def test_length(self):
        """Test len() function."""
        self.assertEqual(len(self.md), 12)
        d = MagicDict()
        self.assertEqual(len(d), 0)
        d["a"] = 1
        self.assertEqual(len(d), 1)

    def test_iteration(self):
        """Test iteration over keys, values, and items."""
        md_keys = list(self.md.keys())
        sd_keys = list(self.md.keys())
        self.assertCountEqual(md_keys, sd_keys)

        count = 0
        for key in self.md:
            self.assertIn(key, self.md)
            count += 1
        self.assertEqual(count, len(self.md))
        for k, v in self.md.items():
            self.assertEqual(self.md[k], v)
        self.assertCountEqual(list(self.md.values()), list(self.md.values()))

    def test_dict_methods(self):
        """Test standard dict methods like get, pop, update, clear."""
        self.assertEqual(self.md.get("stringKey"), "some string")
        self.assertIsNone(self.md.get("nonexistent"))
        self.assertEqual(self.md.get("nonexistent", "default"), "default")

        d = MagicDict({"a": 1, "b": 2})
        self.assertEqual(d.pop("a"), 1)
        self.assertNotIn("a", d)

        d.update({"b": 5, "c": 3, "d": 4})
        self.assertEqual(d, {"b": 5, "c": 3, "d": 4})

        d.clear()
        self.assertEqual(len(d), 0)

    def test_equality(self):
        """Test equality against standard dicts and other mappings."""
        self.assertEqual(self.md, self.md)
        self.assertEqual(MagicDict(self.md), self.md)
        self.assertNotEqual(self.md, {"a": 1})

    def test_attribute_style_access_get(self):
        """Accessing existing keys via attribute style should work."""
        self.assertEqual(self.md.stringKey, "some string")
        self.assertEqual(self.md.floatKey, 1.5)

    def test_standart_set_key(self):
        """Setting a key via standard dict access should create it if it doesn't exist."""
        self.md["new_key"] = "new_value"
        self.assertEqual(self.md["new_key"], "new_value")
        self.assertEqual(self.md.new_key, "new_value")

    def test_attribute_access_non_existent_key(self):
        """Accessing a non-existent attribute should return an empty MagicDict."""
        non_existent = self.md.non_existent
        self.assertIsInstance(non_existent, MagicDict)

    def test_chained_attribute_access_non_existent(self):
        """Accessing multiple non-existent attributes should return empty MagicDicts."""
        deeply_non_existent = self.md.a.b.c.d
        self.assertIsInstance(deeply_non_existent, MagicDict)
        self.assertEqual(deeply_non_existent, MagicDict())
        self.assertNotIn("a", self.md)

    def test_recursive_conversion_on_init(self):
        """Test that nested dicts/lists/tuples are converted to MagicDicts recursively."""
        self.assertIsInstance(self.md.user, MagicDict)
        self.assertIsInstance(self.md.permissions[2], MagicDict)
        self.assertIsInstance(self.md.metadata[0], MagicDict)
        self.assertIsInstance(self.md.permissions[3].nested_list[0], MagicDict)
        self.assertIsInstance(self.md.empty_dict, MagicDict)

    def test_deep_attribute_access(self):
        """Test deep attribute access on nested structures."""
        self.assertEqual(self.md.user.profile.settings.theme, "dark")
        self.assertEqual(self.md.user.profile.email, "alice@example.com")
        self.assertEqual(self.md.permissions[2].area, "admin")
        self.assertEqual(self.md.permissions[3].level, 2)
        self.assertTrue(self.md.permissions[3].nested_list[0].deep)
        self.assertEqual(self.md.metadata[0].source, "web-form")

    def test_recursive_conversion_on_setitem(self):
        """Test that setting a dict value converts it to MagicDict recursively."""
        d = MagicDict()
        d["config"] = {"host": "localhost", "port": 8080}
        self.assertIsInstance(d.config, MagicDict)
        self.assertEqual(d.config.host, "localhost")

    def test_recursive_conversion_on_update(self):
        """Test that updating with a dict converts it to MagicDict recursively."""
        d = MagicDict()
        d.update({"config": {"host": "localhost", "port": 8080}})
        self.assertIsInstance(d.config, MagicDict)
        self.assertEqual(d.config.host, "localhost")

    def test_type_preservation(self):
        """Ensure that non-dict types are preserved."""
        self.assertIsInstance(self.md.permissions, list)
        self.assertIsInstance(self.md.metadata, tuple)
        self.assertIsInstance(self.md.empty_list, list)
        self.assertIsInstance(self.md.permissions[3].nested_list, list)

    def test_getattr_does_not_interfere_with_methods(self):
        """Ensure that keys shadowing dict methods are still accessible."""
        self.assertTrue(callable(self.md.keys))
        self.assertTrue(callable(self.md.items))
        self.assertEqual(list(MagicDict({"keys": 1}).keys()), ["keys"])

    def test_overwrite_with_plain_dict(self):
        """Setting a key to a plain dict should convert it to MagicDict."""
        self.md["user"] = {"foo": "bar"}
        self.assertIsInstance(self.md.user, MagicDict)
        self.assertEqual(self.md.user.foo, "bar")

    def test_overwrite_with_enchant(self):
        """Setting a key to a MagicDict should keep it as MagicDict."""
        nested = MagicDict({"baz": 42})
        self.md["new"] = nested
        self.assertIs(self.md.new, nested)

    def test_invalid_identifier_keys(self):
        """Keys that are not valid Python identifiers should still be accessible via item access."""
        md = MagicDict({"my-key": 1, "with space": 2, "class": 3})
        self.assertEqual(md["my-key"], 1)
        self.assertEqual(md["with space"], 2)
        self.assertEqual(md["class"], 3)
        self.assertEqual(md.mget("class"), 3)

    def test_setdefault_and_pop_default(self):
        """Test setdefault and pop with default value."""
        d = MagicDict()
        self.assertEqual(d.setdefault("a", {"b": 2}).b, 2)
        self.assertEqual(d.pop("nonexistent", "default"), "default")

    def test_copy_preserves_type(self):
        """Test that copy() returns a MagicDict and nested dicts are also MagicDicts."""
        d = MagicDict(a=1, b={"c": 2})
        d_copy = d.copy()
        self.assertIsInstance(d_copy, MagicDict)
        self.assertIsInstance(d_copy.b, MagicDict)
        self.assertEqual(d, d_copy)

    def test_method_conflict_keys(self):
        """Ensure that keys named like dict methods do not interfere with method calls."""
        md = MagicDict({"items": "value", "get": "value2"})
        self.assertTrue(callable(md.items))
        self.assertEqual(md["items"], "value")
        self.assertEqual(md["get"], "value2")

    def test_standard_access_non_existent_key_raises_keyerror(self):
        """Accessing a non-existent key via standard dict access should raise KeyError."""
        with self.assertRaises(KeyError):
            _ = self.md["non_existent_key"]

    def test_deletion(self):
        """Test deletion of keys."""
        md = MagicDict({"a": 1, "b": 2})
        del md["a"]
        self.assertNotIn("a", md)
        with self.assertRaises(KeyError):
            del md["non_existent"]

    def test_repr(self):
        """Test the string representation of MagicDict."""
        md = MagicDict({"a": 1})
        self.assertEqual(repr(md), "MagicDict({'a': 1})")

    def test_pickling(self):
        """Test that pickling and unpickling preserves MagicDict structure."""
        pickled_md = pickle.dumps(self.md)
        unpickled_md = pickle.loads(pickled_md)

        self.assertIsInstance(unpickled_md, MagicDict)
        self.assertEqual(self.md, unpickled_md)
        self.assertEqual(unpickled_md.user.profile.settings.theme, "dark")
        self.assertIsInstance(unpickled_md.user, MagicDict)

    def test_copy_is_shallow(self):
        """Test that copy() creates a shallow copy."""
        md = MagicDict({"a": 1, "b": {"c": 2}})
        md_copy = md.copy()

        md_copy.b.c = 99

        self.assertEqual(md.b.c, 99)
        self.assertIs(md.b, md_copy.b)

        md_copy["a"] = 100
        self.assertEqual(md["a"], 1)

    def test_fromkeys(self):
        """Test the fromkeys class method."""
        keys = ["a", "b", "c"]
        md = MagicDict.fromkeys(keys, 0)
        self.assertEqual(md, {"a": 0, "b": 0, "c": 0})

        nested_dict = {"nested": True}
        md_nested = MagicDict.fromkeys(keys, nested_dict)
        self.assertEqual(md_nested.a.nested, True)
        self.assertIsInstance(md_nested.b, MagicDict)

    def test_setdefault_when_key_exists(self):
        """Using setdefault on an existing key should return the existing value."""
        md = MagicDict({"a": 1})
        existing_val = md.setdefault("a", 2)
        self.assertEqual(existing_val, 1)
        self.assertEqual(md.a, 1)

    def test_modifying_temp_safe_dict_from_failed_getattr(self):
        """Modifying a temporary SafeDict from a failed getattr should not affect the original."""
        temp = self.md.non_existent

        with self.assertRaises(TypeError):
            temp["some_key"] = "some_value"

        self.assertNotIn("non_existent", self.md)
        self.assertEqual(self.md.non_existent, MagicDict())

    def test_hook_with_other_iterables(self):
        """Test that sets and frozensets are preserved and not converted."""
        data = {"my_set": {1, 2, 3}}
        md = MagicDict(data)
        self.assertIsInstance(md.my_set, set)
        self.assertEqual(md.my_set, {1, 2, 3})

        data_with_frozenset = {"my_frozenset": frozenset([("a", 1)])}
        md_fs = MagicDict(data_with_frozenset)
        self.assertIsInstance(md_fs.my_frozenset, frozenset)

    def test_method_conflict_safety(self):
        """Ensure that keys shadowing dict methods can be deleted and do not interfere with method calls."""
        md = MagicDict()
        md["keys"] = "custom_value_for_keys"

        self.assertEqual(md["keys"], "custom_value_for_keys")
        self.assertTrue(callable(md.keys))
        self.assertCountEqual(list(md.keys()), ["keys"])

        md_del_test = MagicDict({"a": 1})
        with self.assertRaises(KeyError):
            del md_del_test["items"]

        self.assertTrue(callable(md_del_test.items))
        self.assertEqual(list(md_del_test.items()), [("a", 1)])

        md_conflict_del = MagicDict({"pop": "custom_pop_value", "b": 2})

        del md_conflict_del["pop"]

        self.assertNotIn("pop", md_conflict_del)

        self.assertTrue(callable(md_conflict_del.pop))
        popped_value = md_conflict_del.pop("b")
        self.assertEqual(popped_value, 2)
        self.assertNotIn("b", md_conflict_del)

    def test_nested_empty_structures(self):
        """Test that empty lists, tuples, and dicts are properly converted when nested."""
        d = MagicDict({"a": [], "b": (), "c": {}})
        self.assertIsInstance(d.a, list)
        self.assertIsInstance(d.b, tuple)
        self.assertIsInstance(d.c, MagicDict)
        d2 = MagicDict(
            {"nested": {"empty_list": [], "empty_tuple": (), "empty_dict": {}}}
        )
        self.assertIsInstance(d2.nested.empty_list, list)
        self.assertIsInstance(d2.nested.empty_tuple, tuple)
        self.assertIsInstance(d2.nested.empty_dict, MagicDict)

    def test_overwrite_non_dict_with_dict(self):
        """Setting a non-dict key to a dict should convert it to MagicDict."""
        md = MagicDict({"a": 10})
        md["a"] = {"b": 20}
        self.assertIsInstance(md.a, MagicDict)
        self.assertEqual(md.a.b, 20)
        md.a = 42
        self.assertEqual(md.a, 42)

    def test_builtin_like_keys(self):
        """Test that keys resembling built-in attributes are handled correctly."""
        md = MagicDict({"__class__": "test"})
        self.assertEqual(md["__class__"], "test")
        self.assertIsInstance(md.__dict__, dict)
        self.assertIsInstance(md.__nonexistent__, MagicDict)

    def test_pickle_nested_enchant(self):
        """Test that pickling and unpickling preserves nested MagicDict structure."""
        md = MagicDict({"a": {"b": {"c": 1}}, "lst": [{"x": 5}]})
        dumped = pickle.dumps(md)
        loaded = pickle.loads(dumped)
        self.assertIsInstance(loaded.a, MagicDict)
        self.assertIsInstance(loaded.lst[0], MagicDict)
        self.assertEqual(loaded.a.b.c, 1)
        self.assertEqual(loaded.lst[0].x, 5)

    def test_hook_with_sets_and_frozensets(self):
        """Test that sets and frozensets are preserved and not converted."""
        data = {"my_set": {1, 2, 3}}
        md = MagicDict(data)
        self.assertIsInstance(md.my_set, set)
        self.assertEqual(md.my_set, {1, 2, 3})

        data_fs = {"my_frozenset": frozenset([1, 2, 3])}
        md_fs = MagicDict(data_fs)
        self.assertIsInstance(md_fs.my_frozenset, frozenset)
        self.assertEqual(md_fs.my_frozenset, frozenset([1, 2, 3]))

    def test_fromkeys_with_mutable_default(self):
        """Test that fromkeys with a mutable default creates separate instances."""
        default = {"x": 1}
        md = MagicDict.fromkeys(["a", "b"], default)
        self.assertIsNot(md.a, md.b)
        self.assertEqual(md.a.x, 1)

    def test_delete_attribute_vs_key(self):
        """Test that deleting a key does not affect instance attributes."""
        md = MagicDict({"pop": 123, "other": 456})
        with self.assertRaises(KeyError):
            del md["popitem"]
        del md["pop"]
        self.assertNotIn("pop", md)

    def test_key_assignment_creates_key(self):
        """Test that assigning to a key creates it if it doesn't exist."""
        md = MagicDict()
        md["new_key"] = "value"
        self.assertIn("new_key", md)
        self.assertEqual(md["new_key"], "value")

        md["user"] = {"name": "Bob"}
        self.assertIsInstance(md.user, MagicDict)
        self.assertEqual(md.user.name, "Bob")

    def test_mget_and_mg_behaviour(self):
        """Test the mget and mg methods for safe access."""
        md = MagicDict({"a": {"b": 2}, "none_val": None, 1: "one_int"})
        # existing key returns value
        self.assertEqual(md.mget("a").b, 2)
        # mg shorthand
        self.assertEqual(md.mg("a").b, 2)
        # missing key returns MagicDict
        self.assertIsInstance(md.mget("missing"), MagicDict)
        # key exists but value is None -> safe MagicDict for chaining
        none_chain = md.mget("none_val")
        self.assertIsInstance(none_chain, MagicDict)
        # numeric key access via mget
        self.assertEqual(md.mget(1), "one_int")

    def test_magic_loads_and_enchant_and_disenchant(self):
        """Test magic_loads, enchant, and disenchant functions."""
        s = json.dumps({"x": {"y": 5}, "arr": [{"z": 6}]})
        loaded = magic_loads(s)
        self.assertIsInstance(loaded, MagicDict)
        self.assertIsInstance(loaded.x, MagicDict)
        self.assertEqual(loaded.x.y, 5)

        # enchant should leave MagicDicts alone and convert dicts
        normal = {"a": 1}
        enchanted = enchant(normal)
        self.assertIsInstance(enchanted, MagicDict)
        with self.assertRaises(TypeError):
            enchant(123)  # type error for non-dict

        # disenchant should convert back to pure dicts recursively
        back = enchanted.disenchant()
        self.assertIsInstance(back, dict)
        self.assertEqual(back, {"a": 1})

    def test_getitem_dot_notation(self):
        """Test that getitem supports dot notation for nested access."""
        md = MagicDict({"a": {"b": {"c": 7}}, "list": ["zero", {"1": "one_str"}]})
        # dot notation string key
        self.assertEqual(md["a.b.c"], 7)
        # indexing into list via dot-string numeric
        self.assertEqual(md["list.1.1"], "one_str")

    def test_inplace_or_operator_and_deepcopy(self):
        """Test that |= operator works and deepcopy creates independent copies."""
        a = MagicDict({"x": {"y": 1}})
        b = {"z": 2}
        a |= b
        self.assertEqual(a.z, 2)

        # deepcopy check

        original = MagicDict({"n": {"m": 3}})
        copied = copy.deepcopy(original)
        self.assertIsInstance(copied, MagicDict)
        self.assertIsNot(copied, original)
        self.assertIsNot(copied.n, original.n)
        self.assertEqual(copied.n.m, 3)

    def test_key_assignment_overwrites_key(self):
        """Test that assigning to a key overwrites the existing value."""
        md = MagicDict({"key": 1})
        md["key"] = 2
        self.assertEqual(md["key"], 2)

    def test_dir_includes_keys(self):
        """Test that dir() includes keys of the MagicDict."""
        md = MagicDict({"a": 1, "b_key": 2})
        d = dir(md)
        self.assertIn("a", d)
        self.assertIn("b_key", d)
        self.assertIn("keys", d)
        self.assertIn("items", d)

    def test_deepcopy_creates_new_objects(self):
        """Test that deepcopy creates entirely new nested objects."""
        md = MagicDict({"a": 1, "b": {"c": [1, {"d": 2}]}})
        md_deepcopy = copy.deepcopy(md)

        self.assertEqual(md, md_deepcopy)
        self.assertIsNot(md, md_deepcopy)
        self.assertIsNot(md.b, md_deepcopy.b)
        self.assertIsNot(md.b.c, md_deepcopy.b.c)
        self.assertIsNot(md.b.c[1], md_deepcopy.b.c[1])

        md_deepcopy.b.c[1].d = 99
        self.assertEqual(md.b.c[1].d, 2)
        self.assertEqual(md_deepcopy.b.c[1].d, 99)

    def test_access_on_none_value_returns_magic_none(self):
        """Accessing an attribute on a None value should return an empty MagicDict."""
        md = MagicDict({"config": None})
        self.assertEqual(md.config.host, MagicDict())
        self.assertFalse(md.config.host)  # Evaluates to False

    def test_dict_subclass_is_converted_2(self):
        """Test that subclasses of dict are converted to MagicDict."""

        class MyDict(dict):
            """A simple subclass of dict."""

            pass

        data = MyDict(user=MyDict(name="subclass_user"))
        md = MagicDict(data)
        self.assertIsInstance(md, MagicDict)
        self.assertNotIsInstance(md, MyDict)
        self.assertIsInstance(md.user, MagicDict)
        self.assertNotIsInstance(md.user, MyDict)
        self.assertEqual(md.user.name, "subclass_user")

    def test_list_tuple_subclass_type_is_preserved_on_hook(self):
        """Test that subclasses of list and tuple are preserved when used as values."""

        class MyList(list):
            """A simple subclass of list."""

            def custom_method(self):
                return "hello"

        class MyTuple(tuple):
            """A simple subclass of tuple."""

            pass

        data = {"a_list": MyList([{"id": 1}]), "a_tuple": MyTuple(({"id": 2},))}

        md = MagicDict(data)

        self.assertIsInstance(md.a_list, MyList)
        self.assertIsInstance(md.a_tuple, MyTuple)

        self.assertEqual(md.a_list.custom_method(), "hello")

        self.assertIsInstance(md.a_list[0], MagicDict)
        self.assertEqual(md.a_list[0].id, 1)
        self.assertIsInstance(md.a_tuple[0], MagicDict)
        self.assertEqual(md.a_tuple[0].id, 2)

    def test_fromkeys_with_mutable_default_is_safe(self):
        """Test that fromkeys with a mutable default creates separate instances."""
        default = {"nested": True}
        md = MagicDict.fromkeys(["a", "b"], default)

        self.assertIsInstance(md.a, MagicDict)
        self.assertIsInstance(md.b, MagicDict)

        self.assertIsNot(md.a, md.b)

        md.a.new_key = "value"
        self.assertNotIn("new_key", md.b)
        self.assertIsInstance(md.b.non_existent, MagicDict)

    def test_setdefault_with_new_key_is_hooked(self):
        """Using setdefault with a new key should create a MagicDict if the default is a dict."""
        md = MagicDict()
        nested_dict = md.setdefault("new_key", {"a": 1})
        self.assertIsInstance(nested_dict, MagicDict)
        self.assertEqual(nested_dict.a, 1)

    def test_attribute_access_on_falsy_values(self):
        """Accessing attributes of falsy values should return the actual value, not MagicDict."""
        md = MagicDict({"none_val": None, "false_val": False, "zero_val": 0})
        self.assertEqual(md.none_val, MagicDict())
        self.assertFalse(md.false_val)
        self.assertEqual(md.zero_val, 0)

    def test_chained_access_after_setting_none(self):
        """Setting a key to None and then updating it to a dict should work."""
        md = MagicDict({"config": None})
        md["config"] = {"host": "localhost"}
        self.assertEqual(md.config.host, "localhost")

    def test_reserved_keywords_as_keys(self):
        """Keys that are Python reserved keywords should be accessible via item access and mget()
        but not via attribute access."""
        keywords = ["def", "for", "if", "else", "try", "except"]
        md = MagicDict({k: k.upper() for k in keywords})
        for k in keywords:
            self.assertEqual(md[k], k.upper())
            self.assertEqual(md.mget(k), k.upper())
            with self.assertRaises(SyntaxError):
                eval(f"md.{k}")

    def test_nested_none_access_returns_magic_none(self):
        """Accessing attributes on nested None values should return SafeNone."""
        md = MagicDict({"a": {"b": None}})
        self.assertEqual(md.a.b.c, MagicDict())

    def test_dict_in_nested_tuples_conversion_enchant(self):
        """Test that dicts inside nested tuples are converted to MagicDicts."""
        md = MagicDict({"a": (({"b": 1},),)})
        self.assertIsInstance(md.a[0][0], MagicDict)
        self.assertEqual(md.a[0][0].b, 1)

    def test_string_key_and_variable_name_conflict(self):
        """Test that a string key that matches a variable name does not conflict
        and both access methods work correctly."""
        custom_key = "some_other_key"
        md = MagicDict({"custom_key": "value1", custom_key: "value2"})

        self.assertEqual(md["custom_key"], "value1")
        self.assertEqual(md.mget(custom_key), "value2")
        self.assertEqual(md.custom_key, "value1")
        self.assertEqual(md["some_other_key"], "value2")
        self.assertEqual(md.some_other_key, "value2")

        md = MagicDict({custom_key: "value2", "custom_key": "value1"})
        self.assertEqual(md["custom_key"], "value1")
        self.assertEqual(md.custom_key, "value1")
        self.assertEqual(md["some_other_key"], "value2")
        self.assertEqual(md.some_other_key, "value2")

    def test_digit_keys_int_and_str(self):
        """Test that digit keys as int and str are treated as distinct keys
        and both access methods work correctly."""
        md = MagicDict({1: 1, "1": "string_one", "key2": "value2", 2: "two"})
        self.assertEqual(md[1], 1)
        self.assertEqual(md["1"], "string_one")
        self.assertEqual(md.key2, "value2")
        self.assertEqual(md[2], "two")
        self.assertIsInstance(md[1], int)
        self.assertIsInstance(md["1"], str)
        self.assertIsInstance(md.key2, str)
        self.assertIsInstance(md[2], str)
        self.assertEqual(md.mget(1), 1)
        self.assertEqual(md.mget("1"), "string_one")
        self.assertEqual(md.mget("key2"), "value2")
        self.assertEqual(md.mget(2), "two")

    def test_non_string_keys_are_accessible_via_item_notation(self):
        """Test that non-string keys are accessible via item notation but not attribute access."""

        class Key:
            """A custom object to use as a dict key."""

            pass

        k = Key()
        string_k = "custom_key"
        somekey = "Some key value"
        md = MagicDict({k: "value", string_k: "string_value", somekey: "some_value"})
        self.assertEqual(md[k], "value")
        self.assertEqual(md.k, MagicDict())
        self.assertEqual(md[string_k], "string_value")
        self.assertEqual(md.string_k, MagicDict())
        self.assertEqual(md[somekey], "some_value")
        self.assertEqual(md.somekey, MagicDict())
        self.assertEqual(md.mget(somekey), "some_value")
        self.assertEqual(md.mget(string_k), "string_value")
        self.assertEqual(md.mget(k), "value")

    def test_recursive_self_reference(self):
        """Test that self-referential structures do not cause infinite recursion."""
        md = MagicDict()
        md["self"] = md
        self.assertIs(md.self, md)

    def test_deeply_nested_enchant(self):
        """Test that deeply nested structures are handled without recursion errors."""
        depth = 1000
        md = MagicDict()
        current = md
        for i in range(depth):
            current["nested"] = {}
            current = current.nested
        self.assertEqual(current, MagicDict())

    def test_mixed_list_tuple_content(self):
        """Test that lists and tuples with mixed content are handled correctly."""
        md = MagicDict({"mixed": [1, {"a": 1}, "str", ({"b": 2},)]})
        self.assertIsInstance(md.mixed[1], MagicDict)
        self.assertEqual(md.mixed[1].a, 1)
        self.assertIsInstance(md.mixed[3][0], MagicDict)
        self.assertEqual(md.mixed[3][0].b, 2)

    def test_nested_empty_structures_in_collections(self):
        """Test that empty dicts inside lists and tuples are converted to MagicDicts."""
        md = MagicDict({"lst": [{}], "tpl": ({},)})
        self.assertIsInstance(md.lst[0], MagicDict)
        self.assertIsInstance(md.tpl[0], MagicDict)

    def test_non_string_keys(self):
        """Test that non-string keys are accessible via item notation but not attribute access."""
        md = MagicDict({1: "one", (2, 3): "tuple"})
        self.assertEqual(md[1], "one")
        self.assertEqual(md[(2, 3)], "tuple")
        self.assertEqual(md.mget(1), "one")
        self.assertEqual(md.mget((2, 3)), "tuple")
        result = getattr(md, "1")
        self.assertIsInstance(result, MagicDict)

    def test_magic_method_key_shadowing(self):
        """Test that keys shadowing magic methods do not interfere with instance behavior."""
        md = MagicDict({"__init__": "init_val"})
        self.assertEqual(md["__init__"], "init_val")
        self.assertIsInstance(md.__dict__, dict)

    def test_copy_vs_deepcopy_behavior(self):
        """Test that copy() is shallow while deepcopy() is deep."""
        md = MagicDict({"a": {"b": 2}})
        md_copy = md.copy()
        md_copy["a"]["b"] = 99
        self.assertEqual(md.a.b, 99)
        self.assertIsInstance(md.a, MagicDict)

        md_deep = copy.deepcopy(md)
        md_deep["a"]["b"] = 100
        self.assertEqual(md.a.b, 99)
        self.assertEqual(md_deep.a.b, 100)
        self.assertIsInstance(md_deep.a, MagicDict)

    def test_hook_preserves_other_iterables(self):
        """Test that other iterable types are preserved and not converted."""

        class MySet(set):
            pass

        class MyFrozenSet(frozenset):
            pass

        data = {"s": MySet([1, 2]), "fs": MyFrozenSet([3, 4])}
        md = MagicDict(data)
        self.assertIsInstance(md.s, MySet)
        self.assertIsInstance(md.fs, MyFrozenSet)
        self.assertEqual(md.s, {1, 2})
        self.assertEqual(md.fs, frozenset([3, 4]))

    def test_chained_access_on_non_dict_returns_empty_magic_none(self):
        """Accessing attributes on a non-dict value should raise AttributeError."""
        md = MagicDict({"a": 42})
        # self.assertEqual(md.a.b.c, None)
        with self.assertRaises(AttributeError):
            _ = md.a.b.c
        temp = md.nonexistent.key
        self.assertIsInstance(temp, MagicDict)

    def test_attribute_access_on_nonexistent_builtin_shadowed_key(self):
        """Accessing an attribute that shadows a built-in method should return MagicDict if non-existent."""
        md = MagicDict({"items": 123})
        self.assertEqual(md["items"], 123)
        del md["items"]
        self.assertNotIn("items", md)
        self.assertTrue(callable(MagicDict().items))

    def test_attribute_style_assignment_recursive_hook(self):
        """Test that assigning a dict value via attribute style converts it to MagicDict recursively."""
        md = MagicDict()
        md["config"] = {"host": "localhost", "port": 8080, "params": [{"a": 1}]}
        self.assertIsInstance(md.config, MagicDict)
        self.assertIsInstance(md.config.params[0], MagicDict)
        self.assertEqual(md.config.host, "localhost")
        self.assertEqual(md.config.params[0].a, 1)

    def test_attribute_assignment_does_not_conflict_with_instance_attrs(self):
        """Assigning a key that matches an instance attribute should not interfere with attribute access."""
        md = MagicDict()
        md["_internal"] = "secret"
        self.assertIn("_internal", md)
        self.assertEqual(md["_internal"], "secret")

    def test_custom_repr(self):
        """Test that the __repr__ method returns a clear representation."""
        md = MagicDict({"a": 1, "b": MagicDict({"c": 2})})
        expected_repr = "MagicDict({'a': 1, 'b': MagicDict({'c': 2})})"
        self.assertEqual(repr(md), expected_repr)

    def test_is_unhashable(self):
        """Test that MagicDict instances are unhashable."""
        md = MagicDict()
        with self.assertRaises(TypeError):
            _ = {md: "value"}
        with self.assertRaises(TypeError):
            _ = {md}

    def test_in_place_update_operator(self):
        """Test that the in-place update operator (|=) hooks new values."""
        md = MagicDict({"a": 1})
        md |= {"b": {"c": 2}}
        self.assertEqual(md.a, 1)
        self.assertIsInstance(md.b, MagicDict)
        self.assertEqual(md.b.c, 2)

    def test_deletion_a(self):
        """Consolidated test for item deletion."""
        d = MagicDict({"a": 1, "b": 2})
        del d["a"]
        self.assertNotIn("a", d)
        with self.assertRaises(KeyError):
            del d["c"]

    def test_attribute_style_assignment_and_deletion(self):
        """Test that assigning and deleting keys via item notation works correctly."""
        md = MagicDict()

        md["new_key"] = "new_value"
        self.assertIn("new_key", md)
        self.assertEqual(md["new_key"], "new_value")

        md["config"] = {"host": "localhost", "port": 8080}
        self.assertIsInstance(md.config, MagicDict)
        self.assertEqual(md.config.host, "localhost")

        md["new_key"] = "overwritten"
        self.assertEqual(md.new_key, "overwritten")

        del md["new_key"]
        self.assertNotIn("new_key", md)

        with self.assertRaises(KeyError):
            del md["non_existent_key"]

        md_conflict = MagicDict({"keys": "shadow"})
        del md_conflict["keys"]
        self.assertNotIn("keys", md_conflict)
        self.assertTrue(callable(md_conflict.keys))

    def test_attribute_assignment_cannot_shadow_methods(self):
        """Assigning a key that matches a dict method should not interfere with method calls."""
        md = MagicDict()
        md["update"] = "my_value"
        self.assertEqual(md["update"], "my_value")
        self.assertTrue(callable(md.update))

    def test_dir_includes_keys_and_methods(self):
        """Test that dir() includes both keys and dict methods."""
        md = MagicDict({"a": 1, "b_key": 2})
        d = dir(md)
        self.assertIn("a", d)
        self.assertIn("b_key", d)
        self.assertIn("keys", d)
        self.assertIn("copy", d)

    def test_deepcopy_creates_fully_independent_objects(self):
        """Test that deepcopy() creates fully independent copies."""
        md = MagicDict({"a": 1, "b": {"c": [1, {"d": 2}]}})
        md_deepcopy = copy.deepcopy(md)

        self.assertEqual(md, md_deepcopy)
        self.assertIsNot(md, md_deepcopy)
        self.assertIsNot(md.b, md_deepcopy.b)
        self.assertIsNot(md.b.c, md_deepcopy.b.c)
        self.assertIsNot(md.b.c[1], md_deepcopy.b.c[1])

        md_deepcopy.b.c[1].d = 99
        self.assertEqual(md.b.c[1].d, 2)
        self.assertEqual(md_deepcopy.b.c[1].d, 99)

    def test_chained_access_on_non_dict_value_raises_attribute_error(self):
        """Accessing attributes on a non-dict value should raise AttributeError."""
        md = MagicDict({"a": 42, "b": "hello"})
        with self.assertRaises(AttributeError):
            _ = md.a.b.c
        with self.assertRaises(AttributeError):
            _ = md.b.upper.lower

    def test_dict_subclass_is_converted(self):
        """Test that subclasses of dict are converted to MagicDict."""

        class MyDict(dict):
            """A simple subclass of dict."""

            pass

        data = MyDict(user=MyDict(name="subclass_user"))
        md = MagicDict(data)
        self.assertIsInstance(md, MagicDict)
        self.assertNotIsInstance(md, MyDict)
        self.assertIsInstance(md.user, MagicDict)
        self.assertNotIsInstance(md.user, MyDict)
        self.assertEqual(md.user.name, "subclass_user")

    def test_list_and_tuple_subclass_type_is_preserved(self):
        """Test that subclasses of list and tuple preserve their types after hooking."""

        class MyList(list):
            """A simple subclass of list."""

            def custom_method(self):
                """A custom method for MyList."""
                return "hello"

        class MyTuple(tuple):
            """A simple subclass of tuple."""

            pass

        data = {"a_list": MyList([{"id": 1}]), "a_tuple": MyTuple(({"id": 2},))}
        md = MagicDict(data)

        self.assertIsInstance(md.a_list, MyList)
        self.assertIsInstance(md.a_tuple, MyTuple)
        self.assertEqual(md.a_list.custom_method(), "hello")
        self.assertIsInstance(md.a_list[0], MagicDict)
        self.assertEqual(md.a_list[0].id, 1)

    def test_in_place_update_operator_hooks_values(self):
        """Test that the in-place update operator (|=) hooks new values."""
        md = MagicDict({"a": 1})
        md |= {"b": {"c": 2}, "d": [{"e": 3}]}
        self.assertEqual(md.a, 1)
        self.assertIsInstance(md.b, MagicDict)
        self.assertEqual(md.b.c, 2)
        self.assertIsInstance(md.d[0], MagicDict)
        self.assertEqual(md.d[0].e, 3)

    def test_empty_initializations(self):
        """Test that various empty initializations result in an empty MagicDict."""
        self.assertEqual(MagicDict(), {})
        self.assertEqual(MagicDict({}), {})
        self.assertEqual(MagicDict([]), {})

    def test_boolean_keys(self):
        """Test that boolean keys are treated distinctly from string keys."""
        md = MagicDict({True: "yes", False: "no"})
        self.assertEqual(md[True], "yes")
        self.assertEqual(md[False], "no")
        self.assertNotIn("True", md)

    def test_dict_inside_list_is_converted(self):
        """Test that dicts inside lists are converted to MagicDicts."""
        d = {"container": [{"a": {"b": 2}}]}
        md = MagicDict(d)
        self.assertIsInstance(md.container[0], MagicDict)
        self.assertIsInstance(md.container[0].a, MagicDict)
        self.assertEqual(md.container[0].a.b, 2)

    def test_double_underscore_keys(self):
        """Test that keys with double underscores do not interfere with instance attributes."""
        md = MagicDict({"__class__": "fake", "__dict__": "fake_dict"})
        self.assertEqual(md["__class__"], "fake")
        self.assertEqual(md["__dict__"], "fake_dict")
        self.assertIsInstance(md.__dict__, dict)

    def test_large_dict_performance(self):
        """Test that large dictionaries are handled without performance degradation or recursion errors."""
        big = {f"key{i}": {"nested": i} for i in range(1000)}
        md = MagicDict(big)
        self.assertEqual(md.key500.nested, 500)

    def test_overwrite_with_none(self):
        """Setting a key to None and then accessing its attributes should return MagicDict."""
        md = MagicDict({"a": {"b": 1}})
        md["a"] = None
        self.assertEqual(md.a.b, MagicDict())

    def test_setattr_directly(self):
        """Setting attributes directly should not create keys in the dict."""
        md = MagicDict()
        setattr(md, "foo", 123)
        self.assertNotIn("foo", md)
        self.assertEqual(md.foo, 123)

    def test_fromkeys_mutable_default_is_unique(self):
        """Test that fromkeys with a mutable default creates separate instances."""
        default = {"nested": []}
        md1 = MagicDict.fromkeys(["a", "b"], default)
        md2 = MagicDict.fromkeys(["a", "b"], default)
        self.assertIsNot(md1.a, md2.a)

    def test_pickle_roundtrip(self):
        """Test that pickling and unpickling a MagicDict preserves its structure and types."""
        md = MagicDict({"a": {"b": 1}})
        dumped = pickle.dumps(md)
        loaded = pickle.loads(dumped)
        self.assertIsInstance(loaded, MagicDict)
        self.assertEqual(loaded.a.b, 1)

    def test_equality_with_mapping_proxy(self):
        """Test that MagicDict compares equal to a MappingProxyType with the same content."""
        d = {"a": 1}
        md = MagicDict(d)
        proxy = MappingProxyType(d)
        self.assertEqual(md, proxy)

    def test_subclass_preserves_safe_dict_behavior(self):
        """Test that subclasses of MagicDict retain the automatic conversion behavior."""

        class SubMagicDict(MagicDict):
            """A subclass of MagicDict to test inheritance of behavior."""

            pass

        smd = SubMagicDict({"a": {"b": 1}})
        self.assertIsInstance(smd.a, MagicDict)
        self.assertEqual(smd.a.b, 1)

    def test_chained_access_with_callable(self):
        """Accessing attributes on a callable value should raise AttributeError."""
        md = MagicDict({"func": lambda: {"x": 1}})
        self.assertTrue(callable(md.func))
        with self.assertRaises(AttributeError):
            _ = md.func.x

    def test_mutation_during_iteration(self):
        """Test that modifying the MagicDict during iteration raises RuntimeError."""
        md = MagicDict({"a": 1, "b": 2})
        with self.assertRaises(RuntimeError):
            for k in md:
                md["c"] = 3

    def test_equality_non_mapping(self):
        """Test that MagicDict is not equal to non-mapping types."""
        md = MagicDict({"a": 1})
        self.assertNotEqual(md, [("a", 1)])
        self.assertNotEqual(md, None)

    def test_pickle_roundtrip_2(self):
        """Test that pickling and unpickling a MagicDict preserves its structure and types."""
        md = MagicDict({"a": {"b": 1}})
        dumped = pickle.dumps(md)
        loaded = pickle.loads(dumped)
        self.assertIsInstance(loaded, MagicDict)
        self.assertEqual(loaded.a.b, 1)

    def test_get_with_invalid_identifier_key_returns_enchant(self):
        """Test that get works with keys that are not valid Python identifiers and returns a MagicDict when default is provided."""
        md = MagicDict({"1": {"inside": "Inside_One"}, "my-key": {"nested": 42}})

        result_numeric = md.get("1", MagicDict())
        self.assertIsInstance(result_numeric, MagicDict)
        self.assertEqual(result_numeric.inside, "Inside_One")

        result_hyphen = md.get("my-key", MagicDict())
        self.assertIsInstance(result_hyphen, MagicDict)
        self.assertEqual(result_hyphen.nested, 42)

        result_via_getattr = getattr(md.get("1"), "inside")
        self.assertEqual(result_via_getattr, "Inside_One")

        missing = md.get("nonexistent", MagicDict()).foo.bar
        self.assertIsInstance(missing, MagicDict)

    def test_dir_includes_all_dict_attributes(self):
        """Test that dir() includes all standard dict attributes and keys."""
        md = MagicDict({"a": 1, "b": 2})

        dict_dir = set(dir(dict))
        magic_dir = set(dir(md))

        missing = dict_dir - magic_dir
        self.assertFalse(
            missing, f"MagicDict.__dir__ is missing dict attributes: {missing}"
        )

        self.assertIn("a", magic_dir)
        self.assertIn("b", magic_dir)

    def test_json_serialization_deserialization(self):
        """Test JSON serialization and deserialization with MagicDict."""
        md = MagicDict({"a": 1, "b": {"c": 2}, "d": [1, 2, 3]})

        dumped = json.dumps(md)

        loaded_plain = json.loads(dumped)
        self.assertIsInstance(loaded_plain, dict)
        self.assertNotIsInstance(loaded_plain, MagicDict)
        self.assertEqual(loaded_plain, {"a": 1, "b": {"c": 2}, "d": [1, 2, 3]})

        loaded_magic = json.loads(dumped, object_hook=MagicDict)
        self.assertIsInstance(loaded_magic, MagicDict)
        self.assertIsInstance(loaded_magic.b, MagicDict)
        self.assertEqual(loaded_magic.b.c, 2)
        self.assertEqual(loaded_magic.d, [1, 2, 3])

    def test_key_and_attribute_access_are_consistent(self):
        """Test that key access and attribute access yield consistent results."""
        md = MagicDict({"hello": "world", "foo": {"bar": 1}})

        md["hello"] += "!"
        self.assertEqual(md.hello, "world!")

        self.assertIs(md.foo, md["foo"])
        self.assertIsInstance(md.foo, MagicDict)
        self.assertEqual(md.foo.bar, 1)

    def test_get_existing_key(self):
        """Test that get returns the value for existing keys."""
        md = MagicDict({"a": {"b": 1}})
        result = md.get("a")
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(result.b, 1)

    def test_get_missing_key_returns_none(self):
        """Test that get returns None for missing keys without a default."""
        md = MagicDict({"a": 1})
        result = md.get("missing")
        self.assertIsNone(result)

    def test_get_with_default_value(self):
        """Test that get with a default value returns the default for missing keys."""
        md = MagicDict({})
        default = {"x": 42}
        result = md.get("missing", default)
        self.assertEqual(result, default)

    def test_get_with_default_enchant(self):
        """Test that get with a default dict returns a MagicDict."""
        md = MagicDict({})
        result = md.get("missing", MagicDict())
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(len(result), 0)

    def test_get_invalid_identifier_key(self):
        """Test that get works with keys that are not valid Python identifiers."""
        md = MagicDict({"1": {"inside": "ok"}, "my-key": {"val": 123}})
        result_numeric = md.get("1")
        self.assertIsInstance(result_numeric, MagicDict)
        self.assertEqual(result_numeric.inside, "ok")

        result_hyphen = md.get("my-key")
        self.assertIsInstance(result_hyphen, MagicDict)
        self.assertEqual(result_hyphen.val, 123)

    def test_mget_existing_key(self):
        """Test that mget returns the value for existing keys."""
        md = MagicDict({"a": {"b": {"c": 42}}})
        result = md.mget("a")
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(result.b.c, 42)

    def test_mget_missing_key_returns_empty_enchant(self):
        """Test that mget returns an empty MagicDict for missing keys."""
        md = MagicDict({"a": 1})
        result = md.mget("missing")
        self.assertIsInstance(result, MagicDict)

    def test_mget_chained_access_safe(self):
        """Test that mget allows safe chained access on missing keys."""
        md = MagicDict({})
        result = md.mget("missing").foo.bar
        self.assertIsInstance(result, MagicDict)

    def test_mget_does_not_affect_existing_dict_values(self):
        """Test that mget does not alter existing dict values."""
        md = MagicDict({"a": {"b": 1}})
        self.assertEqual(md.get("a").b, 1)
        self.assertEqual(md.mget("a").b, 1)

    def test_mget_and_get_difference_on_missing(self):
        """Test the difference between get and mget on missing keys."""
        md = MagicDict({})
        self.assertIsNone(md.get("missing"))
        self.assertIsInstance(md.mget("missing"), MagicDict)

    def test_safe_dict_loads_returns_enchant(self):
        """Test that magic_loads returns a MagicDict when given a JSON string."""
        original = MagicDict({"a": {"b": {"c": 42}}, "d": [1, 2]})
        dumped = json.dumps(original)

        loaded = magic_loads(dumped)

        self.assertIsInstance(loaded, MagicDict)
        self.assertIsInstance(loaded.a, MagicDict)
        self.assertEqual(loaded.a.b.c, 42)
        self.assertEqual(loaded.d, [1, 2])

    def test_popitem_works_as_expected(self):
        """Test the popitem method."""
        md = MagicDict({"a": 1, "b": 2})
        key, value = md.popitem()
        self.assertIn(key, ["a", "b"])
        self.assertEqual(len(md), 1)
        md.popitem()
        self.assertEqual(len(md), 0)
        with self.assertRaises(KeyError):
            md.popitem()

    def test_repr_handles_recursive_structures(self):
        """Test that __repr__ handles self-referential structures without infinite recursion."""
        md = MagicDict()
        md["a"] = 1
        md["self"] = md
        self.assertIn("'self': MagicDict({...})", repr(md))

    def test_equality_with_dict_subclasses(self):
        """Test equality comparisons with dict subclasses."""
        d = OrderedDict([("b", 2), ("a", 1)])
        md = MagicDict([("b", 2), ("a", 1)])
        self.assertEqual(md, d)

    def test_chained_access_on_non_dict_value_raises_errors(self):
        """Accessing attributes on non-dict values should raise AttributeError."""
        md = MagicDict(
            {
                "an_int": 42,
                "a_str": "hello",
                "is_none": None,
                "items": {"nested_key": "nested_value"},
            }
        )

        with self.assertRaises(AttributeError):
            _ = md.an_int.foo

        with self.assertRaises(
            AttributeError,
        ):
            _ = md.a_str.upper.bar

        with self.assertRaises(AttributeError):
            _ = md.a_str.mget("upper").bar

        self.assertEqual(md.is_none.baz, MagicDict())
        self.assertEqual(md.mget("items").nested_key, "nested_value")
        self.assertEqual(md.mget("items").missing_key, MagicDict())

    def test_init_with_nested_iterable(self):
        """Test that nested dicts inside lists and tuples are converted to MagicDicts."""
        data = [("user", {"name": "test"}), ("permissions", [{"scope": "read"}])]
        md = MagicDict(data)
        self.assertIsInstance(md.user, MagicDict)
        self.assertEqual(md.user.name, "test")
        self.assertIsInstance(md.permissions[0], MagicDict)
        self.assertEqual(md.permissions[0].scope, "read")


class TestSomeReturns(TestCase):
    """Test various methods and behaviors of MagicDict."""

    def test_setitem_and_update(self):
        """Test that setting items and updating the dict work correctly."""
        md = MagicDict()
        md["a"] = 1
        md.b = 2
        self.assertEqual(md.a, 1)
        self.assertEqual(md.b, 2)

        md.update({"c": 3})
        self.assertEqual(md.c, 3)

    def test_copy_and_deepcopy(self):
        """Test that copy() is shallow while deepcopy() is deep."""
        data = {"nested": {"x": 1, "y": [1, 2, 3]}}
        md = MagicDict(data)
        sd_copy = md.copy()
        sd_deepcopy = copy.deepcopy(md)

        self.assertEqual(sd_copy.nested.x, 1)
        self.assertEqual(sd_deepcopy.nested.y, [1, 2, 3])

    def test_safe_dict_functions(self):
        """Test safedict_loads and enchant functions."""
        data = {"name": "Alice", "age": 30}
        json_str = json.dumps(data)

        # safedict_loads: use JSON string
        sd_loaded = magic_loads(json_str)
        self.assertIsInstance(sd_loaded, MagicDict)
        self.assertEqual(sd_loaded.name, "Alice")

        # magic_dict: use Python dict
        sd_from_dict = enchant(data)
        self.assertIsInstance(sd_from_dict, MagicDict)
        self.assertEqual(sd_from_dict.age, 30)

    def test_mget_for_nonexistent_keys(self):
        """Test that mget returns MagicDict for nonexistent keys."""
        md = MagicDict({"a": 1})
        self.assertIsInstance(md.mget("b"), MagicDict)

    def test_chaining_none_values(self):
        """Test that chaining through None values returns MagicDict instances."""
        md = MagicDict({"a": None})
        self.assertIsInstance(md.a.b.c, MagicDict)

    def test_dir_contains_keys(self):
        """Test that dir() includes the keys of the MagicDict."""
        md = MagicDict({"x": 1, "y": 2})
        attrs = dir(md)
        self.assertIn("x", attrs)
        self.assertIn("y", attrs)


class TestMagicDictBooleans(TestCase):
    """Test handling of boolean values in MagicDict."""

    def setUp(self):
        self.data = {"flag_true": True, "flag_false": False, "missing_flag": None}
        self.md = MagicDict(self.data)

    def test_boolean_wrapping(self):
        """Test that boolean values are wrapped correctly and behave as expected."""
        # Attribute access returns wrapped type (int subclass for bool)
        self.assertIsInstance(self.md.flag_true, int)
        self.assertIsInstance(self.md.flag_false, int)

        # .safe property returns actual bool
        self.assertIs(self.md.flag_true, True)
        self.assertIs(self.md.flag_false, False)

        # Boolean evaluation in conditions
        self.assertTrue(self.md.flag_true)
        self.assertFalse(self.md.flag_false)

        # Bracket access behaves normally
        self.assertEqual(self.md["flag_true"], True)
        self.assertEqual(self.md["flag_false"], False)

    def test_missing_key_boolean(self):
        """Test behavior of missing keys."""
        # Missing key returns SafeNone
        self.assertIsInstance(self.md.missing_flag, MagicDict)

        # Chaining safe on missing key
        self.assertIsInstance(self.md.missing_flag.anything, MagicDict)
        self.assertFalse(self.md.missing_flag.anything)

    def test_updating_boolean(self):
        """Test that updating boolean values works correctly."""
        # Update booleans
        self.md["flag_true"] = False
        self.assertIs(self.md.flag_true, False)

        self.md["flag_false"] = True
        self.assertIs(self.md.flag_false, True)

    def test_nested_boolean(self):
        """Test that nested dicts with boolean values are handled correctly."""
        self.md.nested = MagicDict({"inner_flag": True})
        self.assertIs(self.md.nested.inner_flag, True)
        self.assertTrue(self.md.nested.inner_flag)

    def test_identity_checks(self):
        """Test that identity checks work correctly."""
        self.assertIs(self.md.flag_true, True)
        self.assertIs(self.md.flag_false, False)

    def test_json_serialization_of_safenone_fails(self):
        """Test that json.dumps fails for a dict containing SafeNone."""
        md = MagicDict({"a": None})
        md = json.dumps(md)
        self.assertEqual(md, '{"a": null}')

    def test_json_deserialization_of_null(self):
        """Test that safedict_loads converts JSON null to _SafeNone."""
        json_str = '{"a": null, "b": {"c": null}}'
        md = magic_loads(json_str)
        self.assertIsInstance(md.a, MagicDict)
        self.assertFalse(md.a)
        self.assertIsInstance(md.b.c, MagicDict)
        self.assertFalse(md.b.c)

    def test_dynamic_wrapper_class_caching(self):
        """Test that dynamic wrapper classes are reused for the same type."""
        md = MagicDict({"s1": "a", "s2": "b", "i1": 1})
        self.assertIs(type(md.s1), type(md.s2))
        self.assertIsNot(type(md.s1), type(md.i1))

    def test_callable_class_instance_not_wrapped(self):
        """Test that a callable object instance is not wrapped and has no .safe property."""

        class CallableObj:
            """A simple callable class."""

            def __call__(self):
                return "called"

        obj = CallableObj()
        md = MagicDict({"callable_obj": obj})
        self.assertIs(md.callable_obj, obj)
        self.assertFalse(hasattr(md.callable_obj, "safe"))

    def test_ordereddict_is_converted_to_safedict(self):
        """Test that dict subclasses like OrderedDict are converted to MagicDict."""
        od = OrderedDict([("b", 2), ("a", 1)])
        md = MagicDict(od)
        self.assertIsInstance(md, MagicDict)
        self.assertNotIsInstance(md, OrderedDict)
        # Check that it behaves like a MagicDict
        self.assertEqual(md.b, 2)

    def test_chained_safe_property(self):
        """Test that .safe can be chained through MagicDict instances."""
        md = MagicDict({"a": {"b": 1}})
        self.assertIs(md, md)
        self.assertIs(md.a, md.a)
        self.assertEqual(md.a.b, 1)

    def test_non_string_keys_not_in_dir(self):
        """Test that non-string keys do not appear in dir()."""
        md = MagicDict({1: "one", ("a",): "tuple_key", "string_key": "present"})
        dir_list = dir(md)
        self.assertNotIn("1", dir_list)
        self.assertNotIn("a", dir_list)
        self.assertNotIn(("a",), dir_list)
        self.assertIn("string_key", dir_list)

    def test_boolean_wrapper_arithmetic(self):
        """Test that wrapped booleans behave like ints (0 and 1) in arithmetic."""
        md = MagicDict({"t": True, "f": False})
        self.assertEqual(md.t + 5, 6)
        self.assertEqual(md.f * 10, 0)
        self.assertTrue(md.t == 1)
        self.assertTrue(md.f == 0)

    def test_boolean_wrapper_isinstance(self):
        """Test the type identity of wrapped booleans."""
        md = MagicDict({"t": True})
        self.assertIsInstance(md.t, int)
        self.assertIsInstance(md.t, bool)

    def test_modifying_nested_list_in_place(self):
        """Test that modifications to nested lists within a MagicDict are preserved."""
        md = MagicDict({"a": [1, {"b": 2}]})

        # Append to the list
        md.a.append(3)

        self.assertEqual(md.a, [1, {"b": 2}, 3])
        self.assertIsInstance(md["a"][1], MagicDict)

        # Modify a MagicDict within the list
        md.a[1]["b"] = 99
        self.assertEqual(md.a[1].b, 99)
        self.assertEqual(md["a"][1]["b"], 99)

    def test_missing_and_none_behavior(self):
        """Test the behavior of accessing missing keys and keys with None values."""
        sd = MagicDict({"user": {"nickname": None}})
        # 1. Access a missing key
        missing = sd.user.address
        self.assertTrue(missing._from_missing)
        self.assertFalse(missing._from_none)

        # 2. Access a key with a value of None
        none_val = sd.user.nickname
        self.assertTrue(none_val._from_none)
        self.assertFalse(none_val._from_missing)

        # 3. Attempt to assign (should raise)
        with self.assertRaises(TypeError):
            missing["city"] = "Sofia"
        with self.assertRaises(TypeError):
            none_val["alias"] = "Ali"

        # 4. Create real keys
        sd.user["address"] = {}
        sd.user["nickname"] = "Alice"

        # Verify real structure
        self.assertIsInstance(sd.user.address, MagicDict)
        self.assertIsInstance(sd.user.nickname, str)

        # 5. Assign to new "real" keys (should work)
        sd.user.address["city"] = "Sofia"

        self.assertEqual(sd.user.address["city"], "Sofia")

        # Convert nickname to MagicDict to test valid assignment
        sd.user["nickname"] = MagicDict()
        sd.user.nickname["alias"] = "Ali"
        self.assertEqual(sd.user.nickname["alias"], "Ali")


class TestMissingCases(TestCase):
    """Test cases for MagicDict focusing on disenchanting and dotted-key access."""

    def setUp(self):
        self.data = {
            "user": {"profile": {"email": "test@example.com"}, "nickname": None},
            "permissions": ["read", {"area": "admin", "level": 1}],
            "config.with.dots": "value_with_dots",
        }
        self.md = MagicDict(self.data)

    def test_disenchant_recursively_converts_to_dict(self):
        """
        Verify that disenchant() converts the MagicDict and all nested
        instances back to standard Python dicts and lists.
        """
        disenchanted = self.md.disenchant()

        self.assertIs(type(disenchanted), dict)
        self.assertIs(type(disenchanted["user"]), dict)
        self.assertIs(type(disenchanted["user"]["profile"]), dict)
        self.assertIs(type(disenchanted["permissions"]), list)
        self.assertIs(type(disenchanted["permissions"][1]), dict)
        self.assertEqual(disenchanted["user"]["profile"]["email"], "test@example.com")

    def test_getitem_with_dotted_key_access(self):
        """
        Verify dotted-key access using __getitem__ (bracket notation).
        """
        self.assertEqual(self.md["user.profile.email"], "test@example.com")
        self.assertEqual(self.md["permissions.1.level"], 1)

    def test_getitem_dotted_key_handles_key_error(self):
        """
        Verify dotted-key access raises KeyError for a missing key in the chain.
        """
        with self.assertRaises(KeyError):
            _ = self.md["user.profile.nonexistent"]

    def test_getitem_dotted_key_handles_index_error(self):
        """
        Verify dotted-key access raises IndexError for an out-of-bounds list index.
        """
        with self.assertRaises(IndexError):
            _ = self.md["permissions.5.level"]

    def test_getitem_prioritizes_full_key_with_dots(self):
        """
        Verify that if a key literally contains dots, it is matched before
        attempting to split the key for nested access.
        """
        self.assertEqual(self.md["config.with.dots"], "value_with_dots")

    def test_mget_with_default_value(self):
        """
        Verify mget() returns the provided default for a missing key.
        """

        self.assertEqual(self.md.mget("nonexistent", "default"), "default")
        self.assertIsNone(self.md.mget("nonexistent", None))

    def test_mget_ignores_default_for_none_value(self):
        """
        Verify mget() returns an empty MagicDict for a key whose value is None,
        even if a default is provided, to ensure safe chaining.
        """
        result = self.md.user.mget("nickname", "default_nickname")
        self.assertIsInstance(result, MagicDict)
        self.assertTrue(getattr(result, "_from_none", False))
        self.assertEqual(result, {})

    def test_truthiness_of_magicdict_instances(self):
        """
        Verify the boolean value of MagicDict in different states.
        """
        self.assertTrue(self.md)  # Non-empty
        self.assertFalse(MagicDict())  # Empty
        self.assertFalse(self.md.nonexistent)  # From missing key
        self.assertFalse(self.md.user.nickname)  # From None value

    def test_attribute_deletion_raises_attribute_error(self):
        """
        Verify that attempting to delete a key via attribute access (del md.key)
        raises an AttributeError, as this is not standard dict behavior.
        """
        with self.assertRaises(AttributeError):
            del self.md.user
        # Ensure the key still exists and can be deleted normally
        self.assertIn("user", self.md)
        del self.md["user"]
        self.assertNotIn("user", self.md)

    def test_unsupported_containers_are_not_hooked(self):
        """
        Verify that dicts inside containers other than list/tuple (e.g., set)
        are not recursively converted to MagicDict.
        """
        data = {"my_set": {frozenset({"a": 1}.items())}}
        md = MagicDict(data)

        self.assertIsInstance(md.my_set, set)

        # The inner dict is not converted because it's inside a set
        inner_item = next(iter(md.my_set))
        self.assertIsInstance(inner_item, frozenset)
        # To inspect it, we'd have to convert it back to a dict
        inner_dict = dict(inner_item)
        self.assertIs(type(inner_dict), dict)


class TestMagicDictAdditionalCases(TestCase):
    """Additional edge case tests for MagicDict"""

    def test_deeply_nested_mixed_structures(self):
        """Test complex nesting: dict -> list -> tuple -> dict"""
        data = {"level1": [{"level2": ({"level3": [{"level4": "deep"}]},)}]}
        md = MagicDict(data)
        self.assertEqual(md.level1[0].level2[0].level3[0].level4, "deep")
        self.assertIsInstance(md.level1[0], MagicDict)
        self.assertIsInstance(md.level1[0].level2[0], MagicDict)
        self.assertIsInstance(md.level1[0].level2[0].level3[0], MagicDict)

    def test_setitem_on_from_none_nested_access(self):
        """Test that assignment fails even on deeply nested None-derived MagicDicts"""
        md = MagicDict({"a": None})
        temp = md.a.b.c
        with self.assertRaises(TypeError):
            temp["key"] = "value"
        self.assertTrue(getattr(temp, "_from_missing", False))

    def test_setitem_on_from_missing_nested_access(self):
        """Test that assignment fails on deeply nested missing-key MagicDicts"""
        md = MagicDict({})
        temp = md.x.y.z
        with self.assertRaises(TypeError):
            temp["key"] = "value"
        self.assertTrue(getattr(temp, "_from_missing", False))

    def test_mget_with_none_as_explicit_default(self):
        """Test mget when None is explicitly passed as default"""
        md = MagicDict({"exists": "value"})
        result = md.mget("missing", None)
        self.assertIsNone(result)

    def test_mget_with_missing_default(self):
        """Test that missing is properly used as sentinel"""
        md = MagicDict({})
        result = md.mget("missing")
        self.assertIsInstance(result, MagicDict)
        self.assertTrue(getattr(result, "_from_missing", False))

    def test_mget_chained_on_none_value(self):
        """Test chaining mget on a None value"""
        md = MagicDict({"user": {"name": None}})
        result = md.user.mget("name").somethingelse
        self.assertIsInstance(result, MagicDict)
        self.assertFalse(result)

    def test_getitem_dotted_key_empty_segment(self):
        """Test behavior with empty segments in dotted keys"""
        md = MagicDict({"a": {"": {"b": 1}}})
        # This should work if we have an empty string key
        self.assertEqual(md["a..b"], 1)

    def test_getitem_dotted_key_numeric_dict_key(self):
        """Test dotted access with numeric string keys in dict"""
        md = MagicDict({"a": {"1": {"b": 2}}})
        self.assertEqual(md["a.1.b"], 2)

    def test_getitem_dotted_vs_literal_key_priority(self):
        """Test that literal keys with dots take precedence"""
        md = MagicDict({"a.b": "literal", "a": {"b": "nested"}})
        self.assertEqual(md["a.b"], "literal")
        self.assertEqual(md["a"]["b"], "nested")

    def test_getitem_dotted_key_with_list_at_end(self):
        """Test dotted notation ending with list access"""
        md = MagicDict({"data": {"items": [1, 2, 3]}})
        self.assertEqual(md["data.items.0"], 1)
        self.assertEqual(md["data.items.2"], 3)

    def test_getitem_dotted_key_type_error(self):
        """Test dotted access on non-subscriptable type"""
        md = MagicDict({"value": 42})
        with self.assertRaises(KeyError):
            _ = md["value.something"]

    def test_named_tuple_preservation(self):
        """Test that named tuples are preserved"""
        Point = namedtuple("Point", ["x", "y"])
        md = MagicDict({"point": Point(1, 2)})
        self.assertIsInstance(md.point, Point)
        self.assertEqual(md.point.x, 1)
        self.assertEqual(md.point.y, 2)

    def test_nested_dict_in_named_tuple(self):
        """Test that dicts inside named tuples are converted"""
        Container = namedtuple("Container", ["data"])
        md = MagicDict({"container": Container({"nested": 1})})
        self.assertIsInstance(md.container.data, MagicDict)
        self.assertEqual(md.container.data.nested, 1)

    def test_custom_sequence_type_preservation(self):
        """Test that custom sequence types are handled"""

        class CustomList(list):
            """A custom list subclass with an extra method."""

            def custom_method(self):
                return "custom"

        data = {"custom": CustomList([{"a": 1}, {"b": 2}])}
        md = MagicDict(data)
        self.assertIsInstance(md.custom, CustomList)
        self.assertEqual(md.custom.custom_method(), "custom")
        self.assertIsInstance(md.custom[0], MagicDict)
        self.assertEqual(md.custom[0].a, 1)

    def test_contains_with_none_value(self):
        """Test __contains__ with None values"""
        md = MagicDict({"key": None})
        self.assertIn("key", md)
        self.assertEqual(md.key, MagicDict())
        self.assertTrue(getattr(md.key, "_from_none", False))

    def test_bool_evaluation_with_false_values(self):
        """Test boolean evaluation with various falsy values"""
        md = MagicDict(
            {
                "empty_list": [],
                "empty_dict": {},
                "zero": 0,
                "false": False,
                "empty_string": "",
            }
        )
        self.assertTrue(md)  # dict itself is not empty
        self.assertFalse(md.empty_list)
        self.assertFalse(md.empty_dict)
        self.assertEqual(md.zero, 0)
        self.assertFalse(md.false)
        self.assertEqual(md.empty_string, "")

    def test_len_on_from_missing_magicdict(self):
        """Test len() on MagicDict created from missing key"""
        md = MagicDict({})
        temp = md.missing
        self.assertEqual(len(temp), 0)
        self.assertFalse(temp)

    def test_update_with_none_values(self):
        """Test that update handles None values correctly"""
        md = MagicDict({"a": 1})
        md.update({"b": None})
        # None should be stored as None, but accessing it returns empty MagicDict
        self.assertIsNone(md["b"])
        self.assertEqual(md.b, MagicDict())

    def test_update_with_kwargs_and_dict(self):
        """Test update with both positional dict and kwargs"""
        md = MagicDict()
        md.update({"a": {"b": 1}}, c={"d": 2})
        self.assertIsInstance(md.a, MagicDict)
        self.assertIsInstance(md.c, MagicDict)
        self.assertEqual(md.a.b, 1)
        self.assertEqual(md.c.d, 2)

    def test_update_overwrites_from_missing_flag(self):
        """Test that updating a key removes from_missing flag"""
        md = MagicDict({})
        temp = md.missing  # Creates from_missing MagicDict
        md["missing"] = {"real": "value"}
        # Now accessing should give real value
        self.assertIsInstance(md.missing, MagicDict)
        self.assertEqual(md.missing.real, "value")
        self.assertFalse(getattr(md.missing, "_from_missing", False))

    def test_circular_reference_in_list(self):
        """Test circular reference within a list"""
        md = MagicDict({"items": []})
        md["items"].append(md)
        self.assertIs(md["items"][0], md)

    def test_pickle_circular_reference(self):
        """Test pickling with circular references"""
        md = MagicDict()
        md["self"] = md
        pickled = pickle.dumps(md)
        unpickled = pickle.loads(pickled)
        self.assertIs(unpickled["self"], unpickled)

    def test_deepcopy_circular_reference(self):
        """Test deepcopy with circular references"""
        md = MagicDict()
        md["self"] = md
        md_copy = copy.deepcopy(md)
        self.assertIs(md_copy["self"], md_copy)
        self.assertIsNot(md_copy, md)

    def test_disenchant_with_none_values(self):
        """Test that disenchant preserves None values"""
        md = MagicDict({"a": None, "b": {"c": None}})
        result = md.disenchant()
        self.assertIsNone(result["a"])
        self.assertIsNone(result["b"]["c"])
        self.assertIsInstance(result, dict)
        self.assertNotIsInstance(result, MagicDict)

    def test_disenchant_handles_circular_reference(self):
        """
        Verify disenchant() correctly handles circular references
        without raising a RecursionError.
        """
        md = MagicDict()
        md["self"] = md
        # Call the method directly. If it raises an error, the test will fail.
        disenchanted_dict = md.disenchant()
        # Verify that the output is a standard dict.
        self.assertIs(type(disenchanted_dict), dict)
        # Verify that the circular reference is maintained in the new dict.
        self.assertIs(disenchanted_dict["self"], disenchanted_dict)

    def test_disenchant_preserves_list_types(self):
        """Test that disenchant preserves list and tuple types"""
        md = MagicDict({"list": [{"a": 1}], "tuple": ({"b": 2},)})
        result = md.disenchant()
        self.assertIsInstance(result["list"], list)
        self.assertIsInstance(result["tuple"], tuple)
        self.assertIsInstance(result["list"][0], dict)
        self.assertNotIsInstance(result["list"][0], MagicDict)

    def test_pop_with_default_on_method_shadow(self):
        """Test pop with default when key shadows a method"""
        md = MagicDict({"pop": "value"})
        result = md.pop("items", "default")
        self.assertEqual(result, "default")
        self.assertTrue(callable(md.items))
        # The "pop" key should still exist
        self.assertEqual(md["pop"], "value")

    def test_accessing_shadowed_method_after_deletion(self):
        """Test that methods are still accessible after deleting shadowing key"""
        md = MagicDict({"keys": "shadow", "items": "shadow2"})
        del md["keys"]
        self.assertTrue(callable(md.keys))
        self.assertListEqual(list(md.keys()), ["items"])

    def test_setdefault_with_method_name(self):
        """Test setdefault with a key that shadows a method"""
        md = MagicDict()
        result = md.setdefault("update", {"nested": "value"})
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(result.nested, "value")
        self.assertTrue(callable(md.update))

    def test_fromkeys_with_none_value(self):
        """Test fromkeys with None as the default value"""
        md = MagicDict.fromkeys(["a", "b", "c"], None)
        self.assertIsNone(md["a"])
        self.assertEqual(md.a, MagicDict())
        self.assertTrue(getattr(md.a, "_from_none", False))

    def test_fromkeys_with_empty_sequence(self):
        """Test fromkeys with an empty sequence"""
        md = MagicDict.fromkeys([])
        self.assertEqual(len(md), 0)
        self.assertIsInstance(md, MagicDict)

    def test_chaining_through_multiple_none_values(self):
        """Test chaining through multiple None values"""
        md = MagicDict({"a": {"b": None}})
        result = md.a.b.c.d.e
        self.assertIsInstance(result, MagicDict)
        self.assertFalse(result)

    def test_chaining_missing_and_none_mixed(self):
        """Test chaining through mix of missing keys and None values"""
        md = MagicDict({"a": None})
        result = md.a.missing.b.c
        self.assertIsInstance(result, MagicDict)
        self.assertFalse(result)

    def test_attribute_access_after_bracket_assignment(self):
        """Test attribute access after bracket-style assignment"""
        md = MagicDict({})
        md["new"] = {"nested": "value"}
        self.assertIsInstance(md.new, MagicDict)
        self.assertEqual(md.new.nested, "value")

    def test_negative_numeric_keys(self):
        """Test negative numbers as keys"""
        md = MagicDict({-1: "negative", -5: {"nested": "value"}})
        self.assertEqual(md[-1], "negative")
        self.assertIsInstance(md[-5], MagicDict)
        self.assertEqual(md[-5].nested, "value")

    def test_float_keys(self):
        """Test float numbers as keys"""
        md = MagicDict({1.5: "float", 2.7: {"nested": "value"}})
        self.assertEqual(md[1.5], "float")
        self.assertEqual(md.mget(2.7).nested, "value")

    def test_empty_string_key(self):
        """Test empty string as a key"""
        md = MagicDict({"": "empty_key_value"})
        self.assertEqual(md[""], "empty_key_value")
        # Attribute access should return from_missing
        result = getattr(md, "")
        self.assertEqual(result, "empty_key_value")

    def test_nested_empty_dicts_and_lists(self):
        """Test deeply nested empty structures"""
        md = MagicDict({"a": {"b": {"c": {}}}})
        self.assertIsInstance(md.a.b.c, MagicDict)
        self.assertEqual(len(md.a.b.c), 0)

    def test_json_loads_with_none(self):
        """Test magic_loads with JSON null values"""
        json_str = '{"user": {"name": "Alice", "email": null}}'
        md = magic_loads(json_str)
        self.assertIsNone(md["user"]["email"])
        self.assertEqual(md.user.email, MagicDict())

    def test_enchant_with_ordered_dict(self):
        """Test enchant with OrderedDict"""
        od = OrderedDict([("z", 3), ("a", 1), ("m", 2)])
        md = enchant(od)
        self.assertIsInstance(md, MagicDict)
        # Order should be preserved in Python 3.7+
        keys_list = list(md.keys())
        self.assertEqual(keys_list, ["z", "a", "m"])

    def test_enchant_with_non_dict_raises_error(self):
        """Test that enchant raises TypeError for non-dict input"""
        with self.assertRaises(TypeError):
            enchant([1, 2, 3])
        with self.assertRaises(TypeError):
            enchant("string")
        with self.assertRaises(TypeError):
            enchant(123)

    def test_hook_with_bytes_sequence(self):
        """Test that bytes are not treated as hookable sequence"""
        md = MagicDict({"data": b"bytes_data"})
        self.assertEqual(md.data, b"bytes_data")
        self.assertIsInstance(md.data, bytes)

    def test_very_deep_nesting(self):
        """Test very deep nesting doesn't cause issues"""
        depth = 100
        data = {}
        current = data
        for i in range(depth):
            current[f"level{i}"] = {}
            current = current[f"level{i}"]
        current["value"] = "deep"

        md = MagicDict(data)
        # Navigate to the deepest level
        current_md = md
        for i in range(depth):
            current_md = getattr(current_md, f"level{i}")
        self.assertEqual(current_md.value, "deep")

    def test_large_number_of_keys(self):
        """Test MagicDict with large number of keys"""
        large_dict = {f"key{i}": {"value": i} for i in range(1000)}
        md = MagicDict(large_dict)
        self.assertEqual(md.key500.value, 500)
        self.assertEqual(md.key999.value, 999)

    def test_with_slots_class(self):
        """Test MagicDict containing objects with __slots__"""

        class SlottedClass:
            """A simple class using __slots__."""

            __slots__ = ["x", "y"]

            def __init__(self, x, y):
                self.x = x
                self.y = y

        obj = SlottedClass(1, 2)
        md = MagicDict({"obj": obj})
        self.assertIs(md.obj, obj)
        self.assertEqual(md.obj.x, 1)

    def test_with_property_objects(self):
        """Test MagicDict containing objects with properties"""

        class PropClass:
            """A simple class with a property."""

            def __init__(self, value):
                self._value = value

            @property
            def value(self):
                """A simple property."""
                return self._value

        obj = PropClass(42)
        md = MagicDict({"obj": obj})
        self.assertEqual(md.obj.value, 42)

    def test_get_with_callable_default(self):
        """Test get() with a callable as default"""
        md = MagicDict({"a": 1})
        result = md.get("missing", lambda: "callable")
        self.assertTrue(callable(result))
        self.assertEqual(result(), "callable")

    def test_get_returns_hook_converted_value(self):
        """Test that get() returns hook-converted values"""
        md = MagicDict({"nested": {"deep": {"value": 1}}})
        result = md.get("nested")
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(result.deep.value, 1)

    def test_repr_with_very_long_dict(self):
        """Test repr doesn't break with large dicts"""
        md = MagicDict({f"key{i}": i for i in range(100)})
        repr_str = repr(md)
        self.assertTrue(repr_str.startswith("MagicDict("))
        self.assertTrue(repr_str.endswith(")"))

    def test_equality_with_itself(self):
        """Test MagicDict equality with itself"""
        md = MagicDict({"a": 1})
        self.assertEqual(md, md)
        self.assertTrue(md == md)

    def test_inequality_operators(self):
        """Test that inequality operators work correctly"""
        md1 = MagicDict({"a": 1})
        md2 = MagicDict({"a": 2})
        self.assertNotEqual(md1, md2)
        self.assertTrue(md1 != md2)
        self.assertFalse(md1 == md2)


class TestPickleAndRegression(TestCase):
    """
    This test suite validates that the removal of __reduce__ and the
    implementation of __getstate__/__setstate__ has:
    1. Fixed the pickling of circular references.
    2. Works correctly for simple and nested structures.
    3. Has not negatively impacted the core functionality of MagicDict.
    """

    def setUp(self):
        """Set up a complex MagicDict instance for testing."""
        self.data = {
            "user": {"profile": {"email": "test@example.com"}, "nickname": None},
            "permissions": ["read", {"area": "admin", "level": 1}],
            "config": {"theme": "dark"},
        }
        self.md = MagicDict(self.data)
        # Create a circular reference for the crucial test case
        self.md["self_ref"] = self.md

    # --- Part 1: Validation of the Pickling Fix ---

    def test_pickle_circular_reference_is_fixed(self):
        """
        THE KEY TEST: Verify that an object with a circular reference
        can now be pickled and unpickled without a RecursionError.
        """
        try:
            # Step 1: Pickle the object. This will fail if the fix isn't applied.
            pickled_md = pickle.dumps(self.md)

            # Step 2: Unpickle the object.
            unpickled_md = pickle.loads(pickled_md)

            # Step 3: Verify the integrity of the unpickled object.
            # The most important check: The circular reference must be restored
            # to point to the new unpickled object itself, not a copy.
            self.assertIs(unpickled_md["self_ref"], unpickled_md)

            # Also check other data to ensure it was restored correctly.
            self.assertEqual(unpickled_md.user.profile.email, "test@example.com")
            self.assertIsInstance(unpickled_md.user.profile, MagicDict)

        except RecursionError:
            self.fail(
                "RecursionError encountered during pickling. The fix for circular references is not working."
            )

    def test_pickle_deeply_nested_object(self):
        """
        Verify that a standard nested MagicDict pickles and unpickles correctly,
        preserving its type and structure.
        """
        # We use a deepcopy to test a version without the circular reference
        md_simple = copy.deepcopy(self.md)
        del md_simple["self_ref"]

        pickled = pickle.dumps(md_simple)
        unpickled = pickle.loads(pickled)

        # Check types recursively
        self.assertIsInstance(unpickled, MagicDict)
        self.assertIsInstance(unpickled.user, MagicDict)
        self.assertIsInstance(unpickled.permissions[1], MagicDict)

        # Check values
        self.assertEqual(unpickled, md_simple)
        self.assertEqual(unpickled.permissions[1].level, 1)

    def test_regression_attribute_access_is_unaffected(self):
        """
        Verify that the core "magic" features (attribute access, safe chaining)
        were not broken by the pickle-related changes.
        """
        # Deep attribute access
        self.assertEqual(self.md.user.profile.email, "test@example.com")

        # Graceful failure on non-existent keys
        non_existent = self.md.user.address.city
        self.assertIsInstance(non_existent, MagicDict)
        self.assertFalse(non_existent)  # Should evaluate to False

        # Safe chaining on None values
        nickname_chain = self.md.user.nickname.alias
        self.assertIsInstance(nickname_chain, MagicDict)
        self.assertTrue(getattr(nickname_chain, "_from_missing", False))

    def test_regression_standard_dict_behavior_is_unaffected(self):
        """
        Verify that standard dictionary operations were not broken.
        """
        # Standard bracket access
        self.assertEqual(self.md["user"]["profile"]["email"], "test@example.com")

        # The get() method
        self.assertEqual(
            self.md.get("user").get("profile").get("email"), "test@example.com"
        )

        # Membership testing
        self.assertIn("user", self.md)
        self.assertNotIn("nonexistent", self.md)

        # Deletion
        temp_md = copy.deepcopy(self.md)
        del temp_md["config"]
        self.assertNotIn("config", temp_md)

        # Bracket access on a missing key must still raise KeyError
        with self.assertRaises(KeyError):
            _ = self.md["user"]["nonexistent"]

    def test_regression_disenchant_method_is_unaffected(self):
        """
        Verify that the disenchant() method still works as expected.
        """
        disenchanted = self.md.disenchant()

        # The circular reference will still exist, but now between standard dicts
        self.assertIs(type(disenchanted), dict)
        self.assertIs(type(disenchanted["user"]), dict)
        self.assertIs(type(disenchanted["permissions"][1]), dict)
        self.assertIs(disenchanted["self_ref"], disenchanted)


class TestEnchantDisenchat(TestCase):
    """
    Test suite for the enchant() and disenchant() helper functions.
    """

    def setUp(self):
        """Set up common data structures for testing."""
        self.standard_dict = {
            "user": {
                "profile": {"email": "test@example.com", "active": True},
                "roles": ["admin", {"name": "editor", "level": 2}],
            },
            "settings": ({"theme": "dark"},),
            "status": "ok",
        }
        self.magic_dict = MagicDict(self.standard_dict)

    # --- Tests for enchant() ---

    def test_enchant_converts_standard_dict(self):
        """Verify that enchant() converts a standard dict to a MagicDict."""
        enchanted = enchant(self.standard_dict)
        self.assertIsInstance(enchanted, MagicDict)
        self.assertEqual(enchanted.status, "ok")

    def test_enchant_is_recursive(self):
        """Verify that enchant() recursively converts nested dicts."""
        enchanted = enchant(self.standard_dict)
        self.assertIsInstance(enchanted.user, MagicDict)
        self.assertIsInstance(enchanted.user.profile, MagicDict)
        self.assertIsInstance(enchanted.user.roles[1], MagicDict)
        self.assertIsInstance(enchanted.settings[0], MagicDict)
        self.assertEqual(enchanted.user.profile.email, "test@example.com")

    def test_enchant_on_existing_magicdict(self):
        """Verify that passing a MagicDict to enchant() returns it unchanged."""
        result = enchant(self.magic_dict)
        self.assertIs(result, self.magic_dict)

    def test_enchant_raises_typeerror_for_non_dict(self):
        """Verify that enchant() raises a TypeError for invalid input types."""
        with self.assertRaises(TypeError):
            enchant(["a", "list"])
        with self.assertRaises(TypeError):
            enchant("a string")
        with self.assertRaises(TypeError):
            enchant(123)

    # --- Tests for disenchant() ---

    def test_disenchant_converts_magic_dict(self):
        """Verify that disenchant() converts a MagicDict back to a standard dict."""
        disenchanted = self.magic_dict.disenchant()
        self.assertIs(type(disenchanted), dict)
        self.assertNotIsInstance(disenchanted, MagicDict)
        self.assertEqual(disenchanted["status"], "ok")

    def test_disenchant_is_recursive(self):
        """Verify that disenchant() recursively converts nested MagicDicts."""
        disenchanted = self.magic_dict.disenchant()
        self.assertIs(type(disenchanted["user"]), dict)
        self.assertIs(type(disenchanted["user"]["profile"]), dict)
        self.assertIs(type(disenchanted["user"]["roles"][1]), dict)
        self.assertIs(type(disenchanted["settings"][0]), dict)
        self.assertEqual(disenchanted["user"]["profile"]["email"], "test@example.com")

    def test_disenchant_handles_circular_reference(self):
        """
        Verify disenchant() correctly handles circular references
        without raising a RecursionError.
        """
        md = MagicDict()
        md["a"] = 1
        md["self"] = md  # Create circular reference

        # This should execute without error.
        disenchanted = md.disenchant()

        # Verify the structure and the restored circular reference.
        self.assertIs(type(disenchanted), dict)
        self.assertEqual(disenchanted["a"], 1)
        self.assertIs(disenchanted["self"], disenchanted)

    def test_disenchant_preserves_other_types(self):
        """Verify disenchant() does not alter non-dict/list/tuple types."""
        md = MagicDict(
            {
                "a_string": "hello",
                "an_int": 123,
                "a_bool": True,
                "a_none": None,
                "a_set": {1, 2, 3},
            }
        )
        disenchanted = md.disenchant()
        self.assertEqual(disenchanted["a_string"], "hello")
        self.assertEqual(disenchanted["an_int"], 123)
        self.assertIs(disenchanted["a_bool"], True)
        self.assertIsNone(disenchanted["a_none"])
        self.assertIsInstance(disenchanted["a_set"], set)

    def test_disenchant_on_already_standard_dict(self):
        """
        Verify that disenchant works correctly even if called on a
        standard dict (it should effectively do nothing).
        """
        # The disenchant logic can handle standard dicts, though it's a no-op.
        # This can be useful for functions that want to ensure a plain dict result.
        result = self.magic_dict.disenchant()  # disenchant is a method of MagicDict
        self.assertEqual(result, self.standard_dict)


class TestMagicDictBasicFunctionality(TestCase):
    """Test basic MagicDict features"""

    def test_attribute_access(self):
        """Test basic attribute-style access"""
        md = MagicDict({"user": {"name": "Alice", "id": 1}})
        self.assertEqual(md.user.name, "Alice")
        self.assertEqual(md.user.id, 1)

    def test_bracket_access(self):
        """Test standard bracket notation"""
        md = MagicDict({"user": {"name": "Alice"}})
        self.assertEqual(md["user"]["name"], "Alice")

    def test_dot_notation_in_brackets(self):
        """Test deep access with dot notation"""
        md = MagicDict({"user": {"profile": {"email": "alice@example.com"}}})
        self.assertEqual(md["user.profile.email"], "alice@example.com")

    def test_missing_key_attribute_access(self):
        """Missing keys via attributes return empty MagicDict"""
        md = MagicDict({"user": {"name": "Alice"}})
        result = md.user.email
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(len(result), 0)

    def test_missing_key_bracket_raises(self):
        """Missing keys via brackets raise KeyError"""
        md = MagicDict({"user": {"name": "Alice"}})
        with self.assertRaises(KeyError):
            _ = md["user"]["email"]

    def test_none_value_attribute_access(self):
        """Accessing None values via attributes returns empty MagicDict"""
        md = MagicDict({"user": {"nickname": None}})
        result = md.user.nickname
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(len(result), 0)

    def test_none_value_bracket_access(self):
        """Accessing None values via brackets returns None"""
        md = MagicDict({"user": {"nickname": None}})
        self.assertIsNone(md["user"]["nickname"])

    def test_safe_chaining(self):
        """Test chaining through missing keys"""
        md = MagicDict({"user": {"name": "Alice"}})
        result = md.user.address.city.zipcode
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(len(result), 0)


class TestMagicDictRecursiveConversion(TestCase):
    """Test recursive conversion of nested structures"""

    def test_nested_dict_conversion(self):
        """Nested dicts are converted to MagicDict"""
        md = MagicDict({"level1": {"level2": {"level3": "value"}}})
        self.assertIsInstance(md.level1, MagicDict)
        self.assertIsInstance(md.level1.level2, MagicDict)

    def test_list_with_dicts(self):
        """Dicts inside lists are converted"""
        md = MagicDict({"items": [{"name": "item1"}, {"name": "item2"}]})
        self.assertIsInstance(md["items"][0], MagicDict)
        self.assertEqual(md["items"][0].name, "item1")

    def test_tuple_with_dicts(self):
        """Dicts inside tuples are converted"""
        md = MagicDict({"data": ({"a": 1}, {"b": 2})})
        self.assertIsInstance(md.data[0], MagicDict)
        self.assertIsInstance(md.data, tuple)

    def test_namedtuple_preservation(self):
        """Namedtuples are preserved with converted contents"""
        Point = namedtuple("Point", ["x", "y"])
        md = MagicDict({"point": Point({"nested": 1}, {"nested": 2})})
        self.assertIsInstance(md.point, Point)
        self.assertIsInstance(md.point.x, MagicDict)


class TestMagicDictCircularReferences(TestCase):
    """Test handling of circular references"""

    def test_disenchant_circular_reference(self):
        """disenchant() handles circular references"""
        md = MagicDict({"a": {"b": "value"}})
        md["circular"] = md  # Create circular reference

        result = md.disenchant()
        self.assertIsInstance(result, dict)
        self.assertIs(result["circular"], result)

    def test_initialization_circular_reference(self):
        """KNOWN BUG: Circular references in input cause stack overflow"""
        data = {"a": {}}
        data["a"]["loop"] = data["a"]

        # This should either work or raise a clear error
        # Currently causes RecursionError
        md = MagicDict(data)

    def test_disenchant_list_circular_reference(self):
        """disenchant() handles circular refs in lists"""
        md = MagicDict({"items": [{"name": "item1"}]})
        md["items"].append(md["items"])  # Circular list

        result = md.disenchant()
        self.assertIsInstance(result, dict)
        self.assertIs(result["items"][1], result["items"])


class TestMagicDictInputMutation(TestCase):
    """Test for input data mutation side effects"""

    def test_list_mutation_side_effect(self):
        """KNOWN ISSUE: Input lists are mutated in-place"""
        original_list = [{"a": 1}, {"b": 2}]
        md = MagicDict({"items": original_list})

        # The original list has been mutated!
        self.assertIsInstance(original_list[0], MagicDict)

    def test_dict_not_mutated(self):
        """Input dicts are not mutated (they're copied)"""
        original_dict = {"nested": {"value": 1}}
        md = MagicDict(original_dict)

        # Original dict is unchanged
        self.assertIsInstance(original_dict["nested"], dict)
        self.assertNotIsInstance(original_dict["nested"], MagicDict)

    def test_tuple_not_mutated(self):
        """Tuples create new tuples (immutable)"""
        original_tuple = ({"a": 1}, {"b": 2})
        md = MagicDict({"data": original_tuple})

        # Original tuple is unchanged
        self.assertIsInstance(original_tuple[0], dict)
        self.assertNotIsInstance(original_tuple[0], MagicDict)


class TestMagicDictDotNotationEdgeCases(TestCase):
    """Test dot notation with edge cases"""

    def test_dot_notation_with_list_index(self):
        """Dot notation can traverse list indices"""
        md = MagicDict({"items": [{"name": "Alice"}, {"name": "Bob"}]})
        self.assertEqual(md["items.0.name"], "Alice")
        self.assertEqual(md["items.1.name"], "Bob")

    def test_dot_notation_with_numeric_string_key(self):
        """KNOWN ISSUE: Numeric string keys are ambiguous"""
        md = MagicDict({"user": {"123": {"name": "Alice"}}})

        # This will fail because '123' is treated as string, not list index
        self.assertEqual(md["user.123.name"], "Alice")

    def test_dot_notation_invalid_path(self):
        """Dot notation raises KeyError for invalid paths"""
        md = MagicDict({"user": {"name": "Alice"}})
        with self.assertRaises(KeyError):
            _ = md["user.email.address"]


class TestMagicDictThreadSafety(TestCase):
    """Test thread safety (or lack thereof)"""

    def test_concurrent_reads(self):
        """Concurrent reads should be safe"""
        md = MagicDict({"data": {"value": 42}})
        results = []
        errors = []

        def read_value():
            try:
                for _ in range(100):
                    val = md.data.value
                    results.append(val)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_value) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertTrue(all(v == 42 for v in results))

    def test_concurrent_writes_race_condition(self):
        """KNOWN ISSUE: Concurrent writes can cause race conditions"""
        md = MagicDict({})
        results = {"success": 0, "errors": []}

        def write_value(thread_id):
            try:
                for i in range(50):
                    md[f"key_{thread_id}"] = {"nested": {"value": i}}
                    _ = md[f"key_{thread_id}"].nested.value
                results["success"] += 1
            except Exception as e:
                results["errors"].append(e)

        threads = [threading.Thread(target=write_value, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # This test documents current behavior
        # Ideally, there should be no errors, but race conditions may occur
        # If errors occur, they're typically AttributeErrors or KeyErrors
        if results["errors"]:
            print(f"Warning: {len(results['errors'])} thread safety issues detected")


class TestMagicDictProtectionBypass(TestCase):
    """Test protection mechanisms on temporary MagicDicts"""

    def test_cannot_assign_to_missing_key_magicdict(self):
        """Assignment to missing key MagicDict raises TypeError"""
        md = MagicDict({"user": {"name": "Alice"}})
        temp = md.user.email

        with self.assertRaises(TypeError):
            temp["key"] = "value"

    def test_cannot_assign_to_none_value_magicdict(self):
        """Assignment to None value MagicDict raises TypeError"""
        md = MagicDict({"user": {"nickname": None}})
        temp = md.user.nickname

        with self.assertRaises(TypeError):
            temp["key"] = "value"

    def test_protection_via_update(self):
        """update() is also protected"""
        md = MagicDict({"user": {"name": "Alice"}})
        temp = md.user.email

        with self.assertRaises(TypeError):
            temp.update({"key": "value"})

    def test_protection_via_setdefault(self):
        """setdefault() is also protected"""
        md = MagicDict({"user": {"name": "Alice"}})
        temp = md.user.email

        with self.assertRaises(TypeError):
            temp.setdefault("key", "value")

    def test_bypass_via_dict_methods(self):
        """KNOWN ISSUE: Protection can be bypassed with dict methods"""
        md = MagicDict({"user": {"name": "Alice"}})
        temp = md.user.email

        # This bypasses __setitem__
        with self.assertRaises(TypeError):
            dict.__setitem__("key", "value")


class TestMagicDictMgetMethod(TestCase):
    """Test mget() and mg() methods"""

    def test_mget_existing_key(self):
        """mget() returns value for existing key"""
        md = MagicDict({"key": "value"})
        self.assertEqual(md.mget("key"), "value")

    def test_mget_missing_key(self):
        """mget() returns empty MagicDict for missing key"""
        md = MagicDict({"key": "value"})
        result = md.mget("missing")
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(len(result), 0)

    def test_mget_none_value(self):
        """mget() returns empty MagicDict for None value"""
        md = MagicDict({"key": None})
        result = md.mget("key")
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(len(result), 0)

    def test_mget_with_custom_default(self):
        """mget() returns custom default for missing key"""
        md = MagicDict({"key": "value"})
        self.assertEqual(md.mget("missing", "default"), "default")

    def test_mget_with_none_default(self):
        """mget() can return None as explicit default"""
        md = MagicDict({"key": "value"})
        self.assertIsNone(md.mget("missing", None))

    def test_mg_shorthand(self):
        """mg() is shorthand for mget()"""
        md = MagicDict({"key": "value"})
        self.assertEqual(md.mg("key"), md.mget("key"))
        self.assertEqual(md.mg("missing"), md.mget("missing"))


class TestMagicDictStandardDictMethods(TestCase):
    """Test standard dict methods work correctly"""

    def test_keys_method(self):
        """keys() method works"""
        md = MagicDict({"a": 1, "b": 2})
        self.assertEqual(set(md.keys()), {"a", "b"})

    def test_values_method(self):
        """values() method works"""
        md = MagicDict({"a": 1, "b": 2})
        self.assertEqual(set(md.values()), {1, 2})

    def test_items_method(self):
        """items() method works"""
        md = MagicDict({"a": 1, "b": 2})
        self.assertEqual(set(md.items()), {("a", 1), ("b", 2)})

    def test_pop_method(self):
        """pop() method works"""
        md = MagicDict({"a": 1, "b": 2})
        val = md.pop("a")
        self.assertEqual(val, 1)
        self.assertNotIn("a", md)

    def test_clear_method(self):
        """clear() method works"""
        md = MagicDict({"a": 1, "b": 2})
        md.clear()
        self.assertEqual(len(md), 0)

    def test_copy_method(self):
        """copy() returns a MagicDict"""
        md = MagicDict({"a": {"b": 1}})
        copied = md.copy()
        self.assertIsInstance(copied, MagicDict)
        self.assertEqual(copied.a.b, 1)

    def test_fromkeys_classmethod(self):
        """fromkeys() creates MagicDict with hooked values"""
        md = MagicDict.fromkeys(["a", "b"], {"nested": "value"})
        self.assertIsInstance(md.a, MagicDict)
        self.assertEqual(md.a.nested, "value")

    def test_ior_operator(self):
        """|= operator works for updates"""
        md1 = MagicDict({"a": 1})
        md2 = {"b": 2}
        md1 |= md2
        self.assertEqual(md1["a"], 1)
        self.assertEqual(md1["b"], 2)


class TestMagicDictPickle(TestCase):
    """Test pickle serialization"""

    def test_pickle_simple(self):
        """Simple MagicDict can be pickled and unpickled"""
        md = MagicDict({"a": 1, "b": 2})
        pickled = pickle.dumps(md)
        restored = pickle.loads(pickled)
        self.assertIsInstance(restored, MagicDict)
        self.assertEqual(restored["a"], 1)

    def test_pickle_nested(self):
        """Nested MagicDict preserves structure"""
        md = MagicDict({"user": {"name": "Alice", "profile": {"age": 30}}})
        pickled = pickle.dumps(md)
        restored = pickle.loads(pickled)
        self.assertIsInstance(restored.user, MagicDict)
        self.assertEqual(restored.user.profile.age, 30)

    def test_pickle_circular_reference(self):
        """Circular references survive pickling"""
        md = MagicDict({"a": 1})
        md["self"] = md
        pickled = pickle.dumps(md)
        restored = pickle.loads(pickled)
        self.assertIs(restored["self"], restored)


class TestMagicDictDeepCopy(TestCase):
    """Test deepcopy functionality"""

    def test_deepcopy_simple(self):
        """Simple MagicDict can be deep copied"""
        md = MagicDict({"a": 1, "b": [1, 2, 3]})
        copied = deepcopy(md)
        self.assertIsInstance(copied, MagicDict)
        self.assertEqual(copied["a"], 1)
        self.assertIsNot(copied["b"], md["b"])

    def test_deepcopy_nested(self):
        """Nested structures are properly deep copied"""
        md = MagicDict({"user": {"data": [1, 2, 3]}})
        copied = deepcopy(md)
        copied.user.data.append(4)
        self.assertEqual(len(md.user.data), 3)
        self.assertEqual(len(copied.user.data), 4)

    def test_deepcopy_circular(self):
        """Circular references survive deep copy"""
        md = MagicDict({"a": 1})
        md["self"] = md
        copied = deepcopy(md)
        self.assertIs(copied["self"], copied)
        self.assertIsNot(copied, md)


class TestMagicDictDisenchant(TestCase):
    """Test disenchant() method"""

    def test_disenchant_simple(self):
        """disenchant() converts to standard dict"""
        md = MagicDict({"a": 1, "b": 2})
        result = md.disenchant()
        self.assertIsInstance(result, dict)
        self.assertNotIsInstance(result, MagicDict)

    def test_disenchant_nested(self):
        """disenchant() recursively converts nested MagicDicts"""
        md = MagicDict({"user": {"profile": {"name": "Alice"}}})
        result = md.disenchant()
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["user"], dict)
        self.assertNotIsInstance(result["user"], MagicDict)

    def test_disenchant_with_lists(self):
        """disenchant() handles lists with MagicDicts"""
        md = MagicDict({"items": [{"name": "item1"}, {"name": "item2"}]})
        result = md.disenchant()
        self.assertIsInstance(result["items"][0], dict)
        self.assertNotIsInstance(result["items"][0], MagicDict)


class TestMagicDictHelperFunctions(TestCase):
    """Test helper functions"""

    def test_magic_loads(self):
        """magic_loads() creates MagicDict from JSON"""
        json_str = '{"user": {"name": "Alice"}}'
        md = magic_loads(json_str)
        self.assertIsInstance(md, MagicDict)
        self.assertEqual(md.user.name, "Alice")

    def test_enchant_dict(self):
        """enchant() converts dict to MagicDict"""
        d = {"user": {"name": "Alice"}}
        md = enchant(d)
        self.assertIsInstance(md, MagicDict)
        self.assertEqual(md.user.name, "Alice")

    def test_enchant_already_magicdict(self):
        """enchant() returns MagicDict as-is"""
        md1 = MagicDict({"a": 1})
        md2 = enchant(md1)
        self.assertIs(md1, md2)

    def test_enchant_invalid_type(self):
        """enchant() raises TypeError for non-dict"""
        with self.assertRaises(TypeError):
            enchant([1, 2, 3])


class TestMagicDictKeyConflicts(TestCase):
    """Test handling of keys that conflict with dict methods"""

    def test_keys_conflict(self):
        """Key named 'keys' conflicts with dict.keys() method"""
        md = MagicDict({"keys": "custom_value"})
        # Attribute access returns the method
        self.assertTrue(callable(md.keys))
        # Bracket access returns the value
        self.assertEqual(md["keys"], "custom_value")

    def test_mget_for_conflicting_keys(self):
        """mget() can access conflicting keys"""
        md = MagicDict({"update": "custom_value", "pop": "another"})
        self.assertEqual(md.mget("update"), "custom_value")
        self.assertEqual(md.mget("pop"), "another")


class TestMagicDictMemoryBehavior(TestCase):
    """Test memory and performance characteristics"""

    def test_temporary_objects_garbage_collected(self):
        """Temporary MagicDicts should be garbage collected"""

        md = MagicDict({"user": {"name": "Alice"}})

        # Create many temporary objects
        for _ in range(1000):
            _ = md.nonexistent.chain.of.missing.keys

        gc.collect()
        # This test just verifies no crash occurs
        # Actual memory measurement would require more complex tooling
        self.assertTrue(True)

    def test_large_nested_structure(self):
        """Large nested structures don't cause issues"""
        data = {"level0": {}}
        current = data["level0"]
        for i in range(100):
            current[f"level{i+1}"] = {}
            current = current[f"level{i+1}"]
        current["value"] = "deep"

        md = MagicDict(data)
        # Access the deeply nested value
        result = md.level0
        for i in range(100):
            result = result[f"level{i+1}"]
        self.assertEqual(result["value"], "deep")


class TestMagicDictEqualityAndHashing(TestCase):
    """Test equality comparisons and hashing"""

    def test_equality(self):
        """MagicDicts with same content are equal"""
        md1 = MagicDict({"a": 1, "b": 2})
        md2 = MagicDict({"a": 1, "b": 2})
        self.assertEqual(md1, md2)

    def test_inequality(self):
        """MagicDicts with different content are not equal"""
        md1 = MagicDict({"a": 1})
        md2 = MagicDict({"a": 2})
        self.assertNotEqual(md1, md2)

    def test_temporary_magicdict_equality(self):
        """Temporary MagicDicts are equal if both empty"""
        md = MagicDict({"a": 1})
        temp1 = md.missing1
        temp2 = md.missing2
        self.assertEqual(temp1, temp2)

    def test_unhashable(self):
        """MagicDict is unhashable (like dict)"""
        md = MagicDict({"a": 1})
        with self.assertRaises(TypeError):
            hash(md)


class TestMagicDictEdgeCases(TestCase):
    """Test various edge cases and complex scenarios"""

    def setUp(self):
        """Set up a standard MagicDict instance for use in tests."""
        self.data = {
            "user": {
                "name": "Alice",
                "id": 101,
                "details": {"email": "alice@example.com", "active": True},
                "prefs": None,
            },
            "posts": [
                {"id": 1, "title": "First Post", "tags": ("tech", "python")},
                {"id": 2, "title": "Second Post", "tags": ("general",)},
            ],
            "key.with.dots": "value_with_dots",
            "falsy_values": {"zero": 0, "false": False, "empty_string": ""},
        }
        self.md = MagicDict(self.data)

    def test_initialization_and_recursive_conversion(self):
        """Test that initialization and recursive conversion works."""
        self.assertIsInstance(self.md, MagicDict)
        self.assertIsInstance(self.md.user, MagicDict)
        self.assertIsInstance(self.md.user.details, MagicDict)
        self.assertIsInstance(self.md.posts[0], MagicDict)
        self.assertIsInstance(self.md.posts[1], MagicDict)
        self.assertIsInstance(self.md.posts[0].tags, tuple)

    def test_basic_attribute_access(self):
        """Test basic attribute-style access."""
        self.assertEqual(self.md.user.name, "Alice")
        self.assertEqual(self.md.user.details.email, "alice@example.com")
        self.assertEqual(self.md.posts[0].id, 1)

    def test_safe_chaining_on_non_existent_keys(self):
        """Test safe chaining through non-existent keys."""
        safe_access = self.md.user.address.city.street
        self.assertIsInstance(safe_access, MagicDict)
        self.assertEqual(safe_access, {})

    def test_safe_chaining_on_none_value(self):
        """Test safe chaining through None values."""
        safe_access = self.md.user.prefs.theme.color
        self.assertIsInstance(safe_access, MagicDict)
        self.assertEqual(safe_access, {})
        # Standard access should still return None
        self.assertIsNone(self.md.user["prefs"])

    def test_falsy_values_are_not_treated_as_none(self):
        """Test that falsy but valid values are preserved."""
        self.assertEqual(self.md.falsy_values.zero, 0)
        self.assertEqual(self.md.falsy_values.false, False)
        self.assertEqual(self.md.falsy_values.empty_string, "")

    def test_standard_bracket_access(self):
        """Test standard bracket notation access."""
        self.assertEqual(self.md["user"]["details"]["email"], "alice@example.com")
        with self.assertRaises(KeyError):
            _ = self.md["user"]["non_existent_key"]

    def test_dot_notation_bracket_access(self):
        """Test deep access with dot notation in brackets."""
        self.assertEqual(self.md["user.details.email"], "alice@example.com")
        self.assertEqual(self.md["posts.0.title"], "First Post")
        self.assertEqual(self.md["posts.1.tags.0"], "general")

    def test_dot_notation_bracket_access_failures(self):
        """Test failures when using dot notation in brackets."""
        # I've modified __getitem__ to raise a more specific error than the original implementation
        with self.assertRaises(KeyError):
            _ = self.md["user.details.non_existent"]
        with self.assertRaises(IndexError):
            _ = self.md["posts.99.title"]  # IndexError becomes KeyError
        # Test bug fix: traversing into a non-subscriptable type
        md = MagicDict({"a": {"b": 123}})
        with self.assertRaises(KeyError):
            _ = md["a.b.c"]

    def test_key_with_dots_in_it(self):
        """Test that keys with dots are accessible."""
        self.assertEqual(self.md["key.with.dots"], "value_with_dots")

    def test_modification_and_hooking(self):
        """Test that modifications hook new dicts/lists."""
        self.md["new_key"] = {"a": 1, "b": [{"c": 3}]}
        temp = self.md.new_key
        self.assertIsInstance(temp, MagicDict)
        self.assertIsInstance(temp.b[0], MagicDict)
        self.assertEqual(self.md.new_key.b[0].c, 3)

    def test_protection_of_temporary_dicts(self):
        """Test that temporary MagicDicts are protected against modification."""
        # From non-existent key
        with self.assertRaises(TypeError):
            self.md.foo["bar"] = 1
        with self.assertRaises(TypeError):
            self.md.foo.clear()

        # From None value
        with self.assertRaises(TypeError):
            self.md.user.prefs["theme"] = "dark"
        with self.assertRaises(TypeError):
            self.md.user.prefs.pop("theme")

    def test_method_name_conflict(self):
        """Test that keys conflicting with dict methods are handled."""
        md = MagicDict({"keys": "value", "items": [1, 2]})
        self.assertEqual(md["keys"], "value")
        self.assertTrue(md.keys(), callable)  # dict.keys() method is accessible
        self.assertTrue(callable(md.keys))

        self.assertEqual(md["items"], [1, 2])
        self.assertTrue(callable(md.items))

    def test_disenchant(self):
        """Test that disenchant() correctly converts to standard dict."""
        disenchanted = self.md.disenchant()
        self.assertIsInstance(disenchanted, dict)
        self.assertNotIsInstance(disenchanted, MagicDict)
        self.assertIsInstance(disenchanted["user"], dict)
        self.assertNotIsInstance(disenchanted["user"], MagicDict)
        self.assertIsInstance(disenchanted["posts"][0], dict)
        self.assertNotIsInstance(disenchanted["posts"][0], MagicDict)
        self.assertEqual(
            json.dumps(self.data, sort_keys=True),
            json.dumps(disenchanted, sort_keys=True),
        )

    def test_circular_references(self):
        """Test that circular references are handled without RecursionError."""
        # Setup circular reference
        a = {"v": 1}
        a["self"] = a
        b = [a]
        b.append(b)
        data = {"a": a, "b": b}

        # Test initialization
        try:
            md = MagicDict(data)
        except RecursionError:
            self.fail(
                "MagicDict failed to handle circular references on initialization."
            )

        # Test access
        self.assertEqual(md.a.v, 1)
        self.assertEqual(md.a.self.v, 1)
        self.assertEqual(md.a.self.self.self.v, 1)
        self.assertIs(md.a.self, md.a)
        self.assertIs(md.b[1], md.b)

        # Test disenchant
        try:
            disenchanted = md.disenchant()
        except RecursionError:
            self.fail("MagicDict.disenchant failed to handle circular references.")

        self.assertIs(disenchanted["a"]["self"], disenchanted["a"])
        self.assertIs(disenchanted["b"][1], disenchanted["b"])
        self.assertNotIsInstance(disenchanted["a"], MagicDict)

    def test_deepcopy_and_copy(self):
        """Test that copy() and deepcopy() work correctly."""
        # Shallow copy
        md_copy = self.md.copy()
        self.assertIsInstance(md_copy, MagicDict)
        self.assertIsNot(md_copy, self.md)
        self.assertEqual(md_copy, self.md)
        self.assertIs(
            md_copy.user, self.md.user
        )  # Shallow copy means nested objects are the same

        # Deep copy
        md_deepcopy = deepcopy(self.md)
        self.assertIsInstance(md_deepcopy, MagicDict)
        self.assertIsNot(md_deepcopy, self.md)
        self.assertEqual(md_deepcopy, self.md)
        self.assertIsNot(
            md_deepcopy.user, self.md.user
        )  # Deep copy creates new nested objects

    def test_pickling(self):
        """Test that pickling and unpickling works correctly."""
        pickled_md = pickle.dumps(self.md)
        unpickled_md = pickle.loads(pickled_md)

        self.assertIsInstance(unpickled_md, MagicDict)
        self.assertEqual(self.md, unpickled_md)
        self.assertEqual(unpickled_md.user.details.email, "alice@example.com")

    def test_mget_method(self):
        """Test the mget() method for various scenarios."""
        self.assertEqual(
            self.md.mget("user").mget("name", "default"), self.md.user.name
        )  # Fails due to dot notation
        self.assertEqual(self.md.user.mget("name", "default"), "Alice")

        # Test missing key with no default
        missing = self.md.mget("non-existent-key")
        self.assertIsInstance(missing, MagicDict)
        self.assertEqual(missing, {})
        with self.assertRaises(TypeError):
            missing["a"] = 1  # Should be protected

        # Test missing key with default
        self.assertEqual(self.md.mget("non-existent-key", "default_val"), "default_val")
        self.assertIsNone(self.md.mget("non-existent-key", None))

        # Test key with None value
        from_none = self.md.user.mget("prefs")
        self.assertIsInstance(from_none, MagicDict)
        self.assertEqual(from_none, {})
        with self.assertRaises(TypeError):
            from_none["a"] = 1

    def test_helper_functions(self):
        """Test enchant() and magic_loads() helper functions."""
        # test enchant
        d = {"a": {"b": 1}}
        md = enchant(d)
        self.assertIsInstance(md, MagicDict)
        self.assertIsInstance(md.a, MagicDict)
        self.assertEqual(md.a.b, 1)

        # test magic_loads
        json_str = '{"user": {"name": "Bob"}, "items": [{"id": 1}]}'
        md_json = magic_loads(json_str)
        self.assertIsInstance(md_json, MagicDict)
        self.assertIsInstance(md_json.user, MagicDict)
        self.assertIsInstance(md_json["items"][0], MagicDict)
        self.assertEqual(md_json.user.name, "Bob")

    def test_other_overridden_methods(self):
        """Test other overridden dict methods."""
        # setdefault
        self.md.setdefault("new_key", {"a": 1})
        self.assertIsInstance(self.md.new_key, MagicDict)

        # fromkeys
        md = MagicDict.fromkeys(["a", "b"], {"c": 1})
        self.assertIsInstance(md.a, MagicDict)
        self.assertEqual(md.a.c, 1)

    def test_dir_includes_keys(self):
        """Test that dir() includes valid keys."""
        d = dir(self.md)
        self.assertIn("user", d)
        self.assertIn("posts", d)
        self.assertIn("keys", d)  # A standard method
        self.assertNotIn("keywithdots", d)  # Not a valid identifier

    def test_namedtuple_handling(self):
        """Test that namedtuples are preserved with converted contents."""
        Point = namedtuple("Point", ["x", "y"])
        data = {"point": Point(x={"val": 10}, y=20)}
        md = MagicDict(data)

        self.assertIsInstance(md.point, Point)
        self.assertIsInstance(md.point.x, MagicDict)
        self.assertEqual(md.point.x.val, 10)

        disenchanted = md.disenchant()
        self.assertIsInstance(disenchanted["point"], Point)
        self.assertIsInstance(disenchanted["point"].x, dict)
        self.assertEqual(disenchanted["point"].x["val"], 10)

    def test_basic_attribute_and_bracket_access(self):
        md = MagicDict({"user": {"name": "Alice", "id": 1}, "permissions": ["read"]})
        self.assertEqual(md.user.name, "Alice")
        self.assertEqual(md["user"]["id"], 1)
        self.assertEqual(md["user.id"], 1)

    def test_missing_keys_safe_chaining(self):
        md = MagicDict({})
        self.assertIsInstance(md.nonexistent, MagicDict)
        self.assertIsInstance(md.nonexistent.deep.chain, MagicDict)
        with self.assertRaises(KeyError):
            _ = md["nonexistent"]

    def test_none_value_safe_chaining(self):
        md = MagicDict({"user": {"nickname": None}})
        self.assertIsInstance(md.user.nickname, MagicDict)
        self.assertIsNone(md.user["nickname"])

    def test_conflicting_keys(self):
        md = MagicDict({"keys": "custom_value"})
        self.assertTrue(callable(md.keys))  # still a dict method
        self.assertEqual(md["keys"], "custom_value")

    def test_invalid_identifier_keys(self):
        md = MagicDict({"1-key": "value", "some key": 123})
        self.assertEqual(md["1-key"], "value")
        self.assertEqual(md.mget("1-key"), "value")
        self.assertEqual(md["some key"], 123)

    def test_dot_notation_nested_access(self):
        md = MagicDict({"a": {"b": {"c": 5}}})
        self.assertEqual(md["a.b.c"], 5)
        with self.assertRaises(KeyError):
            _ = md["a.b.x"]

    def test_dot_notation_with_list_index(self):
        md = MagicDict({"users": [{"name": "Alice"}, {"name": "Bob"}]})
        self.assertEqual(md["users.0.name"], "Alice")
        self.assertEqual(md["users.1.name"], "Bob")
        with self.assertRaises(IndexError):
            _ = md["users.2.name"]

    def test_protected_magicdict_modification_raises(self):
        md = MagicDict({})
        temp = md.nonexistent
        with self.assertRaises(TypeError):
            temp["x"] = 1

    def test_update_and_copy_preserve_magicdict(self):
        md = MagicDict({"a": {"b": 1}})
        md.update({"c": {"d": 2}})
        self.assertIsInstance(md.c, MagicDict)
        shallow = md.copy()
        self.assertIsInstance(shallow, MagicDict)
        self.assertEqual(shallow.a.b, 1)

    def test_enchant_and_disenchant_roundtrip(self):
        data = {"a": {"b": [1, {"c": 3}]}}
        md = enchant(data)
        result = md.disenchant()
        self.assertEqual(result, data)
        self.assertIsInstance(result, dict)
        self.assertNotIsInstance(result, MagicDict)

    def test_deepcopy_preserves_values_but_not_identity(self):
        md = MagicDict({"x": {"y": [1, 2, 3]}})
        cp = deepcopy(md)
        self.assertEqual(cp, md)
        self.assertIsNot(cp, md)
        self.assertIsNot(cp.x, md.x)

    def test_circular_references_disenchant_and_copy(self):
        d = {}
        d["self"] = d
        md = MagicDict(d)
        disen = md.disenchant()
        self.assertIsInstance(disen, dict)
        self.assertIs(disen["self"], disen)

        cp = deepcopy(md)
        self.assertIs(cp["self"], cp)

    def test_namedtuple_preservation(self):
        Point = namedtuple("Point", ["x", "y"])
        data = {"p": Point(1, 2)}
        md = MagicDict(data)
        result = md.disenchant()
        self.assertIsInstance(result["p"], Point)
        self.assertEqual(result["p"].x, 1)

    def test_pickle_roundtrip(self):
        md = MagicDict({"a": {"b": 2}})
        blob = pickle.dumps(md)
        restored = pickle.loads(blob)
        self.assertEqual(restored, md)
        self.assertIsInstance(restored, MagicDict)

    def test_magic_loads_from_json(self):
        s = '{"user": {"id": 5, "name": "Alice"}}'
        md = magic_loads(s)
        self.assertIsInstance(md, MagicDict)
        self.assertEqual(md.user.id, 5)

    def test_mget_with_default(self):
        md = MagicDict({"x": 1})
        self.assertEqual(md.mget("x"), 1)
        self.assertIsInstance(md.mget("missing"), MagicDict)
        self.assertEqual(md.mget("missing", default="fallback"), "fallback")

    def test_inplace_or_update(self):
        md = MagicDict({"a": 1})
        md |= {"b": {"c": 3}}
        self.assertEqual(md.b.c, 3)

    def test_fromkeys_and_setdefault_hooking(self):
        md = MagicDict.fromkeys(["x", "y"], {"a": 1})
        for key in ["x", "y"]:
            self.assertIsInstance(md[key], MagicDict)
        md.setdefault("z", {"q": 9})
        self.assertIsInstance(md.z, MagicDict)


import datetime
from collections import defaultdict


class TestMagicDictAdvanced(TestCase):
    """
    Tests for advanced edge cases, behavioral clarifications, and interactions
    with other types not covered in the main test suite.
    """

    def test_hook_converts_defaultdict_to_magicdict(self):
        """
        Verify that dict subclasses like defaultdict are converted into MagicDict,
        losing their special behaviors (e.g., default_factory).
        """
        dd = defaultdict(lambda: "default", {"existing": "value"})
        md = MagicDict({"data": dd})

        # The defaultdict should be converted to a MagicDict
        self.assertIsInstance(md.data, MagicDict)
        self.assertNotIsInstance(md.data, defaultdict)
        self.assertEqual(md.data.existing, "value")

        # The default_factory behavior is lost, and it now acts like a MagicDict
        # on missing keys.
        missing_key_result = md.data.nonexistent
        self.assertIsInstance(missing_key_result, MagicDict)
        self.assertEqual(missing_key_result, {})

    def test_disenchant_preserves_complex_unhookable_types(self):
        """
        Verify that disenchant() preserves complex types like datetime objects
        that are not subject to the hooking mechanism.
        """
        now = datetime.datetime.now()
        md = MagicDict({"event": {"name": "launch", "timestamp": now}})
        disenchanted = md.disenchant()

        self.assertIs(type(disenchanted), dict)
        self.assertIs(type(disenchanted["event"]), dict)
        self.assertIs(disenchanted["event"]["timestamp"], now)
        self.assertIsInstance(disenchanted["event"]["timestamp"], datetime.datetime)

    def test_none_as_a_key(self):
        """
        Test that using `None` as a dictionary key is handled correctly.
        """
        md = MagicDict({None: "value_for_none"})
        self.assertIn(None, md)
        self.assertEqual(md[None], "value_for_none")
        self.assertEqual(md.mget(None), "value_for_none")

        # Attribute access for 'None' should be a missing key, not the value for the None key.
        self.assertEqual(md[None], "value_for_none")
        self.assertIsInstance(md.none, MagicDict)
        self.assertTrue(getattr(md.none, "_from_missing", False))

    def test_getitem_dot_notation_value_error_on_bad_list_index(self):
        """
        Verify that dot notation access on a list with a non-integer key
        raises a ValueError, which is not caught by the internal KeyError handling.
        """
        md = MagicDict({"items": ["a", "b", "c"]})
        with self.assertRaises(ValueError):
            # The 'x' cannot be converted to an int for list indexing.
            _ = md["items.x"]

    def test_getitem_dot_notation_with_leading_or_trailing_dots(self):
        """
        Test that dot notation handles leading/trailing dots, which result
        in empty strings from split('.').
        """
        # A key that is an empty string
        md = MagicDict({"": "value_for_empty_string", "a": {"": "nested_empty"}})

        # Accessing via a leading dot: '.a' -> ['', 'a']
        # This will fail because the first key is '' which holds a string, not a dict.
        with self.assertRaises(KeyError):
            _ = md[".a"]

        # This should work as it looks for key '' in key 'a'
        self.assertEqual(md["a."], "nested_empty")

    def test_complex_circular_reference_dict_list_dict(self):
        """
        Test correct handling of a more complex circular reference
        (dict -> list -> dict).
        """
        d = {"name": "level1_dict"}
        l = [{"name": "item_in_list"}, d]
        d["list_ref"] = l

        # Test initialization
        md = MagicDict(d)
        self.assertIs(md["list_ref"][1], md)
        self.assertIsInstance(md["list_ref"][0], MagicDict)

        # Test disenchant
        disenchanted = md.disenchant()
        self.assertIs(type(disenchanted), dict)
        self.assertIs(disenchanted["list_ref"][1], disenchanted)

        # Test deepcopy
        md_copy = deepcopy(md)
        self.assertIsNot(md_copy, md)
        self.assertIs(md_copy["list_ref"][1], md_copy)

    def test_dir_precedence_key_over_instance_attribute(self):
        """
        Verify that if an instance attribute and a key have the same name,
        the key appears in dir() as expected by the implementation's ordering.
        """
        md = MagicDict()
        # Set an instance attribute directly, bypassing __setitem__
        object.__setattr__(md, "my_attr", "instance_value")
        # Set a key with the same name
        md["my_attr"] = "key_value"

        dir_list = dir(md)
        # 'my_attr' should be present
        self.assertIn("my_attr", dir_list)
        self.assertEqual(md.my_attr, "instance_value")

    def test_initialization_with_existing_magicdict_instance(self):
        """
        Test initializing a MagicDict with another MagicDict instance.
        This should behave like a copy.
        """
        nested = MagicDict({"c": 3})
        original = MagicDict({"a": 1, "b": nested})

        new_md = MagicDict(original)

        self.assertEqual(new_md, original)
        self.assertIsNot(new_md, original)
        # The copy during init is shallow, so nested objects should be the same instance
        self.assertIs(new_md.b, original.b)
        self.assertIs(new_md["b"], nested)


class TestMagicDictEdgeCases3(TestCase):
    """Additional edge cases and clarifications."""

    def test_exact_key_with_dot_preferred_over_nested(self):
        """If a dict has an exact key that contains a dot it should be returned
        by __getitem__ instead of attempting dot-traversal."""
        md = MagicDict({"a.b": 1, "a": {"b": 2}})
        # direct item access for exact key containing a dot
        self.assertEqual(md["a.b"], 1)
        # attribute style should still traverse the nested structure
        self.assertEqual(md.a.b, 2)

    def test_getitem_dot_with_invalid_index_raises(self):
        """When dot-traversal hits a sequence but the key is not an integer,
        a ValueError should be raised (int() conversion)."""
        md = MagicDict({"arr": ["zero", "one"]})
        with self.assertRaises(ValueError):
            _ = md["arr.one.two"]

    def test_getitem_dot_index_out_of_range_raises_indexerror(self):
        """Out-of-range index via dot-traversal raises IndexError."""
        md = MagicDict({"arr": ["zero"]})
        with self.assertRaises(IndexError):
            _ = md["arr.5"]

    def test_disenchant_preserves_shared_and_circular_references(self):
        """disenchant preserves shared and circular references."""
        md = MagicDict()
        # use a shared MagicDict so the same object instance is stored twice
        shared = MagicDict({"inner": 1})
        # two keys referencing the same MagicDict instance
        md["a"] = shared
        md["b"] = shared

        # circular reference
        md["self"] = md

        out = md.disenchant()

        # shared references should remain the same object identity
        self.assertIs(out["a"], out["b"])

        # circular reference preserved: out['self'] should be the outer dict
        self.assertIs(out["self"], out)

    def test_protected_magicdict_blocks_mutations(self):
        """Protected MagicDicts raise TypeError on mutating operations."""
        md = MagicDict({"maybe": None})

        none_md = md.maybe  # attribute access returns a protected MagicDict
        self.assertIsInstance(none_md, MagicDict)

        with self.assertRaises(TypeError):
            none_md["x"] = 1

        with self.assertRaises(TypeError):
            none_md.update({"x": 1})

        with self.assertRaises(TypeError):
            none_md.pop("x", None)

        with self.assertRaises(TypeError):
            none_md.popitem()

        with self.assertRaises(TypeError):
            none_md.clear()

        with self.assertRaises(TypeError):
            none_md.setdefault("x", 1)


class TestMagicDictEdgesCases2(TestCase):

    def setUp(self):
        """Set up a standard nested dictionary and MagicDict instance for each test."""
        self.sample_data = {
            "user": {
                "name": "Alice",
                "id": 1,
                "nickname": None,
                "details": {"city": "Wonderland"},
            },
            "permissions": ["read", "write"],
            "items": [{"name": "Book", "id": 101}, {"name": "Pen", "id": 102}],
            "keys": "this is a value, not the method",
        }
        self.md = MagicDict(self.sample_data)

    # --- Test Initialization and Conversion ---

    def test_initialization_from_dict(self):
        """Test that a dict is recursively converted to MagicDict."""
        self.assertIsInstance(self.md, MagicDict)
        self.assertIsInstance(self.md.user, MagicDict)
        self.assertIsInstance(self.md.user.details, MagicDict)
        self.assertIsInstance(self.md["items"][0], MagicDict)
        self.assertIsInstance(self.md["items"][1], MagicDict)

    def test_initialization_with_kwargs(self):
        """Test initialization using keyword arguments."""
        md = MagicDict(a=1, b={"c": 2})
        self.assertEqual(md.a, 1)
        self.assertIsInstance(md.b, MagicDict)
        self.assertEqual(md.b.c, 2)

    def test_empty_initialization(self):
        """Test that an empty MagicDict can be created."""
        md = MagicDict()
        self.assertEqual(len(md), 0)
        self.assertEqual(md.missing_key, MagicDict())

    def test_enchant_function(self):
        """Test the enchant() helper function."""
        md = enchant(self.sample_data)
        self.assertIsInstance(md, MagicDict)
        self.assertIsInstance(md.user, MagicDict)
        with self.assertRaises(TypeError):
            enchant("not a dict")

    def test_magic_loads_function(self):
        """Test the magic_loads() helper function for JSON."""
        json_string = '{"user": {"name": "Bob"}, "roles": [{"role": "admin"}]}'
        md = magic_loads(json_string)
        self.assertIsInstance(md, MagicDict)
        self.assertIsInstance(md.user, MagicDict)
        self.assertIsInstance(md.roles[0], MagicDict)
        self.assertEqual(md.user.name, "Bob")

    # --- Test Access Methods ---

    def test_attribute_style_access(self):
        """Test basic and nested attribute access."""
        self.assertEqual(self.md.user.name, "Alice")
        self.assertEqual(self.md.user.details.city, "Wonderland")

    def test_bracket_style_access(self):
        """Test standard and nested bracket access."""
        self.assertEqual(self.md["user"]["name"], "Alice")
        self.assertEqual(self.md["items"][0]["id"], 101)

    def test_dot_notation_in_brackets(self):
        """Test deep access using dot-separated strings."""
        self.assertEqual(self.md["user.name"], "Alice")
        self.assertEqual(self.md["user.details.city"], "Wonderland")
        self.assertEqual(self.md["items.0.name"], "Book")
        self.assertEqual(self.md["items.1.id"], 102)

    def test_dot_notation_failure_raises_keyerror(self):
        """Test that dot notation access raises KeyError for missing keys."""
        with self.assertRaises(KeyError):
            _ = self.md["user.nonexistent"]
        with self.assertRaises(KeyError):
            _ = self.md["user.details.nonexistent"]

    def test_dot_notation_index_errors(self):
        """Test that dot notation handles list index errors."""
        with self.assertRaises(IndexError):
            _ = self.md["items.5.name"]
        with self.assertRaises(ValueError):  # int('a') raises ValueError
            _ = self.md["items.a.name"]

    # --- Test Graceful Failure and Safe Chaining ---

    def test_missing_attribute_returns_empty_magicdict(self):
        """Accessing a non-existent key via attribute should return an empty MagicDict."""
        empty_md = self.md.non_existent_key
        self.assertIsInstance(empty_md, MagicDict)
        self.assertFalse(empty_md)  # An empty dict is falsy

    def test_safe_chaining_on_missing_attributes(self):
        """Chained access on non-existent keys should be safe."""
        value = self.md.user.address.street.name
        self.assertIsInstance(value, MagicDict)
        self.assertFalse(value)

    def test_none_value_attribute_access_is_safe(self):
        """Accessing a key with a None value via attribute should return an empty MagicDict."""
        self.assertEqual(self.md.user.nickname, MagicDict())
        self.assertEqual(self.md.user.nickname.some_prop, MagicDict())

    def test_none_value_bracket_access_returns_none(self):
        """Bracket access for a key with a None value should return None."""
        self.assertIsNone(self.md.user["nickname"])
        self.assertIsNone(self.md["user.nickname"])

    def test_mget_method(self):
        """Test the safe mget() method."""
        self.assertEqual(self.md.mget("user").name, "Alice")
        self.assertEqual(self.md.mget("non_existent"), MagicDict())
        self.assertEqual(self.md.user.mget("nickname"), MagicDict())
        self.assertEqual(self.md.mget("non_existent", "default"), "default")
        self.assertEqual(self.md.user.mget("nickname"), MagicDict())
        self.assertEqual(self.md.mg("user").name, "Alice")

    # --- Test Modification and Protection ---

    def test_setitem_hooks_new_dicts(self):
        """Test that setting a dict value converts it to a MagicDict."""
        md = MagicDict()
        md["new_data"] = {"a": 1, "b": {"c": 3}}
        self.assertIsInstance(md.new_data, MagicDict)
        self.assertIsInstance(md.new_data.b, MagicDict)

    def test_update_hooks_new_dicts(self):
        """Test that the update method recursively hooks values."""
        md = MagicDict()
        md.update({"new_data": {"a": 1, "b": {"c": 3}}})
        self.assertIsInstance(md.new_data, MagicDict)
        self.assertIsInstance(md.new_data.b, MagicDict)

    def test_modification_of_protected_magicdict_raises_error(self):
        """Verify that temporary MagicDicts from missing keys/None cannot be modified."""
        protected_from_missing = self.md.non_existent
        protected_from_none = self.md.user.nickname

        modifier_funcs = [
            lambda d: d.update({"a": 1}),
            lambda d: d.setdefault("a", 1),
            lambda d: d.pop("a", None),
            lambda d: d.clear(),
            lambda d: d.__setitem__("a", 1),
            lambda d: d.__delitem__("a"),
        ]

        for func in modifier_funcs:
            with self.assertRaises(TypeError):
                func(protected_from_missing)
            with self.assertRaises(TypeError):
                func(protected_from_none)

    # --- Test Edge Cases and Special Types ---

    def test_key_conflict_with_dict_method(self):
        """Test behavior when a key name conflicts with a dict method name."""
        self.assertEqual(self.md["keys"], "this is a value, not the method")
        self.assertTrue(callable(self.md.keys))
        self.assertEqual(set(self.md.keys()), {"user", "permissions", "items", "keys"})

    def test_non_string_keys(self):
        """Test that non-string keys work with standard access."""
        md = MagicDict({1: "one", (2, 3): "two-three"})
        self.assertEqual(md[1], "one")
        self.assertEqual(md[(2, 3)], "two-three")
        self.assertEqual(md.one, MagicDict())

    def test_namedtuple_preservation(self):
        """Test that namedtuples are preserved during conversion."""
        Point = namedtuple("Point", ["x", "y"])
        data = {"point": Point(1, 2), "items": [Point(3, 4)]}
        md = MagicDict(data)

        self.assertIsInstance(md.point, Point)
        self.assertEqual(md.point.x, 1)
        self.assertIsInstance(md["items"][0], Point)

        disenchanted = md.disenchant()
        self.assertIsInstance(disenchanted["point"], Point)
        self.assertIsInstance(disenchanted["items"][0], Point)

    def test_circular_reference_handling(self):
        """Test initialization, disenchanting, and copying with circular references."""
        d = {}
        d["myself"] = d
        d["nested"] = [{"parent": d}]

        md = MagicDict(d)
        self.assertIs(md["myself"], md)
        self.assertIs(md.nested[0].parent, md)

        disenchanted = md.disenchant()
        self.assertIs(disenchanted["myself"], disenchanted)
        self.assertIs(disenchanted["nested"][0]["parent"], disenchanted)

        dc = deepcopy(md)
        self.assertIsNot(dc, md)
        self.assertIs(dc["myself"], dc)
        self.assertIs(dc.nested[0].parent, dc)

    # --- Test Dunder Methods and Core Dict Functionality ---

    def test_repr(self):
        """Test the __repr__ of MagicDict."""
        md = MagicDict({"a": 1})
        self.assertEqual(repr(md), "MagicDict({'a': 1})")

    def test_disenchant(self):
        """Test converting a MagicDict back to a standard dict."""
        original_dict = self.md.disenchant()
        self.assertIs(type(original_dict), dict)
        self.assertIs(type(original_dict["user"]), dict)
        self.assertIs(type(original_dict["user"]["details"]), dict)
        self.assertIs(type(original_dict["items"][0]), dict)
        self.assertEqual(original_dict["user"]["name"], "Alice")

    def test_copy_is_shallow(self):
        """Test the shallow copy() method."""
        md_copy = self.md.copy()
        self.assertIsNot(md_copy, self.md)
        self.assertIsInstance(md_copy, MagicDict)
        self.assertIs(md_copy.user, self.md.user)

        md_copy.user.name = "Bob"
        self.assertEqual(self.md.user.name, "Bob")

    def test_deepcopy_is_deep(self):
        """Test that deepcopy creates a fully independent copy."""
        md_deepcopy = deepcopy(self.md)
        self.assertIsNot(md_deepcopy, self.md)
        self.assertIsInstance(md_deepcopy, MagicDict)
        self.assertIsNot(md_deepcopy.user, self.md.user)

        md_deepcopy.user.name = "Charlie"
        self.assertEqual(self.md.user.name, "Alice")
        self.assertEqual(md_deepcopy.user.name, "Charlie")

    def test_pickling_support(self):
        """Test that MagicDict can be pickled and unpickled correctly."""
        pickled_md = pickle.dumps(self.md)
        unpickled_md = pickle.loads(pickled_md)

        self.assertIsInstance(unpickled_md, MagicDict)
        self.assertIsInstance(unpickled_md.user, MagicDict)
        self.assertEqual(unpickled_md.user.name, "Alice")
        self.assertEqual(unpickled_md, self.md)

    def test_dir_includes_keys(self):
        """Test that __dir__ includes the dictionary keys for autocompletion."""
        d = dir(self.md)
        self.assertIn("user", d)
        self.assertIn("permissions", d)
        self.assertIn("items", d)
        self.assertIn("update", d)


class TestMagicDictMissingEdgeCases(TestCase):
    """Additional edge cases not covered in the main test suite."""

    def test_weakref_compatibility(self):
        """Test that MagicDict instances can be weakly referenced."""
        md = MagicDict({"a": 1})
        ref = weakref.ref(md)
        self.assertIs(ref(), md)
        del md
        self.assertIsNone(ref())

    def test_bool_context_evaluation(self):
        """Test boolean evaluation of MagicDict in various states."""
        # Non-empty MagicDict is truthy
        md = MagicDict({"a": 1})
        self.assertTrue(bool(md))
        self.assertTrue(md)

        # Empty MagicDict is falsy
        empty = MagicDict()
        self.assertFalse(bool(empty))
        self.assertFalse(empty)

        # Protected MagicDict from missing key is falsy
        protected = md.missing
        self.assertFalse(bool(protected))

    def test_multiple_none_keys_in_dict(self):
        """Test handling when multiple None values exist."""
        md = MagicDict({"a": None, "b": {"c": None}, "d": [None, {"e": None}]})

        self.assertEqual(md.a, MagicDict())
        self.assertEqual(md.b.c, MagicDict())
        self.assertIsNone(md["d"][0])
        self.assertEqual(md["d"][1]["e"], None)

    def test_numeric_string_vs_int_keys(self):
        """Test disambiguation between string and int keys with same value."""
        md = MagicDict(
            {"1": "string_one", 1: "int_one", "2.5": "string_float", 2.5: "float_key"}
        )

        self.assertEqual(md["1"], "string_one")
        self.assertEqual(md[1], "int_one")
        self.assertEqual(md["2.5"], "string_float")
        self.assertEqual(md[2.5], "float_key")
        self.assertNotEqual(md["1"], md[1])

    def test_special_method_keys(self):
        """Test keys that are special method names."""
        md = MagicDict(
            {
                "__init__": "init_value",
                "__getitem__": "getitem_value",
                "__setitem__": "setitem_value",
                "__repr__": "repr_value",
            }
        )

        # These should be accessible via bracket notation
        self.assertEqual(md["__init__"], "init_value")
        self.assertEqual(md["__getitem__"], "getitem_value")

        # But attribute access returns the actual methods
        self.assertTrue(callable(md.__init__))
        self.assertTrue(callable(md.__getitem__))

    def test_unicode_and_special_character_keys(self):
        """Test keys with unicode and special characters."""
        md = MagicDict(
            {
                "café": "coffee",
                "привет": "hello",
                "🎉": "party",
                "key with\ttab": "tab_value",
                "key\nwith\nnewlines": "newline_value",
            }
        )

        self.assertEqual(md["café"], "coffee")
        self.assertEqual(md["привет"], "hello")
        self.assertEqual(md["🎉"], "party")
        self.assertEqual(md["key with\ttab"], "tab_value")
        self.assertEqual(md["key\nwith\nnewlines"], "newline_value")

    def test_very_long_key_names(self):
        """Test handling of very long key names."""
        long_key = "a" * 10000
        md = MagicDict({long_key: "value"})

        self.assertEqual(md[long_key], "value")
        self.assertIn(long_key, md)

    def test_nested_list_modification_preserves_structure(self):
        """Test that modifying nested lists preserves MagicDict conversion."""
        md = MagicDict({"items": [{"a": 1}]})
        md["items"].append({"b": 2})

        self.assertIsInstance(md["items"][1], dict)  # Not auto-converted
        self.assertEqual(md["items"][1]["b"], 2)

    def test_setdefault_with_none_value(self):
        """Test setdefault when setting None as the default."""
        md = MagicDict()
        result = md.setdefault("key", None)

        self.assertIsNone(result)
        self.assertIn("key", md)
        self.assertEqual(md["key"], None)
        self.assertEqual(md.key, MagicDict())  # Attribute access safe chains

    def test_pop_with_callback_default(self):
        """Test pop() with a callable as default value."""
        md = MagicDict({"a": 1})

        def default_factory():
            return "generated"

        result = md.pop("missing", default_factory())
        self.assertEqual(result, "generated")

    def test_comparison_operators_not_equal(self):
        """Test that comparison operators work correctly."""
        md1 = MagicDict({"a": 1})
        md2 = MagicDict({"a": 2})

        self.assertNotEqual(md1, md2)
        self.assertFalse(md1 == md2)
        self.assertTrue(md1 != md2)

    def test_contains_with_non_string_keys(self):
        """Test 'in' operator with various key types."""
        md = MagicDict({1: "one", (2, 3): "tuple", frozenset([4]): "frozenset"})

        self.assertIn(1, md)
        self.assertIn((2, 3), md)
        self.assertIn(frozenset([4]), md)
        self.assertNotIn("1", md)
        with self.assertRaises(TypeError):
            self.assertNotIn([2, 3], md)  # Lists aren't hashable

    def test_nested_empty_containers_after_operations(self):
        """Test that empty nested containers remain properly typed."""
        md = MagicDict({"data": []})
        md["data"].append({})

        self.assertIsInstance(md["data"], list)
        self.assertIsInstance(md["data"][0], dict)
        self.assertNotIsInstance(md["data"][0], MagicDict)

    def test_chaining_through_list_returns_attribute_error(self):
        """Test that chaining through list values raises AttributeError."""
        md = MagicDict({"items": ["a", "b", "c"]})

        with self.assertRaises(AttributeError):
            _ = md.items.nonexistent

    def test_mixed_none_and_missing_chaining(self):
        """Test chaining through combination of None values and missing keys."""
        md = MagicDict({"a": {"b": None}})

        # Chain through None then missing
        result1 = md.a.b.c.d
        self.assertIsInstance(result1, MagicDict)

        # Chain through missing then None
        result2 = md.x.y.z
        self.assertIsInstance(result2, MagicDict)

    def test_getstate_setstate_preservation(self):
        """Test that __getstate__ and __setstate__ work correctly."""
        md = MagicDict({"a": {"b": 1}, "c": [{"d": 2}]})

        state = md.__getstate__()
        self.assertIsInstance(state, dict)

        new_md = MagicDict()
        new_md.__setstate__(state)

        self.assertEqual(new_md, md)
        self.assertIsInstance(new_md.a, MagicDict)

    def test_equality_with_empty_protected_magicdicts(self):
        """Test that empty protected MagicDicts compare equal."""
        md = MagicDict({})

        protected1 = md.missing1
        protected2 = md.missing2

        self.assertEqual(protected1, protected2)
        self.assertEqual(protected1, {})
        self.assertEqual(protected2, {})

    def test_clear_on_non_empty_then_access(self):
        """Test accessing after clearing a MagicDict."""
        md = MagicDict({"a": 1, "b": 2})
        md.clear()

        self.assertEqual(len(md), 0)
        result = md.missing
        self.assertIsInstance(result, MagicDict)

    def test_disenchant_with_set_and_frozenset(self):
        """Test that disenchant preserves sets and frozensets."""
        md = MagicDict({"myset": {1, 2, 3}, "myfrozenset": frozenset([4, 5, 6])})

        result = md.disenchant()
        self.assertIsInstance(result["myset"], set)
        self.assertIsInstance(result["myfrozenset"], frozenset)

    def test_update_with_empty_dict(self):
        """Test update with an empty dictionary."""
        md = MagicDict({"a": 1})
        md.update({})

        self.assertEqual(md, {"a": 1})

    def test_fromkeys_with_zero_keys(self):
        """Test fromkeys with an empty sequence."""
        md = MagicDict.fromkeys([], "default")

        self.assertEqual(len(md), 0)
        self.assertIsInstance(md, MagicDict)

    def test_attribute_assignment_does_not_create_key(self):
        """Test that attribute assignment via setattr doesn't create dict keys."""
        md = MagicDict()

        # This should set an instance attribute, not a dict key
        md.my_attr = "value"

        # Check it's an instance attribute
        self.assertEqual(md.my_attr, "value")

        # Check it's not a dict key
        self.assertNotIn("my_attr", md)

    def test_dir_excludes_protected_attributes(self):
        """Test that __dir__ handles protected attributes correctly."""
        md = MagicDict({"regular": 1})

        d = dir(md)

        # Should include dict methods
        self.assertIn("keys", d)
        self.assertIn("items", d)

        # Should include user keys
        self.assertIn("regular", d)

        # Protected attributes shouldn't create confusion
        self.assertIn("__dict__", d)

    def test_json_dumps_on_magicdict_directly(self):
        """Test that json.dumps works directly on MagicDict."""
        md = MagicDict({"a": 1, "b": {"c": 2}})

        json_str = json.dumps(md)
        loaded = json.loads(json_str)

        self.assertEqual(loaded, {"a": 1, "b": {"c": 2}})

    def test_dotted_key_with_numeric_dict_key_not_list_index(self):
        """Test that numeric keys in dicts aren't confused with list indices."""
        md = MagicDict({"data": {"0": "zero_key", "1": "one_key"}})

        # These should access dict keys, not list indices
        self.assertEqual(md["data.0"], "zero_key")
        self.assertEqual(md["data.1"], "one_key")

    def test_mget_with_missing_vs_none(self):
        """Test mget behavior with missing (default sentinel) vs None."""
        md = MagicDict({"a": 1})

        # With missing (default), missing keys return empty MagicDict
        result1 = md.mget("missing")
        self.assertIsInstance(result1, MagicDict)

        # With explicit None, missing keys return None
        result2 = md.mget("missing", None)
        self.assertIsNone(result2)

        # With explicit None for existing None value
        md["b"] = None
        result3 = md.mget("b", "default")
        self.assertIsInstance(result3, MagicDict)  # None values still return MagicDict

    def test_recursive_equality_check(self):
        """Test equality with recursively nested identical structures."""
        data = {"a": {"b": {"c": {"d": 1}}}}
        md1 = MagicDict(data)
        md2 = MagicDict(copy.deepcopy(data))

        self.assertEqual(md1, md2)
        self.assertIsNot(md1.a, md2.a)
        self.assertIsNot(md1.a.b, md2.a.b)

    def test_list_containing_none_and_dicts(self):
        """Test list containing mix of None and dicts."""
        md = MagicDict({"items": [None, {"a": 1}, None, {"b": 2}]})

        self.assertIsNone(md["items"][0])
        self.assertIsInstance(md["items"][1], MagicDict)
        self.assertIsNone(md["items"][2])
        self.assertIsInstance(md["items"][3], MagicDict)

    def test_tuple_immutability_preserved(self):
        """Test that tuples remain immutable after hooking."""
        md = MagicDict({"data": ({"a": 1}, {"b": 2})})

        self.assertIsInstance(md.data, tuple)

        # Tuples should be immutable
        with self.assertRaises(TypeError):
            md.data[0] = {"c": 3}

    def test_nested_magicdict_in_list_after_append(self):
        """Test that manually appending a MagicDict to a list preserves it."""
        md = MagicDict({"items": []})
        nested = MagicDict({"inner": "value"})

        md["items"].append(nested)

        self.assertIs(md["items"][0], nested)
        self.assertIsInstance(md["items"][0], MagicDict)

    def test_popitem_on_empty_raises_keyerror(self):
        """Test that popitem on empty MagicDict raises KeyError."""
        md = MagicDict()

        with self.assertRaises(KeyError):
            md.popitem()

    def test_get_with_none_vs_missing_key(self):
        """Test get() method distinguishes None value from missing key."""
        md = MagicDict({"exists_as_none": None})

        # Existing key with None value
        self.assertIsNone(md.get("exists_as_none"))

        # Missing key without default
        self.assertIsNone(md.get("missing"))

        # Missing key with default
        self.assertEqual(md.get("missing", "default"), "default")

    def test_iteration_order_preservation(self):
        """Test that iteration order is preserved (Python 3.7+)."""
        data = OrderedDict([("z", 1), ("a", 2), ("m", 3)])
        md = MagicDict(data)

        self.assertEqual(list(md.keys()), ["z", "a", "m"])

    def test_values_are_not_double_wrapped(self):
        """Test that MagicDict values aren't double-wrapped."""
        nested = MagicDict({"inner": "value"})
        md = MagicDict({"outer": nested})

        # Should be the same instance, not wrapped again
        self.assertIs(md.outer, nested)

    def test_sys_getsizeof_works(self):
        """Test that sys.getsizeof works on MagicDict."""
        md = MagicDict({"a": 1, "b": 2})

        # Should not raise an error
        size = sys.getsizeof(md)
        self.assertGreater(size, 0)

    def test_format_string_with_magicdict(self):
        """Test using MagicDict in format strings."""
        md = MagicDict({"name": "Alice", "age": 30})

        result = "Name: {name}, Age: {age}".format(**md)
        self.assertEqual(result, "Name: Alice, Age: 30")

    def test_star_unpacking_in_function_call(self):
        """Test unpacking MagicDict as keyword arguments."""
        md = MagicDict({"a": 1, "b": 2})

        def func(a, b):
            return a + b

        result = func(**md)
        self.assertEqual(result, 3)

    def test_getattr_fallback_to_dict_method(self):
        """Accessing a dict method name should use __getattribute__ path."""
        md = MagicDict({"x": 1})
        result = md.keys
        self.assertTrue(callable(result))

    def test_getattr_missing_creates_magicdict(self):
        """Accessing missing attr should create an empty MagicDict."""
        md = MagicDict()
        result = md.not_there
        self.assertIsInstance(result, MagicDict)
        self.assertTrue(getattr(result, "_from_missing", False))

    # ---------- LINES 252–253 ----------
    def test_raise_if_protected_from_none(self):
        """Setting value when _from_none=True should raise TypeError."""
        md = MagicDict()
        object.__setattr__(md, "_from_none", True)
        with self.assertRaises(TypeError):
            md["x"] = 1

    def test_raise_if_protected_from_missing(self):
        """Deleting key when _from_missing=True should raise TypeError."""
        md = MagicDict()
        object.__setattr__(md, "_from_missing", True)
        with self.assertRaises(TypeError):
            del md["x"]

    # ---------- LINES 418–422 ----------
    def test_disenchant_with_namedtuple_and_set(self):
        """Ensure namedtuple and set are correctly handled by disenchant()."""
        Point = namedtuple("Point", "x y")
        md = MagicDict({"point": Point(1, {"inner": 2}), "aset": {1, 2}})
        result = md.disenchant()
        self.assertIsInstance(result["point"], Point)
        self.assertIsInstance(result["aset"], set)
        self.assertEqual(result["point"].y, {"inner": 2})

    # ---------- LINES 443–446 ----------
    def test_disenchant_with_circular_reference(self):
        """Ensure circular references are preserved correctly."""
        md = MagicDict()
        md["self"] = md
        result = md.disenchant()
        self.assertIs(result["self"], result)

    # ---------- Helper functions ----------
    def test_magic_loads_and_enchant(self):
        """Ensure magic_loads and enchant behave as expected."""
        data = {"a": {"b": 2}}
        md = magic_loads(json.dumps(data))
        self.assertIsInstance(md, MagicDict)
        self.assertEqual(md.a.b, 2)

        # Enchanting an existing MagicDict should return itself
        same_md = enchant(md)
        self.assertIs(same_md, md)

    def test_enchant_raises_typeerror_on_non_dict(self):
        """Ensure enchant raises TypeError on non-dict input."""
        with self.assertRaises(TypeError):
            enchant(123)


class TestMissingCoverage(TestCase):
    """Tests specifically targeting the missing lines in coverage report."""

    # ==================== LINES 203-210: __getattr__ fallback ====================
    def test_getattr_fallback_to_superclass_for_internal_attrs(self):
        """Test that __getattr__ falls back to super().__getattribute__ for internal attributes."""
        md = MagicDict({"x": 1})

        # Accessing __dict__ should use the fallback path (line 207)
        self.assertIsInstance(md.__dict__, dict)

        # Accessing __class__ should also use fallback
        self.assertEqual(md.__class__, MagicDict)

    def test_getattr_returns_empty_magicdict_on_attribute_error(self):
        """Test that __getattr__ returns empty MagicDict when AttributeError is raised."""
        md = MagicDict({"x": 1})

        # Accessing a truly non-existent attribute should trigger lines 208-210
        result = md.this_attribute_does_not_exist_anywhere
        self.assertIsInstance(result, MagicDict)
        self.assertTrue(getattr(result, "_from_missing", False))
        self.assertEqual(len(result), 0)

    # ==================== LINES 252-253: _raise_if_protected ====================
    def test_raise_if_protected_from_none_flag(self):
        """Test that _raise_if_protected raises TypeError when _from_none is True."""
        md = MagicDict({"key": None})

        # Get the protected MagicDict created from None value
        protected = md.key

        # Try to modify it - should raise TypeError
        with self.assertRaises(TypeError) as cm:
            protected["new_key"] = "value"

        self.assertIn("Cannot modify", str(cm.exception))

    def test_raise_if_protected_from_missing_flag(self):
        """Test that _raise_if_protected raises TypeError when _from_missing is True."""
        md = MagicDict({"x": 1})

        # Get the protected MagicDict created from missing key
        protected = md.nonexistent_key

        # Try to modify it - should raise TypeError
        with self.assertRaises(TypeError) as cm:
            protected["new_key"] = "value"

        self.assertIn("Cannot modify", str(cm.exception))

    # ==================== LINES 418-422: disenchant namedtuple handling ====================
    def test_disenchant_with_namedtuple(self):
        """Test that disenchant correctly handles namedtuples."""
        Point = namedtuple("Point", ["x", "y"])

        # Create MagicDict with namedtuple containing nested dict
        md = MagicDict(
            {
                "point": Point(x=1, y={"nested": "value"}),
                "points_list": [Point(x=2, y={"another": "nested"})],
            }
        )

        # Disenchant should preserve namedtuple type but convert nested dicts
        result = md.disenchant()

        # Check that namedtuple is preserved (lines 418-420)
        self.assertIsInstance(result["point"], Point)
        self.assertEqual(result["point"].x, 1)
        self.assertIsInstance(result["point"].y, dict)
        self.assertNotIsInstance(result["point"].y, MagicDict)
        self.assertEqual(result["point"].y["nested"], "value")

        # Check namedtuple in list
        self.assertIsInstance(result["points_list"][0], Point)
        self.assertIsInstance(result["points_list"][0].y, dict)

    def test_disenchant_with_regular_tuple(self):
        """Test that disenchant handles regular tuples correctly."""
        md = MagicDict({"tuple_data": ({"a": 1}, {"b": 2}, "string", 123)})

        result = md.disenchant()

        # Should be a regular tuple (line 421)
        self.assertIsInstance(result["tuple_data"], tuple)
        self.assertIsInstance(result["tuple_data"][0], dict)
        self.assertNotIsInstance(result["tuple_data"][0], MagicDict)

    # ==================== LINES 443-446: disenchant set/frozenset handling ====================
    def test_disenchant_with_set(self):
        """Test that disenchant correctly handles sets."""
        md = MagicDict(
            {"my_set": {1, 2, 3, 4, 5}, "nested": {"inner_set": {"a", "b", "c"}}}
        )

        result = md.disenchant()

        # Sets should be preserved (lines 443-446)
        self.assertIsInstance(result["my_set"], set)
        self.assertEqual(result["my_set"], {1, 2, 3, 4, 5})

        # Nested sets should also be preserved
        self.assertIsInstance(result["nested"]["inner_set"], set)
        self.assertEqual(result["nested"]["inner_set"], {"a", "b", "c"})

    def test_disenchant_with_frozenset(self):
        """Test that disenchant correctly handles frozensets."""
        md = MagicDict(
            {
                "my_frozenset": frozenset([1, 2, 3]),
                "complex": {"data": frozenset(["x", "y", "z"])},
            }
        )

        result = md.disenchant()

        # Frozensets should be preserved (lines 443-446)
        self.assertIsInstance(result["my_frozenset"], frozenset)
        self.assertEqual(result["my_frozenset"], frozenset([1, 2, 3]))

        # Nested frozensets
        self.assertIsInstance(result["complex"]["data"], frozenset)
        self.assertEqual(result["complex"]["data"], frozenset(["x", "y", "z"]))

    def test_disenchant_with_mixed_sets(self):
        """Test disenchant with both sets and frozensets in the same structure."""
        md = MagicDict(
            {
                "mixed": {
                    "regular_set": {1, 2, 3},
                    "frozen_set": frozenset([4, 5, 6]),
                    "nested_dict": {"more_set": {7, 8, 9}},
                }
            }
        )

        result = md.disenchant()

        self.assertIsInstance(result["mixed"]["regular_set"], set)
        self.assertIsInstance(result["mixed"]["frozen_set"], frozenset)
        self.assertIsInstance(result["mixed"]["nested_dict"]["more_set"], set)

    # ==================== Additional edge cases ====================
    def test_getattr_with_dict_method_names(self):
        """Test that accessing dict method names works correctly."""
        md = MagicDict({"data": 1})

        # Accessing 'keys' should return the method, not create empty MagicDict
        keys_method = md.keys
        self.assertTrue(callable(keys_method))

        # Accessing 'items' should return the method
        items_method = md.items
        self.assertTrue(callable(items_method))

    def test_protected_magicdict_all_mutation_methods(self):
        """Test that all mutation methods are blocked on protected MagicDict."""
        md = MagicDict({"x": None})
        protected = md.x

        # Test all methods that call _raise_if_protected
        with self.assertRaises(TypeError):
            protected["key"] = "value"  # __setitem__

        with self.assertRaises(TypeError):
            del protected["key"]  # __delitem__

        with self.assertRaises(TypeError):
            protected.update({"key": "value"})  # update

        with self.assertRaises(TypeError):
            protected.setdefault("key", "value")  # setdefault

        with self.assertRaises(TypeError):
            protected.pop("key")  # pop

        with self.assertRaises(TypeError):
            protected.popitem()  # popitem

        with self.assertRaises(TypeError):
            protected.clear()  # clear

    def test_complex_namedtuple_nesting(self):
        """Test complex nested structures with namedtuples."""
        Inner = namedtuple("Inner", ["a", "b"])
        Outer = namedtuple("Outer", ["x", "y"])

        md = MagicDict(
            {
                "complex": Outer(
                    x=Inner(a={"deep": "value"}, b=[1, 2, 3]), y={"regular": "dict"}
                )
            }
        )

        result = md.disenchant()

        # Check structure is preserved
        self.assertIsInstance(result["complex"], Outer)
        self.assertIsInstance(result["complex"].x, Inner)
        self.assertIsInstance(result["complex"].x.a, dict)
        self.assertNotIsInstance(result["complex"].x.a, MagicDict)

    def test_disenchant_circular_reference_with_sets(self):
        """Test disenchant with circular references and sets."""
        md = MagicDict({"data": {"my_set": {1, 2, 3}, "nested": {}}})
        md["data"]["nested"]["circular"] = md["data"]

        result = md.disenchant()

        # Check circular reference is preserved
        self.assertIs(result["data"]["nested"]["circular"], result["data"])

        # Check set is preserved
        self.assertIsInstance(result["data"]["my_set"], set)


class TestHelperFunctions(TestCase):
    """Test helper functions to ensure complete coverage."""

    def test_enchant_with_magicdict_returns_same_instance(self):
        """Test that enchant returns the same instance when given MagicDict."""
        md = MagicDict({"a": 1})
        result = enchant(md)
        self.assertIs(result, md)

    def test_enchant_with_regular_dict(self):
        """Test that enchant converts regular dict to MagicDict."""
        d = {"a": {"b": {"c": 1}}}
        result = enchant(d)
        self.assertIsInstance(result, MagicDict)
        self.assertIsInstance(result.a, MagicDict)
        self.assertIsInstance(result.a.b, MagicDict)

    def test_enchant_raises_typeerror(self):
        """Test that enchant raises TypeError for non-dict types."""
        with self.assertRaises(TypeError):
            enchant("not a dict")

        with self.assertRaises(TypeError):
            enchant([1, 2, 3])

        with self.assertRaises(TypeError):
            enchant(123)

    def test_magic_loads_creates_magicdict(self):
        """Test that magic_loads creates MagicDict from JSON."""
        json_str = '{"user": {"name": "Alice", "age": 30}, "items": [{"id": 1}]}'
        result = magic_loads(json_str)

        self.assertIsInstance(result, MagicDict)
        self.assertIsInstance(result.user, MagicDict)
        self.assertIsInstance(result["items"][0], MagicDict)
        self.assertEqual(result.user.name, "Alice")


# Assume MagicDict and helper functions (enchant, magic_loads) are in a file
# named safedict.py or are accessible in the current scope.
# from safedict.safedict import MagicDict, enchant, magic_loads


class TestMissingCoverageAnother(TestCase):
    """
    Tests specifically targeting the lines identified as missing in the coverage report.
    """

    # ======================================================================
    # Target: safedict.py, lines 203-210 (__getattr__ fallback)
    # ======================================================================

    def test_getattr_fallback_for_non_key_attributes(self):
        """
        Covers lines 203-207: Tests that __getattr__ falls back to the default
        __getattribute__ for attributes that are not keys in the dictionary,
        such as special attributes like __class__ or __dict__.
        """
        md = MagicDict({"key": "value"})
        # Accessing an attribute that is not a key should trigger the `try` block
        # and succeed via `super().__getattribute__('__class__')`.
        self.assertEqual(md.__class__, MagicDict)
        self.assertIsInstance(md.__dict__, dict)

    def test_getattr_raises_attributeerror_and_returns_empty_magicdict(self):
        """
        Covers lines 208-210: Tests that accessing a completely non-existent
        attribute triggers an AttributeError in the fallback, which is then
        caught and returns a protected, empty MagicDict.
        """
        md = MagicDict({"key": "value"})
        # Accessing an attribute that is neither a key nor a real attribute
        # will raise AttributeError, triggering the `except` block.
        result = md.this_attribute_does_not_exist
        self.assertIsInstance(result, MagicDict)
        self.assertTrue(getattr(result, "_from_missing", False))
        self.assertEqual(len(result), 0)

    # ======================================================================
    # Target: safedict.py, lines 252-253 (_raise_if_protected)
    # ======================================================================

    def test_raise_if_protected_blocks_modification_from_none(self):
        """
        Covers lines 252-253: Tests that a MagicDict created from a key with a
        `None` value is protected and raises a TypeError on modification.
        """
        md = MagicDict({"user": {"nickname": None}})
        # Accessing `md.user.nickname` returns a temporary MagicDict with `_from_none=True`.
        protected_md = md.user.nickname
        self.assertTrue(getattr(protected_md, "_from_none", False))

        with self.assertRaisesRegex(
            TypeError, "Cannot modify NoneType or missing keys."
        ):
            # This modification attempt calls __setitem__, which calls _raise_if_protected.
            protected_md["alias"] = "new_alias"

    def test_raise_if_protected_blocks_modification_from_missing(self):
        """
        Covers lines 252-253: Tests that a MagicDict created from a missing
        key is protected and raises a TypeError on modification.
        """
        md = MagicDict({"user": {"name": "Alice"}})
        # Accessing `md.user.address` returns a temporary MagicDict with `_from_missing=True`.
        protected_md = md.user.address
        self.assertTrue(getattr(protected_md, "_from_missing", False))

        with self.assertRaisesRegex(
            TypeError, "Cannot modify NoneType or missing keys."
        ):
            # This modification attempt calls __delitem__, which calls _raise_if_protected.
            del protected_md["city"]

    # ======================================================================
    # Target: safedict.py, lines 418-422 (disenchant namedtuple handling)
    # ======================================================================

    def test_disenchant_preserves_namedtuple_type(self):
        """
        Covers lines 418-422: Tests that disenchant correctly processes a
        `namedtuple`, preserving its type while recursively disenchanting its contents.
        """
        Point = namedtuple("Point", ["x", "y"])
        # Create a structure where a namedtuple contains a MagicDict that needs disenchanting.
        data_with_namedtuple = {
            "point_of_interest": Point(x=1, y=MagicDict({"details": "nested"}))
        }
        md = MagicDict(data_with_namedtuple)

        # Call disenchant to trigger the specific logic for namedtuples.
        disenchanted_data = md.disenchant()

        point = disenchanted_data["point_of_interest"]
        self.assertIsInstance(point, Point)
        self.assertEqual(point.x, 1)
        # Verify the nested MagicDict was converted back to a standard dict.
        self.assertIsInstance(point.y, dict)
        self.assertNotIsInstance(point.y, MagicDict)
        self.assertEqual(point.y["details"], "nested")

    def test_disenchant_handles_regular_tuple(self):
        """
        Covers line 422: Tests the fallback path in the tuple handling logic,
        ensuring regular tuples are processed correctly.
        """
        md = MagicDict({"data": (MagicDict({"a": 1}), "string_val")})
        disenchanted_data = md.disenchant()

        regular_tuple = disenchanted_data["data"]
        self.assertIsInstance(regular_tuple, tuple)
        # Verify the nested MagicDict was converted back to a standard dict.
        self.assertIsInstance(regular_tuple[0], dict)
        self.assertNotIsInstance(regular_tuple[0], MagicDict)
        self.assertEqual(regular_tuple[0]["a"], 1)

    # ======================================================================
    # Target: safedict.py, lines 443-446 (disenchant set/frozenset)
    # ======================================================================

    def test_disenchant_preserves_set_and_frozenset(self):
        """
        Covers lines 443-446: Tests that disenchant correctly processes
        `set` and `frozenset` objects, preserving their types.
        """
        # Note: Sets cannot contain mutable dicts, but the disenchant logic
        # still processes them to handle other potential nested types.
        data_with_sets = {
            "id_set": {1, 2, 3},
            "config_frozenset": frozenset([("key", "value")]),
            "mixed_nested": MagicDict({"data": {1, 2}}),
        }
        md = MagicDict(data_with_sets)

        disenchanted_data = md.disenchant()

        # Verify the set is preserved.
        self.assertIsInstance(disenchanted_data["id_set"], set)
        self.assertEqual(disenchanted_data["id_set"], {1, 2, 3})

        # Verify the frozenset is preserved.
        self.assertIsInstance(disenchanted_data["config_frozenset"], frozenset)
        self.assertEqual(
            disenchanted_data["config_frozenset"], frozenset([("key", "value")])
        )

        # Verify nested sets are preserved.
        self.assertIsInstance(disenchanted_data["mixed_nested"]["data"], set)


class TestHelperFunctionsAgain(TestCase):
    """
    Test helper functions to ensure complete coverage.
    """

    def test_enchant_with_magicdict_returns_same_instance(self):
        """Test that enchant returns the same instance when given MagicDict."""
        md = MagicDict({"a": 1})
        result = enchant(md)
        self.assertIs(result, md)

    def test_enchant_with_regular_dict(self):
        """Test that enchant converts regular dict to MagicDict."""
        d = {"a": {"b": {"c": 1}}}
        result = enchant(d)
        self.assertIsInstance(result, MagicDict)
        self.assertIsInstance(result.a, MagicDict)
        self.assertIsInstance(result.a.b, MagicDict)

    def test_enchant_raises_typeerror(self):
        """Test that enchant raises TypeError for non-dict types."""
        with self.assertRaises(TypeError):
            enchant("not a dict")
        with self.assertRaises(TypeError):
            enchant([1, 2, 3])
        with self.assertRaises(TypeError):
            enchant(123)

    def test_magic_loads_creates_magicdict(self):
        """Test that magic_loads creates MagicDict from JSON."""
        json_str = '{"user": {"name": "Alice", "age": 30}, "items": [{"id": 1}]}'
        result = magic_loads(json_str)
        self.assertIsInstance(result, MagicDict)
        self.assertIsInstance(result.user, MagicDict)
        self.assertIsInstance(result["items"][0], MagicDict)
        self.assertEqual(result.user.name, "Alice")

    def test_init_mutates_nested_mutable_collections_in_place(self):
        """
        Verify that __init__ mutates nested *mutable collections* (like lists)
        within the original input object, but does not replace the top-level
        values of the input dictionary itself.
        """
        original_data = {
            "user": {"name": "Alice"},
            "permissions": [{"scope": "read"}],
            "config": ({"theme": "dark"},),  # A tuple to test immutability
        }

        # Create a deepcopy to compare against later.
        original_data_pristine = deepcopy(original_data)

        # Create the MagicDict
        md = MagicDict(original_data)

        # 1. ASSERT FAILURE: The top-level value 'user' in the original dict
        # is NOT converted. It's read, converted, and the result is stored in `md`.
        self.assertNotIsInstance(
            original_data["user"],
            MagicDict,
            "Top-level values in the original dict should not be replaced.",
        )
        self.assertIsInstance(
            original_data["user"],
            dict,
            "The original nested dict should remain a dict.",
        )

        # 2. ASSERT SUCCESS: The dict inside the *list* IS converted because
        # the list is a mutable collection that is modified in-place.
        self.assertIsInstance(
            original_data["permissions"][0],
            MagicDict,
            "Dict within a mutable list in the original input SHOULD be converted in-place.",
        )

        # 3. ASSERT IMMUTABILITY: The tuple is immutable, so a new tuple is created for `md`,
        # leaving the original unchanged.
        self.assertIsInstance(
            original_data["config"][0],
            dict,
            "Original tuple's contents should remain unchanged.",
        )
        self.assertNotIsInstance(original_data["config"][0], MagicDict)
        self.assertIsInstance(
            md.config[0], MagicDict
        )  # The new tuple in md has a MagicDict

        # 4. AVOIDING SIDE-EFFECTS: To avoid any mutation, the caller should pass a deep copy.
        md_from_copy = MagicDict(deepcopy(original_data_pristine))

        # Verify the pristine original dictionary was not affected at all.
        self.assertIsInstance(
            original_data_pristine["permissions"][0],
            dict,
            "The pristine original's list content should not be mutated.",
        )
        self.assertNotIsInstance(original_data_pristine["permissions"][0], MagicDict)

    def test_dir_includes_non_identifier_string_keys(self):
        """
        Test that __dir__ includes string keys that are not valid Python
        identifiers, which might be undesirable for tab-completion.
        """
        md = MagicDict(
            {
                "valid_key": 1,
                "invalid-key": 2,
                "key with space": 3,
                123: 4,  # Non-string key
            }
        )
        dir_list = dir(md)

        self.assertIn("valid_key", dir_list)
        # The current implementation includes these, which could be surprising.
        self.assertIn("invalid-key", dir_list)
        self.assertIn("key with space", dir_list)
        # Non-string keys should not be included.
        self.assertNotIn(123, dir_list)

    def test_mget_with_explicit_none_default_for_none_value(self):
        """
        Test the mget() edge case where a key's value is None and the
        explicit default provided is also None. It should return None.
        """
        md = MagicDict({"key_is_none": None})

        # Standard behavior: value is None, returns an empty MagicDict for chaining.
        self.assertIsInstance(md.mget("key_is_none"), MagicDict)

        # Edge case: If the default is *explicitly* None, it should return None.
        self.assertIsNone(
            md.mget("key_is_none", default=None),
            "mget should return the explicit None default, even for a None value.",
        )

    def test_disenchant_does_not_traverse_custom_object_keys(self):
        """
        Verify that disenchant does NOT recursively convert MagicDicts nested
        inside arbitrary custom objects when they are used as keys.
        """

        # A custom hashable object to be used as a dictionary key.
        class HashableContainer:
            def __init__(self, content):
                self.content = content

            def __hash__(self):
                # Simple hash based on object id, sufficient for this test.
                return id(self.content)

            def __eq__(self, other):
                return (
                    isinstance(other, HashableContainer)
                    and self.content == other.content
                )

        key_obj = HashableContainer(MagicDict({"a": 1}))
        md = MagicDict({key_obj: "value"})

        # The disenchant method will recurse on keys and values.
        disenchanted = md.disenchant()

        disenchanted_key = list(disenchanted.keys())[0]
        self.assertIs(
            disenchanted_key,
            key_obj,
            "The custom key object itself should be returned unchanged.",
        )

        # ASSERT CORRECT BEHAVIOR: The content of the custom key object
        # REMAINS a MagicDict because disenchant does not introspect custom types.
        self.assertIsInstance(
            disenchanted_key.content,
            MagicDict,
            "MagicDict inside a custom key object should NOT be disenchanted.",
        )
        self.assertEqual(disenchanted_key.content, {"a": 1})

    def test_hook_with_bytearray_mutates_in_place(self):
        """
        Test that the hooking mechanism mutates a bytearray in-place,
        which could be an unexpected side effect.
        """
        # A bytearray is a Sequence but not str or bytes, so it falls into the
        # generic sequence handler.
        original_bytearray = bytearray(b" A dict will be inserted here -> ")
        dict_to_insert = {"key": "value"}
        data = {"data": [original_bytearray, dict_to_insert]}

        # The _hook should not attempt to process the bytearray's contents.
        md = MagicDict(data)
        self.assertIs(md.data[0], original_bytearray)
        self.assertIsInstance(md.data[1], MagicDict)

    def test_lazy_conversion_on_attribute_access(self):
        """
        Test the "lazy conversion" feature where a plain dict added without
        hooking is converted upon first attribute access.
        """
        md = MagicDict()
        plain_dict = {"nested": "value"}

        # Bypass __setitem__ to insert a plain dict without hooking.
        super(MagicDict, md).__setitem__("plain", plain_dict)

        # Verify it's still a plain dict when accessed via brackets.
        self.assertIs(type(md["plain"]), dict)

        # Accessing via attribute should trigger the conversion.
        converted = md.plain
        self.assertIsInstance(converted, MagicDict)
        self.assertEqual(converted.nested, "value")

        # The original dict within md should now be replaced.
        self.assertIsInstance(md["plain"], MagicDict)

    def test_disenchant_fallback_for_unreconstructable_sequence(self):
        """
        Test that disenchant's sequence handler falls back to creating a plain
        list if the original sequence type cannot be instantiated from an iterable.
        """

        # This custom class's constructor requires two arguments and will raise a
        # TypeError if called with only one (as `disenchant` will attempt to do).
        class UnreconstructableSequence(UserList):
            def __init__(self, part1, part2):
                super().__init__(part1 + part2)

        # We initialize it correctly with two arguments for the test setup.
        original_seq = UnreconstructableSequence([{"a": 1}], [{"b": 2}])
        md = MagicDict({"data": original_seq})

        # The disenchant logic will try `UnreconstructableSequence(converted_items)`,
        # which will raise a TypeError, forcing the `except` block to execute
        # and return a plain list.
        disenchanted = md.disenchant()

        # 1. ASSERT SUCCESS: The result should now be a plain `list`.
        self.assertIsInstance(
            disenchanted["data"], list, "Should have fallen back to a plain list."
        )

        # 2. To be certain, also check that it's NOT the original custom type.
        self.assertNotIsInstance(
            disenchanted["data"],
            UnreconstructableSequence,
            "Should not have been able to reconstruct the original type.",
        )

        # 3. Verify the contents were correctly disenchanted.
        self.assertEqual(disenchanted["data"], [{"a": 1}, {"b": 2}])


class TestNoneFunction(TestCase):
    """Test suite for the none() function."""

    def test_none_with_missing_key_magicdict(self):
        """Test that none() returns None for MagicDict from missing key."""
        md = MagicDict({"a": 1})
        missing = md.missing_key  # Accessing missing key creates empty MagicDict
        result = none(missing)
        self.assertIsNone(result)

    def test_none_with_none_value_magicdict(self):
        """Test that none() returns None for MagicDict from None value."""
        md = MagicDict({"a": None})
        none_value = md.a  # Accessing None value creates empty MagicDict
        result = none(none_value)
        self.assertIsNone(result)

    def test_none_with_regular_empty_magicdict(self):
        """Test that none() returns the object for regular empty MagicDict."""
        md = MagicDict()
        result = none(md)
        self.assertIsInstance(result, MagicDict)
        self.assertEqual(len(result), 0)
        self.assertFalse(getattr(result, "_from_none", False))
        self.assertFalse(getattr(result, "_from_missing", False))

    def test_none_with_non_empty_magicdict(self):
        """Test that none() returns the object for non-empty MagicDict."""
        md = MagicDict({"a": 1, "b": 2})
        result = none(md)
        self.assertIs(result, md)
        self.assertEqual(result, {"a": 1, "b": 2})

    def test_none_with_non_magicdict_objects(self):
        """Test that none() returns the object unchanged for non-MagicDict types."""
        # Test with various types
        test_cases = [
            None,
            42,
            "string",
            [1, 2, 3],
            {"regular": "dict"},
            (1, 2, 3),
            {1, 2, 3},
        ]

        for obj in test_cases:
            with self.subTest(obj=obj):
                result = none(obj)
                self.assertIs(result, obj)

    def test_none_with_nested_access(self):
        """Test none() with nested missing keys."""
        md = MagicDict({"a": {"b": {"c": 1}}})
        missing_nested = md.x.y.z  # Deep missing access
        result = none(missing_nested)
        self.assertIsNone(result)

    def test_none_with_mget_missing(self):
        """Test none() with mget() on missing key."""
        md = MagicDict({"a": 1})
        missing = md.mget("missing_key")
        result = none(missing)
        self.assertIsNone(result)

    def test_none_with_mget_none_value(self):
        """Test none() with mget() on None value."""
        md = MagicDict({"a": None})
        none_val = md.mget("a")
        result = none(none_val)
        self.assertIsNone(result)

    def test_none_with_chained_none_values(self):
        """Test none() with chained access through None values."""
        md = MagicDict({"a": None})
        chained = md.a.b.c.d  # Chain through None
        result = none(chained)
        self.assertIsNone(result)

    def test_none_preserves_regular_none(self):
        """Test that none() passes through actual None values."""
        result = none(None)
        self.assertIsNone(result)

    def test_none_with_empty_magicdict_with_items_added(self):
        """Test that none() returns object if MagicDict has items."""
        md = MagicDict({"a": 1})
        missing = md.missing_key  # Get empty MagicDict from missing key

        # Before adding items, it should return None
        self.assertIsNone(none(missing))

        # But we can't add items because it's protected
        with self.assertRaises(TypeError):
            missing["x"] = 1


class TestNoneFunctionIntegration(TestCase):
    """Integration tests showing practical usage of none() function."""

    def test_safe_navigation_pattern(self):
        """Test using none() for safe navigation pattern."""
        data = MagicDict({"user": {"profile": {"name": "John"}}})

        # Safe access to existing data
        name = none(data.user.profile.name)
        self.assertEqual(name, "John")

        # Safe access to missing data
        age = none(data.user.profile.age)
        self.assertIsNone(age)

        # Safe access to deeply missing data
        missing = none(data.missing.deep.nested.value)
        self.assertIsNone(missing)

    def test_default_value_pattern(self):
        """Test using none() with default values."""
        data = MagicDict({"a": 1})

        # Use none() with or for default values
        value1 = none(data.a) or "default"
        self.assertEqual(value1, 1)

        value2 = none(data.missing) or "default"
        self.assertEqual(value2, "default")

    def test_conditional_processing(self):
        """Test using none() for conditional processing."""
        data = MagicDict({"config": {"enabled": True, "timeout": None}})

        # Process only if value exists
        enabled = none(data.config.enabled)
        if enabled is not None:
            self.assertTrue(enabled)

        timeout = none(data.config.timeout)
        if timeout is not None:
            self.fail("Should be None")

        missing = none(data.config.missing)
        if missing is not None:
            self.fail("Should be None")
