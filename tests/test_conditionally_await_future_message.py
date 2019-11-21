"""Test ConditionallyAwaitFutureMessage."""

import asyncio
import pytest
from aries_staticagent.static_connection import ConditionallyAwaitFutureMessage


@pytest.mark.asyncio
async def test_can_await_no_cond():
    """Test awaiting a message with no condition."""
    future_message = ConditionallyAwaitFutureMessage()

    task = asyncio.ensure_future(future_message.wait())
    assert future_message.condition_met('asdf') is True
    future_message.set_message('asdf')

    assert await task == 'asdf'


@pytest.mark.asyncio
async def test_can_await_with_cond():
    """Test awaiting a message with condition."""
    future_message = ConditionallyAwaitFutureMessage(
        condition=lambda msg: msg != 'asdf'
    )

    task = asyncio.ensure_future(future_message.wait())
    assert future_message.condition_met('asdf') is False
    assert future_message.condition_met('qwer') is True
    future_message.set_message('qwer')
    assert await task == 'qwer'


@pytest.mark.asyncio
async def test_can_await_multiple():
    """Test awaiting a message at multiple points."""
    future_message = ConditionallyAwaitFutureMessage()

    task = asyncio.ensure_future(future_message.wait())
    task2 = asyncio.ensure_future(future_message.wait())
    future_message.set_message('asdf')

    assert await task == 'asdf'
    assert await task2 == 'asdf'
