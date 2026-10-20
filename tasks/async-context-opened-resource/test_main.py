import asyncio

import pytest

from main import opened_resource

OP_OPN = "open"
OP_CLS = "close"
RESOURCE_NAME = "resource"

class FakeResource:
    def __init__(self, log, name=RESOURCE_NAME, allow_close=None, close_started=None):
        self.log = log
        self.closed = False
        self.name = name
        self._allow_close = allow_close
        self._close_started = close_started

    async def aclose(self) -> None:
        if self._close_started is not None:
            self._close_started.set()
        if self._allow_close is not None:
            await self._allow_close.wait()
        else:
            await asyncio.sleep(0)
        self.closed = True
        self.log.append((OP_CLS, self.name))


def _open(log, resource):
    async def open_fake():
        log.append((OP_OPN, resource.name))
        return resource

    return open_fake


# region: базовые

def test_01():
    """Создание менеджера не открывает ресурс"""
    async def scenario():
        log = []
        resource = FakeResource(log)
        opener = _open(log, resource)
        cm = opened_resource(opener)

        assert log == []
        async with cm as res:
            assert log == [(OP_OPN, RESOURCE_NAME)]
            assert res.closed is False
        assert log == [(OP_OPN, RESOURCE_NAME), (OP_CLS, RESOURCE_NAME)]  # ресурс закрыт ровно один раз

    asyncio.run(scenario())


def test_02():
    """ объект, который нельзя вызвать, отвергается при входе по TypeError"""
    async def scenario():
        cm = opened_resource(123)  # создание не падает
        with pytest.raises(TypeError):
            async with cm:
                pass

    asyncio.run(scenario())


def test_03():
    """Ошибка тела сохраняет объект исключения и не мешает закрытию"""
    async def scenario():
        log = []
        resource = FakeResource(log, RESOURCE_NAME)
        my_error = ValueError("skibdysh")
        with pytest.raises(ValueError) as info:
            async with opened_resource(_open(log, resource=resource)):
                raise my_error
        assert info.value is my_error
        assert resource.closed is True
        assert log == [(OP_OPN, RESOURCE_NAME), (OP_CLS, RESOURCE_NAME)]

    asyncio.run(scenario())


def test_04():
    """Ошибка открытия не вызывает aclose; тело блока недостижимо"""
    async def scenario():
        log = []
        failure = RuntimeError("open failed")

        async def bad_opener():
            log.append(("open_attempt", "r"))
            raise failure

        with pytest.raises(RuntimeError) as info:
            async with opened_resource(bad_opener):
                log.append(("not path",))  # недостижимо
        assert info.value is failure
        assert log == [("open_attempt", "r")]

    asyncio.run(scenario())


def test_05():
    """Два вызова фабрики получают разные ресурсы и не смешивают журнал событий."""
    async def scenario():
        log_a = []
        log_b = []
        async with opened_resource(_open(log_a, FakeResource(log_a, "a"))) as ra:
            async with opened_resource(_open(log_b, FakeResource(log_b, "b"))) as rb:
                assert ra is not rb
        assert log_a == [("open", "a"), ("close", "a")]
        assert log_b == [("open", "b"), ("close", "b")]

    asyncio.run(scenario())


def test_06():
    """Два вложенных менеджера открываются снаружи внутрь, а закрываются в обратном порядке."""
    async def scenario():
        log = []
        ext_res = FakeResource(log, "external")
        int_res = FakeResource(log, "internal")
        async with opened_resource(_open(log, ext_res)):
            async with opened_resource(_open(log, int_res)):
                pass
        assert log == [
            ("open", "external"),
            ("open", "internal"),
            ("close", "internal"),
            ("close", "external"),
        ]

    asyncio.run(scenario())

# endregion


def test_event_hold_close():
    async def scenario():
        log = []
        allow_close = asyncio.Event()
        close_started = asyncio.Event()
        resource = FakeResource(log, "r", allow_close=allow_close, close_started=close_started)

        async def run():
            async with opened_resource(_open(log, resource=resource)):
                pass
            log.append(("exited", "r"))

        task = asyncio.create_task(run())
        await asyncio.wait_for(close_started.wait(), timeout=1)
        assert resource.closed is False
        assert task.done() is False
        assert ("exited", "r") not in log

        allow_close.set()
        await asyncio.wait_for(task, timeout=1)
        assert resource.closed is True
        assert log == [('open', 'r'), ('close', 'r'), ('exited', 'r')]

    asyncio.run(scenario())


def test_cancel_in_body_holds_close():
    async def scenario():
        log = []
        in_body = asyncio.Event()
        allow_close = asyncio.Event()
        close_started = asyncio.Event()
        resource = FakeResource(log, "r", allow_close=allow_close, close_started=close_started)

        async def run():
            async with opened_resource(_open(log, resource=resource)):
                in_body.set()
                await asyncio.sleep(60)

        task = asyncio.create_task(run())
        await asyncio.wait_for(in_body.wait(), timeout=5)
        task.cancel()

        await asyncio.wait_for(close_started.wait(), timeout=5)
        assert resource.closed is False
        assert task.done() is False

        allow_close.set()
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(task, timeout=1)
        assert resource.closed is True
        assert log == [("open", "r"), ("close", "r")]

    asyncio.run(scenario())
