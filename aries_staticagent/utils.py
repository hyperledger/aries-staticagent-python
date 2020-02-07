""" General utils """
import datetime
from typing import Union, Optional

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


async def http_send(msg: bytes, endpoint: str) -> Optional[bytes]:
    """Send over HTTP."""
    async with aiohttp.ClientSession() as session:
        headers = {'content-type': 'application/ssi-agent-wire'}
        async with session.post(
                endpoint,
                data=msg,
                headers=headers) as resp:

            body = await resp.read()
            if resp.status != 200 and resp.status != 202:
                raise Exception(
                    'Error while sending message: {}'.format(
                        resp.status
                    )
                )
            if resp.status == 200 and body:
                return body

    return None


# TODO: Persist websocket until return_route = None sent
async def ws_send(msg: bytes, endpoint: str) -> Optional[bytes]:
    """Send over WS.

    This send method is experimental and should not be used for more than
    experimenting. This method is very inefficient as it throws out the created
    websocket after receiving only a single msg.
    """
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(endpoint) as sock:
            await sock.send_bytes(msg)
            async for msg in sock:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    return msg.data

                if msg.type == aiohttp.WSMsgType.ERROR:
                    raise Exception(
                        'ws connection closed with exception %s' %
                        sock.exception()
                    )
