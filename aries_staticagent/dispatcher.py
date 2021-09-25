""" Dispatcher """
import logging
from typing import Callable, Sequence

from sortedcontainers import SortedSet

from .message import Message, MsgType


class NoRegisteredHandlerException(Exception):
    """Thrown when message has no registered handlers"""


class Handler:  # pylint: disable=too-few-public-methods
    """A Message Handler."""

    __slots__ = ("type", "handler", "context")

    def __init__(self, msg_type: MsgType, handler: Callable):
        if not isinstance(msg_type, MsgType):
            raise ValueError("type parameter must be MsgType object")
        if not callable(handler):
            raise ValueError("handler parameter must be callable")

        self.type = msg_type
        self.handler = handler

    async def run(self, msg, *args, **kwargs):
        """Call the handler with message."""
        return await self.handler(msg, *args, **kwargs)


class Dispatcher:
    """One of the fundamental aspects of an agent; responsible for dispatching
    messages to appropriate handlers.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.handlers = {}
        self.handler_versions = {}

    def clear_handlers(self):
        """Clear routes"""
        self.handlers.clear()
        self.handler_versions.clear()

    def add_handler(self, handler: Handler):
        """Add a handler to routing tables."""
        self.handlers[handler.type.normalized] = handler

        key = (handler.type.doc_uri, handler.type.protocol, handler.type.name)
        if key not in self.handler_versions:
            self.handler_versions[key] = SortedSet()
        self.handler_versions[key].add(handler.type.version_info)

    def add_handlers(self, handlers: Sequence[Handler]):
        """Add a list of handlers to routing tables."""
        for handler in handlers:
            self.add_handler(handler)

    def remove_handler(self, handler):
        """Remove handler from routing tables."""
        if handler.type not in self.handlers:
            raise NoRegisteredHandlerException("Handler is not registered")

        del self.handlers[handler.type]
        key = (handler.type.doc_uri, handler.type.protocol, handler.type.name)
        self.handler_versions[key].remove(key)
        if not self.handler_versions[key]:
            del self.handler_versions[key]

    def select_handler(self, msg: Message):
        """Find the closest appropriate module for a given message."""
        key = (msg.type.doc_uri, msg.type.protocol, msg.type.name)
        if key not in self.handler_versions:
            return None

        registered_version_set = self.handler_versions[key]
        for version in reversed(registered_version_set):
            if msg.type.version_info.major == version.major:
                handler_type = MsgType.unparse(
                    msg.type.doc_uri, msg.type.protocol, version, msg.type.name
                )
                return self.handlers[handler_type]

            if msg.type.version_info.major > version.major:
                break

        return None

    async def dispatch(self, msg: Message, *args, **kwargs):
        """Dispatch message to handler."""
        handler = self.select_handler(msg)
        if not handler:
            raise NoRegisteredHandlerException(
                "No suitable handler for message of type {}".format(msg.type)
            )

        return await handler.run(msg, *args, **kwargs)
