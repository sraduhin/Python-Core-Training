import math
import threading

import pytest

import gil_compare
from gil_compare import ThreadPoolExecutor, compare


def _params(**overrides):
    params = {"jobs": 1, "iterations": 0, "delay": 0, "workers": 1, "repeats": 1}
    params.update(overrides)
    return params


def _assert_samples(report, repeats):
    for mode in ("sequential", "threads"):
        samples = report[mode]["samples"]
        assert len(samples) == repeats
        for sample in samples:
            assert math.isfinite(sample)
            assert sample >= 0


def test_01_02():
    """Оба режима возвращают одинаковые упорядоченные результаты для каждой нагрузки"""
    cpu = compare("cpu", jobs=3, iterations=5, workers=2, repeats=2)
    assert cpu["sequential"]["results"] == cpu["threads"]["results"] == [30, 31, 32]
    _assert_samples(cpu, 2)

    wait = compare("wait", jobs=4, delay=0.01, workers=3, repeats=3)
    assert wait["sequential"]["results"] == wait["threads"]["results"] == [0, 1, 2, 3]
    _assert_samples(wait, 3)


def test_03():
    """Нулевое число CPU-итераций, один worker и один job"""
    zero = compare("cpu", jobs=3, iterations=0, workers=2, repeats=1)
    assert zero["sequential"]["results"] == zero["threads"]["results"] == [0, 1, 2]
    _assert_samples(zero, 1)

    single_worker = compare("wait", jobs=3, delay=0, workers=1, repeats=1)
    assert single_worker["sequential"]["results"] == single_worker["threads"]["results"] == [0, 1, 2]
    _assert_samples(single_worker, 1)

    single_job = compare("cpu", jobs=1, iterations=5, workers=2, repeats=1)
    assert single_job["sequential"]["results"] == single_job["threads"]["results"] == [30]
    _assert_samples(single_job, 1)


def test_04(monkeypatch):
    """Ошибочные параметры отклоняются до создания пула"""
    created = []

    class TrackingExecutor(ThreadPoolExecutor):
        def __init__(self, *args, **kwargs):
            created.append("created")
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(gil_compare, "ThreadPoolExecutor", TrackingExecutor)

    invalid_kinds = (None, 1, "", "CPU", "io")
    for kind in invalid_kinds:
        with pytest.raises(ValueError):
            compare(kind, jobs=1, iterations=0, delay=0, workers=1, repeats=1)

    type_errors = (
        {"jobs": True},
        {"jobs": False},
        {"jobs": 1.0},
        {"iterations": True},
        {"iterations": 1.5},
        {"delay": True},
        {"delay": "0.02"},
        {"delay": None},
        {"workers": False},
        {"repeats": 1.2},
    )
    for kwargs in type_errors:
        with pytest.raises(TypeError):
            compare("cpu", **_params(**kwargs))

    value_errors = (
        {"jobs": 0},
        {"jobs": -2},
        {"iterations": -1},
        {"delay": -0.01},
        {"delay": math.nan},
        {"delay": math.inf},
        {"delay": -math.inf},
        {"workers": 0},
        {"repeats": 0},
        {"repeats": -3},
    )
    for kwargs in value_errors:
        with pytest.raises(ValueError):
            compare("cpu", **_params(**kwargs))

    assert created == []


def test_05():
    """Завершение запуска означает завершение всех принадлежащих ему потоков."""
    compare("wait", jobs=4, delay=0.01, workers=3, repeats=2)

    active_threads = [thread for thread in threading.enumerate() if thread.name.startswith("ThreadPoolExecutor")]
    assert active_threads == []


@pytest.mark.parametrize("measure_name", ("_measure_sequential", "_measure_thread"))
def test_06_extended(monkeypatch, measure_name):
    """Ошибка в первом повторе сразу останавливает оба режима."""
    real_measure = getattr(gil_compare, measure_name)
    calls = {"count": 0}

    def fake_measure(*args):
        calls["count"] += 1
        samples, results = real_measure(*args)
        if calls["count"] == 1:
            return samples, [value + 1 for value in results]
        return samples, results

    monkeypatch.setattr(gil_compare, measure_name, fake_measure)

    with pytest.raises(RuntimeError):
        compare("cpu", jobs=3, iterations=5, workers=1, repeats=2)

    assert calls["count"] == 1
