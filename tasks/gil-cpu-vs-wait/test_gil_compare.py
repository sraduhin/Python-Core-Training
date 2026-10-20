import math
import threading

import pytest

import gil_compare
from gil_compare import compare


def _all_finite_nonnegative(samples):
    return all(isinstance(s, float) and math.isfinite(s) and s >= 0 for s in samples)


def test_results_match_between_variants_cpu():
    data = compare("cpu", jobs=4, iterations=500, workers=2, repeats=2)
    seq = data["sequential"]["results"]
    thr = data["threads"]["results"]
    assert seq == thr
    # Результаты упорядочены по индексам.
    assert seq == [j + sum((i * i) % 97 for i in range(500)) for j in range(4)]


def test_results_match_between_variants_wait():
    data = compare("wait", jobs=3, delay=0.001, workers=2, repeats=2)
    assert data["sequential"]["results"] == [0, 1, 2]
    assert data["threads"]["results"] == [0, 1, 2]


def test_sample_count_and_finiteness():
    repeats = 3
    data = compare("wait", jobs=2, delay=0.001, workers=2, repeats=repeats)
    for variant in ("sequential", "threads"):
        samples = data[variant]["samples"]
        assert len(samples) == repeats
        assert _all_finite_nonnegative(samples)


def test_zero_iterations():
    data = compare("cpu", jobs=3, iterations=0, workers=2, repeats=1)
    # sum по пустому диапазону = 0, поэтому результат = индекс.
    assert data["sequential"]["results"] == [0, 1, 2]
    assert data["threads"]["results"] == [0, 1, 2]


def test_single_worker_and_single_job():
    data = compare("cpu", jobs=1, iterations=100, workers=1, repeats=1)
    assert data["sequential"]["results"] == data["threads"]["results"]
    assert len(data["sequential"]["results"]) == 1


def test_metadata_structure():
    data = compare("wait", jobs=1, delay=0.001, workers=1, repeats=1)
    meta = data["metadata"]
    assert set(meta) == {"python_version", "implementation", "gil_enabled", "params"}
    assert meta["params"] == {
        "kind": "wait",
        "jobs": 1,
        "iterations": 200_000,
        "delay": 0.001,
        "workers": 1,
        "repeats": 1,
    }


@pytest.mark.parametrize(
    "kwargs, exc",
    [
        ({"kind": "bogus"}, ValueError),
        ({"kind": 5}, TypeError),
        ({"kind": "cpu", "jobs": 0}, ValueError),
        ({"kind": "cpu", "jobs": True}, TypeError),
        ({"kind": "cpu", "jobs": 1.0}, TypeError),
        ({"kind": "cpu", "workers": 0}, ValueError),
        ({"kind": "cpu", "repeats": -1}, ValueError),
        ({"kind": "cpu", "iterations": -1}, ValueError),
        ({"kind": "cpu", "iterations": 1.5}, TypeError),
        ({"kind": "cpu", "iterations": True}, TypeError),
        ({"kind": "wait", "delay": -0.1}, ValueError),
        ({"kind": "wait", "delay": math.inf}, ValueError),
        ({"kind": "wait", "delay": True}, TypeError),
        ({"kind": "wait", "delay": "x"}, TypeError),
    ],
)
def test_invalid_params_rejected_before_pool(kwargs, exc, monkeypatch):
    created = []

    def boom(*args, **kw):
        created.append(1)
        raise AssertionError("pool must not be created on invalid params")

    monkeypatch.setattr(gil_compare, "ThreadPoolExecutor", boom)
    with pytest.raises(exc):
        compare(**kwargs)
    assert created == []


def test_no_leftover_pool_threads_after_run():
    before = {t for t in threading.enumerate()}
    compare("wait", jobs=4, delay=0.001, workers=3, repeats=2)
    # Все принадлежащие пулу потоки завершились: новых живых нет.
    after = {t for t in threading.enumerate() if t.is_alive()}
    leftover = {
        t for t in after - before if t.name.startswith("ThreadPoolExecutor")
    }
    assert leftover == set()
