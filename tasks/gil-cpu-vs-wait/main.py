"""Скрипт эксперимента: печатает медианные длительности для cpu и wait."""

from statistics import median

from gil_compare import compare


def _report(kind, **kwargs):
    data = compare(kind, **kwargs)
    seq = median(data["sequential"]["samples"])
    thr = median(data["threads"]["samples"])
    params = data["metadata"]["params"]
    print(f"[{kind}] params={params}")
    print(f"    sequential median: {seq:.4f}s")
    print(f"    threads    median: {thr:.4f}s")
    print(f"    threads/seq ratio : {thr / seq:.2f}")


def main():
    meta = compare("wait", jobs=1, iterations=0, repeats=1)["metadata"]
    print(
        f"python={meta['python_version']} impl={meta['implementation']} "
        f"gil_enabled={meta['gil_enabled']}\n"
    )
    _report("cpu", jobs=4, iterations=200_000, workers=2, repeats=5)
    _report("wait", jobs=4, delay=0.02, workers=2, repeats=5)


if __name__ == "__main__":
    main()
