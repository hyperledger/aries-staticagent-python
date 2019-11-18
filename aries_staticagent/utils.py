""" General utils """
import datetime
from typing import Union

from . import crypto
from .message import Message


def timestamp():
    """ return a timestamp. """
    return datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc
    ).isoformat(' ')


def ensure_key_bytes(key: Union[bytes, str]):
    """Ensure key is formatted as bytes."""
    if isinstance(key, bytes):
        return key
    if isinstance(key, str):
        return crypto.b58_to_bytes(key)

    raise TypeError('key must be bytes or str')


def ensure_key_b58(key: Union[bytes, str]):
    """Ensure key is formatted as b58 string."""
    if isinstance(key, bytes):
        return crypto.bytes_to_b58(key)
    if isinstance(key, str):
        return key

    raise TypeError('key must be bytes or str')


def forward_msg(to: Union[bytes, str], msg: dict):
    """Return a forward message."""
    return Message({
        '@type': 'did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/routing/1.0/forward',
        'to': ensure_key_b58(to),
        'msg': msg
    })
