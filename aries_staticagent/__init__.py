import aiohttp
import asyncio

from .agent import Agent
from .messages import Message
from . import crypto

class StaticAgentConnection:
    def __init__(self, endpoint, their_vk, my_vk, my_sk):
        self.endpoint = endpoint
        self.their_vk = crypto.b58_to_bytes(their_vk)
        self.my_vk = crypto.b58_to_bytes(my_vk)
        self.my_sk = crypto.b58_to_bytes(my_sk)

        self._agent = Agent()

    def route(self, msg_type):
        """ Wrap Agent.route """
        return self._agent.route(msg_type)

    async def handle(self, packed_message):
        """ Unpack and handle message. """
        (msg, sender_vk, recip_vk) = crypto.unpack_message(packed_message, self.my_vk, self.my_sk)
        msg = Message.deserialize(msg)
        await self._agent.handle(msg)

    async def send_async(self, msg):
        #TODO Support WS
        if isinstance(msg, dict):
            msg = Message(msg)

        packed_msg = crypto.pack_message(
            msg.serialize(),
            [self.their_vk],
            self.my_vk,
            self.my_sk
        )

        async with aiohttp.ClientSession() as session:
            headers = {'content-type': 'application/ssi-agent-wire'}
            async with session.post(self.endpoint, data=packed_msg, headers=headers) as resp:
                if resp.status != 202:
                    await self.handle(await resp.read())

    def send(self, msg):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.send(msg))


def keygen():
    """ Convenience method for generating and printing a keypair and DID.
        DID is generated from the first 16 bytes of the VerKey.
    """
    vk_bytes, sk_bytes = crypto.create_keypair()

    # TODO implement DID creation as described in the Peer DID Spec
    # Link: https://openssi.github.io/peer-did-method-spec/index.html
    did_bytes = vk_bytes[0:16]

    vk = crypto.bytes_to_b58(vk_bytes)
    sk = crypto.bytes_to_b58(sk_bytes)
    did = crypto.bytes_to_b58(did_bytes)

    print('For full agent:\n\tDID: {}\n\tVK: {}\n'.format(did, vk))
    print('For static agent:\n\tVK: {}\n\tSK: {}'.format(vk, sk))
