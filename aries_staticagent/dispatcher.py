""" Dispatcher """
import logging
from typing import Callable, Sequence

from sortedcontainers import SortedSet

from .message import Message, parse_type_info
from .utils import Semver


class NoRegisteredHandlerException(Exception):
    """ Thrown when message has no registered handlers """


class Handler:
    """ A Message Handler. """
    __slots__ = (
        'doc_uri',
        'protocol',
        'version',
        'name',
        'type',
        'handler',
        'context'
    )

    def __init__(self, handler: Callable, **kwargs):
        self.doc_uri = kwargs.get('doc_uri')
        self.protocol = kwargs.get('protocol')
        self.version = kwargs.get('version')
        self.name = kwargs.get('name')
        self.type = kwargs.get('type')

        self.handler = handler
        self.context = kwargs.get('context')

        if self.version and isinstance(self.version, str):
            self.version = Semver.from_str(self.version)

        if self.type:
            self.doc_uri, self.protocol, version_str, self.name = \
                parse_type_info(kwargs['type'])
            self.version = Semver.from_str(version_str)

        self.type = '{}{}/{}/{}'.format(
            self.doc_uri,
            self.protocol,
            str(self.version),
            self.name
        )

        if self.doc_uri is None or self.protocol is None or \
                self.version is None or self.name is None:
            raise ValueError(
                'Handler must be given type or '
                'doc_uri, protocol, version, and name'
            )

    async def run(self, msg, *args, **kwargs):
        """ Call the handler with message. """
        args = [msg, *args] if not self.context else [self.context, msg, *args]
        return await self.handler(*args, **kwargs)


class Dispatcher:
    """ One of the fundamental aspects of an agent responsible for dispatching
        messages to appropriate handlers.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.handlers = {}
        self.handler_versions = {}

    def clear_handlers(self):
        """ Clear routes """
        self.handlers.clear()
        self.handler_versions.clear()

    def add_handler(self, handler):
        """ Add a handler to routing tables. """
        self.handlers[handler.type] = handler

        key = (handler.doc_uri, handler.protocol, handler.name)
        if key not in self.handler_versions:
            self.handler_versions[key] = SortedSet()
        self.handler_versions[key].add(handler.version)

    def add_handlers(self, handlers: Sequence[Handler]):
        """ Add a list of handlers to routing tables. """
        for handler in handlers:
            self.add_handler(handler)

    def select_handler(self, msg: Message):
        """ Find the closest appropriate module for a given message.
        """
        key = (msg.doc_uri, msg.protocol, msg.name)
        if key not in self.handler_versions:
            return None

        registered_version_set = self.handler_versions[key]
        for version in reversed(registered_version_set):
            if msg.version_info.major == version.major:
                full_type = '{}{}/{}/{}'.format(
                    msg.doc_uri,
                    msg.protocol,
                    str(version),
                    msg.name
                )
                return self.handlers[full_type]

            if msg.version_info.major > version.major:
                break

        return None

    async def dispatch(self, msg: Message, *args, **kwargs):
        """ Dispatch message to handler. """
        handler = self.select_handler(msg)
        if not handler:
            raise NoRegisteredHandlerException(
                'No suitable handler for message of type {}'.format(
                    msg.type
                )
            )

        await handler.run(msg, *args, **kwargs)
