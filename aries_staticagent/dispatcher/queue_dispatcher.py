"""Dispatcher that stores messages in a queue."""

import logging
from typing import Any, Callable, Mapping, NamedTuple, Optional, Sequence, Union

from async_selective_queue import AsyncSelectiveQueue, Select

from . import Dispatcher
from ..message import Message, MsgType
from ..operators import is_reply_to, msg_type_is


LOGGER = logging.getLogger(__name__)


class QueueEntry(NamedTuple):
    """Entry in Queue."""

    msg: Message
    args: Sequence[Any]
    kwargs: Mapping[str, Any]


class QueueDispatcher(Dispatcher):
    """Dispatcher that holds messages on Queue.

    This dispatcher can optionally delegate processing of messages to a "primary"
    dispatcher when given conditions.
    """

    class QueueAccessor:
        """Helper class for interacting with Queue."""

        def __init__(self, queue: AsyncSelectiveQueue[QueueEntry]):
            """Init accessor."""
            self.queue = queue

        async def get(self, select: Optional[Select] = None, **kwargs) -> Message:
            """Get a message from the queue."""
            return (await self.queue.get(select, **kwargs)).msg

        def get_all(self, select: Optional[Select] = None) -> Sequence[Message]:
            """Get all messages from the queue."""
            return [entry.msg for entry in self.queue.get_all(select)]

        def get_nowait(self, select: Optional[Select] = None) -> Optional[Message]:
            """Get a message from the queue if there are any without waiting."""
            entry = self.queue.get_nowait(select)
            return entry.msg if entry else None

        async def with_type(self, msg_type: Union[str, MsgType], **kwargs) -> Message:
            """Retrieve a message with type matching given value."""
            return (
                await self.queue.get(
                    lambda entry: msg_type_is(msg_type, entry.msg), **kwargs
                )
            ).msg

        async def reply_to(self, msg: Message, **kwargs) -> Message:
            """Retrieve a message that is a reply to the given message."""
            return (
                await self.queue.get(
                    lambda entry: is_reply_to(msg, entry.msg), **kwargs
                )
            ).msg

    def __init__(
        self,
        *,
        queue: Optional[AsyncSelectiveQueue[QueueEntry]] = None,
        dispatcher: Optional[Dispatcher] = None,
        condition: Optional[Callable[[Message], bool]] = None
    ):
        """Init dispatcher."""
        self.queue = queue or AsyncSelectiveQueue()
        self.dispatcher = dispatcher
        self.condition = condition

    async def dispatch(self, msg: Message, *args, **kwargs):
        """Store message in queue."""
        if not self.condition or self.condition(msg):
            await self.queue.put(QueueEntry(msg, args, kwargs))
        elif self.dispatcher:
            await self.dispatcher.dispatch(msg, *args, **kwargs)
        else:
            LOGGER.warning(
                "Message dropped because condition is unmet and no primary dispatcher. "
                "Message: %s",
                msg,
            )

    async def flush(self) -> Sequence[Message]:
        """Clear queue, passing remaining messages to another dispatcher if present."""
        final = self.queue.flush()
        if self.dispatcher:
            for entry in final:
                await self.dispatcher.dispatch(entry.msg, *entry.args, **entry.kwargs)

        return [entry.msg for entry in final]

    def accessor(self) -> QueueAccessor:
        """Return a new accessor over the queue."""
        return self.QueueAccessor(self.queue)
