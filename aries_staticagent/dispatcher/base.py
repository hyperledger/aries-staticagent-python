"""BaseDispatcher."""

from abc import ABC, abstractmethod

from ..message import Message


class Dispatcher(ABC):
    """Dispatcher base class."""

    @abstractmethod
    async def dispatch(self, msg: Message, *args, **kwargs):
        """Dispatch a message."""
