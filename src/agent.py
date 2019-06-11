""" Agent """
from contextlib import suppress
import asyncio
import logging

from sortedcontainers import SortedSet

from compat import create_task
from config import Config
from hooks import self_hook_point, hook
from indy_sdk_utils import open_wallet

class NoRegisteredRouteException(Exception):
    """ Thrown when message has no registered handlers """

class MessageProcessingFailed(Exception):
    """ Thrown when main message processing loop fails to proccess a message """

class Agent:
    """ Agent """
    # TODO Move hook stuff into Hookable
    hooks = {}

    # Constructors and Set up {{{

    def __init__(self):
        # TODO Move hook stuff into Hookable
        self.hooks = Agent.hooks.copy() # Copy statically configured hooks

        # base fields
        self.config = None
        self.wallet_handle = None
        self.logger = logging.getLogger(__name__)
        self.conductor = None

        # message routing
        self.routes = {}
        self.modules = {} # Protocol identifier URI to module
        self.module_versions = {} # Doc URI + Protocol to list of Module Versions

        # async handling
        self.main_task = None

    @classmethod
    async def from_config(cls, config: Config):
        agent = cls()
        agent.config = config
        agent.logger.setLevel(config.log_level)
        agent.wallet_handle = await open_wallet(
            agent.config.wallet,
            agent.config.passphrase,
            agent.config.ephemeral
        )
        return agent

    def set_conductor(self, conductor):
        self.conductor = conductor

    # }}}

    # TODO Move hook stuff into Hookable
    def hook(self, hook_name):
        return hook(self, hook_name)

    # TODO Move hook stuff into Hookable
    def register_hook(self, hook_name, hook_fn):
        hook(self, hook_name)(hook_fn)

    # Async Handling {{{

    async def start(self):
        conductor_task = create_task(self.conductor.start())
        main_loop = create_task(self._loop())
        self.main_task = asyncio.gather(conductor_task, main_loop)

        await self.main_task

    async def shutdown(self):
        await self.conductor.shutdown()
        self.main_task.cancel()
        with suppress(asyncio.CancelledError):
            await self.main_task

    # }}}

    # Main Loop {{{

    async def _do_loop(self):
        msg = await self.conductor.recv()
        self.logger.debug('Handling Message: %s', msg.serialize())

        try:
            await self.handle(msg)
        except Exception as err:
            self.logger.exception(
                'Message processing failed\nMessage: %s\nError: %s',
                msg.serialize(),
                err
            )

            if self.config.halt_on_error:
                raise MessageProcessingFailed(
                    'Failed while processing message: {}'.format(msg.serialize())
                ) from err
        finally:
            self.logger.debug('Message handled: %s', msg.serialize())
            await self.conductor.message_handled()

    async def _loop(self):
        if self.config.num_messages == -1:
            while True:
                await self._do_loop()
        else:
            for _ in range(0, self.config.num_messages):
                await self._do_loop()

    # }}}

    # Message Routing {{{

    def route(self, msg_type):
        """ Register route decorator. """
        def register_route_dec(func):
            self.logger.debug('Setting route for %s to %s', msg_type, func)
            self.routes[msg_type] = func
            return func

        return register_route_dec

    def route_module(self, module_instance):
        # Register module
        self.modules[type(module_instance).protocol_identifer_uri] = module_instance

        # Store version selection info
        version_info = type(module_instance).version_info
        qualified_protocol = type(module_instance).qualified_protocol
        if not qualified_protocol in self.module_versions:
            self.module_versions[qualified_protocol] = SortedSet()

        self.module_versions[qualified_protocol].add(version_info)

    @self_hook_point
    def get_closest_module_for_msg(self, msg):
        if not msg.qualified_protocol in self.module_versions:
            return None

        registered_version_set = self.module_versions[msg.qualified_protocol]
        for version in reversed(registered_version_set):
            if msg.version_info.major == version.major:
                return self.modules[msg.qualified_protocol + '/' + str(version)]
            if msg.version_info.major > version.major:
                break

        return None

    @self_hook_point
    async def handle(self, msg, *args, **kwargs):
        """ Route message """
        if msg.type in self.routes:
            await self.routes[msg.type](self, msg, *args, **kwargs)
            return

        module_instance = self.get_closest_module_for_msg(msg)
        if module_instance:

            if hasattr(module_instance, 'routes'):
                await module_instance.routes[msg.type](module_instance, self, msg, *args, **kwargs)
                return

            # If no routes defined in module, attempt to route based on method matching
            # the message type name
            if hasattr(module_instance, msg.short_type) and \
                    callable(getattr(module_instance, msg.short_type)):

                await getattr(module_instance, msg.short_type)(
                    self, #agent
                    msg,
                    *args,
                    **kwargs
                )
                return

        raise NoRegisteredRouteException

    # }}}


    # Shortcuts to Conductor {{{

    async def send(self, msg, to_key, **kwargs):
        return await self.conductor.send(msg, to_key, **kwargs)

    async def put_message(self, message):
        return await self.conductor.put_message(message)

    # }}}
