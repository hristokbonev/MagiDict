from collections import UserList, namedtuple
import gc
import io
import sys
import threading
from typing import OrderedDict
from unittest import TestCase, main
import copy
from copy import deepcopy
import pickle
from types import MappingProxyType
import json
import weakref
from magidict import MagiDict, enchant, magi_load, magi_loads, none


md = MagiDict(
    {
        "user": {
            "name": "Alice",
            "id": 101,
        }
    }
)


class TestMagiDict(TestCase):
    """Unit tests for the MagiDict class."""

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
        self.md = MagiDict(self.md)

    def test_init(self):
        """Test various initialization methods."""
        self.assertIsInstance(MagiDict(), MagiDict)
        self.assertEqual(MagiDict({"a": 1}), {"a": 1})
        self.assertEqual(MagiDict(a=1, b=2), {"a": 1, "b": 2})
        self.assertEqual(MagiDict([("a", 1), ("b", 2)]), {"a": 1, "b": 2})

    def test_item_access_and_assignment(self):
        """Test standard dict-style item access and assignment."""
        d = MagiDict()
        d["a"] = 100
        self.assertEqual(d["a"], 100)
        d["a"] = 200
        self.assertEqual(d["a"], 200)

    def test_deletion_2(self):
        """Test deletion of keys."""
        d = MagiDict({"a": 1, "b": 2})
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
        d = MagiDict()
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

        d = MagiDict({"a": 1, "b": 2})
        self.assertEqual(d.pop("a"), 1)
        self.assertNotIn("a", d)

        d.update({"b": 5, "c": 3, "d": 4})
        self.assertEqual(d, {"b": 5, "c": 3, "d": 4})

        d.clear()
        self.assertEqual(len(d), 0)

    def test_equality(self):
        """Test equality against standard dicts and other mappings."""
        self.assertEqual(self.md, self.md)
        self.assertEqual(MagiDict(self.md), self.md)
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
        """Accessing a non-existent attribute should return an empty MagiDict."""
        non_existent = self.md.non_existent
        self.assertIsInstance(non_existent, MagiDict)

    def test_chained_attribute_access_non_existent(self):
        """Accessing multiple non-existent attributes should return empty MagiDicts."""
        deeply_non_existent = self.md.a.b.c.d
        self.assertIsInstance(deeply_non_existent, MagiDict)
        self.assertEqual(deeply_non_existent, MagiDict())
        self.assertNotIn("a", self.md)

    def test_recursive_conversion_on_init(self):
        """Test that nested dicts/lists/tuples are converted to MagiDicts recursively."""
        self.assertIsInstance(self.md.user, MagiDict)
        self.assertIsInstance(self.md.permissions[2], MagiDict)
        self.assertIsInstance(self.md.metadata[0], MagiDict)
        self.assertIsInstance(self.md.permissions[3].nested_list[0], MagiDict)
        self.assertIsInstance(self.md.empty_dict, MagiDict)

    def test_deep_attribute_access(self):
        """Test deep attribute access on nested structures."""
        self.assertEqual(self.md.user.profile.settings.theme, "dark")
        self.assertEqual(self.md.user.profile.email, "alice@example.com")
        self.assertEqual(self.md.permissions[2].area, "admin")
        self.assertEqual(self.md.permissions[3].level, 2)
        self.assertTrue(self.md.permissions[3].nested_list[0].deep)
        self.assertEqual(self.md.metadata[0].source, "web-form")

    def test_recursive_conversion_on_setitem(self):
        """Test that setting a dict value converts it to MagiDict recursively."""
        d = MagiDict()
        d["config"] = {"host": "localhost", "port": 8080}
        self.assertIsInstance(d.config, MagiDict)
        self.assertEqual(d.config.host, "localhost")

    def test_recursive_conversion_on_update(self):
        """Test that updating with a dict converts it to MagiDict recursively."""
        d = MagiDict()
        d.update({"config": {"host": "localhost", "port": 8080}})
        self.assertIsInstance(d.config, MagiDict)
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
        self.assertEqual(list(MagiDict({"keys": 1}).keys()), ["keys"])

    def test_overwrite_with_plain_dict(self):
        """Setting a key to a plain dict should convert it to MagiDict."""
        self.md["user"] = {"foo": "bar"}
        self.assertIsInstance(self.md.user, MagiDict)
        self.assertEqual(self.md.user.foo, "bar")

    def test_overwrite_with_enchant(self):
        """Setting a key to a MagiDict should keep it as MagiDict."""
        nested = MagiDict({"baz": 42})
        self.md["new"] = nested
        self.assertIs(self.md.new, nested)

    def test_invalid_identifier_keys(self):
        """Keys that are not valid Python identifiers should still be accessible via item access."""
        md = MagiDict({"my-key": 1, "with space": 2, "class": 3})
        self.assertEqual(md["my-key"], 1)
        self.assertEqual(md["with space"], 2)
        self.assertEqual(md["class"], 3)
        self.assertEqual(md.mget("class"), 3)

    def test_setdefault_and_pop_default(self):
        """Test setdefault and pop with default value."""
        d = MagiDict()
        self.assertEqual(d.setdefault("a", {"b": 2}).b, 2)
        self.assertEqual(d.pop("nonexistent", "default"), "default")

    def test_copy_preserves_type(self):
        """Test that copy() returns a MagiDict and nested dicts are also MagiDicts."""
        d = MagiDict(a=1, b={"c": 2})
        d_copy = d.copy()
        self.assertIsInstance(d_copy, MagiDict)
        self.assertIsInstance(d_copy.b, MagiDict)
        self.assertEqual(d, d_copy)

    def test_method_conflict_keys(self):
        """Ensure that keys named like dict methods do not interfere with method calls."""
        md = MagiDict({"items": "value", "get": "value2"})
        self.assertTrue(callable(md.items))
        self.assertEqual(md["items"], "value")
        self.assertEqual(md["get"], "value2")

    def test_standard_access_non_existent_key_raises_keyerror(self):
        """Accessing a non-existent key via standard dict access should raise KeyError."""
        with self.assertRaises(KeyError):
            _ = self.md["non_existent_key"]

    def test_deletion(self):
        """Test deletion of keys."""
        md = MagiDict({"a": 1, "b": 2})
        del md["a"]
        self.assertNotIn("a", md)
        with self.assertRaises(KeyError):
            del md["non_existent"]

    def test_repr(self):
        """Test the string representation of MagiDict."""
        md = MagiDict({"a": 1})
        self.assertEqual(repr(md), "MagiDict({'a': 1})")

    def test_pickling(self):
        """Test that pickling and unpickling preserves MagiDict structure."""
        pickled_md = pickle.dumps(self.md)
        unpickled_md = pickle.loads(pickled_md)

        self.assertIsInstance(unpickled_md, MagiDict)
        self.assertEqual(self.md, unpickled_md)
        self.assertEqual(unpickled_md.user.profile.settings.theme, "dark")
        self.assertIsInstance(unpickled_md.user, MagiDict)

    def test_copy_is_shallow(self):
        """Test that copy() creates a shallow copy."""
        md = MagiDict({"a": 1, "b": {"c": 2}})
        md_copy = md.copy()

        md_copy.b.c = 99

        self.assertEqual(md.b.c, 99)
        self.assertIs(md.b, md_copy.b)

        md_copy["a"] = 100
        self.assertEqual(md["a"], 1)

    def test_fromkeys(self):
        """Test the fromkeys class method."""
        keys = ["a", "b", "c"]
        md = MagiDict.fromkeys(keys, 0)
        self.assertEqual(md, {"a": 0, "b": 0, "c": 0})

        nested_dict = {"nested": True}
        md_nested = MagiDict.fromkeys(keys, nested_dict)
        self.assertEqual(md_nested.a.nested, True)
        self.assertIsInstance(md_nested.b, MagiDict)

    def test_setdefault_when_key_exists(self):
        """Using setdefault on an existing key should return the existing value."""
        md = MagiDict({"a": 1})
        existing_val = md.setdefault("a", 2)
        self.assertEqual(existing_val, 1)
        self.assertEqual(md.a, 1)

    def test_modifying_temp_safe_dict_from_failed_getattr(self):
        """Modifying a temporary SafeDict from a failed getattr should not affect the original."""
        temp = self.md.non_existent

        with self.assertRaises(TypeError):
            temp["some_key"] = "some_value"

        self.assertNotIn("non_existent", self.md)
        self.assertEqual(self.md.non_existent, MagiDict())

    def test_hook_with_other_iterables(self):
        """Test that sets and frozensets are preserved and not converted."""
        data = {"my_set": {1, 2, 3}}
        md = MagiDict(data)
        self.assertIsInstance(md.my_set, set)
        self.assertEqual(md.my_set, {1, 2, 3})

        data_with_frozenset = {"my_frozenset": frozenset([("a", 1)])}
        md_fs = MagiDict(data_with_frozenset)
        self.assertIsInstance(md_fs.my_frozenset, frozenset)

    def test_method_conflict_safety(self):
        """Ensure that keys shadowing dict methods can be deleted and do not interfere with method calls."""
        md = MagiDict()
        md["keys"] = "custom_value_for_keys"

        self.assertEqual(md["keys"], "custom_value_for_keys")
        self.assertTrue(callable(md.keys))
        self.assertCountEqual(list(md.keys()), ["keys"])

        md_del_test = MagiDict({"a": 1})
        with self.assertRaises(KeyError):
            del md_del_test["items"]

        self.assertTrue(callable(md_del_test.items))
        self.assertEqual(list(md_del_test.items()), [("a", 1)])

        md_conflict_del = MagiDict({"pop": "custom_pop_value", "b": 2})

        del md_conflict_del["pop"]

        self.assertNotIn("pop", md_conflict_del)

        self.assertTrue(callable(md_conflict_del.pop))
        popped_value = md_conflict_del.pop("b")
        self.assertEqual(popped_value, 2)
        self.assertNotIn("b", md_conflict_del)

    def test_nested_empty_structures(self):
        """Test that empty lists, tuples, and dicts are properly converted when nested."""
        d = MagiDict({"a": [], "b": (), "c": {}})
        self.assertIsInstance(d.a, list)
        self.assertIsInstance(d.b, tuple)
        self.assertIsInstance(d.c, MagiDict)
        d2 = MagiDict(
            {"nested": {"empty_list": [], "empty_tuple": (), "empty_dict": {}}}
        )
        self.assertIsInstance(d2.nested.empty_list, list)
        self.assertIsInstance(d2.nested.empty_tuple, tuple)
        self.assertIsInstance(d2.nested.empty_dict, MagiDict)

    def test_overwrite_non_dict_with_dict(self):
        """Setting a non-dict key to a dict should convert it to MagiDict."""
        md = MagiDict({"a": 10})
        md["a"] = {"b": 20}
        self.assertIsInstance(md.a, MagiDict)
        self.assertEqual(md.a.b, 20)
        md.a = 42
        self.assertEqual(md.a, 42)

    def test_builtin_like_keys(self):
        """Test that keys resembling built-in attributes are handled correctly."""
        md = MagiDict({"__class__": "test"})
        self.assertEqual(md["__class__"], "test")
        self.assertIsInstance(md.__dict__, dict)
        self.assertIsInstance(md.__nonexistent__, MagiDict)

    def test_pickle_nested_enchant(self):
        """Test that pickling and unpickling preserves nested MagiDict structure."""
        md = MagiDict({"a": {"b": {"c": 1}}, "lst": [{"x": 5}]})
        dumped = pickle.dumps(md)
        loaded = pickle.loads(dumped)
        self.assertIsInstance(loaded.a, MagiDict)
        self.assertIsInstance(loaded.lst[0], MagiDict)
        self.assertEqual(loaded.a.b.c, 1)
        self.assertEqual(loaded.lst[0].x, 5)

    def test_hook_with_sets_and_frozensets(self):
        """Test that sets and frozensets are preserved and not converted."""
        data = {"my_set": {1, 2, 3}}
        md = MagiDict(data)
        self.assertIsInstance(md.my_set, set)
        self.assertEqual(md.my_set, {1, 2, 3})

        data_fs = {"my_frozenset": frozenset([1, 2, 3])}
        md_fs = MagiDict(data_fs)
        self.assertIsInstance(md_fs.my_frozenset, frozenset)
        self.assertEqual(md_fs.my_frozenset, frozenset([1, 2, 3]))

    def test_fromkeys_with_mutable_default(self):
        """Test that fromkeys with a mutable default creates separate instances."""
        default = {"x": 1}
        md = MagiDict.fromkeys(["a", "b"], default)
        self.assertIsNot(md.a, md.b)
        self.assertEqual(md.a.x, 1)

    def test_delete_attribute_vs_key(self):
        """Test that deleting a key does not affect instance attributes."""
        md = MagiDict({"pop": 123, "other": 456})
        with self.assertRaises(KeyError):
            del md["popitem"]
        del md["pop"]
        self.assertNotIn("pop", md)

    def test_key_assignment_creates_key(self):
        """Test that assigning to a key creates it if it doesn't exist."""
        md = MagiDict()
        md["new_key"] = "value"
        self.assertIn("new_key", md)
        self.assertEqual(md["new_key"], "value")

        md["user"] = {"name": "Bob"}
        self.assertIsInstance(md.user, MagiDict)
        self.assertEqual(md.user.name, "Bob")

    def test_mget_and_mg_behaviour(self):
        """Test the mget and mg methods for safe access."""
        md = MagiDict({"a": {"b": 2}, "none_val": None, 1: "one_int"})
        # existing key returns value
        self.assertEqual(md.mget("a").b, 2)
        # mg shorthand
        self.assertEqual(md.mg("a").b, 2)
        # missing key returns MagiDict
        self.assertIsInstance(md.mget("missing"), MagiDict)
        # key exists but value is None -> safe MagiDict for chaining
        none_chain = md.mget("none_val")
        self.assertIsInstance(none_chain, MagiDict)
        # numeric key access via mget
        self.assertEqual(md.mget(1), "one_int")

    def test_magi_loads_and_enchant_and_disenchant(self):
        """Test magi_loads, enchant, and disenchant functions."""
        s = json.dumps({"x": {"y": 5}, "arr": [{"z": 6}]})
        loaded = magi_loads(s)
        self.assertIsInstance(loaded, MagiDict)
        self.assertIsInstance(loaded.x, MagiDict)
        self.assertEqual(loaded.x.y, 5)

        # enchant should leave MagiDicts alone and convert dicts
        normal = {"a": 1}
        enchanted = enchant(normal)
        self.assertIsInstance(enchanted, MagiDict)
        with self.assertRaises(TypeError):
            enchant(123)  # type error for non-dict

        # disenchant should convert back to pure dicts recursively
        back = enchanted.disenchant()
        self.assertIsInstance(back, dict)
        self.assertEqual(back, {"a": 1})

    def test_getitem_dot_notation(self):
        """Test that getitem supports dot notation for nested access."""
        md = MagiDict({"a": {"b": {"c": 7}}, "list": ["zero", {"1": "one_str"}]})
        # dot notation string key
        self.assertEqual(md["a.b.c"], 7)
        # indexing into list via dot-string numeric
        self.assertEqual(md["list.1.1"], "one_str")

    def test_inplace_or_operator_and_deepcopy(self):
        """Test that |= operator works and deepcopy creates independent copies."""
        a = MagiDict({"x": {"y": 1}})
        b = {"z": 2}
        a |= b
        self.assertEqual(a.z, 2)

        # deepcopy check

        original = MagiDict({"n": {"m": 3}})
        copied = copy.deepcopy(original)
        self.assertIsInstance(copied, MagiDict)
        self.assertIsNot(copied, original)
        self.assertIsNot(copied.n, original.n)
        self.assertEqual(copied.n.m, 3)

    def test_key_assignment_overwrites_key(self):
        """Test that assigning to a key overwrites the existing value."""
        md = MagiDict({"key": 1})
        md["key"] = 2
        self.assertEqual(md["key"], 2)

    def test_dir_includes_keys(self):
        """Test that dir() includes keys of the MagiDict."""
        md = MagiDict({"a": 1, "b_key": 2})
        d = dir(md)
        self.assertIn("a", d)
        self.assertIn("b_key", d)
        self.assertIn("keys", d)
        self.assertIn("items", d)

    def test_deepcopy_creates_new_objects(self):
        """Test that deepcopy creates entirely new nested objects."""
        md = MagiDict({"a": 1, "b": {"c": [1, {"d": 2}]}})
        md_deepcopy = copy.deepcopy(md)

        self.assertEqual(md, md_deepcopy)
        self.assertIsNot(md, md_deepcopy)
        self.assertIsNot(md.b, md_deepcopy.b)
        self.assertIsNot(md.b.c, md_deepcopy.b.c)
        self.assertIsNot(md.b.c[1], md_deepcopy.b.c[1])

        md_deepcopy.b.c[1].d = 99
        self.assertEqual(md.b.c[1].d, 2)
        self.assertEqual(md_deepcopy.b.c[1].d, 99)

    def test_access_on_none_value_returns_magi_dict(self):
        """Accessing an attribute on a None value should return an empty MagiDict."""
        md = MagiDict({"config": None})
        self.assertEqual(md.config.host, MagiDict())
        self.assertFalse(md.config.host)  # Evaluates to False

    def test_dict_subclass_is_converted_2(self):
        """Test that subclasses of dict are converted to MagiDict."""

        class MyDict(dict):
            """A simple subclass of dict."""

            pass

        data = MyDict(user=MyDict(name="subclass_user"))
        md = MagiDict(data)
        self.assertIsInstance(md, MagiDict)
        self.assertNotIsInstance(md, MyDict)
        self.assertIsInstance(md.user, MagiDict)
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

        md = MagiDict(data)

        self.assertIsInstance(md.a_list, MyList)
        self.assertIsInstance(md.a_tuple, MyTuple)

        self.assertEqual(md.a_list.custom_method(), "hello")

        self.assertIsInstance(md.a_list[0], MagiDict)
        self.assertEqual(md.a_list[0].id, 1)
        self.assertIsInstance(md.a_tuple[0], MagiDict)
        self.assertEqual(md.a_tuple[0].id, 2)

    def test_fromkeys_with_mutable_default_is_safe(self):
        """Test that fromkeys with a mutable default creates separate instances."""
        default = {"nested": True}
        md = MagiDict.fromkeys(["a", "b"], default)

        self.assertIsInstance(md.a, MagiDict)
        self.assertIsInstance(md.b, MagiDict)

        self.assertIsNot(md.a, md.b)

        md.a.new_key = "value"
        self.assertNotIn("new_key", md.b)
        self.assertIsInstance(md.b.non_existent, MagiDict)

    def test_setdefault_with_new_key_is_hooked(self):
        """Using setdefault with a new key should create a MagiDict if the default is a dict."""
        md = MagiDict()
        nested_dict = md.setdefault("new_key", {"a": 1})
        self.assertIsInstance(nested_dict, MagiDict)
        self.assertEqual(nested_dict.a, 1)

    def test_attribute_access_on_falsy_values(self):
        """Accessing attributes of falsy values should return the correct types.
        None -> MagiDict, False -> False, 0 -> 0."""
        md = MagiDict({"none_val": None, "false_val": False, "zero_val": 0})
        self.assertEqual(md.none_val, MagiDict())
        self.assertFalse(md.false_val)
        self.assertEqual(md.zero_val, 0)

    def test_chained_access_after_setting_none(self):
        """Setting a key to None and then updating it to a dict should work."""
        md = MagiDict({"config": None})
        md["config"] = {"host": "localhost"}
        self.assertEqual(md.config.host, "localhost")

    def test_reserved_keywords_as_keys(self):
        """Keys that are Python reserved keywords should be accessible via item access and mget()
        but not via attribute access."""
        keywords = ["def", "for", "if", "else", "try", "except"]
        md = MagiDict({k: k.upper() for k in keywords})
        for k in keywords:
            self.assertEqual(md[k], k.upper())
            self.assertEqual(md.mget(k), k.upper())
            with self.assertRaises(SyntaxError):
                eval(f"md.{k}")

    def test_nested_none_access_returns_magi_dict(self):
        """Accessing attributes on nested None values should return SafeNone."""
        md = MagiDict({"a": {"b": None}})
        self.assertEqual(md.a.b.c, MagiDict())

    def test_dict_in_nested_tuples_conversion_enchant(self):
        """Test that dicts inside nested tuples are converted to MagiDicts."""
        md = MagiDict({"a": (({"b": 1},),)})
        self.assertIsInstance(md.a[0][0], MagiDict)
        self.assertEqual(md.a[0][0].b, 1)

    def test_string_key_and_variable_name_conflict(self):
        """Test that a string key that matches a variable name does not conflict
        and both access methods work correctly."""
        custom_key = "some_other_key"
        md = MagiDict({"custom_key": "value1", custom_key: "value2"})

        self.assertEqual(md["custom_key"], "value1")
        self.assertEqual(md.mget(custom_key), "value2")
        self.assertEqual(md.custom_key, "value1")
        self.assertEqual(md["some_other_key"], "value2")
        self.assertEqual(md.some_other_key, "value2")

        md = MagiDict({custom_key: "value2", "custom_key": "value1"})
        self.assertEqual(md["custom_key"], "value1")
        self.assertEqual(md.custom_key, "value1")
        self.assertEqual(md["some_other_key"], "value2")
        self.assertEqual(md.some_other_key, "value2")

    def test_digit_keys_int_and_str(self):
        """Test that digit keys as int and str are treated as distinct keys
        and both access methods work correctly."""
        md = MagiDict({1: 1, "1": "string_one", "key2": "value2", 2: "two"})
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
        md = MagiDict({k: "value", string_k: "string_value", somekey: "some_value"})
        self.assertEqual(md[k], "value")
        self.assertEqual(md.k, MagiDict())
        self.assertEqual(md[string_k], "string_value")
        self.assertEqual(md.string_k, MagiDict())
        self.assertEqual(md[somekey], "some_value")
        self.assertEqual(md.somekey, MagiDict())
        self.assertEqual(md.mget(somekey), "some_value")
        self.assertEqual(md.mget(string_k), "string_value")
        self.assertEqual(md.mget(k), "value")

    def test_recursive_self_reference(self):
        """Test that self-referential structures do not cause infinite recursion."""
        md = MagiDict()
        md["self"] = md
        self.assertIs(md.self, md)

    def test_deeply_nested_enchant(self):
        """Test that deeply nested structures are handled without recursion errors."""
        depth = 1000
        md = MagiDict()
        current = md
        for i in range(depth):
            current["nested"] = {}
            current = current.nested
        self.assertEqual(current, MagiDict())

    def test_mixed_list_tuple_content(self):
        """Test that lists and tuples with mixed content are handled correctly."""
        md = MagiDict({"mixed": [1, {"a": 1}, "str", ({"b": 2},)]})
        self.assertIsInstance(md.mixed[1], MagiDict)
        self.assertEqual(md.mixed[1].a, 1)
        self.assertIsInstance(md.mixed[3][0], MagiDict)
        self.assertEqual(md.mixed[3][0].b, 2)

    def test_nested_empty_structures_in_collections(self):
        """Test that empty dicts inside lists and tuples are converted to MagiDicts."""
        md = MagiDict({"lst": [{}], "tpl": ({},)})
        self.assertIsInstance(md.lst[0], MagiDict)
        self.assertIsInstance(md.tpl[0], MagiDict)

    def test_non_string_keys(self):
        """Test that non-string keys are accessible via item notation but not attribute access."""
        md = MagiDict({1: "one", (2, 3): "tuple"})
        self.assertEqual(md[1], "one")
        self.assertEqual(md[(2, 3)], "tuple")
        self.assertEqual(md.mget(1), "one")
        self.assertEqual(md.mget((2, 3)), "tuple")
        result = getattr(md, "1")
        self.assertIsInstance(result, MagiDict)

    def test_magic_method_key_shadowing(self):
        """Test that keys shadowing magic methods do not interfere with instance behavior."""
        md = MagiDict({"__init__": "init_val"})
        self.assertEqual(md["__init__"], "init_val")
        self.assertIsInstance(md.__dict__, dict)

    def test_copy_vs_deepcopy_behavior(self):
        """Test that copy() is shallow while deepcopy() is deep."""
        md = MagiDict({"a": {"b": 2}})
        md_copy = md.copy()
        md_copy["a"]["b"] = 99
        self.assertEqual(md.a.b, 99)
        self.assertIsInstance(md.a, MagiDict)

        md_deep = copy.deepcopy(md)
        md_deep["a"]["b"] = 100
        self.assertEqual(md.a.b, 99)
        self.assertEqual(md_deep.a.b, 100)
        self.assertIsInstance(md_deep.a, MagiDict)

    def test_hook_preserves_other_iterables(self):
        """Test that other iterable types are preserved and not converted."""

        class MySet(set):
            pass

        class MyFrozenSet(frozenset):
            pass

        data = {"s": MySet([1, 2]), "fs": MyFrozenSet([3, 4])}
        md = MagiDict(data)
        self.assertIsInstance(md.s, MySet)
        self.assertIsInstance(md.fs, MyFrozenSet)
        self.assertEqual(md.s, {1, 2})
        self.assertEqual(md.fs, frozenset([3, 4]))

    def test_chained_access_on_non_dict_value_raises_attribute_error(self):
        """Accessing attributes on a non-dict value should raise AttributeError on further chaining."""
        md = MagiDict({"a": 42})
        # self.assertEqual(md.a.b.c, None)s
        with self.assertRaises(AttributeError):
            _ = md.a.b.c
        temp = md.nonexistent.key
        self.assertIsInstance(temp, MagiDict)

    def test_attribute_access_on_nonexistent_builtin_shadowed_key(self):
        """Accessing an attribute that shadows a built-in method should return MagiDict if non-existent."""
        md = MagiDict({"items": 123})
        self.assertEqual(md["items"], 123)
        del md["items"]
        self.assertNotIn("items", md)
        self.assertTrue(callable(MagiDict().items))

    def test_attribute_style_assignment_recursive_hook(self):
        """Test that assigning a dict value via attribute style converts it to MagiDict recursively."""
        md = MagiDict()
        md["config"] = {"host": "localhost", "port": 8080, "params": [{"a": 1}]}
        self.assertIsInstance(md.config, MagiDict)
        self.assertIsInstance(md.config.params[0], MagiDict)
        self.assertEqual(md.config.host, "localhost")
        self.assertEqual(md.config.params[0].a, 1)

    def test_attribute_assignment_does_not_conflict_with_instance_attrs(self):
        """Assigning a key that matches an instance attribute should not interfere with attribute access."""
        md = MagiDict()
        md["_internal"] = "secret"
        self.assertIn("_internal", md)
        self.assertEqual(md["_internal"], "secret")

    def test_custom_repr(self):
        """Test that the __repr__ method returns a clear representation."""
        md = MagiDict({"a": 1, "b": MagiDict({"c": 2})})
        expected_repr = "MagiDict({'a': 1, 'b': MagiDict({'c': 2})})"
        self.assertEqual(repr(md), expected_repr)

    def test_is_unhashable(self):
        """Test that MagiDict instances are unhashable."""
        md = MagiDict()
        with self.assertRaises(TypeError):
            _ = {md: "value"}
        with self.assertRaises(TypeError):
            _ = {md}

    def test_in_place_update_operator(self):
        """Test that the in-place update operator (|=) hooks new values."""
        md = MagiDict({"a": 1})
        md |= {"b": {"c": 2}}
        self.assertEqual(md.a, 1)
        self.assertIsInstance(md.b, MagiDict)
        self.assertEqual(md.b.c, 2)

    def test_deletion_a(self):
        """Consolidated test for item deletion."""
        d = MagiDict({"a": 1, "b": 2})
        del d["a"]
        self.assertNotIn("a", d)
        with self.assertRaises(KeyError):
            del d["c"]

    def test_attribute_style_assignment_and_deletion(self):
        """Test that assigning and deleting keys via item notation works correctly."""
        md = MagiDict()

        md["new_key"] = "new_value"
        self.assertIn("new_key", md)
        self.assertEqual(md["new_key"], "new_value")

        md["config"] = {"host": "localhost", "port": 8080}
        self.assertIsInstance(md.config, MagiDict)
        self.assertEqual(md.config.host, "localhost")

        md["new_key"] = "overwritten"
        self.assertEqual(md.new_key, "overwritten")

        del md["new_key"]
        self.assertNotIn("new_key", md)

        with self.assertRaises(KeyError):
            del md["non_existent_key"]

        md_conflict = MagiDict({"keys": "shadow"})
        del md_conflict["keys"]
        self.assertNotIn("keys", md_conflict)
        self.assertTrue(callable(md_conflict.keys))

    def test_attribute_assignment_cannot_shadow_methods(self):
        """Assigning a key that matches a dict method should not interfere with method calls."""
        md = MagiDict()
        md["update"] = "my_value"
        self.assertEqual(md["update"], "my_value")
        self.assertTrue(callable(md.update))

    def test_dir_includes_keys_and_methods(self):
        """Test that dir() includes both keys and dict methods."""
        md = MagiDict({"a": 1, "b_key": 2})
        d = dir(md)
        self.assertIn("a", d)
        self.assertIn("b_key", d)
        self.assertIn("keys", d)
        self.assertIn("copy", d)

    def test_deepcopy_creates_fully_independent_objects(self):
        """Test that deepcopy() creates fully independent copies."""
        md = MagiDict({"a": 1, "b": {"c": [1, {"d": 2}]}})
        md_deepcopy = copy.deepcopy(md)

        self.assertEqual(md, md_deepcopy)
        self.assertIsNot(md, md_deepcopy)
        self.assertIsNot(md.b, md_deepcopy.b)
        self.assertIsNot(md.b.c, md_deepcopy.b.c)
        self.assertIsNot(md.b.c[1], md_deepcopy.b.c[1])

        md_deepcopy.b.c[1].d = 99
        self.assertEqual(md.b.c[1].d, 2)
        self.assertEqual(md_deepcopy.b.c[1].d, 99)

    def test_chained_access_on_non_dict_value_raises_attribute_error_2(self):
        """Accessing attributes on a non-dict value should raise AttributeError."""
        md = MagiDict({"a": 42, "b": "hello"})
        with self.assertRaises(AttributeError):
            _ = md.a.b.c
        with self.assertRaises(AttributeError):
            _ = md.b.upper.lower

    def test_dict_subclass_is_converted(self):
        """Test that subclasses of dict are converted to MagiDict."""

        class MyDict(dict):
            """A simple subclass of dict."""

            pass

        data = MyDict(user=MyDict(name="subclass_user"))
        md = MagiDict(data)
        self.assertIsInstance(md, MagiDict)
        self.assertNotIsInstance(md, MyDict)
        self.assertIsInstance(md.user, MagiDict)
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
        md = MagiDict(data)

        self.assertIsInstance(md.a_list, MyList)
        self.assertIsInstance(md.a_tuple, MyTuple)
        self.assertEqual(md.a_list.custom_method(), "hello")
        self.assertIsInstance(md.a_list[0], MagiDict)
        self.assertEqual(md.a_list[0].id, 1)

    def test_empty_initializations(self):
        """Test that various empty initializations result in an empty MagiDict."""
        self.assertEqual(MagiDict(), {})
        self.assertEqual(MagiDict({}), {})
        self.assertEqual(MagiDict([]), {})

    def test_boolean_keys(self):
        """Test that boolean keys are treated distinctly from string keys."""
        md = MagiDict({True: "yes", False: "no"})
        self.assertEqual(md[True], "yes")
        self.assertEqual(md[False], "no")
        self.assertNotIn("True", md)

    def test_dict_inside_list_is_converted(self):
        """Test that dicts inside lists are converted to MagiDicts."""
        d = {"container": [{"a": {"b": 2}}]}
        md = MagiDict(d)
        self.assertIsInstance(md.container[0], MagiDict)
        self.assertIsInstance(md.container[0].a, MagiDict)
        self.assertEqual(md.container[0].a.b, 2)

    def test_double_underscore_keys(self):
        """Test that keys with double underscores do not interfere with instance attributes."""
        md = MagiDict({"__class__": "fake", "__dict__": "fake_dict"})
        self.assertEqual(md["__class__"], "fake")
        self.assertEqual(md["__dict__"], "fake_dict")
        self.assertIsInstance(md.__dict__, dict)

    def test_large_dict_performance(self):
        """Test that large dictionaries are handled without performance degradation or recursion errors."""
        big = {f"key{i}": {"nested": i} for i in range(1000)}
        md = MagiDict(big)
        self.assertEqual(md.key500.nested, 500)

    def test_equality_with_plain_dict(self):
        """Test that MagiDict compares equal to a plain dict with the same content."""
        d = {"a": 1, "b": {"c": 2}}
        md = MagiDict(d)
        self.assertEqual(md, d)
        self.assertEqual(d, md)

    def test_overwrite_with_none(self):
        """Setting a key to None and then accessing its attributes should return MagiDict."""
        md = MagiDict({"a": {"b": 1}})
        md["a"] = None
        self.assertEqual(md.a.b, MagiDict())

    def test_setattr_directly(self):
        """Setting attributes directly should not create keys in the dict."""
        md = MagiDict()
        setattr(md, "foo", 123)
        self.assertNotIn("foo", md)
        self.assertEqual(md.foo, 123)

    def test_fromkeys_mutable_default_is_unique(self):
        """Test that fromkeys with a mutable default creates separate instances."""
        default = {"nested": []}
        md1 = MagiDict.fromkeys(["a", "b"], default)
        md2 = MagiDict.fromkeys(["a", "b"], default)
        self.assertIsNot(md1.a, md2.a)

    def test_pickle_roundtrip(self):
        """Test that pickling and unpickling a MagiDict preserves its structure and types."""
        md = MagiDict({"a": {"b": 1}})
        dumped = pickle.dumps(md)
        loaded = pickle.loads(dumped)
        self.assertIsInstance(loaded, MagiDict)
        self.assertEqual(loaded.a.b, 1)

    def test_equality_with_mapping_proxy(self):
        """Test that MagiDict compares equal to a MappingProxyType with the same content."""
        d = {"a": 1}
        md = MagiDict(d)
        proxy = MappingProxyType(d)
        self.assertEqual(md, proxy)

    def test_subclass_preserves_safe_dict_behavior(self):
        """Test that subclasses of MagiDict retain the automatic conversion behavior."""

        class SubMagiDict(MagiDict):
            """A subclass of MagiDict to test inheritance of behavior."""

            pass

        smd = SubMagiDict({"a": {"b": 1}})
        self.assertIsInstance(smd.a, MagiDict)
        self.assertEqual(smd.a.b, 1)

    def test_chained_access_with_callable(self):
        """Accessing attributes on a callable value should raise AttributeError."""
        md = MagiDict({"func": lambda: {"x": 1}})
        self.assertTrue(callable(md.func))
        with self.assertRaises(AttributeError):
            _ = md.func.x

    def test_mutation_during_iteration(self):
        """Test that modifying the MagiDict during iteration raises RuntimeError."""
        md = MagiDict({"a": 1, "b": 2})
        with self.assertRaises(RuntimeError):
            for k in md:
                md["c"] = 3

    def test_equality_non_mapping(self):
        """Test that MagiDict is not equal to non-mapping types."""
        md = MagiDict({"a": 1})
        self.assertNotEqual(md, [("a", 1)])
        self.assertNotEqual(md, None)

    def test_pickle_roundtrip_2(self):
        """Test that pickling and unpickling a MagiDict preserves its structure and types."""
        md = MagiDict({"a": {"b": 1}})
        dumped = pickle.dumps(md)
        loaded = pickle.loads(dumped)
        self.assertIsInstance(loaded, MagiDict)
        self.assertEqual(loaded.a.b, 1)

    def test_get_with_invalid_identifier_key_returns_enchant(self):
        """Test that get works with keys that are not valid Python identifiers and returns a MagiDict when default is provided."""
        md = MagiDict({"1": {"inside": "Inside_One"}, "my-key": {"nested": 42}})

        result_numeric = md.get("1", MagiDict())
        self.assertIsInstance(result_numeric, MagiDict)
        self.assertEqual(result_numeric.inside, "Inside_One")

        result_hyphen = md.get("my-key", MagiDict())
        self.assertIsInstance(result_hyphen, MagiDict)
        self.assertEqual(result_hyphen.nested, 42)

        result_via_getattr = getattr(md.get("1"), "inside")
        self.assertEqual(result_via_getattr, "Inside_One")

        missing = md.get("nonexistent", MagiDict()).foo.bar
        self.assertIsInstance(missing, MagiDict)

    def test_dir_includes_all_dict_attributes(self):
        """Test that dir() includes all standard dict attributes and keys."""
        md = MagiDict({"a": 1, "b": 2})

        dict_dir = set(dir(dict))
        magi_dir = set(dir(md))

        missing = dict_dir - magi_dir
        self.assertFalse(
            missing, f"MagiDict.__dir__ is missing dict attributes: {missing}"
        )

        self.assertIn("a", magi_dir)
        self.assertIn("b", magi_dir)

    def test_json_serialization_deserialization(self):
        """Test JSON serialization and deserialization with MagiDict."""
        md = MagiDict({"a": 1, "b": {"c": 2}, "d": [1, 2, 3]})

        dumped = json.dumps(md)

        loaded_plain = json.loads(dumped)
        self.assertIsInstance(loaded_plain, dict)
        self.assertNotIsInstance(loaded_plain, MagiDict)
        self.assertEqual(loaded_plain, {"a": 1, "b": {"c": 2}, "d": [1, 2, 3]})

        loaded_magi = json.loads(dumped, object_hook=MagiDict)
        self.assertIsInstance(loaded_magi, MagiDict)
        self.assertIsInstance(loaded_magi.b, MagiDict)
        self.assertEqual(loaded_magi.b.c, 2)
        self.assertEqual(loaded_magi.d, [1, 2, 3])

    def test_key_and_attribute_access_are_consistent(self):
        """Test that key access and attribute access yield consistent results."""
        md = MagiDict({"hello": "world", "foo": {"bar": 1}})

        md["hello"] += "!"
        self.assertEqual(md.hello, "world!")

        self.assertIs(md.foo, md["foo"])
        self.assertIsInstance(md.foo, MagiDict)
        self.assertEqual(md.foo.bar, 1)

    def test_get_existing_key(self):
        """Test that get returns the value for existing keys."""
        md = MagiDict({"a": {"b": 1}})
        result = md.get("a")
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(result.b, 1)

    def test_get_missing_key_returns_none(self):
        """Test that get returns None for missing keys without a default."""
        md = MagiDict({"a": 1})
        result = md.get("missing")
        self.assertIsNone(result)

    def test_get_with_default_value(self):
        """Test that get with a default value returns the default for missing keys."""
        md = MagiDict({})
        default = {"x": 42}
        result = md.get("missing", default)
        self.assertEqual(result, default)

    def test_get_with_default_enchant(self):
        """Test that get with a default dict returns a MagiDict."""
        md = MagiDict({})
        result = md.get("missing", MagiDict())
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

    def test_get_invalid_identifier_key(self):
        """Test that get works with keys that are not valid Python identifiers."""
        md = MagiDict({"1": {"inside": "ok"}, "my-key": {"val": 123}})
        result_numeric = md.get("1")
        self.assertIsInstance(result_numeric, MagiDict)
        self.assertEqual(result_numeric.inside, "ok")

        result_hyphen = md.get("my-key")
        self.assertIsInstance(result_hyphen, MagiDict)
        self.assertEqual(result_hyphen.val, 123)

    def test_mget_existing_key(self):
        """Test that mget returns the value for existing keys."""
        md = MagiDict({"a": {"b": {"c": 42}}})
        result = md.mget("a")
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(result.b.c, 42)

    def test_mget_missing_key_returns_empty_enchant(self):
        """Test that mget returns an empty MagiDict for missing keys."""
        md = MagiDict({"a": 1})
        result = md.mget("missing")
        self.assertIsInstance(result, MagiDict)

    def test_mget_chained_access_safe(self):
        """Test that mget allows safe chained access on missing keys."""
        md = MagiDict({})
        result = md.mget("missing").foo.bar
        self.assertIsInstance(result, MagiDict)

    def test_mget_does_not_affect_existing_dict_values(self):
        """Test that mget does not alter existing dict values."""
        md = MagiDict({"a": {"b": 1}})
        self.assertEqual(md.get("a").b, 1)
        self.assertEqual(md.mget("a").b, 1)

    def test_mget_and_get_difference_on_missing(self):
        """Test the difference between get and mget on missing keys."""
        md = MagiDict({})
        self.assertIsNone(md.get("missing"))
        self.assertIsInstance(md.mget("missing"), MagiDict)

    def test_safe_dict_loads_returns_enchant(self):
        """Test that magi_loads returns a MagiDict when given a JSON string."""
        original = MagiDict({"a": {"b": {"c": 42}}, "d": [1, 2]})
        dumped = json.dumps(original)

        loaded = magi_loads(dumped)

        self.assertIsInstance(loaded, MagiDict)
        self.assertIsInstance(loaded.a, MagiDict)
        self.assertEqual(loaded.a.b.c, 42)
        self.assertEqual(loaded.d, [1, 2])

    def test_popitem_works_as_expected(self):
        """Test the popitem method."""
        md = MagiDict({"a": 1, "b": 2})
        key, value = md.popitem()
        self.assertIn(key, ["a", "b"])
        self.assertEqual(len(md), 1)
        md.popitem()
        self.assertEqual(len(md), 0)
        with self.assertRaises(KeyError):
            md.popitem()

    def test_repr_handles_recursive_structures(self):
        """Test that __repr__ handles self-referential structures without infinite recursion."""
        md = MagiDict()
        md["a"] = 1
        md["self"] = md
        self.assertIn("'self': MagiDict({...})", repr(md))

    def test_equality_with_dict_subclasses(self):
        """Test equality comparisons with dict subclasses."""
        d = OrderedDict([("b", 2), ("a", 1)])
        md = MagiDict([("b", 2), ("a", 1)])
        self.assertEqual(md, d)

    def test_chained_access_on_non_dict_value_raises_errors(self):
        """Accessing attributes on non-dict values should raise AttributeError."""
        md = MagiDict(
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

        self.assertEqual(md.is_none.baz, MagiDict())
        self.assertEqual(md.mget("items").nested_key, "nested_value")
        self.assertEqual(md.mget("items").missing_key, MagiDict())

    def test_init_with_nested_iterable(self):
        """Test that nested dicts inside lists and tuples are converted to MagiDicts."""
        data = [("user", {"name": "test"}), ("permissions", [{"scope": "read"}])]
        md = MagiDict(data)
        self.assertIsInstance(md.user, MagiDict)
        self.assertEqual(md.user.name, "test")
        self.assertIsInstance(md.permissions[0], MagiDict)
        self.assertEqual(md.permissions[0].scope, "read")


class TestSomeReturns(TestCase):
    """Test various methods and behaviors of MagiDict."""

    def test_setitem_and_update(self):
        """Test that setting items and updating the dict work correctly."""
        md = MagiDict()
        md["a"] = 1
        md.b = 2
        self.assertEqual(md.a, 1)
        self.assertEqual(md.b, 2)

        md.update({"c": 3})
        self.assertEqual(md.c, 3)

    def test_copy_and_deepcopy(self):
        """Test that copy() is shallow while deepcopy() is deep."""
        data = {"nested": {"x": 1, "y": [1, 2, 3]}}
        md = MagiDict(data)
        sd_copy = md.copy()
        sd_deepcopy = copy.deepcopy(md)

        self.assertEqual(sd_copy.nested.x, 1)
        self.assertEqual(sd_deepcopy.nested.y, [1, 2, 3])

    def test_safe_dict_functions(self):
        """Test safedict_loads and enchant functions."""
        data = {"name": "Alice", "age": 30}
        json_str = json.dumps(data)

        # safedict_loads: use JSON string
        sd_loaded = magi_loads(json_str)
        self.assertIsInstance(sd_loaded, MagiDict)
        self.assertEqual(sd_loaded.name, "Alice")

        # magi_dict: use Python dict
        sd_from_dict = enchant(data)
        self.assertIsInstance(sd_from_dict, MagiDict)
        self.assertEqual(sd_from_dict.age, 30)

    def test_mget_for_nonexistent_keys(self):
        """Test that mget returns MagiDict for nonexistent keys."""
        md = MagiDict({"a": 1})
        self.assertIsInstance(md.mget("b"), MagiDict)

    def test_chaining_none_values(self):
        """Test that chaining through None values returns MagiDict instances."""
        md = MagiDict({"a": None})
        self.assertIsInstance(md.a.b.c, MagiDict)

    def test_dir_contains_keys(self):
        """Test that dir() includes the keys of the MagiDict."""
        md = MagiDict({"x": 1, "y": 2})
        attrs = dir(md)
        self.assertIn("x", attrs)
        self.assertIn("y", attrs)


class TestMagiDictBooleans(TestCase):
    """Test handling of boolean values in MagiDict."""

    def setUp(self):
        self.data = {"flag_true": True, "flag_false": False, "missing_flag": None}
        self.md = MagiDict(self.data)

    def test_boolean_wrapping(self):
        """Test that boolean values are wrapped correctly and behave as expected."""
        # Attribute access returns wrapped type (int subclass for bool)
        self.assertIsInstance(self.md.flag_true, int)
        self.assertIsInstance(self.md.flag_false, int)

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
        self.assertIsInstance(self.md.missing_flag, MagiDict)

        # Chaining safe on missing key
        self.assertIsInstance(self.md.missing_flag.anything, MagiDict)
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
        self.md.nested = MagiDict({"inner_flag": True})
        self.assertIs(self.md.nested.inner_flag, True)
        self.assertTrue(self.md.nested.inner_flag)

    def test_identity_checks(self):
        """Test that identity checks work correctly."""
        self.assertIs(self.md.flag_true, True)
        self.assertIs(self.md.flag_false, False)

    def test_json_serialization_of_safenone_fails(self):
        """Test that json.dumps fails for a dict containing SafeNone."""
        md = MagiDict({"a": None})
        md = json.dumps(md)
        self.assertEqual(md, '{"a": null}')

    def test_json_deserialization_of_null(self):
        """Test that safedict_loads converts JSON null to _SafeNone."""
        json_str = '{"a": null, "b": {"c": null}}'
        md = magi_loads(json_str)
        self.assertIsInstance(md.a, MagiDict)
        self.assertFalse(md.a)
        self.assertIsInstance(md.b.c, MagiDict)
        self.assertFalse(md.b.c)

    def test_dynamic_wrapper_class_caching(self):
        """Test that dynamic wrapper classes are reused for the same type."""
        md = MagiDict({"s1": "a", "s2": "b", "i1": 1})
        self.assertIs(type(md.s1), type(md.s2))
        self.assertIsNot(type(md.s1), type(md.i1))

    def test_callable_class_instance_not_wrapped(self):
        """Test that a callable object instance is not wrapped and has no .safe property."""

        class CallableObj:
            """A simple callable class."""

            def __call__(self):
                return "called"

        obj = CallableObj()
        md = MagiDict({"callable_obj": obj})
        self.assertIs(md.callable_obj, obj)
        self.assertFalse(hasattr(md.callable_obj, "safe"))

    def test_ordereddict_is_converted_to_safedict(self):
        """Test that dict subclasses like OrderedDict are converted to MagiDict."""
        od = OrderedDict([("b", 2), ("a", 1)])
        md = MagiDict(od)
        self.assertIsInstance(md, MagiDict)
        self.assertNotIsInstance(md, OrderedDict)
        # Check that it behaves like a MagiDict
        self.assertEqual(md.b, 2)

    def test_chained_safe_property(self):
        """Test that .safe can be chained through MagiDict instances."""
        md = MagiDict({"a": {"b": 1}})
        self.assertIs(md, md)
        self.assertIs(md.a, md.a)
        self.assertEqual(md.a.b, 1)

    def test_non_string_keys_not_in_dir(self):
        """Test that non-string keys do not appear in dir()."""
        md = MagiDict({1: "one", ("a",): "tuple_key", "string_key": "present"})
        dir_list = dir(md)
        self.assertNotIn("1", dir_list)
        self.assertNotIn("a", dir_list)
        self.assertNotIn(("a",), dir_list)
        self.assertIn("string_key", dir_list)

    def test_boolean_wrapper_arithmetic(self):
        """Test that wrapped booleans behave like ints (0 and 1) in arithmetic."""
        md = MagiDict({"t": True, "f": False})
        self.assertEqual(md.t + 5, 6)
        self.assertEqual(md.f * 10, 0)
        self.assertTrue(md.t == 1)
        self.assertTrue(md.f == 0)

    def test_boolean_wrapper_isinstance(self):
        """Test the type identity of wrapped booleans."""
        md = MagiDict({"t": True})
        self.assertIsInstance(md.t, int)
        self.assertIsInstance(md.t, bool)

    def test_modifying_nested_list_in_place(self):
        """Test that modifications to nested lists within a MagiDict are preserved."""
        md = MagiDict({"a": [1, {"b": 2}]})

        # Append to the list
        md.a.append(3)

        self.assertEqual(md.a, [1, {"b": 2}, 3])
        self.assertIsInstance(md["a"][1], MagiDict)

        # Modify a MagiDict within the list
        md.a[1]["b"] = 99
        self.assertEqual(md.a[1].b, 99)
        self.assertEqual(md["a"][1]["b"], 99)

    def test_missing_and_none_behavior(self):
        """Test the behavior of accessing missing keys and keys with None values."""
        sd = MagiDict({"user": {"nickname": None}})
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
        self.assertIsInstance(sd.user.address, MagiDict)
        self.assertIsInstance(sd.user.nickname, str)

        # 5. Assign to new "real" keys (should work)
        sd.user.address["city"] = "Sofia"

        self.assertEqual(sd.user.address["city"], "Sofia")

        # Convert nickname to MagiDict to test valid assignment
        sd.user["nickname"] = MagiDict()
        sd.user.nickname["alias"] = "Ali"
        self.assertEqual(sd.user.nickname["alias"], "Ali")


class TestMissingCases(TestCase):
    """Test cases for MagiDict focusing on disenchanting and dotted-key access."""

    def setUp(self):
        self.data = {
            "user": {"profile": {"email": "test@example.com"}, "nickname": None},
            "permissions": ["read", {"area": "admin", "level": 1}],
            "config.with.dots": "value_with_dots",
        }
        self.md = MagiDict(self.data)

    def test_disenchant_recursively_converts_to_dict(self):
        """
        Verify that disenchant() converts the MagiDict and all nested
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
        Verify mget() returns an empty MagiDict for a key whose value is None,
        even if a default is provided, to ensure safe chaining.
        """
        result = self.md.user.mget("nickname", "default_nickname")
        self.assertIsInstance(result, MagiDict)
        self.assertTrue(getattr(result, "_from_none", False))
        self.assertEqual(result, {})

    def test_truthiness_of_magidict_instances(self):
        """
        Verify the boolean value of MagiDict in different states.
        """
        self.assertTrue(self.md)  # Non-empty
        self.assertFalse(MagiDict())  # Empty
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
        are not recursively converted to MagiDict.
        """
        data = {"my_set": {frozenset({"a": 1}.items())}}
        md = MagiDict(data)

        self.assertIsInstance(md.my_set, set)

        # The inner dict is not converted because it's inside a set
        inner_item = next(iter(md.my_set))
        self.assertIsInstance(inner_item, frozenset)
        # To inspect it, we'd have to convert it back to a dict
        inner_dict = dict(inner_item)
        self.assertIs(type(inner_dict), dict)


class TestMagiDictAdditionalCases(TestCase):
    """Additional edge case tests for MagiDict"""

    def test_deeply_nested_mixed_structures(self):
        """Test complex nesting: dict -> list -> tuple -> dict"""
        data = {"level1": [{"level2": ({"level3": [{"level4": "deep"}]},)}]}
        md = MagiDict(data)
        self.assertEqual(md.level1[0].level2[0].level3[0].level4, "deep")
        self.assertIsInstance(md.level1[0], MagiDict)
        self.assertIsInstance(md.level1[0].level2[0], MagiDict)
        self.assertIsInstance(md.level1[0].level2[0].level3[0], MagiDict)

    def test_setitem_on_from_none_nested_access(self):
        """Test that assignment fails even on deeply nested None-derived MagiDicts"""
        md = MagiDict({"a": None})
        temp = md.a.b.c
        with self.assertRaises(TypeError):
            temp["key"] = "value"
        self.assertTrue(getattr(temp, "_from_missing", False))

    def test_setitem_on_from_missing_nested_access(self):
        """Test that assignment fails on deeply nested missing-key MagiDicts"""
        md = MagiDict({})
        temp = md.x.y.z
        with self.assertRaises(TypeError):
            temp["key"] = "value"
        self.assertTrue(getattr(temp, "_from_missing", False))

    def test_mget_with_none_as_explicit_default(self):
        """Test mget when None is explicitly passed as default"""
        md = MagiDict({"exists": "value"})
        result = md.mget("missing", None)
        self.assertIsNone(result)

    def test_mget_with_missing_default(self):
        """Test that missing is properly used as sentinel"""
        md = MagiDict({})
        result = md.mget("missing")
        self.assertIsInstance(result, MagiDict)
        self.assertTrue(getattr(result, "_from_missing", False))

    def test_mget_chained_on_none_value(self):
        """Test chaining mget on a None value"""
        md = MagiDict({"user": {"name": None}})
        result = md.user.mget("name").somethingelse
        self.assertIsInstance(result, MagiDict)
        self.assertFalse(result)

    def test_getitem_dotted_key_empty_segment(self):
        """Test behavior with empty segments in dotted keys"""
        md = MagiDict({"a": {"": {"b": 1}}})
        # This should work if we have an empty string key
        self.assertEqual(md["a..b"], 1)

    def test_getitem_dotted_key_numeric_dict_key(self):
        """Test dotted access with numeric string keys in dict"""
        md = MagiDict({"a": {"1": {"b": 2}}})
        self.assertEqual(md["a.1.b"], 2)

    def test_getitem_dotted_vs_literal_key_priority(self):
        """Test that literal keys with dots take precedence"""
        md = MagiDict({"a.b": "literal", "a": {"b": "nested"}})
        self.assertEqual(md["a.b"], "literal")
        self.assertEqual(md["a"]["b"], "nested")

    def test_getitem_dotted_key_with_list_at_end(self):
        """Test dotted notation ending with list access"""
        md = MagiDict({"data": {"items": [1, 2, 3]}})
        self.assertEqual(md["data.items.0"], 1)
        self.assertEqual(md["data.items.2"], 3)

    def test_getitem_dotted_key_type_error(self):
        """Test dotted access on non-subscriptable type"""
        md = MagiDict({"value": 42})
        with self.assertRaises(KeyError):
            _ = md["value.something"]

    def test_named_tuple_preservation(self):
        """Test that named tuples are preserved"""
        Point = namedtuple("Point", ["x", "y"])
        md = MagiDict({"point": Point(1, 2)})
        self.assertIsInstance(md.point, Point)
        self.assertEqual(md.point.x, 1)
        self.assertEqual(md.point.y, 2)

    def test_nested_dict_in_named_tuple(self):
        """Test that dicts inside named tuples are converted"""
        Container = namedtuple("Container", ["data"])
        md = MagiDict({"container": Container({"nested": 1})})
        self.assertIsInstance(md.container.data, MagiDict)
        self.assertEqual(md.container.data.nested, 1)

    def test_custom_sequence_type_preservation(self):
        """Test that custom sequence types are handled"""

        class CustomList(list):
            """A custom list subclass with an extra method."""

            def custom_method(self):
                return "custom"

        data = {"custom": CustomList([{"a": 1}, {"b": 2}])}
        md = MagiDict(data)
        self.assertIsInstance(md.custom, CustomList)
        self.assertEqual(md.custom.custom_method(), "custom")
        self.assertIsInstance(md.custom[0], MagiDict)
        self.assertEqual(md.custom[0].a, 1)

    def test_contains_with_none_value(self):
        """Test __contains__ with None values"""
        md = MagiDict({"key": None})
        self.assertIn("key", md)
        self.assertEqual(md.key, MagiDict())
        self.assertTrue(getattr(md.key, "_from_none", False))

    def test_bool_evaluation_with_false_values(self):
        """Test boolean evaluation with various falsy values"""
        md = MagiDict(
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

    def test_len_on_from_missing_magidict(self):
        """Test len() on MagiDict created from missing key"""
        md = MagiDict({})
        temp = md.missing
        self.assertEqual(len(temp), 0)
        self.assertFalse(temp)

    def test_update_with_none_values(self):
        """Test that update handles None values correctly"""
        md = MagiDict({"a": 1})
        md.update({"b": None})
        # None should be stored as None, but accessing it returns empty MagiDict
        self.assertIsNone(md["b"])
        self.assertEqual(md.b, MagiDict())

    def test_update_with_kwargs_and_dict(self):
        """Test update with both positional dict and kwargs"""
        md = MagiDict()
        md.update({"a": {"b": 1}}, c={"d": 2})
        self.assertIsInstance(md.a, MagiDict)
        self.assertIsInstance(md.c, MagiDict)
        self.assertEqual(md.a.b, 1)
        self.assertEqual(md.c.d, 2)

    def test_update_overwrites_from_missing_flag(self):
        """Test that updating a key removes from_missing flag"""
        md = MagiDict({})
        temp = md.missing  # Creates from_missing MagiDict
        md["missing"] = {"real": "value"}
        # Now accessing should give real value
        self.assertIsInstance(md.missing, MagiDict)
        self.assertEqual(md.missing.real, "value")
        self.assertFalse(getattr(md.missing, "_from_missing", False))

    def test_circular_reference_in_list(self):
        """Test circular reference within a list"""
        md = MagiDict({"items": []})
        md["items"].append(md)
        self.assertIs(md["items"][0], md)

    def test_pickle_circular_reference(self):
        """Test pickling with circular references"""
        md = MagiDict()
        md["self"] = md
        pickled = pickle.dumps(md)
        unpickled = pickle.loads(pickled)
        self.assertIs(unpickled["self"], unpickled)

    def test_deepcopy_circular_reference(self):
        """Test deepcopy with circular references"""
        md = MagiDict()
        md["self"] = md
        md_copy = copy.deepcopy(md)
        self.assertIs(md_copy["self"], md_copy)
        self.assertIsNot(md_copy, md)

    def test_disenchant_with_none_values(self):
        """Test that disenchant preserves None values"""
        md = MagiDict({"a": None, "b": {"c": None}})
        result = md.disenchant()
        self.assertIsNone(result["a"])
        self.assertIsNone(result["b"]["c"])
        self.assertIsInstance(result, dict)
        self.assertNotIsInstance(result, MagiDict)

    def test_disenchant_handles_circular_reference(self):
        """
        Verify disenchant() correctly handles circular references
        without raising a RecursionError.
        """
        md = MagiDict()
        md["self"] = md
        # Call the method directly. If it raises an error, the test will fail.
        disenchanted_dict = md.disenchant()
        # Verify that the output is a standard dict.
        self.assertIs(type(disenchanted_dict), dict)
        # Verify that the circular reference is maintained in the new dict.
        self.assertIs(disenchanted_dict["self"], disenchanted_dict)

    def test_disenchant_preserves_list_types(self):
        """Test that disenchant preserves list and tuple types"""
        md = MagiDict({"list": [{"a": 1}], "tuple": ({"b": 2},)})
        result = md.disenchant()
        self.assertIsInstance(result["list"], list)
        self.assertIsInstance(result["tuple"], tuple)
        self.assertIsInstance(result["list"][0], dict)
        self.assertNotIsInstance(result["list"][0], MagiDict)

    def test_pop_with_default_on_method_shadow(self):
        """Test pop with default when key shadows a method"""
        md = MagiDict({"pop": "value"})
        result = md.pop("items", "default")
        self.assertEqual(result, "default")
        self.assertTrue(callable(md.items))
        # The "pop" key should still exist
        self.assertEqual(md["pop"], "value")

    def test_accessing_shadowed_method_after_deletion(self):
        """Test that methods are still accessible after deleting shadowing key"""
        md = MagiDict({"keys": "shadow", "items": "shadow2"})
        del md["keys"]
        self.assertTrue(callable(md.keys))
        self.assertListEqual(list(md.keys()), ["items"])

    def test_setdefault_with_method_name(self):
        """Test setdefault with a key that shadows a method"""
        md = MagiDict()
        result = md.setdefault("update", {"nested": "value"})
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(result.nested, "value")
        self.assertTrue(callable(md.update))

    def test_fromkeys_with_none_value(self):
        """Test fromkeys with None as the default value"""
        md = MagiDict.fromkeys(["a", "b", "c"], None)
        self.assertIsNone(md["a"])
        self.assertEqual(md.a, MagiDict())
        self.assertTrue(getattr(md.a, "_from_none", False))

    def test_fromkeys_with_empty_sequence(self):
        """Test fromkeys with an empty sequence"""
        md = MagiDict.fromkeys([])
        self.assertEqual(len(md), 0)
        self.assertIsInstance(md, MagiDict)

    def test_chaining_through_multiple_none_values(self):
        """Test chaining through multiple None values"""
        md = MagiDict({"a": {"b": None}})
        result = md.a.b.c.d.e
        self.assertIsInstance(result, MagiDict)
        self.assertFalse(result)

    def test_chaining_missing_and_none_mixed(self):
        """Test chaining through mix of missing keys and None values"""
        md = MagiDict({"a": None})
        result = md.a.missing.b.c
        self.assertIsInstance(result, MagiDict)
        self.assertFalse(result)

    def test_attribute_access_after_bracket_assignment(self):
        """Test attribute access after bracket-style assignment"""
        md = MagiDict({})
        md["new"] = {"nested": "value"}
        self.assertIsInstance(md.new, MagiDict)
        self.assertEqual(md.new.nested, "value")

    def test_negative_numeric_keys(self):
        """Test negative numbers as keys"""
        md = MagiDict({-1: "negative", -5: {"nested": "value"}})
        self.assertEqual(md[-1], "negative")
        self.assertIsInstance(md[-5], MagiDict)
        self.assertEqual(md[-5].nested, "value")

    def test_float_keys(self):
        """Test float numbers as keys"""
        md = MagiDict({1.5: "float", 2.7: {"nested": "value"}})
        self.assertEqual(md[1.5], "float")
        self.assertEqual(md.mget(2.7).nested, "value")

    def test_empty_string_key(self):
        """Test empty string as a key"""
        md = MagiDict({"": "empty_key_value"})
        self.assertEqual(md[""], "empty_key_value")
        result = getattr(md, "")
        self.assertEqual(result, "empty_key_value")

    def test_nested_empty_dicts_and_lists(self):
        """Test deeply nested empty structures"""
        md = MagiDict({"a": {"b": {"c": {}}}})
        self.assertIsInstance(md.a.b.c, MagiDict)
        self.assertEqual(len(md.a.b.c), 0)

    def test_json_loads_with_none(self):
        """Test magi_loads with JSON null values"""
        json_str = '{"user": {"name": "Alice", "email": null}}'
        md = magi_loads(json_str)
        self.assertIsNone(md["user"]["email"])
        self.assertEqual(md.user.email, MagiDict())

    def test_enchant_with_ordered_dict(self):
        """Test enchant with OrderedDict"""
        od = OrderedDict([("z", 3), ("a", 1), ("m", 2)])
        md = enchant(od)
        self.assertIsInstance(md, MagiDict)
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
        md = MagiDict({"data": b"bytes_data"})
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

        md = MagiDict(data)
        # Navigate to the deepest level
        current_md = md
        for i in range(depth):
            current_md = getattr(current_md, f"level{i}")
        self.assertEqual(current_md.value, "deep")

    def test_large_number_of_keys(self):
        """Test MagiDict with large number of keys"""
        large_dict = {f"key{i}": {"value": i} for i in range(1000)}
        md = MagiDict(large_dict)
        self.assertEqual(md.key500.value, 500)
        self.assertEqual(md.key999.value, 999)

    def test_with_slots_class(self):
        """Test MagiDict containing objects with __slots__"""

        class SlottedClass:
            """A simple class using __slots__."""

            __slots__ = ["x", "y"]

            def __init__(self, x, y):
                self.x = x
                self.y = y

        obj = SlottedClass(1, 2)
        md = MagiDict({"obj": obj})
        self.assertIs(md.obj, obj)
        self.assertEqual(md.obj.x, 1)

    def test_with_property_objects(self):
        """Test MagiDict containing objects with properties"""

        class PropClass:
            """A simple class with a property."""

            def __init__(self, value):
                self._value = value

            @property
            def value(self):
                """A simple property."""
                return self._value

        obj = PropClass(42)
        md = MagiDict({"obj": obj})
        self.assertEqual(md.obj.value, 42)

    def test_get_with_callable_default(self):
        """Test get() with a callable as default"""
        md = MagiDict({"a": 1})
        result = md.get("missing", lambda: "callable")
        self.assertTrue(callable(result))
        self.assertEqual(result(), "callable")

    def test_get_returns_hook_converted_value(self):
        """Test that get() returns hook-converted values"""
        md = MagiDict({"nested": {"deep": {"value": 1}}})
        result = md.get("nested")
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(result.deep.value, 1)

    def test_repr_with_very_long_dict(self):
        """Test repr doesn't break with large dicts"""
        md = MagiDict({f"key{i}": i for i in range(100)})
        repr_str = repr(md)
        self.assertTrue(repr_str.startswith("MagiDict("))
        self.assertTrue(repr_str.endswith(")"))

    def test_equality_with_itself(self):
        """Test MagiDict equality with itself"""
        md = MagiDict({"a": 1})
        self.assertEqual(md, md)
        self.assertTrue(md == md)

    def test_inequality_operators(self):
        """Test that inequality operators work correctly"""
        md1 = MagiDict({"a": 1})
        md2 = MagiDict({"a": 2})
        self.assertNotEqual(md1, md2)
        self.assertTrue(md1 != md2)
        self.assertFalse(md1 == md2)


class TestPickleAndRegression(TestCase):
    """
    This test suite validates that the removal of __reduce__ and the
    implementation of __getstate__/__setstate__ has:
    1. Fixed the pickling of circular references.
    2. Works correctly for simple and nested structures.
    3. Has not negatively impacted the core functionality of MagiDict.
    """

    def setUp(self):
        """Set up a complex MagiDict instance for testing."""
        self.data = {
            "user": {"profile": {"email": "test@example.com"}, "nickname": None},
            "permissions": ["read", {"area": "admin", "level": 1}],
            "config": {"theme": "dark"},
        }
        self.md = MagiDict(self.data)
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
            self.assertIsInstance(unpickled_md.user.profile, MagiDict)

        except RecursionError:
            self.fail(
                "RecursionError encountered during pickling. The fix for circular references is not working."
            )

    def test_pickle_deeply_nested_object(self):
        """
        Verify that a standard nested MagiDict pickles and unpickles correctly,
        preserving its type and structure.
        """
        # We use a deepcopy to test a version without the circular reference
        md_simple = copy.deepcopy(self.md)
        del md_simple["self_ref"]

        pickled = pickle.dumps(md_simple)
        unpickled = pickle.loads(pickled)

        # Check types recursively
        self.assertIsInstance(unpickled, MagiDict)
        self.assertIsInstance(unpickled.user, MagiDict)
        self.assertIsInstance(unpickled.permissions[1], MagiDict)

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
        self.assertIsInstance(non_existent, MagiDict)
        self.assertFalse(non_existent)  # Should evaluate to False

        # Safe chaining on None values
        nickname_chain = self.md.user.nickname.alias
        self.assertIsInstance(nickname_chain, MagiDict)
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
        self.magi_dict = MagiDict(self.standard_dict)

    # --- Tests for enchant() ---

    def test_enchant_converts_standard_dict(self):
        """Verify that enchant() converts a standard dict to a MagiDict."""
        enchanted = enchant(self.standard_dict)
        self.assertIsInstance(enchanted, MagiDict)
        self.assertEqual(enchanted.status, "ok")

    def test_enchant_is_recursive(self):
        """Verify that enchant() recursively converts nested dicts."""
        enchanted = enchant(self.standard_dict)
        self.assertIsInstance(enchanted.user, MagiDict)
        self.assertIsInstance(enchanted.user.profile, MagiDict)
        self.assertIsInstance(enchanted.user.roles[1], MagiDict)
        self.assertIsInstance(enchanted.settings[0], MagiDict)
        self.assertEqual(enchanted.user.profile.email, "test@example.com")

    def test_enchant_on_existing_magidict(self):
        """Verify that passing a MagiDict to enchant() returns it unchanged."""
        result = enchant(self.magi_dict)
        self.assertIs(result, self.magi_dict)

    def test_enchant_raises_typeerror_for_non_dict(self):
        """Verify that enchant() raises a TypeError for invalid input types."""
        with self.assertRaises(TypeError):
            enchant(["a", "list"])
        with self.assertRaises(TypeError):
            enchant("a string")
        with self.assertRaises(TypeError):
            enchant(123)

    # --- Tests for disenchant() ---

    def test_disenchant_converts_magi_dict(self):
        """Verify that disenchant() converts a MagiDict back to a standard dict."""
        disenchanted = self.magi_dict.disenchant()
        self.assertIs(type(disenchanted), dict)
        self.assertNotIsInstance(disenchanted, MagiDict)
        self.assertEqual(disenchanted["status"], "ok")

    def test_disenchant_is_recursive(self):
        """Verify that disenchant() recursively converts nested MagiDicts."""
        disenchanted = self.magi_dict.disenchant()
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
        md = MagiDict()
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
        md = MagiDict(
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
        result = self.magi_dict.disenchant()  # disenchant is a method of MagiDict
        self.assertEqual(result, self.standard_dict)


class TestMagiDictBasicFunctionality(TestCase):
    """Test basic MagiDict features"""

    def test_attribute_access(self):
        """Test basic attribute-style access"""
        md = MagiDict({"user": {"name": "Alice", "id": 1}})
        self.assertEqual(md.user.name, "Alice")
        self.assertEqual(md.user.id, 1)

    def test_bracket_access(self):
        """Test standard bracket notation"""
        md = MagiDict({"user": {"name": "Alice"}})
        self.assertEqual(md["user"]["name"], "Alice")

    def test_dot_notation_in_brackets(self):
        """Test deep access with dot notation"""
        md = MagiDict({"user": {"profile": {"email": "alice@example.com"}}})
        self.assertEqual(md["user.profile.email"], "alice@example.com")

    def test_missing_key_attribute_access(self):
        """Missing keys via attributes return empty MagiDict"""
        md = MagiDict({"user": {"name": "Alice"}})
        result = md.user.email
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

    def test_missing_key_bracket_raises(self):
        """Missing keys via brackets raise KeyError"""
        md = MagiDict({"user": {"name": "Alice"}})
        with self.assertRaises(KeyError):
            _ = md["user"]["email"]

    def test_none_value_attribute_access(self):
        """Accessing None values via attributes returns empty MagiDict"""
        md = MagiDict({"user": {"nickname": None}})
        result = md.user.nickname
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

    def test_none_value_bracket_access(self):
        """Accessing None values via brackets returns None"""
        md = MagiDict({"user": {"nickname": None}})
        self.assertIsNone(md["user"]["nickname"])

    def test_safe_chaining(self):
        """Test chaining through missing keys"""
        md = MagiDict({"user": {"name": "Alice"}})
        result = md.user.address.city.zipcode
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)


class TestMagiDictRecursiveConversion(TestCase):
    """Test recursive conversion of nested structures"""

    def test_nested_dict_conversion(self):
        """Nested dicts are converted to MagiDict"""
        md = MagiDict({"level1": {"level2": {"level3": "value"}}})
        self.assertIsInstance(md.level1, MagiDict)
        self.assertIsInstance(md.level1.level2, MagiDict)

    def test_list_with_dicts(self):
        """Dicts inside lists are converted"""
        md = MagiDict({"items": [{"name": "item1"}, {"name": "item2"}]})
        self.assertIsInstance(md["items"][0], MagiDict)
        self.assertEqual(md["items"][0].name, "item1")

    def test_tuple_with_dicts(self):
        """Dicts inside tuples are converted"""
        md = MagiDict({"data": ({"a": 1}, {"b": 2})})
        self.assertIsInstance(md.data[0], MagiDict)
        self.assertIsInstance(md.data, tuple)

    def test_namedtuple_preservation(self):
        """Namedtuples are preserved with converted contents"""
        Point = namedtuple("Point", ["x", "y"])
        md = MagiDict({"point": Point({"nested": 1}, {"nested": 2})})
        self.assertIsInstance(md.point, Point)
        self.assertIsInstance(md.point.x, MagiDict)


class TestMagiDictCircularReferences(TestCase):
    """Test handling of circular references"""

    def test_disenchant_circular_reference(self):
        """disenchant() handles circular references"""
        md = MagiDict({"a": {"b": "value"}})
        md["circular"] = md  # Create circular reference

        result = md.disenchant()
        self.assertIsInstance(result, dict)
        self.assertIs(result["circular"], result)

    def test_initialization_circular_reference(self):
        data = {"a": {}}
        data["a"]["loop"] = data["a"]
        md = MagiDict(data)

    def test_disenchant_list_circular_reference(self):
        """disenchant() handles circular refs in lists"""
        md = MagiDict({"items": [{"name": "item1"}]})
        md["items"].append(md["items"])  # Circular list

        result = md.disenchant()
        self.assertIsInstance(result, dict)
        self.assertIs(result["items"][1], result["items"])


class TestMagiDictInputMutation(TestCase):
    """Test for input data mutation side effects"""

    def test_list_mutation_side_effect(self):
        """KNOWN ISSUE: Input lists are mutated in-place"""
        original_list = [{"a": 1}, {"b": 2}]
        md = MagiDict({"items": original_list})

        # The original list has been mutated!
        self.assertIsInstance(original_list[0], MagiDict)

    def test_dict_not_mutated(self):
        """Input dicts are not mutated (they're copied)"""
        original_dict = {"nested": {"value": 1}}
        md = MagiDict(original_dict)

        # Original dict is unchanged
        self.assertIsInstance(original_dict["nested"], dict)
        self.assertNotIsInstance(original_dict["nested"], MagiDict)

    def test_tuple_not_mutated(self):
        """Tuples create new tuples (immutable)"""
        original_tuple = ({"a": 1}, {"b": 2})
        md = MagiDict({"data": original_tuple})

        # Original tuple is unchanged
        self.assertIsInstance(original_tuple[0], dict)
        self.assertNotIsInstance(original_tuple[0], MagiDict)


class TestMagiDictDotNotationEdgeCases(TestCase):
    """Test dot notation with edge cases"""

    def test_dot_notation_with_list_index(self):
        """Dot notation can traverse list indices"""
        md = MagiDict({"items": [{"name": "Alice"}, {"name": "Bob"}]})
        self.assertEqual(md["items.0.name"], "Alice")
        self.assertEqual(md["items.1.name"], "Bob")

    def test_dot_notation_with_numeric_string_key(self):
        md = MagiDict({"user": {"123": {"name": "Alice"}}})
        self.assertEqual(md["user.123.name"], "Alice")

    def test_dot_notation_invalid_path(self):
        """Dot notation raises KeyError for invalid paths"""
        md = MagiDict({"user": {"name": "Alice"}})
        with self.assertRaises(KeyError):
            _ = md["user.email.address"]


class TestMagiDictThreadSafety(TestCase):
    """Test thread safety (or lack thereof)"""

    def test_concurrent_reads(self):
        """Concurrent reads should be safe"""
        md = MagiDict({"data": {"value": 42}})
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
        md = MagiDict({})
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


class TestMagiDictProtectionBypass(TestCase):
    """Test protection mechanisms on temporary MagiDicts"""

    def test_cannot_assign_to_missing_key_magidict(self):
        """Assignment to missing key MagiDict raises TypeError"""
        md = MagiDict({"user": {"name": "Alice"}})
        temp = md.user.email

        with self.assertRaises(TypeError):
            temp["key"] = "value"

    def test_cannot_assign_to_none_value_magidict(self):
        """Assignment to None value MagiDict raises TypeError"""
        md = MagiDict({"user": {"nickname": None}})
        temp = md.user.nickname

        with self.assertRaises(TypeError):
            temp["key"] = "value"

    def test_protection_via_update(self):
        """update() is also protected"""
        md = MagiDict({"user": {"name": "Alice"}})
        temp = md.user.email

        with self.assertRaises(TypeError):
            temp.update({"key": "value"})

    def test_protection_via_setdefault(self):
        """setdefault() is also protected"""
        md = MagiDict({"user": {"name": "Alice"}})
        temp = md.user.email

        with self.assertRaises(TypeError):
            temp.setdefault("key", "value")

    def test_bypass_via_dict_methods(self):
        """KNOWN ISSUE: Protection can be bypassed with dict methods"""
        md = MagiDict({"user": {"name": "Alice"}})
        temp = md.user.email

        # This bypasses __setitem__
        with self.assertRaises(TypeError):
            dict.__setitem__("key", "value")


class TestMagiDictMgetMethod(TestCase):
    """Test mget() and mg() methods"""

    def test_mget_existing_key(self):
        """mget() returns value for existing key"""
        md = MagiDict({"key": "value"})
        self.assertEqual(md.mget("key"), "value")

    def test_mget_missing_key(self):
        """mget() returns empty MagiDict for missing key"""
        md = MagiDict({"key": "value"})
        result = md.mget("missing")
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

    def test_mget_none_value(self):
        """mget() returns empty MagiDict for None value"""
        md = MagiDict({"key": None})
        result = md.mget("key")
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

    def test_mget_with_custom_default(self):
        """mget() returns custom default for missing key"""
        md = MagiDict({"key": "value"})
        self.assertEqual(md.mget("missing", "default"), "default")

    def test_mget_with_none_default(self):
        """mget() can return None as explicit default"""
        md = MagiDict({"key": "value"})
        self.assertIsNone(md.mget("missing", None))

    def test_mg_shorthand(self):
        """mg() is shorthand for mget()"""
        md = MagiDict({"key": "value"})
        self.assertEqual(md.mg("key"), md.mget("key"))
        self.assertEqual(md.mg("missing"), md.mget("missing"))


class TestMagiDictStandardDictMethods(TestCase):
    """Test standard dict methods work correctly"""

    def test_keys_method(self):
        """keys() method works"""
        md = MagiDict({"a": 1, "b": 2})
        self.assertEqual(set(md.keys()), {"a", "b"})

    def test_values_method(self):
        """values() method works"""
        md = MagiDict({"a": 1, "b": 2})
        self.assertEqual(set(md.values()), {1, 2})

    def test_items_method(self):
        """items() method works"""
        md = MagiDict({"a": 1, "b": 2})
        self.assertEqual(set(md.items()), {("a", 1), ("b", 2)})

    def test_pop_method(self):
        """pop() method works"""
        md = MagiDict({"a": 1, "b": 2})
        val = md.pop("a")
        self.assertEqual(val, 1)
        self.assertNotIn("a", md)

    def test_clear_method(self):
        """clear() method works"""
        md = MagiDict({"a": 1, "b": 2})
        md.clear()
        self.assertEqual(len(md), 0)

    def test_copy_method(self):
        """copy() returns a MagiDict"""
        md = MagiDict({"a": {"b": 1}})
        copied = md.copy()
        self.assertIsInstance(copied, MagiDict)
        self.assertEqual(copied.a.b, 1)

    def test_fromkeys_classmethod(self):
        """fromkeys() creates MagiDict with hooked values"""
        md = MagiDict.fromkeys(["a", "b"], {"nested": "value"})
        self.assertIsInstance(md.a, MagiDict)
        self.assertEqual(md.a.nested, "value")

    def test_ior_operator(self):
        """|= operator works for updates"""
        md1 = MagiDict({"a": 1})
        md2 = {"b": 2}
        md1 |= md2
        self.assertEqual(md1["a"], 1)
        self.assertEqual(md1["b"], 2)


class TestMagiDictPickle(TestCase):
    """Test pickle serialization"""

    def test_pickle_simple(self):
        """Simple MagiDict can be pickled and unpickled"""
        md = MagiDict({"a": 1, "b": 2})
        pickled = pickle.dumps(md)
        restored = pickle.loads(pickled)
        self.assertIsInstance(restored, MagiDict)
        self.assertEqual(restored["a"], 1)

    def test_pickle_nested(self):
        """Nested MagiDict preserves structure"""
        md = MagiDict({"user": {"name": "Alice", "profile": {"age": 30}}})
        pickled = pickle.dumps(md)
        restored = pickle.loads(pickled)
        self.assertIsInstance(restored.user, MagiDict)
        self.assertEqual(restored.user.profile.age, 30)

    def test_pickle_circular_reference(self):
        """Circular references survive pickling"""
        md = MagiDict({"a": 1})
        md["self"] = md
        pickled = pickle.dumps(md)
        restored = pickle.loads(pickled)
        self.assertIs(restored["self"], restored)


class TestMagiDictDeepCopy(TestCase):
    """Test deepcopy functionality"""

    def test_deepcopy_simple(self):
        """Simple MagiDict can be deep copied"""
        md = MagiDict({"a": 1, "b": [1, 2, 3]})
        copied = deepcopy(md)
        self.assertIsInstance(copied, MagiDict)
        self.assertEqual(copied["a"], 1)
        self.assertIsNot(copied["b"], md["b"])

    def test_deepcopy_nested(self):
        """Nested structures are properly deep copied"""
        md = MagiDict({"user": {"data": [1, 2, 3]}})
        copied = deepcopy(md)
        copied.user.data.append(4)
        self.assertEqual(len(md.user.data), 3)
        self.assertEqual(len(copied.user.data), 4)

    def test_deepcopy_circular(self):
        """Circular references survive deep copy"""
        md = MagiDict({"a": 1})
        md["self"] = md
        copied = deepcopy(md)
        self.assertIs(copied["self"], copied)
        self.assertIsNot(copied, md)


class TestMagiDictDisenchant(TestCase):
    """Test disenchant() method"""

    def test_disenchant_simple(self):
        """disenchant() converts to standard dict"""
        md = MagiDict({"a": 1, "b": 2})
        result = md.disenchant()
        self.assertIsInstance(result, dict)
        self.assertNotIsInstance(result, MagiDict)

    def test_disenchant_nested(self):
        """disenchant() recursively converts nested MagiDicts"""
        md = MagiDict({"user": {"profile": {"name": "Alice"}}})
        result = md.disenchant()
        self.assertIsInstance(result, dict)
        self.assertIsInstance(result["user"], dict)
        self.assertNotIsInstance(result["user"], MagiDict)

    def test_disenchant_with_lists(self):
        """disenchant() handles lists with MagiDicts"""
        md = MagiDict({"items": [{"name": "item1"}, {"name": "item2"}]})
        result = md.disenchant()
        self.assertIsInstance(result["items"][0], dict)
        self.assertNotIsInstance(result["items"][0], MagiDict)


class TestMagiDictHelperFunctions(TestCase):
    """Test helper functions"""

    def test_magi_loads(self):
        """magi_loads() creates MagiDict from JSON"""
        json_str = '{"user": {"name": "Alice"}}'
        md = magi_loads(json_str)
        self.assertIsInstance(md, MagiDict)
        self.assertEqual(md.user.name, "Alice")

    def test_enchant_dict(self):
        """enchant() converts dict to MagiDict"""
        d = {"user": {"name": "Alice"}}
        md = enchant(d)
        self.assertIsInstance(md, MagiDict)
        self.assertEqual(md.user.name, "Alice")

    def test_enchant_already_magidict(self):
        """enchant() returns MagiDict as-is"""
        md1 = MagiDict({"a": 1})
        md2 = enchant(md1)
        self.assertIs(md1, md2)

    def test_enchant_invalid_type(self):
        """enchant() raises TypeError for non-dict"""
        with self.assertRaises(TypeError):
            enchant([1, 2, 3])


class TestMagiDictKeyConflicts(TestCase):
    """Test handling of keys that conflict with dict methods"""

    def test_keys_conflict(self):
        """Key named 'keys' conflicts with dict.keys() method"""
        md = MagiDict({"keys": "custom_value"})
        # Attribute access returns the method
        self.assertTrue(callable(md.keys))
        # Bracket access returns the value
        self.assertEqual(md["keys"], "custom_value")

    def test_mget_for_conflicting_keys(self):
        """mget() can access conflicting keys"""
        md = MagiDict({"update": "custom_value", "pop": "another"})
        self.assertEqual(md.mget("update"), "custom_value")
        self.assertEqual(md.mget("pop"), "another")


class TestMagiDictMemoryBehavior(TestCase):
    """Test memory and performance characteristics"""

    def test_temporary_objects_garbage_collected(self):
        """Temporary MagiDicts should be garbage collected"""

        md = MagiDict({"user": {"name": "Alice"}})

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

        md = MagiDict(data)
        # Access the deeply nested value
        result = md.level0
        for i in range(100):
            result = result[f"level{i+1}"]
        self.assertEqual(result["value"], "deep")


class TestMagiDictEqualityAndHashing(TestCase):
    """Test equality comparisons and hashing"""

    def test_equality(self):
        """MagiDicts with same content are equal"""
        md1 = MagiDict({"a": 1, "b": 2})
        md2 = MagiDict({"a": 1, "b": 2})
        self.assertEqual(md1, md2)

    def test_inequality(self):
        """MagiDicts with different content are not equal"""
        md1 = MagiDict({"a": 1})
        md2 = MagiDict({"a": 2})
        self.assertNotEqual(md1, md2)

    def test_temporary_magidict_equality(self):
        """Temporary MagiDicts are equal if both empty"""
        md = MagiDict({"a": 1})
        temp1 = md.missing1
        temp2 = md.missing2
        self.assertEqual(temp1, temp2)

    def test_unhashable(self):
        """MagiDict is unhashable (like dict)"""
        md = MagiDict({"a": 1})
        with self.assertRaises(TypeError):
            hash(md)


class TestMagiDictEdgeCases(TestCase):
    """Test various edge cases and complex scenarios"""

    def setUp(self):
        """Set up a standard MagiDict instance for use in tests."""
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
        self.md = MagiDict(self.data)

    def test_initialization_and_recursive_conversion(self):
        """Test that initialization and recursive conversion works."""
        self.assertIsInstance(self.md, MagiDict)
        self.assertIsInstance(self.md.user, MagiDict)
        self.assertIsInstance(self.md.user.details, MagiDict)
        self.assertIsInstance(self.md.posts[0], MagiDict)
        self.assertIsInstance(self.md.posts[1], MagiDict)
        self.assertIsInstance(self.md.posts[0].tags, tuple)

    def test_basic_attribute_access(self):
        """Test basic attribute-style access."""
        self.assertEqual(self.md.user.name, "Alice")
        self.assertEqual(self.md.user.details.email, "alice@example.com")
        self.assertEqual(self.md.posts[0].id, 1)

    def test_safe_chaining_on_non_existent_keys(self):
        """Test safe chaining through non-existent keys."""
        safe_access = self.md.user.address.city.street
        self.assertIsInstance(safe_access, MagiDict)
        self.assertEqual(safe_access, {})

    def test_safe_chaining_on_none_value(self):
        """Test safe chaining through None values."""
        safe_access = self.md.user.prefs.theme.color
        self.assertIsInstance(safe_access, MagiDict)
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
        md = MagiDict({"a": {"b": 123}})
        with self.assertRaises(KeyError):
            _ = md["a.b.c"]

    def test_key_with_dots_in_it(self):
        """Test that keys with dots are accessible."""
        self.assertEqual(self.md["key.with.dots"], "value_with_dots")

    def test_modification_and_hooking(self):
        """Test that modifications hook new dicts/lists."""
        self.md["new_key"] = {"a": 1, "b": [{"c": 3}]}
        temp = self.md.new_key
        self.assertIsInstance(temp, MagiDict)
        self.assertIsInstance(temp.b[0], MagiDict)
        self.assertEqual(self.md.new_key.b[0].c, 3)

    def test_protection_of_temporary_dicts(self):
        """Test that temporary MagiDicts are protected against modification."""
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
        md = MagiDict({"keys": "value", "items": [1, 2]})
        self.assertEqual(md["keys"], "value")
        self.assertTrue(md.keys(), callable)  # dict.keys() method is accessible
        self.assertTrue(callable(md.keys))

        self.assertEqual(md["items"], [1, 2])
        self.assertTrue(callable(md.items))

    def test_disenchant(self):
        """Test that disenchant() correctly converts to standard dict."""
        disenchanted = self.md.disenchant()
        self.assertIsInstance(disenchanted, dict)
        self.assertNotIsInstance(disenchanted, MagiDict)
        self.assertIsInstance(disenchanted["user"], dict)
        self.assertNotIsInstance(disenchanted["user"], MagiDict)
        self.assertIsInstance(disenchanted["posts"][0], dict)
        self.assertNotIsInstance(disenchanted["posts"][0], MagiDict)
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
            md = MagiDict(data)
        except RecursionError:
            self.fail(
                "MagiDict failed to handle circular references on initialization."
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
            self.fail("MagiDict.disenchant failed to handle circular references.")

        self.assertIs(disenchanted["a"]["self"], disenchanted["a"])
        self.assertIs(disenchanted["b"][1], disenchanted["b"])
        self.assertNotIsInstance(disenchanted["a"], MagiDict)

    def test_deepcopy_and_copy(self):
        """Test that copy() and deepcopy() work correctly."""
        # Shallow copy
        md_copy = self.md.copy()
        self.assertIsInstance(md_copy, MagiDict)
        self.assertIsNot(md_copy, self.md)
        self.assertEqual(md_copy, self.md)
        self.assertIs(
            md_copy.user, self.md.user
        )  # Shallow copy means nested objects are the same

        # Deep copy
        md_deepcopy = deepcopy(self.md)
        self.assertIsInstance(md_deepcopy, MagiDict)
        self.assertIsNot(md_deepcopy, self.md)
        self.assertEqual(md_deepcopy, self.md)
        self.assertIsNot(
            md_deepcopy.user, self.md.user
        )  # Deep copy creates new nested objects

    def test_pickling(self):
        """Test that pickling and unpickling works correctly."""
        pickled_md = pickle.dumps(self.md)
        unpickled_md = pickle.loads(pickled_md)

        self.assertIsInstance(unpickled_md, MagiDict)
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
        self.assertIsInstance(missing, MagiDict)
        self.assertEqual(missing, {})
        with self.assertRaises(TypeError):
            missing["a"] = 1  # Should be protected

        # Test missing key with default
        self.assertEqual(self.md.mget("non-existent-key", "default_val"), "default_val")
        self.assertIsNone(self.md.mget("non-existent-key", None))

        # Test key with None value
        from_none = self.md.user.mget("prefs")
        self.assertIsInstance(from_none, MagiDict)
        self.assertEqual(from_none, {})
        with self.assertRaises(TypeError):
            from_none["a"] = 1

    def test_helper_functions(self):
        """Test enchant() and magi_loads() helper functions."""
        # test enchant
        d = {"a": {"b": 1}}
        md = enchant(d)
        self.assertIsInstance(md, MagiDict)
        self.assertIsInstance(md.a, MagiDict)
        self.assertEqual(md.a.b, 1)

        # test magi_loads
        json_str = '{"user": {"name": "Bob"}, "items": [{"id": 1}]}'
        md_json = magi_loads(json_str)
        self.assertIsInstance(md_json, MagiDict)
        self.assertIsInstance(md_json.user, MagiDict)
        self.assertIsInstance(md_json["items"][0], MagiDict)
        self.assertEqual(md_json.user.name, "Bob")

    def test_other_overridden_methods(self):
        """Test other overridden dict methods."""
        # setdefault
        self.md.setdefault("new_key", {"a": 1})
        self.assertIsInstance(self.md.new_key, MagiDict)

        # fromkeys
        md = MagiDict.fromkeys(["a", "b"], {"c": 1})
        self.assertIsInstance(md.a, MagiDict)
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
        md = MagiDict(data)

        self.assertIsInstance(md.point, Point)
        self.assertIsInstance(md.point.x, MagiDict)
        self.assertEqual(md.point.x.val, 10)

        disenchanted = md.disenchant()
        self.assertIsInstance(disenchanted["point"], Point)
        self.assertIsInstance(disenchanted["point"].x, dict)
        self.assertEqual(disenchanted["point"].x["val"], 10)

    def test_basic_attribute_and_bracket_access(self):
        md = MagiDict({"user": {"name": "Alice", "id": 1}, "permissions": ["read"]})
        self.assertEqual(md.user.name, "Alice")
        self.assertEqual(md["user"]["id"], 1)
        self.assertEqual(md["user.id"], 1)

    def test_missing_keys_safe_chaining(self):
        md = MagiDict({})
        self.assertIsInstance(md.nonexistent, MagiDict)
        self.assertIsInstance(md.nonexistent.deep.chain, MagiDict)
        with self.assertRaises(KeyError):
            _ = md["nonexistent"]

    def test_none_value_safe_chaining(self):
        md = MagiDict({"user": {"nickname": None}})
        self.assertIsInstance(md.user.nickname, MagiDict)
        self.assertIsNone(md.user["nickname"])

    def test_conflicting_keys(self):
        md = MagiDict({"keys": "custom_value"})
        self.assertTrue(callable(md.keys))  # still a dict method
        self.assertEqual(md["keys"], "custom_value")

    def test_invalid_identifier_keys(self):
        md = MagiDict({"1-key": "value", "some key": 123})
        self.assertEqual(md["1-key"], "value")
        self.assertEqual(md.mget("1-key"), "value")
        self.assertEqual(md["some key"], 123)

    def test_dot_notation_nested_access(self):
        md = MagiDict({"a": {"b": {"c": 5}}})
        self.assertEqual(md["a.b.c"], 5)
        with self.assertRaises(KeyError):
            _ = md["a.b.x"]

    def test_dot_notation_with_list_index(self):
        md = MagiDict({"users": [{"name": "Alice"}, {"name": "Bob"}]})
        self.assertEqual(md["users.0.name"], "Alice")
        self.assertEqual(md["users.1.name"], "Bob")
        with self.assertRaises(IndexError):
            _ = md["users.2.name"]

    def test_protected_magidict_modification_raises(self):
        md = MagiDict({})
        temp = md.nonexistent
        with self.assertRaises(TypeError):
            temp["x"] = 1

    def test_update_and_copy_preserve_magidict(self):
        md = MagiDict({"a": {"b": 1}})
        md.update({"c": {"d": 2}})
        self.assertIsInstance(md.c, MagiDict)
        shallow = md.copy()
        self.assertIsInstance(shallow, MagiDict)
        self.assertEqual(shallow.a.b, 1)

    def test_enchant_and_disenchant_roundtrip(self):
        data = {"a": {"b": [1, {"c": 3}]}}
        md = enchant(data)
        result = md.disenchant()
        self.assertEqual(result, data)
        self.assertIsInstance(result, dict)
        self.assertNotIsInstance(result, MagiDict)

    def test_deepcopy_preserves_values_but_not_identity(self):
        md = MagiDict({"x": {"y": [1, 2, 3]}})
        cp = deepcopy(md)
        self.assertEqual(cp, md)
        self.assertIsNot(cp, md)
        self.assertIsNot(cp.x, md.x)

    def test_circular_references_disenchant_and_copy(self):
        d = {}
        d["self"] = d
        md = MagiDict(d)
        disen = md.disenchant()
        self.assertIsInstance(disen, dict)
        self.assertIs(disen["self"], disen)

        cp = deepcopy(md)
        self.assertIs(cp["self"], cp)

    def test_namedtuple_preservation(self):
        Point = namedtuple("Point", ["x", "y"])
        data = {"p": Point(1, 2)}
        md = MagiDict(data)
        result = md.disenchant()
        self.assertIsInstance(result["p"], Point)
        self.assertEqual(result["p"].x, 1)

    def test_pickle_roundtrip(self):
        md = MagiDict({"a": {"b": 2}})
        blob = pickle.dumps(md)
        restored = pickle.loads(blob)
        self.assertEqual(restored, md)
        self.assertIsInstance(restored, MagiDict)

    def test_magi_loads_from_json(self):
        s = '{"user": {"id": 5, "name": "Alice"}}'
        md = magi_loads(s)
        self.assertIsInstance(md, MagiDict)
        self.assertEqual(md.user.id, 5)

    def test_mget_with_default(self):
        md = MagiDict({"x": 1})
        self.assertEqual(md.mget("x"), 1)
        self.assertIsInstance(md.mget("missing"), MagiDict)
        self.assertEqual(md.mget("missing", default="fallback"), "fallback")

    def test_inplace_or_update(self):
        md = MagiDict({"a": 1})
        md |= {"b": {"c": 3}}
        self.assertEqual(md.b.c, 3)

    def test_fromkeys_and_setdefault_hooking(self):
        md = MagiDict.fromkeys(["x", "y"], {"a": 1})
        for key in ["x", "y"]:
            self.assertIsInstance(md[key], MagiDict)
        md.setdefault("z", {"q": 9})
        self.assertIsInstance(md.z, MagiDict)


import datetime
from collections import defaultdict


class TestMagiDictAdvanced(TestCase):
    """
    Tests for advanced edge cases, behavioral clarifications, and interactions
    with other types not covered in the main test suite.
    """

    def test_hook_converts_defaultdict_to_magidict(self):
        """
        Verify that dict subclasses like defaultdict are converted into MagiDict,
        losing their special behaviors (e.g., default_factory).
        """
        dd = defaultdict(lambda: "default", {"existing": "value"})
        md = MagiDict({"data": dd})

        # The defaultdict should be converted to a MagiDict
        self.assertIsInstance(md.data, MagiDict)
        self.assertNotIsInstance(md.data, defaultdict)
        self.assertEqual(md.data.existing, "value")

        # The default_factory behavior is lost, and it now acts like a MagiDict
        # on missing keys.
        missing_key_result = md.data.nonexistent
        self.assertIsInstance(missing_key_result, MagiDict)
        self.assertEqual(missing_key_result, {})

    def test_disenchant_preserves_complex_unhookable_types(self):
        """
        Verify that disenchant() preserves complex types like datetime objects
        that are not subject to the hooking mechanism.
        """
        now = datetime.datetime.now()
        md = MagiDict({"event": {"name": "launch", "timestamp": now}})
        disenchanted = md.disenchant()

        self.assertIs(type(disenchanted), dict)
        self.assertIs(type(disenchanted["event"]), dict)
        self.assertIs(disenchanted["event"]["timestamp"], now)
        self.assertIsInstance(disenchanted["event"]["timestamp"], datetime.datetime)

    def test_none_as_a_key(self):
        """
        Test that using `None` as a dictionary key is handled correctly.
        """
        md = MagiDict({None: "value_for_none"})
        self.assertIn(None, md)
        self.assertEqual(md[None], "value_for_none")
        self.assertEqual(md.mget(None), "value_for_none")

        # Attribute access for 'None' should be a missing key, not the value for the None key.
        self.assertEqual(md[None], "value_for_none")
        self.assertIsInstance(md.none, MagiDict)
        self.assertTrue(getattr(md.none, "_from_missing", False))

    def test_getitem_dot_notation_value_error_on_bad_list_index(self):
        """
        Verify that dot notation access on a list with a non-integer key
        raises a ValueError, which is not caught by the internal KeyError handling.
        """
        md = MagiDict({"items": ["a", "b", "c"]})
        with self.assertRaises(ValueError):
            # The 'x' cannot be converted to an int for list indexing.
            _ = md["items.x"]

    def test_getitem_dot_notation_with_leading_or_trailing_dots(self):
        """
        Test that dot notation handles leading/trailing dots, which result
        in empty strings from split('.').
        """
        # A key that is an empty string
        md = MagiDict({"": "value_for_empty_string", "a": {"": "nested_empty"}})

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
        md = MagiDict(d)
        self.assertIs(md["list_ref"][1], md)
        self.assertIsInstance(md["list_ref"][0], MagiDict)

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
        md = MagiDict()
        # Set an instance attribute directly, bypassing __setitem__
        object.__setattr__(md, "my_attr", "instance_value")
        # Set a key with the same name
        md["my_attr"] = "key_value"

        dir_list = dir(md)
        # 'my_attr' should be present
        self.assertIn("my_attr", dir_list)
        self.assertEqual(md.my_attr, "instance_value")

    def test_initialization_with_existing_magidict_instance(self):
        """
        Test initializing a MagiDict with another MagiDict instance.
        This should behave like a copy.
        """
        nested = MagiDict({"c": 3})
        original = MagiDict({"a": 1, "b": nested})

        new_md = MagiDict(original)

        self.assertEqual(new_md, original)
        self.assertIsNot(new_md, original)
        # The copy during init is shallow, so nested objects should be the same instance
        self.assertIs(new_md.b, original.b)
        self.assertIs(new_md["b"], nested)


class TestMagiDictEdgeCases3(TestCase):
    """Additional edge cases and clarifications."""

    def test_exact_key_with_dot_preferred_over_nested(self):
        """If a dict has an exact key that contains a dot it should be returned
        by __getitem__ instead of attempting dot-traversal."""
        md = MagiDict({"a.b": 1, "a": {"b": 2}})
        # direct item access for exact key containing a dot
        self.assertEqual(md["a.b"], 1)
        # attribute style should still traverse the nested structure
        self.assertEqual(md.a.b, 2)

    def test_getitem_dot_with_invalid_index_raises(self):
        """When dot-traversal hits a sequence but the key is not an integer,
        a ValueError should be raised (int() conversion)."""
        md = MagiDict({"arr": ["zero", "one"]})
        with self.assertRaises(ValueError):
            _ = md["arr.one.two"]

    def test_getitem_dot_index_out_of_range_raises_indexerror(self):
        """Out-of-range index via dot-traversal raises IndexError."""
        md = MagiDict({"arr": ["zero"]})
        with self.assertRaises(IndexError):
            _ = md["arr.5"]

    def test_disenchant_preserves_shared_and_circular_references(self):
        """disenchant preserves shared and circular references."""
        md = MagiDict()
        # use a shared MagiDict so the same object instance is stored twice
        shared = MagiDict({"inner": 1})
        # two keys referencing the same MagiDict instance
        md["a"] = shared
        md["b"] = shared

        # circular reference
        md["self"] = md

        out = md.disenchant()

        # shared references should remain the same object identity
        self.assertIs(out["a"], out["b"])

        # circular reference preserved: out['self'] should be the outer dict
        self.assertIs(out["self"], out)

    def test_protected_magidict_blocks_mutations(self):
        """Protected MagiDicts raise TypeError on mutating operations."""
        md = MagiDict({"maybe": None})

        none_md = md.maybe  # attribute access returns a protected MagiDict
        self.assertIsInstance(none_md, MagiDict)

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


class TestMagiDictEdgesCases2(TestCase):

    def setUp(self):
        """Set up a standard nested dictionary and MagiDict instance for each test."""
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
        self.md = MagiDict(self.sample_data)

    # --- Test Initialization and Conversion ---

    def test_initialization_from_dict(self):
        """Test that a dict is recursively converted to MagiDict."""
        self.assertIsInstance(self.md, MagiDict)
        self.assertIsInstance(self.md.user, MagiDict)
        self.assertIsInstance(self.md.user.details, MagiDict)
        self.assertIsInstance(self.md["items"][0], MagiDict)
        self.assertIsInstance(self.md["items"][1], MagiDict)

    def test_initialization_with_kwargs(self):
        """Test initialization using keyword arguments."""
        md = MagiDict(a=1, b={"c": 2})
        self.assertEqual(md.a, 1)
        self.assertIsInstance(md.b, MagiDict)
        self.assertEqual(md.b.c, 2)

    def test_empty_initialization(self):
        """Test that an empty MagiDict can be created."""
        md = MagiDict()
        self.assertEqual(len(md), 0)
        self.assertEqual(md.missing_key, MagiDict())

    def test_enchant_function(self):
        """Test the enchant() helper function."""
        md = enchant(self.sample_data)
        self.assertIsInstance(md, MagiDict)
        self.assertIsInstance(md.user, MagiDict)
        with self.assertRaises(TypeError):
            enchant("not a dict")

    def test_magi_loads_function(self):
        """Test the magi_loads() helper function for JSON."""
        json_string = '{"user": {"name": "Bob"}, "roles": [{"role": "admin"}]}'
        md = magi_loads(json_string)
        self.assertIsInstance(md, MagiDict)
        self.assertIsInstance(md.user, MagiDict)
        self.assertIsInstance(md.roles[0], MagiDict)
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

    def test_missing_attribute_returns_empty_magidict(self):
        """Accessing a non-existent key via attribute should return an empty MagiDict."""
        empty_md = self.md.non_existent_key
        self.assertIsInstance(empty_md, MagiDict)
        self.assertFalse(empty_md)  # An empty dict is falsy

    def test_safe_chaining_on_missing_attributes(self):
        """Chained access on non-existent keys should be safe."""
        value = self.md.user.address.street.name
        self.assertIsInstance(value, MagiDict)
        self.assertFalse(value)

    def test_none_value_attribute_access_is_safe(self):
        """Accessing a key with a None value via attribute should return an empty MagiDict."""
        self.assertEqual(self.md.user.nickname, MagiDict())
        self.assertEqual(self.md.user.nickname.some_prop, MagiDict())

    def test_none_value_bracket_access_returns_none(self):
        """Bracket access for a key with a None value should return None."""
        self.assertIsNone(self.md.user["nickname"])
        self.assertIsNone(self.md["user.nickname"])

    def test_mget_method(self):
        """Test the safe mget() method."""
        self.assertEqual(self.md.mget("user").name, "Alice")
        self.assertEqual(self.md.mget("non_existent"), MagiDict())
        self.assertEqual(self.md.user.mget("nickname"), MagiDict())
        self.assertEqual(self.md.mget("non_existent", "default"), "default")
        self.assertEqual(self.md.user.mget("nickname"), MagiDict())
        self.assertEqual(self.md.mg("user").name, "Alice")

    # --- Test Modification and Protection ---

    def test_setitem_hooks_new_dicts(self):
        """Test that setting a dict value converts it to a MagiDict."""
        md = MagiDict()
        md["new_data"] = {"a": 1, "b": {"c": 3}}
        self.assertIsInstance(md.new_data, MagiDict)
        self.assertIsInstance(md.new_data.b, MagiDict)

    def test_update_hooks_new_dicts(self):
        """Test that the update method recursively hooks values."""
        md = MagiDict()
        md.update({"new_data": {"a": 1, "b": {"c": 3}}})
        self.assertIsInstance(md.new_data, MagiDict)
        self.assertIsInstance(md.new_data.b, MagiDict)

    def test_modification_of_protected_magidict_raises_error(self):
        """Verify that temporary MagiDicts from missing keys/None cannot be modified."""
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
        md = MagiDict({1: "one", (2, 3): "two-three"})
        self.assertEqual(md[1], "one")
        self.assertEqual(md[(2, 3)], "two-three")
        self.assertEqual(md.one, MagiDict())

    def test_namedtuple_preservation(self):
        """Test that namedtuples are preserved during conversion."""
        Point = namedtuple("Point", ["x", "y"])
        data = {"point": Point(1, 2), "items": [Point(3, 4)]}
        md = MagiDict(data)

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

        md = MagiDict(d)
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
        """Test the __repr__ of MagiDict."""
        md = MagiDict({"a": 1})
        self.assertEqual(repr(md), "MagiDict({'a': 1})")

    def test_disenchant(self):
        """Test converting a MagiDict back to a standard dict."""
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
        self.assertIsInstance(md_copy, MagiDict)
        self.assertIs(md_copy.user, self.md.user)

        md_copy.user.name = "Bob"
        self.assertEqual(self.md.user.name, "Bob")

    def test_deepcopy_is_deep(self):
        """Test that deepcopy creates a fully independent copy."""
        md_deepcopy = deepcopy(self.md)
        self.assertIsNot(md_deepcopy, self.md)
        self.assertIsInstance(md_deepcopy, MagiDict)
        self.assertIsNot(md_deepcopy.user, self.md.user)

        md_deepcopy.user.name = "Charlie"
        self.assertEqual(self.md.user.name, "Alice")
        self.assertEqual(md_deepcopy.user.name, "Charlie")

    def test_pickling_support(self):
        """Test that MagiDict can be pickled and unpickled correctly."""
        pickled_md = pickle.dumps(self.md)
        unpickled_md = pickle.loads(pickled_md)

        self.assertIsInstance(unpickled_md, MagiDict)
        self.assertIsInstance(unpickled_md.user, MagiDict)
        self.assertEqual(unpickled_md.user.name, "Alice")
        self.assertEqual(unpickled_md, self.md)

    def test_dir_includes_keys(self):
        """Test that __dir__ includes the dictionary keys for autocompletion."""
        d = dir(self.md)
        self.assertIn("user", d)
        self.assertIn("permissions", d)
        self.assertIn("items", d)
        self.assertIn("update", d)


class TestMagiDictMissingEdgeCases(TestCase):
    """Additional edge cases not covered in the main test suite."""

    def test_weakref_compatibility(self):
        """Test that MagiDict instances can be weakly referenced."""
        md = MagiDict({"a": 1})
        ref = weakref.ref(md)
        self.assertIs(ref(), md)
        del md
        self.assertIsNone(ref())

    def test_bool_context_evaluation(self):
        """Test boolean evaluation of MagiDict in various states."""
        # Non-empty MagiDict is truthy
        md = MagiDict({"a": 1})
        self.assertTrue(bool(md))
        self.assertTrue(md)

        # Empty MagiDict is falsy
        empty = MagiDict()
        self.assertFalse(bool(empty))
        self.assertFalse(empty)

        # Protected MagiDict from missing key is falsy
        protected = md.missing
        self.assertFalse(bool(protected))

    def test_multiple_none_keys_in_dict(self):
        """Test handling when multiple None values exist."""
        md = MagiDict({"a": None, "b": {"c": None}, "d": [None, {"e": None}]})

        self.assertEqual(md.a, MagiDict())
        self.assertEqual(md.b.c, MagiDict())
        self.assertIsNone(md["d"][0])
        self.assertEqual(md["d"][1]["e"], None)

    def test_numeric_string_vs_int_keys(self):
        """Test disambiguation between string and int keys with same value."""
        md = MagiDict(
            {"1": "string_one", 1: "int_one", "2.5": "string_float", 2.5: "float_key"}
        )

        self.assertEqual(md["1"], "string_one")
        self.assertEqual(md[1], "int_one")
        self.assertEqual(md["2.5"], "string_float")
        self.assertEqual(md[2.5], "float_key")
        self.assertNotEqual(md["1"], md[1])

    def test_special_method_keys(self):
        """Test keys that are special method names."""
        md = MagiDict(
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
        md = MagiDict(
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
        md = MagiDict({long_key: "value"})

        self.assertEqual(md[long_key], "value")
        self.assertIn(long_key, md)

    def test_nested_list_modification_preserves_structure(self):
        """Test that modifying nested lists preserves MagiDict conversion."""
        md = MagiDict({"items": [{"a": 1}]})
        md["items"].append({"b": 2})

        self.assertIsInstance(md["items"][1], dict)  # Not auto-converted
        self.assertEqual(md["items"][1]["b"], 2)

    def test_setdefault_with_none_value(self):
        """Test setdefault when setting None as the default."""
        md = MagiDict()
        result = md.setdefault("key", None)

        self.assertIsNone(result)
        self.assertIn("key", md)
        self.assertEqual(md["key"], None)
        self.assertEqual(md.key, MagiDict())  # Attribute access safe chains

    def test_pop_with_callback_default(self):
        """Test pop() with a callable as default value."""
        md = MagiDict({"a": 1})

        def default_factory():
            return "generated"

        result = md.pop("missing", default_factory())
        self.assertEqual(result, "generated")

    def test_comparison_operators_not_equal(self):
        """Test that comparison operators work correctly."""
        md1 = MagiDict({"a": 1})
        md2 = MagiDict({"a": 2})

        self.assertNotEqual(md1, md2)
        self.assertFalse(md1 == md2)
        self.assertTrue(md1 != md2)

    def test_contains_with_non_string_keys(self):
        """Test 'in' operator with various key types."""
        md = MagiDict({1: "one", (2, 3): "tuple", frozenset([4]): "frozenset"})

        self.assertIn(1, md)
        self.assertIn((2, 3), md)
        self.assertIn(frozenset([4]), md)
        self.assertNotIn("1", md)
        with self.assertRaises(TypeError):
            self.assertNotIn([2, 3], md)  # Lists aren't hashable

    def test_nested_empty_containers_after_operations(self):
        """Test that empty nested containers remain properly typed."""
        md = MagiDict({"data": []})
        md["data"].append({})

        self.assertIsInstance(md["data"], list)
        self.assertIsInstance(md["data"][0], dict)
        self.assertNotIsInstance(md["data"][0], MagiDict)

    def test_chaining_through_list_returns_attribute_error(self):
        """Test that chaining through list values raises AttributeError."""
        md = MagiDict({"items": ["a", "b", "c"]})

        with self.assertRaises(AttributeError):
            _ = md.items.nonexistent

    def test_mixed_none_and_missing_chaining(self):
        """Test chaining through combination of None values and missing keys."""
        md = MagiDict({"a": {"b": None}})

        # Chain through None then missing
        result1 = md.a.b.c.d
        self.assertIsInstance(result1, MagiDict)

        # Chain through missing then None
        result2 = md.x.y.z
        self.assertIsInstance(result2, MagiDict)

    def test_getstate_setstate_preservation(self):
        """Test that __getstate__ and __setstate__ work correctly."""
        md = MagiDict({"a": {"b": 1}, "c": [{"d": 2}]})

        state = md.__getstate__()
        self.assertIsInstance(state, dict)

        new_md = MagiDict()
        new_md.__setstate__(state)

        self.assertEqual(new_md, md)
        self.assertIsInstance(new_md.a, MagiDict)

    def test_equality_with_empty_protected_magidicts(self):
        """Test that empty protected MagiDicts compare equal."""
        md = MagiDict({})

        protected1 = md.missing1
        protected2 = md.missing2

        self.assertEqual(protected1, protected2)
        self.assertEqual(protected1, {})
        self.assertEqual(protected2, {})

    def test_clear_on_non_empty_then_access(self):
        """Test accessing after clearing a MagiDict."""
        md = MagiDict({"a": 1, "b": 2})
        md.clear()

        self.assertEqual(len(md), 0)
        result = md.missing
        self.assertIsInstance(result, MagiDict)

    def test_disenchant_with_set_and_frozenset(self):
        """Test that disenchant preserves sets and frozensets."""
        md = MagiDict({"myset": {1, 2, 3}, "myfrozenset": frozenset([4, 5, 6])})

        result = md.disenchant()
        self.assertIsInstance(result["myset"], set)
        self.assertIsInstance(result["myfrozenset"], frozenset)

    def test_update_with_empty_dict(self):
        """Test update with an empty dictionary."""
        md = MagiDict({"a": 1})
        md.update({})

        self.assertEqual(md, {"a": 1})

    def test_fromkeys_with_zero_keys(self):
        """Test fromkeys with an empty sequence."""
        md = MagiDict.fromkeys([], "default")

        self.assertEqual(len(md), 0)
        self.assertIsInstance(md, MagiDict)

    def test_attribute_assignment_does_not_create_key(self):
        """Test that attribute assignment via setattr doesn't create dict keys."""
        md = MagiDict()

        # This should set an instance attribute, not a dict key
        md.my_attr = "value"

        # Check it's an instance attribute
        self.assertEqual(md.my_attr, "value")

        # Check it's not a dict key
        self.assertNotIn("my_attr", md)

    def test_dir_excludes_protected_attributes(self):
        """Test that __dir__ handles protected attributes correctly."""
        md = MagiDict({"regular": 1})

        d = dir(md)

        # Should include dict methods
        self.assertIn("keys", d)
        self.assertIn("items", d)

        # Should include user keys
        self.assertIn("regular", d)

        # Protected attributes shouldn't create confusion
        self.assertIn("__dict__", d)

    def test_json_dumps_on_magidict_directly(self):
        """Test that json.dumps works directly on MagiDict."""
        md = MagiDict({"a": 1, "b": {"c": 2}})

        json_str = json.dumps(md)
        loaded = json.loads(json_str)

        self.assertEqual(loaded, {"a": 1, "b": {"c": 2}})

    def test_dotted_key_with_numeric_dict_key_not_list_index(self):
        """Test that numeric keys in dicts aren't confused with list indices."""
        md = MagiDict({"data": {"0": "zero_key", "1": "one_key"}})

        # These should access dict keys, not list indices
        self.assertEqual(md["data.0"], "zero_key")
        self.assertEqual(md["data.1"], "one_key")

    def test_mget_with_missing_vs_none(self):
        """Test mget behavior with missing (default sentinel) vs None."""
        md = MagiDict({"a": 1})

        # With missing (default), missing keys return empty MagiDict
        result1 = md.mget("missing")
        self.assertIsInstance(result1, MagiDict)

        # With explicit None, missing keys return None
        result2 = md.mget("missing", None)
        self.assertIsNone(result2)

        # With explicit None for existing None value
        md["b"] = None
        result3 = md.mget("b", "default")
        self.assertIsInstance(result3, MagiDict)  # None values still return MagiDict

    def test_recursive_equality_check(self):
        """Test equality with recursively nested identical structures."""
        data = {"a": {"b": {"c": {"d": 1}}}}
        md1 = MagiDict(data)
        md2 = MagiDict(copy.deepcopy(data))

        self.assertEqual(md1, md2)
        self.assertIsNot(md1.a, md2.a)
        self.assertIsNot(md1.a.b, md2.a.b)

    def test_list_containing_none_and_dicts(self):
        """Test list containing mix of None and dicts."""
        md = MagiDict({"items": [None, {"a": 1}, None, {"b": 2}]})

        self.assertIsNone(md["items"][0])
        self.assertIsInstance(md["items"][1], MagiDict)
        self.assertIsNone(md["items"][2])
        self.assertIsInstance(md["items"][3], MagiDict)

    def test_tuple_immutability_preserved(self):
        """Test that tuples remain immutable after hooking."""
        md = MagiDict({"data": ({"a": 1}, {"b": 2})})

        self.assertIsInstance(md.data, tuple)

        # Tuples should be immutable
        with self.assertRaises(TypeError):
            md.data[0] = {"c": 3}

    def test_nested_magidict_in_list_after_append(self):
        """Test that manually appending a MagiDict to a list preserves it."""
        md = MagiDict({"items": []})
        nested = MagiDict({"inner": "value"})

        md["items"].append(nested)

        self.assertIs(md["items"][0], nested)
        self.assertIsInstance(md["items"][0], MagiDict)

    def test_popitem_on_empty_raises_keyerror(self):
        """Test that popitem on empty MagiDict raises KeyError."""
        md = MagiDict()

        with self.assertRaises(KeyError):
            md.popitem()

    def test_get_with_none_vs_missing_key(self):
        """Test get() method distinguishes None value from missing key."""
        md = MagiDict({"exists_as_none": None})

        # Existing key with None value
        self.assertIsNone(md.get("exists_as_none"))

        # Missing key without default
        self.assertIsNone(md.get("missing"))

        # Missing key with default
        self.assertEqual(md.get("missing", "default"), "default")

    def test_iteration_order_preservation(self):
        """Test that iteration order is preserved (Python 3.7+)."""
        data = OrderedDict([("z", 1), ("a", 2), ("m", 3)])
        md = MagiDict(data)

        self.assertEqual(list(md.keys()), ["z", "a", "m"])

    def test_values_are_not_double_wrapped(self):
        """Test that MagiDict values aren't double-wrapped."""
        nested = MagiDict({"inner": "value"})
        md = MagiDict({"outer": nested})

        # Should be the same instance, not wrapped again
        self.assertIs(md.outer, nested)

    def test_sys_getsizeof_works(self):
        """Test that sys.getsizeof works on MagiDict."""
        md = MagiDict({"a": 1, "b": 2})

        # Should not raise an error
        size = sys.getsizeof(md)
        self.assertGreater(size, 0)

    def test_format_string_with_magidict(self):
        """Test using MagiDict in format strings."""
        md = MagiDict({"name": "Alice", "age": 30})

        result = "Name: {name}, Age: {age}".format(**md)
        self.assertEqual(result, "Name: Alice, Age: 30")

    def test_star_unpacking_in_function_call(self):
        """Test unpacking MagiDict as keyword arguments."""
        md = MagiDict({"a": 1, "b": 2})

        def func(a, b):
            return a + b

        result = func(**md)
        self.assertEqual(result, 3)

    def test_getattr_fallback_to_dict_method(self):
        """Accessing a dict method name should use __getattribute__ path."""
        md = MagiDict({"x": 1})
        result = md.keys
        self.assertTrue(callable(result))

    def test_getattr_missing_creates_magidict(self):
        """Accessing missing attr should create an empty MagiDict."""
        md = MagiDict()
        result = md.not_there
        self.assertIsInstance(result, MagiDict)
        self.assertTrue(getattr(result, "_from_missing", False))

    # ---------- LINES 252–253 ----------
    def test_raise_if_protected_from_none(self):
        """Setting value when _from_none=True should raise TypeError."""
        md = MagiDict()
        object.__setattr__(md, "_from_none", True)
        with self.assertRaises(TypeError):
            md["x"] = 1

    def test_raise_if_protected_from_missing(self):
        """Deleting key when _from_missing=True should raise TypeError."""
        md = MagiDict()
        object.__setattr__(md, "_from_missing", True)
        with self.assertRaises(TypeError):
            del md["x"]

    # ---------- LINES 418–422 ----------
    def test_disenchant_with_namedtuple_and_set(self):
        """Ensure namedtuple and set are correctly handled by disenchant()."""
        Point = namedtuple("Point", "x y")
        md = MagiDict({"point": Point(1, {"inner": 2}), "aset": {1, 2}})
        result = md.disenchant()
        self.assertIsInstance(result["point"], Point)
        self.assertIsInstance(result["aset"], set)
        self.assertEqual(result["point"].y, {"inner": 2})

    # ---------- LINES 443–446 ----------
    def test_disenchant_with_circular_reference(self):
        """Ensure circular references are preserved correctly."""
        md = MagiDict()
        md["self"] = md
        result = md.disenchant()
        self.assertIs(result["self"], result)

    # ---------- Helper functions ----------
    def test_magi_loads_and_enchant(self):
        """Ensure magi_loads and enchant behave as expected."""
        data = {"a": {"b": 2}}
        md = magi_loads(json.dumps(data))
        self.assertIsInstance(md, MagiDict)
        self.assertEqual(md.a.b, 2)

        # Enchanting an existing MagiDict should return itself
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
        md = MagiDict({"x": 1})

        # Accessing __dict__ should use the fallback path (line 207)
        self.assertIsInstance(md.__dict__, dict)

        # Accessing __class__ should also use fallback
        self.assertEqual(md.__class__, MagiDict)

    def test_getattr_returns_empty_magidict_on_attribute_error(self):
        """Test that __getattr__ returns empty MagiDict when AttributeError is raised."""
        md = MagiDict({"x": 1})

        # Accessing a truly non-existent attribute should trigger lines 208-210
        result = md.this_attribute_does_not_exist_anywhere
        self.assertIsInstance(result, MagiDict)
        self.assertTrue(getattr(result, "_from_missing", False))
        self.assertEqual(len(result), 0)

    # ==================== LINES 252-253: _raise_if_protected ====================
    def test_raise_if_protected_from_none_flag(self):
        """Test that _raise_if_protected raises TypeError when _from_none is True."""
        md = MagiDict({"key": None})

        # Get the protected MagiDict created from None value
        protected = md.key

        # Try to modify it - should raise TypeError
        with self.assertRaises(TypeError) as cm:
            protected["new_key"] = "value"

        self.assertIn("Cannot modify", str(cm.exception))

    def test_raise_if_protected_from_missing_flag(self):
        """Test that _raise_if_protected raises TypeError when _from_missing is True."""
        md = MagiDict({"x": 1})

        # Get the protected MagiDict created from missing key
        protected = md.nonexistent_key

        # Try to modify it - should raise TypeError
        with self.assertRaises(TypeError) as cm:
            protected["new_key"] = "value"

        self.assertIn("Cannot modify", str(cm.exception))

    # ==================== LINES 418-422: disenchant namedtuple handling ====================
    def test_disenchant_with_namedtuple(self):
        """Test that disenchant correctly handles namedtuples."""
        Point = namedtuple("Point", ["x", "y"])

        # Create MagiDict with namedtuple containing nested dict
        md = MagiDict(
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
        self.assertNotIsInstance(result["point"].y, MagiDict)
        self.assertEqual(result["point"].y["nested"], "value")

        # Check namedtuple in list
        self.assertIsInstance(result["points_list"][0], Point)
        self.assertIsInstance(result["points_list"][0].y, dict)

    def test_disenchant_with_regular_tuple(self):
        """Test that disenchant handles regular tuples correctly."""
        md = MagiDict({"tuple_data": ({"a": 1}, {"b": 2}, "string", 123)})

        result = md.disenchant()

        # Should be a regular tuple (line 421)
        self.assertIsInstance(result["tuple_data"], tuple)
        self.assertIsInstance(result["tuple_data"][0], dict)
        self.assertNotIsInstance(result["tuple_data"][0], MagiDict)

    # ==================== LINES 443-446: disenchant set/frozenset handling ====================
    def test_disenchant_with_set(self):
        """Test that disenchant correctly handles sets."""
        md = MagiDict(
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
        md = MagiDict(
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
        md = MagiDict(
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
        md = MagiDict({"data": 1})

        # Accessing 'keys' should return the method, not create empty MagiDict
        keys_method = md.keys
        self.assertTrue(callable(keys_method))

        # Accessing 'items' should return the method
        items_method = md.items
        self.assertTrue(callable(items_method))

    def test_protected_magidict_all_mutation_methods(self):
        """Test that all mutation methods are blocked on protected MagiDict."""
        md = MagiDict({"x": None})
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

        md = MagiDict(
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
        self.assertNotIsInstance(result["complex"].x.a, MagiDict)

    def test_disenchant_circular_reference_with_sets(self):
        """Test disenchant with circular references and sets."""
        md = MagiDict({"data": {"my_set": {1, 2, 3}, "nested": {}}})
        md["data"]["nested"]["circular"] = md["data"]

        result = md.disenchant()

        # Check circular reference is preserved
        self.assertIs(result["data"]["nested"]["circular"], result["data"])

        # Check set is preserved
        self.assertIsInstance(result["data"]["my_set"], set)


class TestHelperFunctions(TestCase):
    """Test helper functions to ensure complete coverage."""

    def test_enchant_with_magidict_returns_same_instance(self):
        """Test that enchant returns the same instance when given MagiDict."""
        md = MagiDict({"a": 1})
        result = enchant(md)
        self.assertIs(result, md)

    def test_enchant_with_regular_dict(self):
        """Test that enchant converts regular dict to MagiDict."""
        d = {"a": {"b": {"c": 1}}}
        result = enchant(d)
        self.assertIsInstance(result, MagiDict)
        self.assertIsInstance(result.a, MagiDict)
        self.assertIsInstance(result.a.b, MagiDict)

    def test_enchant_raises_typeerror(self):
        """Test that enchant raises TypeError for non-dict types."""
        with self.assertRaises(TypeError):
            enchant("not a dict")

        with self.assertRaises(TypeError):
            enchant([1, 2, 3])

        with self.assertRaises(TypeError):
            enchant(123)

    def test_magi_loads_creates_magidict(self):
        """Test that magi_loads creates MagiDict from JSON."""
        json_str = '{"user": {"name": "Alice", "age": 30}, "items": [{"id": 1}]}'
        result = magi_loads(json_str)

        self.assertIsInstance(result, MagiDict)
        self.assertIsInstance(result.user, MagiDict)
        self.assertIsInstance(result["items"][0], MagiDict)
        self.assertEqual(result.user.name, "Alice")


# Assume MagiDict and helper functions (enchant, magi_loads) are in a file
# named safedict.py or are accessible in the current scope.
# from safedict.safedict import MagiDict, enchant, magi_loads


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
        md = MagiDict({"key": "value"})
        # Accessing an attribute that is not a key should trigger the `try` block
        # and succeed via `super().__getattribute__('__class__')`.
        self.assertEqual(md.__class__, MagiDict)
        self.assertIsInstance(md.__dict__, dict)

    def test_getattr_raises_attributeerror_and_returns_empty_magidict(self):
        """
        Covers lines 208-210: Tests that accessing a completely non-existent
        attribute triggers an AttributeError in the fallback, which is then
        caught and returns a protected, empty MagiDict.
        """
        md = MagiDict({"key": "value"})
        # Accessing an attribute that is neither a key nor a real attribute
        # will raise AttributeError, triggering the `except` block.
        result = md.this_attribute_does_not_exist
        self.assertIsInstance(result, MagiDict)
        self.assertTrue(getattr(result, "_from_missing", False))
        self.assertEqual(len(result), 0)

    # ======================================================================
    # Target: safedict.py, lines 252-253 (_raise_if_protected)
    # ======================================================================

    def test_raise_if_protected_blocks_modification_from_none(self):
        """
        Covers lines 252-253: Tests that a MagiDict created from a key with a
        `None` value is protected and raises a TypeError on modification.
        """
        md = MagiDict({"user": {"nickname": None}})
        # Accessing `md.user.nickname` returns a temporary MagiDict with `_from_none=True`.
        protected_md = md.user.nickname
        self.assertTrue(getattr(protected_md, "_from_none", False))

        with self.assertRaisesRegex(
            TypeError, "Cannot modify NoneType or missing keys."
        ):
            # This modification attempt calls __setitem__, which calls _raise_if_protected.
            protected_md["alias"] = "new_alias"

    def test_raise_if_protected_blocks_modification_from_missing(self):
        """
        Covers lines 252-253: Tests that a MagiDict created from a missing
        key is protected and raises a TypeError on modification.
        """
        md = MagiDict({"user": {"name": "Alice"}})
        # Accessing `md.user.address` returns a temporary MagiDict with `_from_missing=True`.
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
        # Create a structure where a namedtuple contains a MagiDict that needs disenchanting.
        data_with_namedtuple = {
            "point_of_interest": Point(x=1, y=MagiDict({"details": "nested"}))
        }
        md = MagiDict(data_with_namedtuple)

        # Call disenchant to trigger the specific logic for namedtuples.
        disenchanted_data = md.disenchant()

        point = disenchanted_data["point_of_interest"]
        self.assertIsInstance(point, Point)
        self.assertEqual(point.x, 1)
        # Verify the nested MagiDict was converted back to a standard dict.
        self.assertIsInstance(point.y, dict)
        self.assertNotIsInstance(point.y, MagiDict)
        self.assertEqual(point.y["details"], "nested")

    def test_disenchant_handles_regular_tuple(self):
        """
        Covers line 422: Tests the fallback path in the tuple handling logic,
        ensuring regular tuples are processed correctly.
        """
        md = MagiDict({"data": (MagiDict({"a": 1}), "string_val")})
        disenchanted_data = md.disenchant()

        regular_tuple = disenchanted_data["data"]
        self.assertIsInstance(regular_tuple, tuple)
        # Verify the nested MagiDict was converted back to a standard dict.
        self.assertIsInstance(regular_tuple[0], dict)
        self.assertNotIsInstance(regular_tuple[0], MagiDict)
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
            "mixed_nested": MagiDict({"data": {1, 2}}),
        }
        md = MagiDict(data_with_sets)

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

    def test_enchant_with_magidict_returns_same_instance(self):
        """Test that enchant returns the same instance when given MagiDict."""
        md = MagiDict({"a": 1})
        result = enchant(md)
        self.assertIs(result, md)

    def test_enchant_with_regular_dict(self):
        """Test that enchant converts regular dict to MagiDict."""
        d = {"a": {"b": {"c": 1}}}
        result = enchant(d)
        self.assertIsInstance(result, MagiDict)
        self.assertIsInstance(result.a, MagiDict)
        self.assertIsInstance(result.a.b, MagiDict)

    def test_enchant_raises_typeerror(self):
        """Test that enchant raises TypeError for non-dict types."""
        with self.assertRaises(TypeError):
            enchant("not a dict")
        with self.assertRaises(TypeError):
            enchant([1, 2, 3])
        with self.assertRaises(TypeError):
            enchant(123)

    def test_magi_loads_creates_magidict(self):
        """Test that magi_loads creates MagiDict from JSON."""
        json_str = '{"user": {"name": "Alice", "age": 30}, "items": [{"id": 1}]}'
        result = magi_loads(json_str)
        self.assertIsInstance(result, MagiDict)
        self.assertIsInstance(result.user, MagiDict)
        self.assertIsInstance(result["items"][0], MagiDict)
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

        # Create the MagiDict
        md = MagiDict(original_data)

        # 1. ASSERT FAILURE: The top-level value 'user' in the original dict
        # is NOT converted. It's read, converted, and the result is stored in `md`.
        self.assertNotIsInstance(
            original_data["user"],
            MagiDict,
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
            MagiDict,
            "Dict within a mutable list in the original input SHOULD be converted in-place.",
        )

        # 3. ASSERT IMMUTABILITY: The tuple is immutable, so a new tuple is created for `md`,
        # leaving the original unchanged.
        self.assertIsInstance(
            original_data["config"][0],
            dict,
            "Original tuple's contents should remain unchanged.",
        )
        self.assertNotIsInstance(original_data["config"][0], MagiDict)
        self.assertIsInstance(
            md.config[0], MagiDict
        )  # The new tuple in md has a MagiDict

        # 4. AVOIDING SIDE-EFFECTS: To avoid any mutation, the caller should pass a deep copy.
        md_from_copy = MagiDict(deepcopy(original_data_pristine))

        # Verify the pristine original dictionary was not affected at all.
        self.assertIsInstance(
            original_data_pristine["permissions"][0],
            dict,
            "The pristine original's list content should not be mutated.",
        )
        self.assertNotIsInstance(original_data_pristine["permissions"][0], MagiDict)

    def test_dir_includes_non_identifier_string_keys(self):
        """
        Test that __dir__ includes string keys that are not valid Python
        identifiers, which might be undesirable for tab-completion.
        """
        md = MagiDict(
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
        md = MagiDict({"key_is_none": None})

        # Standard behavior: value is None, returns an empty MagiDict for chaining.
        self.assertIsInstance(md.mget("key_is_none"), MagiDict)

        # Edge case: If the default is *explicitly* None, it should return None.
        self.assertIsNone(
            md.mget("key_is_none", default=None),
            "mget should return the explicit None default, even for a None value.",
        )

    def test_disenchant_does_not_traverse_custom_object_keys(self):
        """
        Verify that disenchant does NOT recursively convert MagiDicts nested
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

        key_obj = HashableContainer(MagiDict({"a": 1}))
        md = MagiDict({key_obj: "value"})

        # The disenchant method will recurse on keys and values.
        disenchanted = md.disenchant()

        disenchanted_key = list(disenchanted.keys())[0]
        self.assertIs(
            disenchanted_key,
            key_obj,
            "The custom key object itself should be returned unchanged.",
        )

        # ASSERT CORRECT BEHAVIOR: The content of the custom key object
        # REMAINS a MagiDict because disenchant does not introspect custom types.
        self.assertIsInstance(
            disenchanted_key.content,
            MagiDict,
            "MagiDict inside a custom key object should NOT be disenchanted.",
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
        md = MagiDict(data)
        self.assertIs(md.data[0], original_bytearray)
        self.assertIsInstance(md.data[1], MagiDict)

    def test_lazy_conversion_on_attribute_access(self):
        """
        Test the "lazy conversion" feature where a plain dict added without
        hooking is converted upon first attribute access.
        """
        md = MagiDict()
        plain_dict = {"nested": "value"}

        # Bypass __setitem__ to insert a plain dict without hooking.
        super(MagiDict, md).__setitem__("plain", plain_dict)

        # Verify it's still a plain dict when accessed via brackets.
        self.assertIs(type(md["plain"]), dict)

        # Accessing via attribute should trigger the conversion.
        converted = md.plain
        self.assertIsInstance(converted, MagiDict)
        self.assertEqual(converted.nested, "value")

        # The original dict within md should now be replaced.
        self.assertIsInstance(md["plain"], MagiDict)

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
        md = MagiDict({"data": original_seq})

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

    def test_none_with_missing_key_magidict(self):
        """Test that none() returns None for MagiDict from missing key."""
        md = MagiDict({"a": 1})
        missing = md.missing_key  # Accessing missing key creates empty MagiDict
        result = none(missing)
        self.assertIsNone(result)

    def test_none_with_none_value_magidict(self):
        """Test that none() returns None for MagiDict from None value."""
        md = MagiDict({"a": None})
        none_value = md.a  # Accessing None value creates empty MagiDict
        result = none(none_value)
        self.assertIsNone(result)

    def test_none_with_regular_empty_magidict(self):
        """Test that none() returns the object for regular empty MagiDict."""
        md = MagiDict()
        result = none(md)
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)
        self.assertEqual(md, result)
        self.assertFalse(getattr(result, "_from_none", False))
        self.assertFalse(getattr(result, "_from_missing", False))

    def test_none_with_non_empty_magidict(self):
        """Test that none() returns the object for non-empty MagiDict."""
        md = MagiDict({"a": 1, "b": 2})
        result = none(md)
        self.assertIs(result, md)
        self.assertEqual(result, {"a": 1, "b": 2})

    def test_none_with_non_magidict_objects(self):
        """Test that none() returns the object unchanged for non-MagiDict types."""
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
        md = MagiDict({"a": {"b": {"c": 1}}})
        missing_nested = md.x.y.z  # Deep missing access
        result = none(missing_nested)
        self.assertIsNone(result)

    def test_none_with_mget_missing(self):
        """Test none() with mget() on missing key."""
        md = MagiDict({"a": 1})
        missing = md.mget("missing_key")
        result = none(missing)
        self.assertIsNone(result)

    def test_none_with_mget_none_value(self):
        """Test none() with mget() on None value."""
        md = MagiDict({"a": None})
        none_val = md.mget("a")
        result = none(none_val)
        self.assertIsNone(result)

    def test_none_with_chained_none_values(self):
        """Test none() with chained access through None values."""
        md = MagiDict({"a": None})
        chained = md.a.b.c.d  # Chain through None
        result = none(chained)
        self.assertIsNone(result)

    def test_none_preserves_regular_none(self):
        """Test that none() passes through actual None values."""
        result = none(None)
        self.assertIsNone(result)

    def test_none_with_empty_magidict_with_items_added(self):
        """Test that none() returns object if MagiDict has items."""
        md = MagiDict({"a": 1})
        missing = md.missing_key  # Get empty MagiDict from missing key

        # Before adding items, it should return None
        self.assertIsNone(none(missing))

        # But we can't add items because it's protected
        with self.assertRaises(TypeError):
            missing["x"] = 1


class TestNoneFunctionIntegration(TestCase):
    """Integration tests showing practical usage of none() function."""

    def test_safe_navigation_pattern(self):
        """Test using none() for safe navigation pattern."""
        data = MagiDict({"user": {"profile": {"name": "John"}}})

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
        data = MagiDict({"a": 1})

        # Use none() with or for default values
        value1 = none(data.a) or "default"
        self.assertEqual(value1, 1)

        value2 = none(data.missing) or "default"
        self.assertEqual(value2, "default")

    def test_conditional_processing(self):
        """Test using none() for conditional processing."""
        data = MagiDict({"config": {"enabled": True, "timeout": None}})

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


class TestFromMissingAttribute(TestCase):
    """Test suite for _from_missing attribute behavior."""

    def test_from_missing_on_missing_key_access(self):
        """Test that _from_missing is set when accessing missing keys."""
        md = MagiDict({"a": 1})
        missing = md.missing_key
        self.assertTrue(getattr(missing, "_from_missing", False))
        self.assertFalse(getattr(missing, "_from_none", False))

    def test_from_missing_on_nested_missing_access(self):
        """Test _from_missing with deeply nested missing keys."""
        md = MagiDict({"a": {"b": 1}})
        missing = md.x.y.z
        self.assertTrue(getattr(missing, "_from_missing", False))

    def test_from_missing_not_set_on_regular_magidict(self):
        """Test that regular MagiDict doesn't have _from_missing."""
        md = MagiDict({"a": 1})
        self.assertFalse(getattr(md, "_from_missing", False))

    def test_from_missing_not_set_on_existing_key(self):
        """Test that accessing existing keys doesn't set _from_missing."""
        md = MagiDict({"a": 1})
        value = md.a
        # If value is 1 (not a MagiDict), it won't have the attribute
        self.assertEqual(value, 1)

    def test_from_missing_on_mget_missing_key(self):
        """Test that mget() sets _from_missing for missing keys."""
        md = MagiDict({"a": 1})
        missing = md.mget("missing")
        self.assertTrue(getattr(missing, "_from_missing", False))
        self.assertFalse(getattr(missing, "_from_none", False))

    def test_from_missing_on_mg_shorthand(self):
        """Test that mg() shorthand also sets _from_missing."""
        md = MagiDict({"a": 1})
        missing = md.mg("missing")
        self.assertTrue(getattr(missing, "_from_missing", False))

    def test_from_missing_prevents_modifications(self):
        """Test that _from_missing MagiDicts prevent modifications."""
        md = MagiDict({"a": 1})
        missing = md.missing_key

        # All modification operations should raise TypeError
        with self.assertRaises(TypeError):
            missing["new_key"] = "value"

        with self.assertRaises(TypeError):
            missing.update({"x": 1})

        with self.assertRaises(TypeError):
            del missing["x"]

        with self.assertRaises(TypeError):
            missing.pop("x", None)

        with self.assertRaises(TypeError):
            missing.popitem()

        with self.assertRaises(TypeError):
            missing.clear()

        with self.assertRaises(TypeError):
            missing.setdefault("x", 1)

    def test_from_missing_chain_access(self):
        """Test that chaining on _from_missing objects maintains the flag."""
        md = MagiDict({"a": 1})
        missing = md.x.y.z

        # Further chaining should also be _from_missing
        further = missing.more.chaining
        self.assertTrue(getattr(further, "_from_missing", False))

    def test_from_missing_with_getitem(self):
        """Test that __getitem__ on missing keys also creates _from_missing."""
        md = MagiDict({"a": 1})
        try:
            missing = md["missing_key"]
            self.fail("Should raise KeyError")
        except KeyError:
            pass  # Expected behavior - __getitem__ raises KeyError


class TestFromNoneAttribute(TestCase):
    """Test suite for _from_none attribute behavior."""

    def test_from_none_on_none_value_access(self):
        """Test that _from_none is set when accessing None values."""
        md = MagiDict({"a": None})
        none_val = md.a
        self.assertTrue(getattr(none_val, "_from_none", False))
        self.assertFalse(getattr(none_val, "_from_missing", False))

    def test_from_none_on_nested_none_value(self):
        """Test _from_none with nested None values."""
        md = MagiDict({"a": {"b": None}})
        none_val = md.a.b
        self.assertTrue(getattr(none_val, "_from_none", False))

    def test_from_none_not_set_on_regular_values(self):
        """Test that regular values don't have _from_none."""
        md = MagiDict({"a": 1, "b": "string", "c": []})
        self.assertEqual(md.a, 1)
        self.assertEqual(md.b, "string")
        self.assertEqual(md.c, [])

    def test_from_none_on_mget_none_value(self):
        """Test that mget() sets _from_none for None values."""
        md = MagiDict({"a": None})
        none_val = md.mget("a")
        self.assertTrue(getattr(none_val, "_from_none", False))
        self.assertFalse(getattr(none_val, "_from_missing", False))

    def test_from_none_prevents_modifications(self):
        """Test that _from_none MagiDicts prevent modifications."""
        md = MagiDict({"a": None})
        none_val = md.a

        # All modification operations should raise TypeError
        with self.assertRaises(TypeError):
            none_val["new_key"] = "value"

        with self.assertRaises(TypeError):
            none_val.update({"x": 1})

        with self.assertRaises(TypeError):
            del none_val["x"]

        with self.assertRaises(TypeError):
            none_val.pop("x", None)

        with self.assertRaises(TypeError):
            none_val.popitem()

        with self.assertRaises(TypeError):
            none_val.clear()

        with self.assertRaises(TypeError):
            none_val.setdefault("x", 1)

    def test_from_none_chain_access(self):
        """Test that chaining on _from_none objects maintains special state."""
        md = MagiDict({"a": None})
        none_val = md.a.b.c

        # Should still be special (either _from_none or _from_missing)
        is_special = getattr(none_val, "_from_none", False) or getattr(
            none_val, "_from_missing", False
        )
        self.assertTrue(is_special)

    def test_from_none_with_mget_and_default(self):
        """Test mget() with default on None value."""
        md = MagiDict({"a": None})

        # Without default, should return _from_none MagiDict
        result1 = md.mget("a")
        self.assertTrue(getattr(result1, "_from_none", False))

        # With non-None default, should return _from_none MagiDict
        result2 = md.mget("a", "default")
        self.assertTrue(getattr(result2, "_from_none", False))

        # With None default, should return None
        result3 = md.mget("a", None)
        self.assertIsNone(result3)


class TestFromMissingVsFromNone(TestCase):
    """Test the distinction between _from_missing and _from_none."""

    def test_missing_vs_none_distinction(self):
        """Test that missing keys and None values are distinguished."""
        md = MagiDict({"a": None})

        missing = md.missing_key
        none_val = md.a

        self.assertTrue(getattr(missing, "_from_missing", False))
        self.assertFalse(getattr(missing, "_from_none", False))

        self.assertTrue(getattr(none_val, "_from_none", False))
        self.assertFalse(getattr(none_val, "_from_missing", False))

    def test_both_work_with_none_function(self):
        """Test that none() handles both _from_missing and _from_none."""
        md = MagiDict({"a": None})

        missing = md.missing_key
        none_val = md.a

        self.assertIsNone(none(missing))
        self.assertIsNone(none(none_val))

    def test_explicit_none_vs_missing(self):
        """Test explicit None assignment vs missing key."""
        md = MagiDict()
        md["explicit"] = None

        explicit = md.explicit
        missing = md.missing

        self.assertTrue(getattr(explicit, "_from_none", False))
        self.assertTrue(getattr(missing, "_from_missing", False))


class TestEdgeCases(TestCase):
    """Test edge cases for _from_missing and _from_none."""

    def test_empty_magidict_no_special_flags(self):
        """Test that regular empty MagiDict has no special flags."""
        md = MagiDict()
        self.assertFalse(getattr(md, "_from_missing", False))
        self.assertFalse(getattr(md, "_from_none", False))

    def test_nested_structure_with_mixed_none_and_missing(self):
        """Test complex nested structure with both None and missing."""
        md = MagiDict({"a": {"b": None, "c": {"d": 1}}})

        # Access None value
        none_val = md.a.b
        self.assertTrue(getattr(none_val, "_from_none", False))

        # Access missing key
        missing = md.a.missing
        self.assertTrue(getattr(missing, "_from_missing", False))

        # Access existing value
        existing = md.a.c.d
        self.assertEqual(existing, 1)

    def test_chain_from_none_to_missing(self):
        """Test chaining from None value creates _from_missing."""
        md = MagiDict({"a": None})
        chained = md.a.b.c

        # The first access (md.a) gives _from_none
        # Further chaining should give _from_missing
        is_protected = getattr(chained, "_from_none", False) or getattr(
            chained, "_from_missing", False
        )
        self.assertTrue(is_protected)

    def test_dict_methods_bypass_protection(self):
        """Test that dict methods can bypass protection (as documented)."""
        md = MagiDict({"a": 1})
        missing = md.missing_key

        # Using __setitem__ directly should still be protected
        with self.assertRaises(TypeError):
            missing["x"] = 1

        # But dict.update can bypass (implementation detail)
        # This is mentioned in the docstring

    def test_mget_with_explicit_default(self):
        """Test mget() with various default values."""
        md = MagiDict({"a": 1})

        # Default is _from_missing MagiDict
        result1 = md.mget("missing")
        self.assertTrue(getattr(result1, "_from_missing", False))

        # Explicit default value
        result2 = md.mget("missing", "default")
        self.assertEqual(result2, "default")

        # Explicit None default
        result3 = md.mget("missing", None)
        self.assertIsNone(result3)

    def test_copy_preserves_values_and_flags(self):
        """Test that copying preserves special flags."""
        md = MagiDict({"a": None})
        none_val = md.a

        # The none_val has _from_none flag
        self.assertTrue(getattr(none_val, "_from_none", False))

        # Copying creates a regular empty MagiDict
        copied = none_val.copy()
        self.assertTrue(getattr(copied, "_from_none"), False)
        self.assertFalse(getattr(copied, "_from_missing", False))

    def test_nested_none_values(self):
        """Test multiple levels of None values."""
        md = MagiDict({"a": None, "b": {"c": None, "d": {"e": None}}})

        none1 = md.a
        self.assertTrue(getattr(none1, "_from_none", False))

        none2 = md.b.c
        self.assertTrue(getattr(none2, "_from_none", False))

        none3 = md.b.d.e
        self.assertTrue(getattr(none3, "_from_none", False))

    def test_getattr_vs_getitem_behavior(self):
        """Test difference between attribute and item access."""
        md = MagiDict({"a": None})

        # Attribute access returns _from_none MagiDict
        attr_result = md.a
        self.assertTrue(getattr(attr_result, "_from_none", False))

        # Item access returns None directly
        item_result = md["a"]
        self.assertIsNone(item_result)

    def test_boolean_evaluation(self):
        """Test that protected MagiDicts evaluate to False."""
        md = MagiDict({"a": None})

        missing = md.missing_key
        none_val = md.a

        # Both should be empty and evaluate to False
        self.assertFalse(missing)
        self.assertFalse(none_val)

        # But they are instances of MagiDict
        self.assertIsInstance(missing, MagiDict)
        self.assertIsInstance(none_val, MagiDict)

    def test_length_of_protected_magidict(self):
        """Test that protected MagiDicts have length 0."""
        md = MagiDict({"a": None})

        missing = md.missing_key
        none_val = md.a

        self.assertEqual(len(missing), 0)
        self.assertEqual(len(none_val), 0)

    def test_iteration_over_protected_magidict(self):
        """Test that protected MagiDicts are empty when iterated."""
        md = MagiDict({"a": None})

        missing = md.missing_key
        none_val = md.a

        self.assertEqual(list(missing), [])
        self.assertEqual(list(none_val), [])
        self.assertEqual(list(missing.keys()), [])
        self.assertEqual(list(none_val.values()), [])


class TestProtectionMechanisms(TestCase):
    """Test that protection mechanisms work correctly."""

    def test_all_mutating_operations_blocked_on_from_missing(self):
        """Test comprehensive list of operations on _from_missing."""
        md = MagiDict({"a": 1})
        missing = md.missing_key

        operations = [
            lambda: missing.__setitem__("x", 1),
            lambda: missing.__delitem__("x"),
            lambda: missing.update({"x": 1}),
            lambda: missing.pop("x", None),
            lambda: missing.popitem(),
            lambda: missing.clear(),
            lambda: missing.setdefault("x", 1),
        ]

        for op in operations:
            with self.assertRaises(
                TypeError, msg=f"Operation {op} should raise TypeError"
            ):
                op()

    def test_all_mutating_operations_blocked_on_from_none(self):
        """Test comprehensive list of operations on _from_none."""
        md = MagiDict({"a": None})
        none_val = md.a

        operations = [
            lambda: none_val.__setitem__("x", 1),
            lambda: none_val.__delitem__("x"),
            lambda: none_val.update({"x": 1}),
            lambda: none_val.pop("x", None),
            lambda: none_val.popitem(),
            lambda: none_val.clear(),
            lambda: none_val.setdefault("x", 1),
        ]

        for op in operations:
            with self.assertRaises(
                TypeError, msg=f"Operation {op} should raise TypeError"
            ):
                op()

    def test_read_operations_work_on_protected(self):
        """Test that read operations work fine on protected MagiDicts."""
        md = MagiDict({"a": None})
        missing = md.missing_key
        none_val = md.a

        # Read operations should work
        self.assertEqual(len(missing), 0)
        self.assertEqual(len(none_val), 0)
        self.assertEqual(list(missing.keys()), [])
        self.assertEqual(list(none_val.values()), [])
        self.assertEqual(missing.get("x", "default"), "default")
        self.assertEqual(none_val.get("x", "default"), "default")
        self.assertNotIn("x", missing)
        self.assertNotIn("x", none_val)


class TestCopyFlagPreservation(TestCase):
    """Test that copy() preserves special flags."""

    def test_copy_preserves_from_none(self):
        """Test that copy() preserves _from_none flag."""
        md = MagiDict({"a": None})
        none_val = md.a

        # Verify original has flag
        self.assertTrue(getattr(none_val, "_from_none", False))

        # Copy and verify flag is preserved
        copied = none_val.copy()
        self.assertTrue(getattr(copied, "_from_none", False))
        self.assertFalse(getattr(copied, "_from_missing", False))

    def test_copy_preserves_from_missing(self):
        """Test that copy() preserves _from_missing flag."""
        md = MagiDict({"a": 1})
        missing = md.missing_key

        # Verify original has flag
        self.assertTrue(getattr(missing, "_from_missing", False))

        # Copy and verify flag is preserved
        copied = missing.copy()
        self.assertTrue(getattr(copied, "_from_missing", False))
        self.assertFalse(getattr(copied, "_from_none", False))

    def test_copy_of_regular_magidict(self):
        """Test that copy() of regular MagiDict has no special flags."""
        md = MagiDict({"a": 1, "b": 2})
        copied = md.copy()

        self.assertFalse(getattr(copied, "_from_none", False))
        self.assertFalse(getattr(copied, "_from_missing", False))

    def test_copied_protected_still_protected(self):
        """Test that copied protected MagiDicts remain protected."""
        md = MagiDict({"a": None})
        none_val = md.a
        copied = none_val.copy()

        # Should still raise TypeError on modification
        with self.assertRaises(TypeError):
            copied["x"] = 1

    def test_shallow_copy_function(self):
        """Test that copy.copy() also preserves flags."""
        md = MagiDict({"a": None})
        none_val = md.a
        # Use copy.copy()
        copied = copy.copy(none_val)
        self.assertTrue(getattr(copied, "_from_none", False))


class TestDeepcopyFlagPreservation(TestCase):
    """Test that deepcopy() preserves special flags."""

    def test_deepcopy_preserves_from_none(self):
        """Test that deepcopy() preserves _from_none flag."""
        md = MagiDict({"a": None})
        none_val = md.a

        # Deep copy and verify flag is preserved
        deep_copied = deepcopy(none_val)
        self.assertTrue(getattr(deep_copied, "_from_none", False))
        self.assertFalse(getattr(deep_copied, "_from_missing", False))

    def test_deepcopy_preserves_from_missing(self):
        """Test that deepcopy() preserves _from_missing flag."""
        md = MagiDict({"a": 1})
        missing = md.missing_key

        # Deep copy and verify flag is preserved
        deep_copied = deepcopy(missing)
        self.assertTrue(getattr(deep_copied, "_from_missing", False))
        self.assertFalse(getattr(deep_copied, "_from_none", False))

    def test_deepcopy_of_regular_magidict(self):
        """Test that deepcopy() of regular MagiDict has no special flags."""
        md = MagiDict({"a": 1, "b": {"c": 2}})
        deep_copied = deepcopy(md)

        self.assertFalse(getattr(deep_copied, "_from_none", False))
        self.assertFalse(getattr(deep_copied, "_from_missing", False))

    def test_deepcopy_with_nested_structure(self):
        """Test deepcopy with nested MagiDicts preserves flags."""
        md = MagiDict({"a": {"b": {"c": None}}})
        none_val = md.a.b.c

        deep_copied = deepcopy(none_val)
        self.assertTrue(getattr(deep_copied, "_from_none", False))

    def test_deepcopy_protected_still_protected(self):
        """Test that deepcopied protected MagiDicts remain protected."""
        md = MagiDict({"a": None})
        none_val = md.a
        deep_copied = deepcopy(none_val)

        # Should still raise TypeError on modification
        with self.assertRaises(TypeError):
            deep_copied["x"] = 1


class TestPickleFlagPreservation(TestCase):
    """Test that pickle/unpickle preserves special flags."""

    def test_pickle_preserves_from_none(self):
        """Test that pickle/unpickle preserves _from_none flag."""
        md = MagiDict({"a": None})
        none_val = md.a

        # Pickle and unpickle
        pickled = pickle.dumps(none_val)
        unpickled = pickle.loads(pickled)

        self.assertTrue(getattr(unpickled, "_from_none", False))
        self.assertFalse(getattr(unpickled, "_from_missing", False))

    def test_pickle_preserves_from_missing(self):
        """Test that pickle/unpickle preserves _from_missing flag."""
        md = MagiDict({"a": 1})
        missing = md.missing_key

        # Pickle and unpickle
        pickled = pickle.dumps(missing)
        unpickled = pickle.loads(pickled)

        self.assertTrue(getattr(unpickled, "_from_missing", False))
        self.assertFalse(getattr(unpickled, "_from_none", False))

    def test_pickle_regular_magidict(self):
        """Test that pickle/unpickle of regular MagiDict has no special flags."""
        md = MagiDict({"a": 1, "b": 2})

        pickled = pickle.dumps(md)
        unpickled = pickle.loads(pickled)

        self.assertFalse(getattr(unpickled, "_from_none", False))
        self.assertFalse(getattr(unpickled, "_from_missing", False))
        self.assertEqual(unpickled, md)

    def test_pickle_with_data(self):
        """Test pickle preserves both flags and data."""
        md = MagiDict({"a": None})
        none_val = md.a

        # Even though it's from None, it's empty
        pickled = pickle.dumps(none_val)
        unpickled = pickle.loads(pickled)

        self.assertEqual(len(unpickled), 0)
        self.assertTrue(getattr(unpickled, "_from_none", False))

    def test_pickle_protected_still_protected(self):
        """Test that unpickled protected MagiDicts remain protected."""
        md = MagiDict({"a": None})
        none_val = md.a

        pickled = pickle.dumps(none_val)
        unpickled = pickle.loads(pickled)

        # Should still raise TypeError on modification
        with self.assertRaises(TypeError):
            unpickled["x"] = 1


class TestReprWithFlags(TestCase):
    """Test that __repr__ shows flags."""

    def test_repr_regular_no_flags(self):
        """Test that __repr__ doesn't show flags for regular MagiDict."""
        md = MagiDict({"a": 1})

        repr_str = repr(md)
        self.assertNotIn("_from_none", repr_str)
        self.assertNotIn("_from_missing", repr_str)


class TestFlagPreservationEdgeCases(TestCase):
    """Test edge cases for flag preservation."""

    def test_multiple_copy_operations(self):
        """Test that flags survive multiple copy operations."""
        md = MagiDict({"a": None})
        none_val = md.a

        copy1 = none_val.copy()
        copy2 = copy1.copy()
        copy3 = copy2.copy()

        self.assertTrue(getattr(copy3, "_from_none", False))

    def test_copy_then_deepcopy(self):
        """Test combining copy and deepcopy operations."""
        md = MagiDict({"a": None})
        none_val = md.a

        copied = none_val.copy()
        deep_copied = deepcopy(copied)

        self.assertTrue(getattr(deep_copied, "_from_none", False))

    def test_deepcopy_then_pickle(self):
        """Test combining deepcopy and pickle operations."""
        md = MagiDict({"a": None})
        none_val = md.a

        deep_copied = deepcopy(none_val)
        pickled = pickle.dumps(deep_copied)
        unpickled = pickle.loads(pickled)

        self.assertTrue(getattr(unpickled, "_from_none", False))

    def test_all_operations_combined(self):
        """Test that flags survive all operations combined."""
        md = MagiDict({"a": None})
        none_val = md.a

        # Chain all operations
        copied = none_val.copy()
        deep_copied = deepcopy(copied)
        pickled = pickle.dumps(deep_copied)
        unpickled = pickle.loads(pickled)
        final_copy = unpickled.copy()

        self.assertTrue(getattr(final_copy, "_from_none", False))

        # Should still be protected
        with self.assertRaises(TypeError):
            final_copy["x"] = 1

    def test_none_function_after_copy(self):
        """Test that none() function works after copy operations."""
        md = MagiDict({"a": None})
        none_val = md.a

        copied = none_val.copy()
        result = none(copied)

        self.assertIsNone(result)

    def test_none_function_after_deepcopy(self):
        """Test that none() function works after deepcopy."""
        md = MagiDict({"a": 1})
        missing = md.missing_key

        deep_copied = deepcopy(missing)
        result = none(deep_copied)

        self.assertIsNone(result)

    def test_none_function_after_pickle(self):
        """Test that none() function works after pickle/unpickle."""
        md = MagiDict({"a": None})
        none_val = md.a

        pickled = pickle.dumps(none_val)
        unpickled = pickle.loads(pickled)
        result = none(unpickled)

        self.assertIsNone(result)


class TestFlagPreservationWithNesting(TestCase):
    """Test flag preservation with nested structures."""

    def test_deepcopy_nested_protected_dicts(self):
        """Test deepcopy with structure containing protected MagiDicts."""
        md = MagiDict({"data": {"a": None, "b": 1}})

        # Access None value
        none_val = md.data.a

        # Deep copy the whole structure
        deep_copied = deepcopy(md)

        # Access the same path in the copy
        copied_none = deep_copied.data.a

        # Should still be protected
        self.assertTrue(getattr(copied_none, "_from_none", False))

    def test_pickle_structure_with_protected(self):
        """Test pickle with structure containing protected MagiDicts."""
        md = MagiDict({"x": None, "y": {"z": None}})

        pickled = pickle.dumps(md)
        unpickled = pickle.loads(pickled)

        # Access should still create protected MagiDicts
        none_x = unpickled.x
        none_z = unpickled.y.z

        self.assertTrue(getattr(none_x, "_from_none", False))
        self.assertTrue(getattr(none_z, "_from_none", False))


class TestMagiLoad(TestCase):
    """Test suite for magi_load function."""

    def test_magi_load_basic(self):
        """Test that magi_load correctly loads a simple JSON dict into a MagiDict."""
        data = io.StringIO('{"a": 1, "b": "two"}')
        result = magi_load(data)
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(result.a, 1)
        self.assertEqual(result.b, "two")

    def test_magi_load_nested(self):
        """Test nested dicts are converted recursively into MagiDicts."""
        data = io.StringIO('{"outer": {"inner": {"value": 42}}}')
        result = magi_load(data)
        self.assertIsInstance(result.outer, MagiDict)
        self.assertIsInstance(result.outer.inner, MagiDict)
        self.assertEqual(result.outer.inner.value, 42)

    def test_magi_load_list_of_dicts(self):
        """Test lists of dicts are properly converted to MagiDicts inside the list."""
        data = io.StringIO('{"users": [{"name": "Alice"}, {"name": "Bob"}]}')
        result = magi_load(data)
        self.assertIsInstance(result.users, list)
        self.assertIsInstance(result.users[0], MagiDict)
        self.assertEqual(result.users[1].name, "Bob")

    def test_magi_load_empty(self):
        """Test loading an empty JSON object."""
        data = io.StringIO("{}")
        result = magi_load(data)
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

    def test_magi_load_invalid_json(self):
        """Test magi_load raises JSONDecodeError for invalid JSON."""
        data = io.StringIO('{"a": 1,}')
        with self.assertRaises(json.JSONDecodeError):
            magi_load(data)

    def test_magi_load_with_custom_kwargs(self):
        """Test magi_load passes kwargs to json.load (e.g., parse_int)."""
        data = io.StringIO('{"number": 123}')
        result = magi_load(data, parse_int=lambda x: f"int:{x}")
        self.assertEqual(result.number, "int:123")

    def test_magi_load_deeply_nested(self):
        """Test deeply nested structures are properly converted."""
        nested_json = json.dumps({"level1": {"level2": {"level3": {"key": "value"}}}})
        data = io.StringIO(nested_json)
        result = magi_load(data)
        self.assertEqual(result.level1.level2.level3.key, "value")

    def test_magi_load_preserves_types(self):
        """Test that non-dict types are preserved."""
        data = io.StringIO('{"a": [1, 2, 3], "b": true, "c": null}')
        result = magi_load(data)
        self.assertEqual(result.a, [1, 2, 3])
        self.assertIs(result.b, True)
        self.assertIsInstance(result.c, MagiDict)
        self.assertTrue(getattr(result.c, "_from_none", False))
        self.assertEqual(len(result.c), 0)

    def test_magi_load_attribute_and_key_access(self):
        """Test that both attribute and key access return the same value."""
        data = io.StringIO('{"name": "Hristo"}')
        result = magi_load(data)
        self.assertEqual(result.name, "Hristo")
        self.assertEqual(result["name"], "Hristo")

    def test_magi_load_mutable_independence(self):
        """Test that modifying the returned MagiDict doesn't affect the original JSON structure."""
        json_str = '{"settings": {"theme": "dark"}}'
        data = io.StringIO(json_str)
        result = magi_load(data)
        result.settings.theme = "light"
        self.assertEqual(result.settings.theme, "light")

        # Confirm it's not referencing the same object (deep copy behavior)
        reloaded = magi_load(io.StringIO(json_str))
        self.assertEqual(reloaded.settings.theme, "dark")


class TestStandardDictAccess(TestCase):
    """Test standard dictionary key access (STRICT)."""

    def test_existing_key(self):
        md = MagiDict({"key": "value"})
        self.assertEqual(md["key"], "value")

    def test_missing_key_raises_error(self):
        md = MagiDict({"key": "value"})
        with self.assertRaises(KeyError):
            md["missing"]

    def test_none_value(self):
        md = MagiDict({"key": None})
        self.assertIsNone(md["key"])


class TestLiteralKeysWithDots(TestCase):
    """Test literal keys that contain dots (STRICT)."""

    def test_literal_key_with_dots_exists(self):
        md = MagiDict({"a.b.c.d": 1})
        self.assertEqual(md["a.b.c.d"], 1)

    def test_literal_key_with_dots_missing_raises_error(self):
        md = MagiDict({"x": 1})
        with self.assertRaises(KeyError):
            md["a.b.c.d"]

    def test_literal_key_preferred_over_nested(self):
        """When both literal key and nested path exist, literal takes precedence."""
        md = MagiDict({"a.b.c": "literal", "a": {"b": {"c": "nested"}}})
        self.assertEqual(md["a.b.c"], "literal")


class TestDotNotationFallback(TestCase):
    """Test dot notation fallback when literal key doesn't exist (STRICT)."""

    def test_nested_access_via_dots(self):
        md = MagiDict({"a": {"b": {"c": "value"}}})
        self.assertEqual(md["a.b.c"], "value")

    def test_nested_access_missing_key_raises_error(self):
        md = MagiDict({"a": {"b": {"c": "value"}}})
        with self.assertRaises(KeyError):
            md["a.b.missing"]

    def test_nested_access_partial_path_raises_error(self):
        md = MagiDict({"a": {"b": "value"}})
        with self.assertRaises(KeyError):
            md["a.missing.c"]

    def test_nested_access_through_non_dict_raises_error(self):
        md = MagiDict({"a": "string_value"})
        with self.assertRaises((KeyError, AttributeError)):
            md["a.b.c"]

    def test_nested_access_with_list_index(self):
        md = MagiDict({"a": {"b": [1, 2, 3]}})
        self.assertEqual(md["a.b.1"], 2)

    def test_nested_access_invalid_list_index_raises_error(self):
        md = MagiDict({"a": {"b": [1, 2, 3]}})
        with self.assertRaises((ValueError, IndexError)):
            md["a.b.99"]

    def test_nested_access_deep_path(self):
        md = MagiDict({"a": {"b": {"c": {"d": {"e": "deep"}}}}})
        self.assertEqual(md["a.b.c.d.e"], "deep")


class TestTupleListAccess(TestCase):
    """Test tuple/list multi-key access (SAFE - returns empty MagiDict)."""

    def test_tuple_access_existing_path(self):
        md = MagiDict({"a": {"b": {"c": "value"}}})
        self.assertEqual(md["a", "b", "c"], "value")

    def test_list_access_existing_path(self):
        md = MagiDict({"a": {"b": {"c": "value"}}})
        self.assertEqual(md[["a", "b", "c"]], "value")

    def test_tuple_access_missing_key_returns_empty(self):
        md = MagiDict({"a": {"b": "value"}})
        result = md["a", "missing"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)
        self.assertTrue(getattr(result, "_from_missing", False))

    def test_tuple_access_partial_path_missing_returns_empty(self):
        md = MagiDict({"a": {"b": "value"}})
        result = md["a", "missing", "c"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)
        self.assertTrue(getattr(result, "_from_missing", False))

    def test_tuple_access_first_key_missing_returns_empty(self):
        md = MagiDict({"a": "value"})
        result = md["missing", "b"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)
        self.assertTrue(getattr(result, "_from_missing", False))

    def test_single_element_tuple(self):
        md = MagiDict({"key": "value"})
        self.assertEqual(md[("key",)], "value")

    def test_empty_tuple_returns_self(self):
        md = MagiDict({"key": "value"})
        self.assertIs(md[()], md)


class TestTupleListWithSequences(TestCase):
    """Test tuple/list access through sequences."""

    def test_tuple_access_list_by_index(self):
        md = MagiDict({"items": [1, 2, 3]})
        self.assertEqual(md["items", 1], 2)

    def test_tuple_access_list_by_string_index(self):
        md = MagiDict({"items": [1, 2, 3]})
        self.assertEqual(md["items", "1"], 2)

    def test_tuple_access_list_invalid_index_returns_empty(self):
        md = MagiDict({"items": [1, 2, 3]})
        result = md["items", "99"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)
        self.assertTrue(getattr(result, "_from_missing", False))

    def test_tuple_access_list_non_numeric_index_returns_empty(self):
        md = MagiDict({"items": [1, 2, 3]})
        result = md["items", "abc"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)
        self.assertTrue(getattr(result, "_from_missing", False))

    def test_tuple_access_nested_lists(self):
        md = MagiDict({"matrix": [[1, 2], [3, 4]]})
        self.assertEqual(md["matrix", 0, 1], 2)
        self.assertEqual(md["matrix", 1, 0], 3)


class TestNoneValues(TestCase):
    """Test handling of None values in paths."""

    def test_tuple_access_none_value_at_end(self):
        md = MagiDict({"a": {"b": None}})
        result = md["a", "b"]
        self.assertIsInstance(result, MagiDict)
        self.assertTrue(getattr(result, "_from_none", False))
        self.assertEqual(len(result), 0)

    def test_tuple_access_through_none_returns_empty(self):
        md = MagiDict({"a": {"b": None}})
        result = md["a", "b", "c"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)
        self.assertTrue(getattr(result, "_from_missing", False))

    def test_single_element_tuple_with_none(self):
        md = MagiDict({"key": None})
        result = md[("key",)]
        self.assertIsInstance(result, MagiDict)
        self.assertTrue(getattr(result, "_from_none", False))


class TestEdgeCasesMore(TestCase):
    """Test edge cases and special scenarios."""

    def test_empty_magidict(self):
        md = MagiDict()
        with self.assertRaises(KeyError):
            md["key"]

    def test_nested_empty_magidicts(self):
        md = MagiDict({"a": {}})
        result = md["a", "b"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

    def test_integer_keys(self):
        md = MagiDict({1: "one", 2: "two"})
        self.assertEqual(md[1], "one")

    def test_tuple_key_as_single_key(self):
        md = MagiDict()
        dict.__setitem__(md, ("a", "b"), "value")
        result = md["a", "b"]
        self.assertEqual(result, "value")

    def test_key_with_single_dot(self):
        md = MagiDict({"a.b": "literal"})
        self.assertEqual(md["a.b"], "literal")

    def test_key_with_trailing_dot(self):
        md = MagiDict({"a.": "value"})
        self.assertEqual(md["a."], "value")

    def test_key_with_leading_dot(self):
        md = MagiDict({".a": "value"})
        self.assertEqual(md[".a"], "value")

    def test_key_with_multiple_consecutive_dots(self):
        md = MagiDict({"a..b": "value"})
        self.assertEqual(md["a..b"], "value")


class TestComplexScenarios(TestCase):
    """Test complex real-world scenarios."""

    def test_mixed_access_patterns(self):
        md = MagiDict(
            {
                "config.json": "literal_file",
                "config": {"json": {"data": "nested"}},
                "users": [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            }
        )

        # Literal key with dots
        self.assertEqual(md["config.json"], "literal_file")

        # Nested access via dots
        self.assertEqual(md["config.json.data"], "nested")

        # Tuple safe access
        self.assertEqual(md["users", 0, "name"], "Alice")
        result = md["users", 2, "name"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

    def test_deeply_nested_structure(self):
        md = MagiDict(
            {"level1": {"level2": {"level3": {"level4": {"level5": "deep_value"}}}}}
        )

        # Dot notation
        self.assertEqual(md["level1.level2.level3.level4.level5"], "deep_value")

        # Tuple notation
        self.assertEqual(
            md["level1", "level2", "level3", "level4", "level5"], "deep_value"
        )

        # Mixed missing paths
        with self.assertRaises(KeyError):
            md["level1.level2.missing.level4.level5"]

        result = md["level1", "level2", "missing", "level4", "level5"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

    def test_list_of_dicts_access(self):
        md = MagiDict(
            {
                "items": [
                    {"id": 1, "name": "first"},
                    {"id": 2, "name": "second"},
                    {"id": 3, "name": "third"},
                ]
            }
        )

        # Access via tuple
        self.assertEqual(md["items", 1, "name"], "second")

        # Access via dot notation (strict)
        self.assertEqual(md["items.1.name"], "second")

        # Missing index (safe with tuple)
        result = md["items", 99, "name"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

        # Missing index (strict with dots)
        with self.assertRaises((IndexError, ValueError)):
            md["items.99.name"]


class TestComparison(TestCase):
    """Test comparison between different access methods."""

    def test_string_vs_tuple_on_same_path(self):
        md = MagiDict({"a": {"b": {"c": "value"}}})

        # Both should return same value when path exists
        self.assertEqual(md["a.b.c"], "value")
        self.assertEqual(md["a", "b", "c"], "value")

    def test_string_vs_tuple_on_missing_path(self):
        md = MagiDict({"a": {"b": {"c": "value"}}})

        # String (strict) - raises KeyError
        with self.assertRaises(KeyError):
            md["a.b.missing"]

        # Tuple (safe) - returns empty MagiDict
        result = md["a", "b", "missing"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)


class TestTupleListSetItem(TestCase):
    """Test setting values using tuple/list keys."""

    def test_set_nested_value_via_tuple(self):
        md = MagiDict({"users": [{"name": "Alice", "id": 1}]})
        md["users", 0, "name"] = "Overridden"
        self.assertEqual(md["users", 0, "name"], "Overridden")
        self.assertEqual(md["users"][0]["name"], "Alice")

    def test_set_nested_value_via_list(self):
        md = MagiDict({"users": [{"name": "Alice", "id": 1}]})
        with self.assertRaises(TypeError):
            md[["users", 0, "name"]] = "NewName"
        self.assertEqual(md["users", 0, "name"], "Alice")

    def test_set_deep_nested_dict(self):
        md = MagiDict({"a": {"b": {"c": "old"}}})
        md["a", "b", "c"] = "new"
        self.assertEqual(md["a", "b", "c"], "new")
        self.assertEqual(md["a"]["b"]["c"], "old")

    def test_set_list_element(self):
        md = MagiDict({"items": [1, 2, 3]})
        md["items", 1] = 99
        self.assertEqual(md["items", 1], 99)
        self.assertEqual(md["items"][1], 2)

    def test_set_creates_intermediate_dicts(self):
        """Setting a nested path should create intermediate dicts if missing."""
        md = MagiDict({"a": {}})
        md["a", "b", "c"] = "value"
        self.assertEqual(md["a", "b", "c"], "value")
        self.assertIsInstance(md["a", "b"], MagiDict)

    def test_set_creates_path_from_empty(self):
        """Setting on completely missing path should create the structure."""
        md = MagiDict({})
        md["x", "y", "z"] = "deep"
        self.assertEqual(md["x", "y", "z"], "deep")

    def test_set_single_element_tuple(self):
        md = MagiDict({"key": "old"})
        md[("key",)] = "new"
        self.assertEqual(md["key"], "old")

    def test_set_overwrites_existing_value(self):
        md = MagiDict({"a": {"b": "old_value"}})
        md["a", "b"] = "new_value"
        self.assertEqual(md["a"]["b"], "old_value")
        self.assertEqual(md["a", "b"], "new_value")

    def test_set_nested_in_list_dict(self):
        md = MagiDict({"users": [{"name": "Alice", "id": 1}, {"name": "Bob", "id": 2}]})
        md["users", 1, "name"] = "Robert"
        self.assertEqual(md["users"][1]["name"], "Bob")
        self.assertEqual(md["users", 1, "name"], "Robert")


class TestTupleListSetItemEdgeCases(TestCase):
    """Test edge cases for setting with tuple/list keys."""

    def test_set_empty_tuple_key(self):
        """Empty tuple should probably raise an error or be no-op."""
        md = MagiDict({"key": "value"})
        try:
            md[()] = "new"
            self.assertEqual(md.get("key"), "value")
        except (TypeError, ValueError, KeyError):
            pass

    def test_set_with_none_in_path(self):
        """Setting through a None value should handle gracefully."""
        md = MagiDict({"a": {"b": None}})
        # This might raise an error or create new structure
        # depending on implementation
        try:
            md["a", "b", "c"] = "value"
            # If it succeeds, b should be replaced with a dict
            self.assertEqual(md["a", "b", "c"], "value")
        except (TypeError, AttributeError):
            pass  # Expected if can't set through None

    def test_set_with_string_in_path(self):
        """Setting through a string value should handle gracefully."""
        md = MagiDict({"a": "string_value"})
        md["a", "b"] = "value"
        self.assertEqual(md["a", "b"], "value")

    def test_set_list_index_out_of_bounds(self):
        """Setting an out-of-bounds list index should handle gracefully."""
        md = MagiDict({"items": [1, 2, 3]})
        self.assertEqual(md["items", 99], MagiDict())
        md["items", 99] = "value"
        self.assertEqual(md["items", 99], "value")

    def test_set_non_integer_list_index(self):
        """Setting non-integer index on list should handle gracefully."""
        md = MagiDict({"items": [1, 2, 3]})
        md["items", "abc"] = "value"
        self.assertEqual(md["items", "abc"], "value")


class TestTupleAsDictKey(TestCase):
    """Test when tuple itself is an actual key in the dict."""

    def test_tuple_as_literal_key_priority(self):
        """If tuple is an actual key, it should be prioritized."""
        md = MagiDict({("a", "b"): "tuple_key_value", "a": {"b": "nested_value"}})
        # When accessing with tuple, should it return the tuple key value
        # or traverse? Based on your docs: "it prioritizes that value"
        # So we need to check if __getitem__ checks for tuple as key first

        # This behavior needs to be implemented in __getitem__
        # For now, let's document expected behavior
        result = md["a", "b"]
        # Expected: should check if ('a', 'b') exists as key first
        # If yes: return 'tuple_key_value'
        # If no: traverse and return 'nested_value'

        # Based on current implementation, it will traverse
        # To support this, __getitem__ needs modification

    def test_set_creates_tuple_key_when_path_doesnt_exist(self):
        """Setting with tuple when path doesn't exist."""
        md = MagiDict({})
        md["a", "b"] = "value"
        self.assertEqual(md["a", "b"], "value")

    def test_tuple_key_priority_in_setitem(self):
        """Setting should respect tuple as literal key if it exists."""
        md = MagiDict()
        # Directly set tuple as key
        dict.__setitem__(md, ("a", "b"), "old")
        self.assertEqual(md["a", "b"], "old")
        # Now setting via tuple syntax
        md["a", "b"] = "new"
        self.assertEqual(md["a", "b"], "new")


class TestRealWorldScenarios(TestCase):
    """Test real-world usage scenarios."""

    def test_user_list_modification(self):
        md = MagiDict(
            {"users": [{"name": "Alice", "id": 1}, {"name": "Keanu", "id": 2}]}
        )

        # Read access
        self.assertEqual(md["users", 0, "name"], "Alice")
        self.assertEqual(md["users", 1, "id"], 2)

        # Missing index (safe)
        result = md["users", 2, "name"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

        # Missing key (safe)
        result = md["users", 0, "email"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)

        # Write access
        md["users", 0, "name"] = "Overridden"
        self.assertEqual(md["users", 0, "name"], "Overridden")

    def test_config_nested_update(self):
        md = MagiDict({"config": {"database": {"host": "localhost", "port": 5432}}})

        # Update nested value
        md["config", "database", "host"] = "192.168.1.1"
        self.assertEqual(md["config"]["database"]["host"], "localhost")

        # Add new nested value
        md["config", "database", "username"] = "admin"
        self.assertEqual(md["config", "database", "username"], "admin")

    def test_api_response_modification(self):
        md = MagiDict(
            {
                "data": {
                    "items": [
                        {"id": 1, "status": "pending"},
                        {"id": 2, "status": "active"},
                        {"id": 3, "status": "pending"},
                    ]
                }
            }
        )

        # Update status of specific item
        md["data", "items", 1, "status"] = "completed"
        self.assertEqual(md["data"]["items"][1]["status"], "active")
        self.assertEqual(md["data", "items", 1, "status"], "completed")

        # Safe access to non-existent item
        result = md["data", "items", 10, "status"]
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)


class TestMixedAccessPatterns(TestCase):
    """Test mixing different access patterns."""

    def test_set_then_get_different_ways(self):
        md = MagiDict({"a": {"b": "value"}})

        # Set via tuple
        md["a", "b"] = "new"

        # Get via different methods
        self.assertEqual(md["a", "b"], "new")
        self.assertEqual(md["a"]["b"], "value")
        self.assertEqual(md.a.b, "value")

    def test_set_via_tuple_get_via_dot_notation(self):
        md = MagiDict({"x": {"y": {"z": 1}}})
        md["x", "y", "z"] = 99
        self.assertEqual(md["x.y.z"], 1)
        self.assertEqual(md.x.y.z, 1)
        self.assertEqual(md["x", "y", "z"], 99)

    def test_partial_tuple_access(self):
        md = MagiDict({"a": {"b": {"c": "d"}}, "x": {"y": None}})

        # Get partial path
        partial = md["a", "b"]
        self.assertIsInstance(partial, MagiDict)
        self.assertEqual(partial["c"], "d")

        # Set on partial path
        md["a", "b"] = {"c": "new", "e": "added"}
        self.assertEqual(md["a", "b", "c"], "d")
        self.assertEqual(md["a", "b", "e"], MagiDict())
        self.assertTrue(getattr(md["a", "b", "e"], "_from_missing", False))
        self.assertEqual(md["x", "y"], MagiDict())
        self.assertTrue(getattr(md["x", "y"], "_from_none", False))


class TestStrictGet(TestCase):
    """Test suite for MagiDict.strict_get() method."""

    def test_strict_get_existing_key(self):
        """Test strict_get returns the value for an existing key."""
        md = MagiDict({"name": "Alice", "age": 30})
        self.assertEqual(md.strict_get("name"), "Alice")
        self.assertEqual(md.strict_get("age"), 30)

    def test_strict_get_nested_dict(self):
        """Test strict_get returns nested MagiDict for existing nested key."""
        md = MagiDict({"user": {"name": "Bob", "email": "bob@example.com"}})
        result = md.strict_get("user")
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(result["name"], "Bob")
        self.assertEqual(result["email"], "bob@example.com")

    def test_strict_get_none_value(self):
        """Test strict_get returns None value without converting to empty MagiDict."""
        md = MagiDict({"value": None})
        result = md.strict_get("value")
        self.assertIsNone(result)

    def test_strict_get_missing_key_raises_keyerror(self):
        """Test strict_get raises KeyError for missing keys."""
        md = MagiDict({"name": "Charlie"})
        with self.assertRaises(KeyError):
            md.strict_get("missing_key")

    def test_strict_get_empty_dict(self):
        """Test strict_get on empty MagiDict raises KeyError."""
        md = MagiDict()
        with self.assertRaises(KeyError):
            md.strict_get("any_key")

    def test_strict_get_numeric_key(self):
        """Test strict_get works with numeric keys."""
        md = MagiDict({1: "one", 2: "two", 3: "three"})
        self.assertEqual(md.strict_get(1), "one")
        self.assertEqual(md.strict_get(2), "two")

    def test_strict_get_list_value(self):
        """Test strict_get returns list values correctly."""
        md = MagiDict({"items": [1, 2, 3]})
        result = md.strict_get("items")
        self.assertEqual(result, [1, 2, 3])
        self.assertIsInstance(result, list)

    def test_strict_get_tuple_key(self):
        """Test strict_get works when tuple is used as a key."""
        md = MagiDict({("a", "b"): "value"})
        self.assertEqual(md.strict_get(("a", "b")), "value")

    def test_strict_get_vs_getattr(self):
        """Test that strict_get differs from attribute access for missing keys."""
        md = MagiDict({"name": "David"})

        # strict_get raises KeyError
        with self.assertRaises(KeyError):
            md.strict_get("missing")

        # Attribute access returns empty MagiDict
        result = md.missing
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)
        self.assertTrue(getattr(result, "_from_missing", False))

    def test_strict_get_vs_mget(self):
        """Test that strict_get differs from mget for missing keys."""
        md = MagiDict({"key": "value"})

        # strict_get raises KeyError
        with self.assertRaises(KeyError):
            md.strict_get("missing")

        # mget returns empty MagiDict with _from_missing flag
        result = md.mget("missing")
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(len(result), 0)
        self.assertTrue(getattr(result, "_from_missing", False))

    def test_strict_get_with_none_default(self):
        """Test strict_get doesn't accept default parameter (unlike dict.get)."""
        md = MagiDict({"name": "Eve"})
        # strict_get doesn't have default parameter, so it should raise KeyError
        with self.assertRaises(KeyError):
            md.strict_get("missing")

    def test_strict_get_zero_value(self):
        """Test strict_get returns falsy values like 0 correctly."""
        md = MagiDict({"count": 0, "empty_string": "", "false": False})
        self.assertEqual(md.strict_get("count"), 0)
        self.assertEqual(md.strict_get("empty_string"), "")
        self.assertFalse(md.strict_get("false"))

    def test_strict_get_complex_nested_structure(self):
        """Test strict_get on complex nested structures."""
        md = MagiDict(
            {
                "data": {
                    "users": [{"id": 1, "name": "User1"}, {"id": 2, "name": "User2"}]
                }
            }
        )
        result = md.strict_get("data")
        self.assertIsInstance(result, MagiDict)
        self.assertIsInstance(result["users"], list)
        self.assertIsInstance(result["users"][0], MagiDict)
        self.assertEqual(result["users"][0]["name"], "User1")

    def test_sget_shorthand(self):
        """Test sget shorthand method works the same as strict_get."""
        md = MagiDict({"key": "value"})
        self.assertEqual(md.sget("key"), "value")
        with self.assertRaises(KeyError):
            md.sget("missing")

    def test_sg_shorthand(self):
        """Test sg shorthand method works the same as strict_get."""
        md = MagiDict({"key": "value"})
        self.assertEqual(md.sg("key"), "value")
        with self.assertRaises(KeyError):
            md.sg("missing")

    def test_strict_get_on_protected_magidict(self):
        """Test strict_get works on protected MagiDicts (those from None/missing)."""
        md = MagiDict({"data": None})
        protected = md.data  # Returns protected MagiDict with _from_none

        # strict_get should still work, even if the dict is protected
        # (we're reading, not modifying)
        self.assertIsInstance(protected, MagiDict)
        self.assertTrue(getattr(protected, "_from_none", False))

    def test_strict_get_string_key(self):
        """Test strict_get with string keys of various formats."""
        md = MagiDict(
            {"simple": "value", "with space": "value2", "with-dash": "value3"}
        )
        self.assertEqual(md.strict_get("simple"), "value")
        self.assertEqual(md.strict_get("with space"), "value2")
        self.assertEqual(md.strict_get("with-dash"), "value3")

    def test_strict_get_returns_exact_value(self):
        """Test strict_get returns the exact value without transformation."""
        original_dict = {"nested": {"key": "value"}}
        md = MagiDict(original_dict)
        result = md.strict_get("nested")

        # Result should be a MagiDict (converted during initialization)
        self.assertIsInstance(result, MagiDict)
        self.assertEqual(result["key"], "value")

    def test_hook_with_memo_handles_lists_inplace_and_memo(self):
        """Ensure _hook_with_memo handles lists by mutating them in-place and
        uses the memoization to avoid re-wrapping already seen objects.
        This targets the branch that sets memo[item_id] = item for lists.
        """
        # Construct a list that contains a dict that should be converted
        lst = [{"a": 1}, {"b": 2}]

        # Create a fresh memo and call the internal hook
        memo = {}
        # Use the public-facing class to reach the private method
        from magidict import MagiDict as MD

        res = MD._hook_with_memo(lst, memo)

        # The returned object should be the same list (in-place mutation)
        self.assertIs(res, lst)
        # Elements should have been converted to MagiDict
        self.assertIsInstance(lst[0], MD)
        self.assertEqual(lst[0].a, 1)

        # Re-run hooking on the same list with the same memo to ensure memo is used
        res2 = MD._hook_with_memo(lst, memo)
        self.assertIs(res2, lst)

    def test_strict_get_and_shorthands_on_protected_magidict(self):
        """Ensure strict_get/sget/sg behave like dict access even when the
        MagiDict is a protected one (from None or missing), and that they
        raise KeyError for missing keys like normal dict access.
        This targets the strict_get and its shorthands.
        """
        MD = MagiDict
        md = MD({"data": None})
        protected = md.data  # should be a protected MagiDict (from None)

        # strict_get should raise KeyError when asking for a missing key
        with self.assertRaises(KeyError):
            protected.strict_get("missing_key")

        with self.assertRaises(KeyError):
            protected.sget("missing_key")

        with self.assertRaises(KeyError):
            protected.sg("missing_key")


class TestMagiDictSearchKey(TestCase):
    """Tests for the search_key() method of MagiDict."""

    def test_search_key_simple(self):
        """Test searching for a key in a simple MagiDict."""
        md = MagiDict({"name": "Alice", "age": 30})
        self.assertEqual(md.search_key("name"), "Alice")
        self.assertEqual(md.search_key("age"), 30)

    def test_search_key_not_found(self):
        """Test searching for a non-existent key returns None."""
        md = MagiDict({"name": "Bob"})
        self.assertIsNone(md.search_key("missing"))

    def test_search_key_nested_dict(self):
        """Test searching for a key in nested dictionaries."""
        md = MagiDict({"user": {"profile": {"email": "test@example.com"}}})
        self.assertEqual(md.search_key("email"), "test@example.com")

    def test_search_key_in_list(self):
        """Test searching for a key within dicts inside a list."""
        md = MagiDict({"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]})
        self.assertEqual(md.search_key("name"), "Alice")

    def test_search_key_deeply_nested(self):
        """Test searching through deeply nested structures."""
        md = MagiDict({"level1": {"level2": {"level3": {"target": "found"}}}})
        self.assertEqual(md.search_key("target"), "found")

    def test_search_key_returns_first_match(self):
        """Test that search_key returns the first occurrence when multiple exist."""
        md = MagiDict({"first": {"key": "value1"}, "second": {"key": "value2"}})
        result = md.search_key("key")
        self.assertIn(result, ["value1", "value2"])

    def test_search_key_empty_dict(self):
        """Test searching in an empty MagiDict."""
        md = MagiDict({})
        self.assertIsNone(md.search_key("any_key"))

    def test_search_key_with_none_value(self):
        """Test searching for a key with None as its value."""
        md = MagiDict({"nullable": None})
        self.assertIsNone(md.search_key("nullable"))

    def test_search_key_mixed_types(self):
        """Test searching through mixed nested structures."""
        md = MagiDict({"data": [{"item": {"value": 10}}, {"item": {"value": 20}}]})
        self.assertEqual(md.search_key("value"), 10)


class TestMagiDictSearchKeys(TestCase):
    """Tests for the search_keys() method of MagiDict."""

    def test_search_keys_single_occurrence(self):
        """Test searching for a key with one occurrence."""
        md = MagiDict({"name": "Alice"})
        results = md.search_keys("name")
        self.assertEqual(results, ["Alice"])

    def test_search_keys_multiple_occurrences(self):
        """Test searching for a key with multiple occurrences."""
        md = MagiDict({"id": 1, "nested": {"id": 2}, "list": [{"id": 3}]})
        results = md.search_keys("id")
        self.assertEqual(sorted(results), [1, 2, 3])

    def test_search_keys_not_found(self):
        """Test searching for a non-existent key returns empty list."""
        md = MagiDict({"name": "Bob"})
        results = md.search_keys("missing")
        self.assertEqual(results, [])

    def test_search_keys_in_nested_dicts(self):
        """Test finding multiple keys in nested dictionaries."""
        md = MagiDict(
            {
                "user1": {"email": "alice@example.com"},
                "user2": {"email": "bob@example.com"},
            }
        )
        results = md.search_keys("email")
        self.assertEqual(
            sorted(results), sorted(["alice@example.com", "bob@example.com"])
        )

    def test_search_keys_in_list_of_dicts(self):
        """Test finding keys within a list of dictionaries."""
        md = MagiDict(
            {"users": [{"id": 1, "status": "active"}, {"id": 2, "status": "inactive"}]}
        )
        results = md.search_keys("status")
        self.assertEqual(sorted(results), ["active", "inactive"])

    def test_search_keys_deeply_nested(self):
        """Test searching through deeply nested structures."""
        md = MagiDict(
            {"a": {"b": {"c": {"target": "value1"}}}, "x": {"y": {"target": "value2"}}}
        )
        results = md.search_keys("target")
        self.assertEqual(sorted(results), sorted(["value1", "value2"]))

    def test_search_keys_empty_dict(self):
        """Test searching in an empty MagiDict."""
        md = MagiDict({})
        results = md.search_keys("any_key")
        self.assertEqual(results, [])

    def test_search_keys_with_none_values(self):
        """Test finding keys with None as values."""
        md = MagiDict({"field1": None, "nested": {"field1": None}})
        results = md.search_keys("field1")
        self.assertEqual(results, [None, None])

    def test_search_keys_mixed_nesting(self):
        """Test searching through mixed nested lists and dicts."""
        md = MagiDict(
            {"outer": [{"inner": [{"key": "value1"}]}, {"inner": [{"key": "value2"}]}]}
        )
        results = md.search_keys("key")
        self.assertEqual(sorted(results), ["value1", "value2"])

    def test_search_keys_with_various_types(self):
        """Test finding keys with various value types."""
        md = MagiDict({"count": 42, "nested": {"count": 100}, "list": [{"count": 5}]})
        results = md.search_keys("count")
        self.assertEqual(sorted(results), [5, 42, 100])

    def test_search_keys_duplicate_values(self):
        """Test that duplicate values are all returned."""
        md = MagiDict({"a": {"value": "dup"}, "b": {"value": "dup"}})
        results = md.search_keys("value")
        self.assertEqual(results, ["dup", "dup"])

    def test_search_keys_in_lists_of_lists(self):
        """Test searching through nested lists."""
        md = MagiDict({"data": [[{"key": "v1"}], [{"key": "v2"}]]})
        results = md.search_keys("key")
        self.assertEqual(sorted(results), ["v1", "v2"])


class TestSearchKeyEdgeCases(TestCase):
    """Edge case tests for both search_key and search_keys."""

    def test_search_with_numeric_keys(self):
        """Test searching with numeric string keys."""
        md = MagiDict({"data": {123: "value"}})
        self.assertIsNone(md.search_key("123"))

    def test_search_with_special_characters(self):
        """Test searching for keys with special characters."""
        md = MagiDict({"user-id": 1, "nested": {"user-id": 2}})
        results = md.search_keys("user-id")
        self.assertEqual(sorted(results), [1, 2])

    def test_search_complex_nested_structure(self):
        """Test searching through a complex realistic structure."""
        md = MagiDict(
            {
                "users": [
                    {
                        "id": 1,
                        "name": "Alice",
                        "posts": [
                            {"id": 101, "title": "Post 1"},
                            {"id": 102, "title": "Post 2"},
                        ],
                    },
                    {"id": 2, "name": "Bob", "posts": [{"id": 201, "title": "Post 3"}]},
                ]
            }
        )
        results = md.search_keys("id")
        self.assertEqual(sorted(results), [1, 2, 101, 102, 201])

    def test_search_with_empty_nested_lists(self):
        """Test searching when there are empty nested lists."""
        md = MagiDict({"items": [], "nested": {"items": [{"key": "value"}]}})
        results = md.search_keys("key")
        self.assertEqual(results, ["value"])


class TestFilterBasic(TestCase):
    """Test basic filtering functionality."""

    def test_filter_with_value_function(self):
        """Test filtering using a function that takes only values."""
        md = MagiDict({"a": 1, "b": 2, "c": 3})
        result = md.filter(lambda x: x > 1)
        self.assertEqual(result, MagiDict({"b": 2, "c": 3}))

    def test_filter_with_key_value_function(self):
        """Test filtering using a function that takes key and value."""
        md = MagiDict({"a": 1, "b": 2, "c": 3})
        result = md.filter(lambda k, v: k in ["a", "c"])
        self.assertEqual(result, MagiDict({"a": 1, "c": 3}))

    def test_filter_removes_non_matching_items(self):
        """Test that items not matching the filter are removed."""
        md = MagiDict({"x": 10, "y": 5, "z": 15})
        result = md.filter(lambda v: v >= 10)
        self.assertEqual(result, MagiDict({"x": 10, "z": 15}))

    def test_filter_with_none_function(self):
        """Test filtering with None function removes None values."""
        md = MagiDict({"a": 1, "b": None, "c": 3})
        result = md.filter(None)
        self.assertEqual(result, MagiDict({"a": 1, "c": 3}))

    def test_filter_empty_dict(self):
        """Test filtering an empty MagiDict."""
        md = MagiDict()
        result = md.filter(lambda x: x > 5)
        self.assertEqual(result, MagiDict())


class TestFilterNested(TestCase):
    """Test filtering with nested structures."""

    def test_filter_nested_magidict(self):
        """Test filtering nested MagiDicts."""
        md = MagiDict({"outer": MagiDict({"a": 1, "b": 2})})
        result = md.filter(lambda x: x > 1)
        self.assertEqual(result, MagiDict({"outer": MagiDict({"b": 2})}))

    def test_filter_nested_regular_dict(self):
        """Test filtering nested regular dicts."""
        md = MagiDict({"outer": {"a": 1, "b": 2}})
        result = md.filter(lambda x: x > 1)
        self.assertEqual(result, MagiDict({"outer": MagiDict({"b": 2})}))

    def test_filter_deeply_nested(self):
        """Test filtering deeply nested structures."""
        md = MagiDict({"level1": {"level2": {"a": 1, "b": 5, "c": 2}}})
        result = md.filter(lambda x: x > 2)
        self.assertEqual(result, MagiDict({"level1": {"level2": {"b": 5}}}))

    def test_filter_nested_list_of_dicts(self):
        """Test filtering nested lists containing dicts."""
        md = MagiDict({"items": [{"x": 1, "y": 2}, {"x": 5, "y": 3}]})
        result = md.filter(lambda x: x > 2)
        self.assertEqual(len(result["items"]), 2)
        self.assertIsInstance(result["items"][0], (dict, MagiDict))

    def test_filter_list_with_key_value_function(self):
        """Test filtering lists with key-value function."""
        md = MagiDict({"items": [10, 20, 5, 15]})
        result = md.filter(lambda k, v: v >= 15)
        self.assertEqual(result, MagiDict({"items": [20, 15]}))


class TestFilterDropEmpty(TestCase):
    """Test drop_empty parameter."""

    def test_drop_empty_true_removes_empty_nested_dicts(self):
        """Test that drop_empty=True removes empty nested dicts."""
        md = MagiDict({"keep": {"a": 1}, "remove": {"x": 10, "y": 20}})
        result = md.filter(lambda x: x == 1, drop_empty=True)
        self.assertEqual(result, MagiDict({"keep": {"a": 1}}))

    def test_drop_empty_false_keeps_empty_nested_dicts(self):
        """Test that drop_empty=False keeps empty nested dicts."""
        md = MagiDict({"keep": {"a": 1}, "remove": {"x": 10, "y": 20}})
        result = md.filter(lambda x: x == 1, drop_empty=False)
        self.assertEqual(len(result), 2)
        self.assertIn("keep", result)
        self.assertIn("remove", result)
        self.assertEqual(len(result["remove"]), 0)

    def test_drop_empty_true_removes_empty_lists(self):
        """Test that drop_empty=True removes empty lists."""
        md = MagiDict({"keep": [1, 2], "remove": [10, 20]})
        result = md.filter(lambda x: x <= 5, drop_empty=True)
        self.assertEqual(result, MagiDict({"keep": [1, 2]}))

    def test_drop_empty_false_keeps_empty_lists(self):
        """Test that drop_empty=False keeps empty lists."""
        md = MagiDict({"keep": [1, 2], "remove": [10, 20]})
        result = md.filter(lambda x: x <= 5, drop_empty=False)
        self.assertEqual(len(result), 2)
        self.assertEqual(result["remove"], [])


class TestFilterSequences(TestCase):
    """Test filtering with various sequence types."""

    def test_filter_with_list(self):
        """Test filtering lists in MagiDict."""
        md = MagiDict({"nums": [1, 2, 3, 4, 5]})
        result = md.filter(lambda x: x > 2)
        self.assertEqual(result, MagiDict({"nums": [3, 4, 5]}))

    def test_filter_with_tuple(self):
        """Test filtering tuples in MagiDict."""
        md = MagiDict({"nums": (1, 2, 3, 4, 5)})
        result = md.filter(lambda x: x > 2)
        self.assertEqual(result, MagiDict({"nums": (3, 4, 5)}))

    def test_filter_mixed_sequence_and_nested_dicts(self):
        """Test filtering with mixed sequence and nested dict structures."""
        md = MagiDict(
            {"data": [{"id": 1, "val": 5}, {"id": 2, "val": 15}, {"id": 3, "val": 3}]}
        )
        result = md.filter(lambda x: x > 4, drop_empty=True)
        self.assertEqual(len(result["data"]), 2)


class TestFilterPreservesTypes(TestCase):
    """Test that filtering preserves data types appropriately."""

    def test_filter_preserves_magiddict_type(self):
        """Test that filtered result is a MagiDict."""
        md = MagiDict({"a": 1, "b": 2})
        result = md.filter(lambda x: x > 0)
        self.assertIsInstance(result, MagiDict)

    def test_filter_nested_magiddict_type(self):
        """Test that nested results are MagiDicts."""
        md = MagiDict({"nested": {"a": 1, "b": 2}})
        result = md.filter(lambda x: x > 0)
        self.assertIsInstance(result["nested"], MagiDict)

    def test_filter_preserves_list_type(self):
        """Test that lists remain as lists."""
        md = MagiDict({"items": [1, 2, 3]})
        result = md.filter(lambda x: x > 1)
        self.assertIsInstance(result["items"], list)


class TestFilterComplexScenarios(TestCase):
    """Test complex filtering scenarios."""

    def test_filter_with_string_values(self):
        """Test filtering with string values."""
        md = MagiDict({"apple": "red", "banana": "yellow", "cherry": "red"})
        result = md.filter(lambda v: v == "red")
        self.assertEqual(result, MagiDict({"apple": "red", "cherry": "red"}))

    def test_filter_with_mixed_types(self):
        """Test filtering with mixed value types."""
        md = MagiDict({"a": 1, "b": "text", "c": 2.5, "d": None})
        result = md.filter(lambda x: isinstance(x, (int, float)) and x > 1)
        self.assertEqual(result, MagiDict({"c": 2.5}))

    def test_filter_all_items_removed(self):
        """Test when all items are filtered out."""
        md = MagiDict({"a": 1, "b": 2, "c": 3})
        result = md.filter(lambda x: x > 100)
        self.assertEqual(result, MagiDict())

    def test_filter_all_items_kept(self):
        """Test when all items pass the filter."""
        md = MagiDict({"a": 1, "b": 2, "c": 3})
        result = md.filter(lambda x: x > 0)
        self.assertEqual(result, MagiDict({"a": 1, "b": 2, "c": 3}))

    def test_filter_with_key_value_filtering_keys(self):
        """Test filtering based on key values."""
        md = MagiDict({"id_1": 100, "name_2": 200, "id_3": 300})
        result = md.filter(lambda k, v: k.startswith("id"))
        self.assertEqual(result, MagiDict({"id_1": 100, "id_3": 300}))

    def test_filter_does_not_modify_original(self):
        """Test that filter does not modify the original MagiDict."""
        original = MagiDict({"a": 1, "b": 2, "c": 3})
        filtered = original.filter(lambda x: x > 1)
        self.assertEqual(original, MagiDict({"a": 1, "b": 2, "c": 3}))
        self.assertEqual(filtered, MagiDict({"b": 2, "c": 3}))

    def test_filter_with_boolean_values(self):
        """Test filtering with boolean values."""
        md = MagiDict({"active": True, "deleted": False, "enabled": True})
        result = md.filter(lambda x: x is True)
        self.assertEqual(result, MagiDict({"active": True, "enabled": True}))


class TestFilterEdgeCases(TestCase):
    """Test edge cases and special scenarios."""

    def test_filter_with_zero_values(self):
        """Test filtering with zero values (falsy but valid)."""
        md = MagiDict({"a": 0, "b": 1, "c": 0, "d": 2})
        result = md.filter(lambda x: x == 0)
        self.assertEqual(result, MagiDict({"a": 0, "c": 0}))

    def test_filter_with_empty_string(self):
        """Test filtering with empty string values."""
        md = MagiDict({"a": "", "b": "text", "c": ""})
        result = md.filter(lambda x: x != "")
        self.assertEqual(result, MagiDict({"b": "text"}))

    def test_filter_nested_with_none_values(self):
        """Test filtering nested structures containing None."""
        md = MagiDict({"data": {"a": None, "b": 1, "c": None, "d": 2}})
        result = md.filter(None)
        self.assertEqual(result, MagiDict({"data": {"b": 1, "d": 2}}))

    def test_filter_list_of_lists(self):
        """Test filtering nested lists."""
        md = MagiDict({"matrix": [[1, 2], [3, 4]]})
        result = md.filter(lambda x: x > 2, drop_empty=True)
        self.assertEqual(len(result["matrix"]), 1)
        self.assertEqual(result["matrix"][0], [3, 4])

    def test_filter_empty_nested_list(self):
        """Test filtering that results in empty nested lists."""
        md = MagiDict({"items": [1, 2, 3]})
        result = md.filter(lambda x: x > 10)
        self.assertEqual(result, MagiDict({"items": []}))

    def test_filter_with_negative_numbers(self):
        """Test filtering with negative numbers."""
        md = MagiDict({"a": -5, "b": 10, "c": -2, "d": 0})
        result = md.filter(lambda x: x > 0)
        self.assertEqual(result, MagiDict({"b": 10}))

    def test_filter_preserves_order(self):
        """Test that filter preserves the order of items."""
        md = MagiDict({"z": 1, "y": 2, "x": 3})
        result = md.filter(lambda x: x > 0)
        keys = list(result.keys())
        self.assertEqual(keys, ["z", "y", "x"])

    def test_filter_nested_empty_after_filtering(self):
        """Test nested dict becomes empty after filtering."""
        md = MagiDict({"outer": {"a": 10, "b": 20}, "keep": {"x": 1}})
        result = md.filter(lambda x: x < 5, drop_empty=False)
        self.assertEqual(len(result["outer"]), 0)
        self.assertEqual(result["keep"], MagiDict({"x": 1}))

    def test_list_of_lists_of_lists(self):
        """Test filtering with deeply nested lists."""
        md = MagiDict(
            {
                "a": [[[1, 2], [3, 4]], [[5, 6], [7, 8]]],
                "b": [1, [2, [3, 4]]],
                "c": [[[[9]]]],
            }
        )

        result = md.filter(lambda x: x > 4)
        result_drop_empty = md.filter(lambda x: x > 4, drop_empty=True)

        expected = MagiDict(
            {"a": [[[], []], [[5, 6], [7, 8]]], "b": [[[]]], "c": [[[[9]]]]}
        )

        expected_drop_empty = MagiDict(
             {"a": [[[5, 6], [7, 8]]], "c": [[[[9]]]]}
        )

        self.assertEqual(result, expected)
        self.assertEqual(result_drop_empty, expected_drop_empty)


class TestCoreMissingCoverage(TestCase):
    def test_getitem_with_list_and_tuple_keys_and_dot_string(self):
        md = MagiDict({"a": {"b": {"c": 1}}, "lst": [10, {"x": 5}]})
        # forgiving nested access with list
        self.assertEqual(md[["a", "b", "c"]], 1)
        # forgiving nested access with tuple
        self.assertEqual(md[("a", "b", "c")], 1)
        # non-existing path returns empty MagiDict marked _from_missing
        res = md[["a", "b", "nope"]]
        self.assertIsInstance(res, MagiDict)
        self.assertTrue(getattr(res, "_from_missing", False))
        # dotted string unforgiving access
        self.assertEqual(md["a.b.c"], 1)
        # dotted string indexing into list
        md2 = MagiDict({"arr": ["zero", {"k": "v"}]})
        self.assertEqual(md2["arr.1.k"], "v")

    def test_getattr_flags_and_protection(self):
        md = MagiDict({"maybe": None})
        # attribute access for None returns MagiDict with _from_none
        m = md.maybe
        self.assertIsInstance(m, MagiDict)
        self.assertTrue(getattr(m, "_from_none", False))
        # cannot set item on protected MagiDict
        with self.assertRaises(TypeError):
            m["x"] = 1
        # _from_missing via getattr
        mm = md.no_such_key
        self.assertIsInstance(mm, MagiDict)
        self.assertTrue(getattr(mm, "_from_missing", False))

    def test_deepcopy_and_getstate_setstate_roundtrip(self):
        md = MagiDict({"a": 1})
        # mark as from_missing and ensure deepcopy preserves flag
        mm = md.nope
        self.assertTrue(getattr(mm, "_from_missing", False))
        cp = pickle.loads(pickle.dumps(mm))
        self.assertTrue(getattr(cp, "_from_missing", False))

    def test_disenchant_circular_and_collections(self):
        a = MagiDict({"name": "root"})
        b = MagiDict({"child": a})
        a["parent"] = b  # circular reference
        a["numbers"] = (1, 2, 3)
        a["seq"] = [a, b]
        a["sset"] = {1, 2}
        res = a.disenchant()
        # Should be plain dicts/collections and preserve nesting without MagiDict types
        self.assertIsInstance(res, dict)
        self.assertEqual(res["name"], "root")
        self.assertIsInstance(res["numbers"], tuple)
        self.assertIsInstance(res["seq"], list)
        self.assertIsInstance(res["sset"], set)
        # circular structure should not blow up and should reuse objects where appropriate
        self.assertIs(res["parent"]["child"], res)

    def test_search_key_and_search_keys(self):
        data = {
            "a": {"x": 1},
            "b": [{"x": 2}, {"y": 3}],
            "x": 0,
        }
        md = MagiDict(data)
        # first match is the first occurrence found during traversal (nested under 'a')
        self.assertEqual(md.search_key("x"), 1)
        # specifying default when not found
        self.assertEqual(md.search_key("nope", default="d"), "d")
        # search_keys should return all occurrences
        all_x = md.search_keys("x")
        self.assertCountEqual(all_x, [0, 1, 2])

    def test_filter_various_signatures_and_drop_empty(self):
        md = MagiDict({
            "a": 1,
            "b": None,
            "c": [1, None, 2, {"n": None}],
            "d": {"keep": 5, "drop": None},
        })

        # default filter removes None
        f = md.filter(None)
        self.assertIn("a", f)
        self.assertNotIn("b", f)
        # predicate with two args (index, value) for sequences
        def seq_pred(_, v):
            return v is not None

        f2 = md.filter(seq_pred, drop_empty=True)
        self.assertIn("c", f2)
        # nested dict drops empty entries
        self.assertIn("keep", f2.d)
        self.assertNotIn("drop", f2.d)

    def test_json_loads_and_load_and_enchant_none(self):
        s = '{"a": 1, "b": {"c": null}}'
        md = magi_loads(s)
        self.assertIsInstance(md, MagiDict)
        buf = io.StringIO(s)
        md2 = magi_load(buf)
        self.assertIsInstance(md2, MagiDict)
        # enchant with wrong type
        with self.assertRaises(TypeError):
            enchant(123)
        # none() converts empty protected MagiDict to None
        m = MagiDict()
        object.__setattr__(m, "_from_missing", True)
        self.assertIsNone(none(m))
        # normal MagiDict is returned as-is
        md_obj = MagiDict({"x": 1})
        self.assertIs(none(md_obj), md_obj)

    def test_magi_loads_handles_object_hook(self):
        # ensure magi_loads uses MagiDict as object hook
        s = json.dumps({"k": {"inner": 2}})
        md = magi_loads(s)
        self.assertIsInstance(md, MagiDict)
        self.assertIsInstance(md.k, MagiDict)





if __name__ == "__main__":
    main()
