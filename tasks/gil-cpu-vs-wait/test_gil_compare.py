import inspect
import math
import threading

import pytest

import gil_compare
from gil_compare import ThreadPoolExecutor, compare


def _params(**overrides):
    params = {"jobs": 1, "iterations": 0, "delay": 0, "workers": 1, "repeats": 1}
    params.update(overrides)
    return params


def test_01_02():
    """Оба режима возвращают одинаковые упорядоченные результаты для каждой нагрузки"""
    cpu = compare("cpu", repeats=2)
    assert cpu["sequential"]["results"] == cpu["threads"]["results"]

    wait = compare("wait", jobs=4, delay=0.01, workers=3, repeats=3)
    assert wait["sequential"]["results"] == wait["threads"]["results"]

    # Есть ровно repeats конечных неотрицательных измерений каждого варианта.
    assert len(cpu["sequential"]["samples"]) == 2
    assert len(wait["sequential"]["samples"]) == 3


def test_03():
    """Нулевое число CPU-итераций, один worker и один job"""
    zero = compare("cpu", jobs=3, iterations=0, workers=2, repeats=1)
    assert zero["sequential"]["results"] == zero["threads"]["results"] == [0, 1, 2]

    single_worker = compare("wait", jobs=3, delay=0, workers=1, repeats=1)
    assert single_worker["sequential"]["results"] == single_worker["threads"]["results"] == [0, 1, 2]

    single_job = compare("cpu", jobs=1, iterations=5, workers=2, repeats=1)
    assert single_job["sequential"]["results"] == single_job["sequential"]["results"]


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
