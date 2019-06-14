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

    async def send(self, msg):
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

    def send_blocking(self, msg):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.send(msg))
