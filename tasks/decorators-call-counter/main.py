import functools
import inspect


def count_calls(func):
    if (
        not callable(func)
        or inspect.iscoroutinefunction(func)
        or inspect.isgeneratorfunction(func)
        or inspect.isasyncgenfunction(func)
    ):
        raise TypeError(f"count_calls expects a simple sync function, got {func!r}")

    count = 0

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        nonlocal count
        count += 1
        return func(*args, **kwargs)

    wrapper.call_count = lambda: count
    return wrapper
