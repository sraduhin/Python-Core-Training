"""Сравнение последовательного и поточного выполнения CPU- и wait-нагрузки."""

import math
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

_KINDS = ("cpu", "wait")


def _check_positive_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be int, got {type(value).__name__}")
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def _check_nonnegative_int(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def _check_delay(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"delay must be int or float, got {type(value).__name__}")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"delay must be finite and non-negative, got {value!r}")


def _make_task(kind, iterations, delay):
    if kind == "cpu":
        def task(j):
            return j + sum((i * i) % 97 for i in range(iterations))
    else:
        def task(j):
            time.sleep(delay)
            return j
    return task


def _measure(runner, repeats, expected):
    """Запустить runner repeats раз, вернуть (samples, results последнего запуска).

    Результаты каждого запуска проверяются до принятия измерения. Пул создаётся
    и закрывается внутри runner; при ошибке измерение завершается исключением.
    """
    samples = []
    results = None
    for _ in range(repeats):
        start = perf_counter()
        results = runner()
        duration = perf_counter() - start
        if results != expected:
            raise RuntimeError("results differ from the reference run")
        samples.append(duration)
    return samples, results


def compare(kind, *, jobs=4, iterations=200_000, delay=0.02, workers=2, repeats=3) -> dict:
    """Выполнить одну и ту же последовательность заданий последовательно и в пуле потоков.

    kind — "cpu" или "wait". Возвращает dict с metadata и по двум вариантам
    (sequential/threads), каждый с samples (длительности perf_counter) и results
    (результаты последнего запуска в порядке индексов).
    """
    if not isinstance(kind, str):
        raise TypeError(f"kind must be str, got {type(kind).__name__}")
    if kind not in _KINDS:
        raise ValueError(f"kind must be one of {_KINDS}, got {kind!r}")

    _check_positive_int("jobs", jobs)
    _check_nonnegative_int("iterations", iterations)
    _check_delay(delay)
    _check_positive_int("workers", workers)
    _check_positive_int("repeats", repeats)

    task = _make_task(kind, iterations, delay)
    indices = list(range(jobs))
    expected = [task(j) for j in indices]  # эталон для проверки результатов

    def run_sequential():
        return [task(j) for j in indices]

    def run_threads():
        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(task, indices))

    seq_samples, seq_results = _measure(run_sequential, repeats, expected)
    thr_samples, thr_results = _measure(run_threads, repeats, expected)

    gil_enabled = getattr(sys, "_is_gil_enabled", lambda: True)()

    return {
        "metadata": {
            "python_version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "gil_enabled": gil_enabled,
            "params": {
                "kind": kind,
                "jobs": jobs,
                "iterations": iterations,
                "delay": delay,
                "workers": workers,
                "repeats": repeats,
            },
        },
        "sequential": {"samples": seq_samples, "results": seq_results},
        "threads": {"samples": thr_samples, "results": thr_results},
    }
