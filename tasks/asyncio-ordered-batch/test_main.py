import asyncio

import pytest

from main import run_batch


def test_01():
    """Пустой вход и один элемент."""
    async def scenario():
        calls = []

        async def work(item):
            calls.append(item)
            return item * 2

        assert await run_batch([], work) == []
        assert calls == []

        assert await run_batch([7], work) == [14]
        assert calls == [7]

    asyncio.run(scenario())


def test_02():
    """Три операции сообщают о старте через Event до разрешения закончить хоть одну:
     последовательный цикл такую проверку не проходит."""
    # раз 10 прочитал, так и не понял, что значит "последовательный цикл такую проверку не проходит"
    async def scenario():
        started = 0
        all_started = asyncio.Event()
        allow_finish = asyncio.Event()

        async def work(item):
            nonlocal started
            started += 1
            if started == 3:
                all_started.set()
            await allow_finish.wait()
            return item

        batch = asyncio.create_task(run_batch([1, 2, 3], work))
        await all_started.wait()
        allow_finish.set()
        assert await batch == [1, 2, 3]

    asyncio.run(scenario())


def test_03():
    """Завершение в порядке 3–2–1 сохраняет исходный порядок ответа."""

    async def scenario():
        started = 0
        finish_order = []

        async def work(item):
            nonlocal started
            started += 1
            await asyncio.sleep(3 - started)
            finish_order.append(item)
            return item * 10

        batch = asyncio.create_task(run_batch([1, 2, 3], work))

        assert await batch == [10, 20, 30]
        assert finish_order == [3, 2, 1]

    asyncio.run(scenario())


def test_04():
    """Дубликаты запускают отдельные операции и занимают отдельные позиции."""

    async def scenario():
        calls = []

        async def work(item):
            calls.append(item)
            return item

        result = await run_batch([10, 20, 10], work)
        assert result == [10, 20, 10]
        assert calls == [10, 20, 10]

    asyncio.run(scenario())


def test_05():
    """Заранее созданный ValueError попадает в ответ тем же объектом; соседние операции успешно заканчиваются."""

    async def scenario():
        error = ValueError("watta hell")

        async def work(item):
            if item == 2:
                raise error
            return item * 10

        result = await run_batch([1, 2, 3], work)
        assert result[0] == 10
        assert result[1] is error
        assert result[2] == 30

    asyncio.run(scenario())


def test_06():
    """После внешней отмены все начавшиеся операции выполнили очистку до выхода партии."""

    async def scenario():
        started = 0
        all_started = asyncio.Event()
        allow_finish = asyncio.Event()

        async def work(item):
            nonlocal started
            started += 1
            if started == 3:
                all_started.set()
            await allow_finish.wait()
            return item

        batch = asyncio.create_task(run_batch([1, 2, 3], work))
        await all_started.wait()
        batch.cancel()

        with pytest.raises(asyncio.CancelledError):
            await batch

        leftover = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        assert leftover == []

    asyncio.run(scenario())


def test_07():
    """Два независимых запуска не смешивают результаты."""

    async def scenario():
        async def work_a(item):
            return item + 100

        async def work_b(item):
            return item + 200

        first, second = await asyncio.gather(
            run_batch([1, 2], work_a),
            run_batch([3, 4], work_b),
        )
        assert first == [101, 102]
        assert second == [203, 204]

    asyncio.run(scenario())
