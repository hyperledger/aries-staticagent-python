import aiohttp

import crypto

from .agent import Agent

class StaticAgentConnection:
    def __init__(self, endpoint, their_vk, my_vk, my_sk):
        self.endpoint = endpoint
        self.their_vk = their_vk
        self.my_vk = my_vk
        self.my_sk = my_sk

        self._agent = Agent()

    def route(self, msg_type):
        """ Wrap Agent.route """
        return self._agent.route(msg_type)

    async def handle(self, packed_message):
        """ Unpack and handle message. """
        msg = await crypto.unpack_message(packed_message, self.my_vk, self.my_sk)
        await self._agent.handle(msg)

    async def send(self, msg):
        packed_msg = await crypto.pack_message(
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
