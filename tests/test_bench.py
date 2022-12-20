import sys
import time

import pytest

from psygnal import Signal

pytest.importorskip("pytest_benchmark")
if all("--benchmark" not in x for x in sys.argv):
    pytest.skip("use --benchmark-enable to run bench", allow_module_level=True)


class ST:
    changed = Signal(int)


def make_superqt_class():
    return ST()


@pytest.mark.benchmark(group="create")
def test_create_superqt_bench(benchmark):
    benchmark(make_superqt_class)


def callback():
    time.sleep(0.01)


@pytest.mark.benchmark(group="connect")
def test_connect_superqt_bench(benchmark):
    obj = make_superqt_class()
    benchmark(obj.changed.connect, callback)


@pytest.mark.benchmark(group="connect")
def test_connect_superqt_bench_typed(benchmark):
    obj = make_superqt_class()
    benchmark(obj.changed.connect, callback, check_types=True)


@pytest.mark.benchmark(group="emit")
@pytest.mark.parametrize("connections", range(0, 2**4, 2))
def test_emit_superqt_bench(benchmark, connections):
    obj = make_superqt_class()
    for _ in range(connections):
        obj.changed.connect(callback, unique=False)
    benchmark(obj.changed.emit, 1)
