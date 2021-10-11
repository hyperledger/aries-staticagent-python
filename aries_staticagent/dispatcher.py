""" Dispatcher """
import logging
from typing import Callable, Dict, Mapping, Optional, Union

from sortedcontainers import SortedSet

from .message import Message, MsgType


class NoRegisteredHandlerException(Exception):
    """Thrown when message has no registered handlers"""


class Dispatcher:
    """One of the fundamental aspects of an agent; responsible for dispatching
    messages to appropriate handlers.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.handlers: Dict[str, Callable] = {}
        self.handler_versions = {}

    def clear_handlers(self):
        """Clear routes"""
        self.handlers.clear()
        self.handler_versions.clear()

    def add_handler(self, msg_type: Union[str, MsgType], handler: Callable):
        """Add a handler to routing tables."""
        if not isinstance(msg_type, MsgType):
            msg_type = MsgType(msg_type)

        self.handlers[msg_type.normalized] = handler

        key = (msg_type.doc_uri, msg_type.protocol, msg_type.name)
        if key not in self.handler_versions:
            self.handler_versions[key] = SortedSet()
        self.handler_versions[key].add(msg_type.version_info)

    def add_handlers(self, handlers: Mapping[MsgType, Callable]):
        """Add a list of handlers to routing tables."""
        for msg_type, handler in handlers.items():
            self.add_handler(msg_type, handler)

    def remove_handler(self, msg_type: MsgType):
        """Remove handler from routing tables."""
        if msg_type.normalized not in self.handlers:
            raise NoRegisteredHandlerException("Handler is not registered")

        del self.handlers[msg_type.normalized]
        key = (msg_type.doc_uri, msg_type.protocol, msg_type.name)
        self.handler_versions[key].remove(key)
        if not self.handler_versions[key]:
            del self.handler_versions[key]

    def select_handler(self, msg: Message) -> Optional[Callable]:
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
                return self.handlers[handler_type.normalized]

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

        return await handler(msg, *args, **kwargs)
