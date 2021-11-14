"""
Dispatcher that stores messages in a queue and provides handle to retrieve
stored messages.
"""

import asyncio
from functools import partial
from typing import Any, Callable, List, Mapping, NamedTuple, Optional, Sequence, Union

from . import Dispatcher
from ..message import Message, MsgType
from ..operators import is_reply_to, msg_type_is


class QueueEntry(NamedTuple):
    msg: Message
    args: Sequence[Any]
    kwargs: Mapping[str, Any]


class MsgQueue:
    def __init__(
        self,
        *,
        condition: Callable[[Message], bool] = None,
        dispatcher: Dispatcher = None
    ):
        self._queue: List[QueueEntry] = []
        self._cond = asyncio.Condition()
        self.condition = condition
        self.dispatcher = dispatcher

    def _first_matching_index(self, condition: Callable):
        for index, entry in enumerate(self._queue):
            if condition(entry.msg):
                return index
        return None

    async def _get(self, condition: Callable = None) -> Message:
        """Retrieve a message from the queue."""
        while True:
            async with self._cond:
                # Lock acquired
                if not self._queue:
                    # No items on queue yet so we need to wait for items to show up
                    await self._cond.wait()

                if not self._queue:
                    # Another task grabbed the value before we got to it
                    continue

                if not condition:
                    # Just get the first message
                    return self._queue.pop().msg

                # Return first matching item, if present
                match_idx = self._first_matching_index(condition)
                if match_idx is not None:
                    return self._queue.pop(match_idx).msg

    async def get(self, condition: Callable = None, *, timeout: int = 5) -> Message:
        """Retrieve a message from the queue."""
        return await asyncio.wait_for(self._get(condition), timeout)

    def get_all(self, condition: Callable = None) -> Sequence[Message]:
        """Return all messages matching a given condition."""
        messages = []
        if not self._queue:
            return messages

        if not condition:
            messages = [entry.msg for entry in self._queue]
            self._queue.clear()
            return messages

        # Store not matched in order
        filtered = []
        for entry in self._queue:
            if condition(entry.msg):
                messages.append(entry.msg)
            else:
                filtered.append(entry)

        # Original queue - matching
        self._queue[:] = filtered
        return messages

    def get_nowait(self, condition: Callable = None) -> Optional[Message]:
        """Return a message from the queue without waiting."""
        if not self._queue:
            return None

        if not condition:
            return self._queue.pop().msg

        match_idx = self._first_matching_index(condition)
        if match_idx is not None:
            return self._queue.pop(match_idx).msg

        return None

    async def put(self, msg: Message, *args, **kwargs):
        """Push a message onto the queue and notify waiting tasks."""
        if not self.condition or self.condition(msg):
            async with self._cond:
                self._queue.append(QueueEntry(msg, args, kwargs))
                self._cond.notify_all()
        elif self.dispatcher:
            await self.dispatcher.dispatch(msg, *args, **kwargs)

    async def flush(self) -> Sequence[Message]:
        """Clear queue, passing remaining messages to another dispatcher if present."""
        if self.dispatcher:
            for entry in self._queue:
                await self.dispatcher.dispatch(entry.msg, *entry.args, **entry.kwargs)
        final = self._queue.copy()
        self._queue.clear()
        return [entry.msg for entry in final]

    async def with_type(self, msg_type: Union[str, MsgType], **kwargs) -> Message:
        """Retrieve a message with type matching given value."""
        return await self.get(partial(msg_type_is, msg_type), **kwargs)

    async def reply_to(self, msg: Message, **kwargs) -> Message:
        """Retrieve a message that is a reply to the given message."""
        return await self.get(partial(is_reply_to, msg), **kwargs)


class QueueDispatcher(Dispatcher):
    def __init__(self, queue: MsgQueue = None):
        self.queue = queue or MsgQueue()

    async def dispatch(self, msg: Message, *args, **kwargs):
        """Store message in queue."""
        await self.queue.put(msg, *args, **kwargs)
