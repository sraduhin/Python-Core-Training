import inspect

import pytest

from main import count_calls


def test_01():
    """Декорирование не вызывает исходную функцию; начальный счётчик равен нулю."""
    calls = []

    @count_calls
    def f():
        calls.append(1)

    assert calls == []
    assert f.call_count() == 0


def test_02():
    """Позиционные, именованные и аргументы по умолчанию работают без изменений."""
    @count_calls
    def add(a, b, c=10):
        return a + b + c

    assert add(1, 2) == 13
    assert add(1, 2, 3) == 6
    assert add(1, b=2, c=0) == 3
    assert add.call_count() == 3


def test_03():
    """Результаты None, False и изменяемый объект возвращаются без замены или копирования."""
    _none = None
    obj = [1, 2, 3]

    @count_calls
    def f(x):
        return x

    assert f(_none) is None
    assert f(False) is False
    assert f(obj) is obj


def test_04():
    """Ошибка тела учитываются ровно один раз; исключения не подавляются."""
    failure = ValueError("skbdysh")

    @count_calls
    def raise_func():
        raise failure

    with pytest.raises(ValueError) as info:
        raise_func()
    assert info.value is failure
    assert raise_func.call_count() == 1


def test_04_2():
    """ошибка связывания аргументов учитываются ровно один раз; исключения не подавляются."""
    @count_calls
    def two_args_func(a, b):
        return a + b

    with pytest.raises(TypeError):
        two_args_func(1)
    assert two_args_func.call_count() == 1


def test_05():
    """call_count() и прямой вызов __wrapped__ не меняют счётчик обёртки."""
    @count_calls
    def f():
        return 42

    f()
    assert f.call_count() == 1

    f.call_count()
    assert f.call_count() == 1

    assert f.__wrapped__() == 42
    assert f.call_count() == 1


def test_06():
    """Метаданные сохранены; inspect.signature показывает сигнатуру исходной функции."""
    @count_calls
    def echo_arg(name: str) -> str:
        """some docstring"""
        return name

    assert echo_arg.__name__ == "echo_arg"
    assert echo_arg.__doc__ == "some docstring"
    assert str(inspect.signature(echo_arg)) == "(name: str) -> str"


def test_07():
    """Независимые обёртки не делят состояние"""
    def simple():
        return 1

    w1 = count_calls(simple)
    w2 = count_calls(simple)
    w1()
    w1()
    w2()
    assert w1.call_count() == 2
    assert w2.call_count() == 1

    @count_calls
    def other():
        return 2

    assert other.call_count() == 0


def test_07_2():
    """неподдерживаемые функции отклоняются."""
    with pytest.raises(TypeError):
        count_calls(123)

    async def coro():
        return 1

    with pytest.raises(TypeError):
        count_calls(coro)

    def gen():
        yield 1

    with pytest.raises(TypeError):
        count_calls(gen)

    async def agen():
        yield 1

    with pytest.raises(TypeError):
        count_calls(agen)

    with pytest.raises(TypeError):
        count_calls(len)
