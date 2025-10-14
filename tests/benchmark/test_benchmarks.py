import pytest
from box import Box
from dotmap import DotMap
from addict import Dict as AddictDict
from magidict import MagiDict


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


# --- Benchmarks ---

def test_access_magi(benchmark, magi):
    benchmark(lambda: magi.user.profile.name)


def test_access_box(benchmark, box_obj):
    benchmark(lambda: box_obj.user.profile.name)


def test_access_dotmap(benchmark, dotmap_obj):
    benchmark(lambda: dotmap_obj.user.profile.name)


def test_access_addict(benchmark, addict_obj):
    benchmark(lambda: addict_obj.user.profile.name)


def test_mget_magi(benchmark, magi):
    benchmark(lambda: magi.mget("user.profile.name"))


def test_update_magi(benchmark, magi):
    def mutate():
        magi.user.profile.age += 1
    benchmark(mutate)


def test_disenchant_magi(benchmark, magi):
    benchmark(lambda: magi.disenchant())
