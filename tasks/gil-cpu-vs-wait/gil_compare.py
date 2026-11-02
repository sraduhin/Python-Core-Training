import math
import platform
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial


def compare(
    kind,
    *,
    jobs=4,
    iterations=200_000,
    delay=0.02,
    workers=2,
    repeats=3,
) -> dict:
    _validate(kind, jobs, iterations, delay, workers, repeats)
    job = partial(_run_job, kind, iterations, delay)

    sequential_samples = []
    sequential_results = None
    for _ in range(repeats):
        samples, sequential_results = _measure_sequential(job, jobs)
        sequential_samples.append(samples)

    thread_samples = []
    thread_results = None
    for _ in range(repeats):
        samples, thread_results = _measure_thread(job, jobs, workers)
        thread_samples.append(samples)

    return {
        "metadata": {
            "python_version": platform.python_version(),
            "implementation": sys.implementation.name,
            "gil_enabled": True,
            "params": {
                "kind": kind,
                "jobs": jobs,
                "iterations": iterations,
                "delay": delay,
                "workers": workers,
                "repeats": repeats,
            },
        },
        "sequential": {
            "samples": sequential_samples,
            "results": sequential_results,
        },
        "threads": {
            "samples": thread_samples,
            "results": thread_results,
        },
    }


def _validate(kind, jobs, iterations, delay, workers, repeats):
    if kind not in ("cpu", "wait"):
        raise ValueError("kind должен быть 'cpu' или 'wait'")
    _check_int("jobs", jobs, min=1)
    _check_int("iterations", iterations, min=0)
    _check_delay(delay)
    _check_int("workers", workers, min=1)
    _check_int("repeats", repeats, min=1)


def _check_int(name, value, min):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} должен быть целым числом")
    if value < min:
        raise ValueError(f"{name} должен быть не меньше {min}")


def _check_delay(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("delay должен быть int или float")
    if not math.isfinite(value) or value < 0:
        raise ValueError("delay должен быть конечным и неотрицательным")



def _run_job(kind, iterations, delay, index):
    if kind == "cpu":
        return index + sum((i * i) % 97 for i in range(iterations))
    time.sleep(delay)
    return index


def _measure_sequential(job, jobs):
    start = time.perf_counter()
    results = [job(index) for index in range(jobs)]
    samples = time.perf_counter() - start
    return samples, results


def _measure_thread(job, jobs, workers):
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(job, range(jobs)))
    samples = time.perf_counter() - start
    return samples, results


def _print_report(kind, report):
    print(f"kind={kind} gil_enabled={report['metadata']['gil_enabled']}")
    for mode in ("sequential", "threads"):
        samples = report[mode]["samples"]
        mean = sum(samples) / len(samples)
        print(f"  {mode}: samples={samples} mean={mean:.6f} results={report[mode]['results']}")


if __name__ == "__main__":
    cpu = compare("cpu", jobs=4, iterations=100_000, workers=2, repeats=3)
    wait = compare("wait", jobs=4, delay=0.05, workers=2, repeats=3)
    _print_report("cpu", cpu)
    _print_report("wait", wait)
