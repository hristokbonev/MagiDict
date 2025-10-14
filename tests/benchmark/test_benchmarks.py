import pytest
from box import Box
from dotmap import DotMap
from addict import Dict as AddictDict
from magidict import MagiDict, enchant, magi_loads
import json


# --- Setup sample data ---
@pytest.fixture(scope="session")
def nested_data():
    return {
        "user": {
            "profile": {"name": "Alice", "age": 30},
            "settings": {"theme": "dark", "language": "en"},
        },
        "posts": [{"title": f"Post {i}", "likes": i * 3} for i in range(100)],
    }


@pytest.fixture(scope="session")
def deep_nested_data():
    """Very deeply nested structure for stress testing"""
    data = {"level0": {}}
    current = data["level0"]
    for i in range(1, 20):
        current[f"level{i}"] = {}
        current = current[f"level{i}"]
    current["value"] = "deep_value"
    return data


@pytest.fixture(scope="session")
def wide_data():
    """Wide structure with many keys at same level"""
    return {f"key{i}": {"nested": {"value": i}} for i in range(1000)}


@pytest.fixture(scope="session")
def json_string(nested_data):
    return json.dumps(nested_data)


@pytest.fixture(scope="session")
def magi(nested_data):
    return MagiDict(nested_data)


@pytest.fixture(scope="session")
def box_obj(nested_data):
    return Box(nested_data)


@pytest.fixture(scope="session")
def dotmap_obj(nested_data):
    return DotMap(nested_data)


@pytest.fixture(scope="session")
def addict_obj(nested_data):
    return AddictDict(nested_data)


# --- Basic Access Benchmarks ---
def test_access_magi(benchmark, magi):
    benchmark(lambda: magi.user.profile.name)


def test_access_box(benchmark, box_obj):
    benchmark(lambda: box_obj.user.profile.name)


def test_access_dotmap(benchmark, dotmap_obj):
    benchmark(lambda: dotmap_obj.user.profile.name)


def test_access_addict(benchmark, addict_obj):
    benchmark(lambda: addict_obj.user.profile.name)


# --- Bracket Access Benchmarks ---
def test_bracket_access_magi(benchmark, magi):
    benchmark(lambda: magi["user"]["profile"]["name"])


def test_bracket_access_box(benchmark, box_obj):
    benchmark(lambda: box_obj["user"]["profile"]["name"])


def test_bracket_access_dotmap(benchmark, dotmap_obj):
    benchmark(lambda: dotmap_obj["user"]["profile"]["name"])


def test_bracket_access_addict(benchmark, addict_obj):
    benchmark(lambda: addict_obj["user"]["profile"]["name"])


# --- Dot Notation String Access (MagiDict specific) ---
def test_dot_notation_string_magi(benchmark, magi):
    benchmark(lambda: magi["user.profile.name"])


# --- Missing Key Access Benchmarks ---
def test_missing_key_magi(benchmark, magi):
    benchmark(lambda: magi.user.missing.deeply.nested.key)


def test_missing_key_box(benchmark, box_obj):
    benchmark(lambda: box_obj.get("user", {}).get("missing", {}).get("deeply"))


def test_missing_key_dotmap(benchmark, dotmap_obj):
    def access():
        try:
            return dotmap_obj.user.missing.deeply.nested.key
        except (KeyError, AttributeError):
            return None

    benchmark(access)


def test_missing_key_addict(benchmark, addict_obj):
    benchmark(lambda: addict_obj.user.missing.deeply.nested.key)


# --- mget() Benchmarks ---
def test_mget_magi(benchmark, magi):
    benchmark(lambda: magi.mget("user"))


def test_mget_missing_magi(benchmark, magi):
    benchmark(lambda: magi.mget("nonexistent"))


def test_mget_with_default_magi(benchmark, magi):
    benchmark(lambda: magi.mget("nonexistent", "default"))


# --- Initialization Benchmarks ---
def test_init_magi(benchmark, nested_data):
    benchmark(lambda: MagiDict(nested_data))


def test_init_box(benchmark, nested_data):
    benchmark(lambda: Box(nested_data))


def test_init_dotmap(benchmark, nested_data):
    benchmark(lambda: DotMap(nested_data))


def test_init_addict(benchmark, nested_data):
    benchmark(lambda: AddictDict(nested_data))


def test_init_regular_dict(benchmark, nested_data):
    benchmark(lambda: dict(nested_data))


# --- Deep Initialization Benchmarks ---
def test_init_deep_magi(benchmark, deep_nested_data):
    benchmark(lambda: MagiDict(deep_nested_data))


def test_init_deep_box(benchmark, deep_nested_data):
    benchmark(lambda: Box(deep_nested_data))


def test_init_deep_dotmap(benchmark, deep_nested_data):
    benchmark(lambda: DotMap(deep_nested_data))


def test_init_deep_addict(benchmark, deep_nested_data):
    benchmark(lambda: AddictDict(deep_nested_data))


# --- Wide Structure Benchmarks ---
def test_init_wide_magi(benchmark, wide_data):
    benchmark(lambda: MagiDict(wide_data))


def test_init_wide_box(benchmark, wide_data):
    benchmark(lambda: Box(wide_data))


def test_init_wide_dotmap(benchmark, wide_data):
    benchmark(lambda: DotMap(wide_data))


def test_init_wide_addict(benchmark, wide_data):
    benchmark(lambda: AddictDict(wide_data))


# --- Update Benchmarks ---
def test_update_magi(benchmark, magi):
    def mutate():
        m = MagiDict(magi)
        m["user"]["profile"]["age"] = m["user"]["profile"]["age"] + 1
        return m

    benchmark(mutate)


def test_update_box(benchmark, box_obj):
    def mutate():
        b = Box(box_obj)
        b.user.profile.age += 1
        return b

    benchmark(mutate)


def test_update_dotmap(benchmark, dotmap_obj):
    def mutate():
        d = DotMap(dotmap_obj)
        d.user.profile.age += 1
        return d

    benchmark(mutate)


def test_update_addict(benchmark, addict_obj):
    def mutate():
        a = AddictDict(addict_obj)
        a.user.profile.age += 1
        return a

    benchmark(mutate)


# --- Bulk Update Benchmarks ---
def test_bulk_update_magi(benchmark, magi):
    def bulk_update():
        m = MagiDict(magi)
        m.update({"new_key1": "value1", "new_key2": {"nested": "value2"}})
        return m

    benchmark(bulk_update)


def test_bulk_update_box(benchmark, box_obj):
    def bulk_update():
        b = Box(box_obj)
        b.update({"new_key1": "value1", "new_key2": {"nested": "value2"}})
        return b

    benchmark(bulk_update)


# --- List Access Benchmarks ---
def test_list_access_magi(benchmark, magi):
    benchmark(lambda: magi.posts[50].title)


def test_list_access_box(benchmark, box_obj):
    benchmark(lambda: box_obj.posts[50].title)


def test_list_access_dotmap(benchmark, dotmap_obj):
    benchmark(lambda: dotmap_obj.posts[50].title)


def test_list_access_addict(benchmark, addict_obj):
    benchmark(lambda: addict_obj.posts[50].title)


# --- List Iteration Benchmarks ---
def test_list_iteration_magi(benchmark, magi):
    def iterate():
        total = 0
        for post in magi.posts:
            total += post.likes
        return total

    benchmark(iterate)


def test_list_iteration_box(benchmark, box_obj):
    def iterate():
        total = 0
        for post in box_obj.posts:
            total += post.likes
        return total

    benchmark(iterate)


def test_list_iteration_dotmap(benchmark, dotmap_obj):
    def iterate():
        total = 0
        for post in dotmap_obj.posts:
            total += post.likes
        return total

    benchmark(iterate)


def test_list_iteration_addict(benchmark, addict_obj):
    def iterate():
        total = 0
        for post in addict_obj.posts:
            total += post.likes
        return total

    benchmark(iterate)


# --- Conversion Benchmarks ---
def test_disenchant_magi(benchmark, magi):
    benchmark(lambda: magi.disenchant())


def test_to_dict_box(benchmark, box_obj):
    benchmark(lambda: box_obj.to_dict())


def test_to_dict_dotmap(benchmark, dotmap_obj):
    benchmark(lambda: dotmap_obj.toDict())


def test_to_dict_addict(benchmark, addict_obj):
    benchmark(lambda: dict(addict_obj))


# --- Enchant Benchmark ---
def test_enchant_magi(benchmark, nested_data):
    benchmark(lambda: enchant(nested_data))


# --- JSON Loading Benchmarks ---
def test_magi_loads(benchmark, json_string):
    benchmark(lambda: magi_loads(json_string))


def test_json_loads_regular(benchmark, json_string):
    benchmark(lambda: json.loads(json_string))


def test_json_loads_box(benchmark, json_string):
    benchmark(lambda: Box(json.loads(json_string)))


# --- Copy Benchmarks ---
def test_copy_magi(benchmark, magi):
    benchmark(lambda: magi.copy())


def test_copy_box(benchmark, box_obj):
    benchmark(lambda: box_obj.copy())


def test_copy_dotmap(benchmark, dotmap_obj):
    benchmark(lambda: dotmap_obj.copy())


def test_copy_addict(benchmark, addict_obj):
    benchmark(lambda: addict_obj.copy())


# --- Deep Copy Benchmarks ---
def test_deepcopy_magi(benchmark, magi):
    from copy import deepcopy

    benchmark(lambda: deepcopy(magi))


def test_deepcopy_box(benchmark, box_obj):
    from copy import deepcopy

    benchmark(lambda: deepcopy(box_obj))


def test_deepcopy_dotmap(benchmark, dotmap_obj):
    from copy import deepcopy

    benchmark(lambda: deepcopy(dotmap_obj))


def test_deepcopy_addict(benchmark, addict_obj):
    from copy import deepcopy

    benchmark(lambda: deepcopy(addict_obj))


# --- Keys/Values/Items Iteration ---
def test_keys_iteration_magi(benchmark, magi):
    benchmark(lambda: list(magi.user.profile.keys()))


def test_values_iteration_magi(benchmark, magi):
    benchmark(lambda: list(magi.user.profile.values()))


def test_items_iteration_magi(benchmark, magi):
    benchmark(lambda: list(magi.user.profile.items()))


# --- Contains Check Benchmarks ---
def test_contains_magi(benchmark, magi):
    benchmark(lambda: "user" in magi)


def test_contains_box(benchmark, box_obj):
    benchmark(lambda: "user" in box_obj)


def test_contains_dotmap(benchmark, dotmap_obj):
    benchmark(lambda: "user" in dotmap_obj)


def test_contains_addict(benchmark, addict_obj):
    benchmark(lambda: "user" in addict_obj)


# --- Get Method Benchmarks ---
def test_get_method_magi(benchmark, magi):
    benchmark(lambda: magi.get("user"))


def test_get_method_box(benchmark, box_obj):
    benchmark(lambda: box_obj.get("user"))


def test_get_method_dotmap(benchmark, dotmap_obj):
    benchmark(lambda: dotmap_obj.get("user"))


def test_get_method_addict(benchmark, addict_obj):
    benchmark(lambda: addict_obj.get("user"))


# --- Setdefault Benchmarks ---
def test_setdefault_magi(benchmark, magi):
    def setdef():
        m = MagiDict(magi)
        m.setdefault("new_key", {"default": "value"})
        return m

    benchmark(setdef)


def test_setdefault_box(benchmark, box_obj):
    def setdef():
        b = Box(box_obj)
        b.setdefault("new_key", {"default": "value"})
        return b

    benchmark(setdef)


# --- Pop Benchmarks ---
def test_pop_magi(benchmark, nested_data):
    def pop():
        m = MagiDict(nested_data)
        m.pop("user", None)
        return m

    benchmark(pop)


def test_pop_box(benchmark, nested_data):
    def pop():
        b = Box(nested_data)
        b.pop("user", None)
        return b

    benchmark(pop)


# --- Memory-intensive Operations ---
def test_large_nested_access_magi(benchmark):
    """Test with a large nested structure"""
    large_data = {f"level{i}": {f"sub{j}": j for j in range(100)} for i in range(100)}
    m = MagiDict(large_data)
    benchmark(lambda: m.level50.sub50)


def test_large_nested_access_box(benchmark):
    large_data = {f"level{i}": {f"sub{j}": j for j in range(100)} for i in range(100)}
    b = Box(large_data)
    benchmark(lambda: b.level50.sub50)


# --- Nested List with Dict Access ---
def test_nested_list_dict_access_magi(benchmark, magi):
    benchmark(lambda: magi["posts.50.likes"])


# --- Multiple Sequential Accesses ---
def test_sequential_access_magi(benchmark, magi):
    def multi_access():
        name = magi.user.profile.name
        age = magi.user.profile.age
        theme = magi.user.settings.theme
        lang = magi.user.settings.language
        return name, age, theme, lang

    benchmark(multi_access)


def test_sequential_access_box(benchmark, box_obj):
    def multi_access():
        name = box_obj.user.profile.name
        age = box_obj.user.profile.age
        theme = box_obj.user.settings.theme
        lang = box_obj.user.settings.language
        return name, age, theme, lang

    benchmark(multi_access)


# --- Chained Missing Key Access ---
def test_chained_missing_magi(benchmark, magi):
    benchmark(lambda: magi.a.b.c.d.e.f.g.h.i.j)


def test_chained_missing_addict(benchmark, addict_obj):
    benchmark(lambda: addict_obj.a.b.c.d.e.f.g.h.i.j)


# --- None value handling ---
def test_none_value_access_magi(benchmark):
    m = MagiDict({"key": None})
    benchmark(lambda: m.key.nested.access)


# --- Merge Operations ---
def test_merge_operator_magi(benchmark, magi):
    def merge():
        m = MagiDict(magi)
        return m | {"extra": {"data": "value"}}

    benchmark(merge)


def test_merge_operator_regular_dict(benchmark, nested_data):
    def merge():
        d = dict(nested_data)
        return d | {"extra": {"data": "value"}}

    benchmark(merge)
