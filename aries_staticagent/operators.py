"""Operators for use in conditions and tools to use them.

These operators embody common checks on messages.
"""

import re
from typing import Callable, Pattern, Sequence, TypeVar, Union
from .message import Message, MsgType, ProtocolIdentifier


Subject = TypeVar("Subject")


def all(ops: Sequence[Callable[[Subject], bool]], subject: Subject):
    """Whether all operators evaluate to true on message."""
    for op in ops:
        if not op(subject):
            return False
    return True


def any(ops: Sequence[Callable[[Subject], bool]], subject: Subject):
    """Whether any operator evaluates to true on message."""
    for op in ops:
        if op(subject):
            return True
    return False


def msg_type_is(msg_type: Union[str, MsgType], msg: Message):
    """If msg_type == msg.type."""
    return msg_type == msg.type


def msg_type_matches(pattern: Union[str, Pattern], msg: Message):
    """If msg.type matches pattern."""
    if isinstance(pattern, str):
        pattern = re.compile(pattern)
    return pattern.match(msg.type)


def msg_type_is_compatible_with(msg_type: Union[str, MsgType], msg: Message):
    """If msg.type is compatibile with msg_type.

    Compatibility is defined as message major version matches.
    """
    if not isinstance(msg_type, MsgType):
        msg_type = MsgType(msg_type)
    return msg_type.version_info.major == msg.type.version_info.major


def in_protocol(protocol: Union[str, ProtocolIdentifier], msg: Message):
    """If msg.type is in protocol."""
    if not isinstance(protocol, ProtocolIdentifier):
        # Validate protocol str
        protocol = ProtocolIdentifier(protocol)
    return msg.type.startswith(protocol)


def is_reply_to(original: Message, msg: Message):
    """If msg.~thread.id == original.@id."""
    return msg.thread.get("thid") == original.id
