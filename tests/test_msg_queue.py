import asyncio
import pytest

from aries_staticagent import MsgQueue


@pytest.fixture
def queue():
    yield MsgQueue()


@pytest.mark.asyncio
async def test_multiple_consumers(queue: MsgQueue):
    async def consume():
        await queue.get()

    async def produce(additional_timeout=0):
        await asyncio.sleep(1 + additional_timeout)
        await queue.put(None)

    tasks = []
    for _ in range(3):
        tasks.append(asyncio.ensure_future(consume()))
    for i in range(3):
        tasks.append(asyncio.ensure_future(produce(i)))

    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_condition_msg_present_no_match(queue):
    await queue.put(None)

    async def consume():
        await queue.get(lambda msg: msg is not None)

    async def produce():
        await asyncio.sleep(1)
        await queue.put(1)

    tasks = (asyncio.ensure_future(consume()), asyncio.ensure_future(produce()))
    await asyncio.gather(*tasks)
