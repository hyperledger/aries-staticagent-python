""" General utils """
import datetime
from typing import Union, Callable, Awaitable

import aiohttp

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


FORWARD = 'did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/routing/1.0/forward'


def forward_msg(to: Union[bytes, str], msg: dict):
    """Return a forward message."""
    return Message({
        '@type': FORWARD,
        'to': ensure_key_b58(to),
        'msg': msg
    })


async def http_send(
        msg: bytes,
        endpoint: str,
        response_handler: Callable[[bytes], Awaitable[None]],
        error_handler: Callable[[str], Awaitable[None]]):
    """Send over HTTP."""
    async with aiohttp.ClientSession() as session:
        headers = {'content-type': 'application/ssi-agent-wire'}
        async with session.post(
                endpoint,
                data=msg,
                headers=headers) as resp:

            body = await resp.read()
            if resp.status != 200 and resp.status != 202:
                await error_handler(
                    'Error while sending message: {}'.format(
                        resp.status
                    )
                )
            if resp.status == 200 and body:
                await response_handler(body)
