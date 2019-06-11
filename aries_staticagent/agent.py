""" Agent """
import logging

from sortedcontainers import SortedSet

class NoRegisteredRouteException(Exception):
    """ Thrown when message has no registered handlers """

class Agent:
    """ The Base of an Agent. Handles routing messages to appropriate handlers. """
    def __init__(self):
        self.routes = {}
        self.modules = {} # Protocol identifier URI to module
        self.module_versions = {} # Doc URI + Protocol to list of Module Versions
        self.logger = logging.getLogger(__name__)

    def route(self, msg_type):
        """ Register route decorator. """
        def register_route_dec(func):
            self.logger.debug('Setting route for %s to %s', msg_type, func)
            self.routes[msg_type] = func
            return func

        return register_route_dec

    def route_module(self, module_instance):
        """ Register a module for routing.
            Modules are routed to based on protocol and version. Newer versions
            are favored over older versions. Major version number must match.
        """
        # Register module
        self.modules[type(module_instance).protocol_identifer_uri] = module_instance

        # Store version selection info
        version_info = type(module_instance).version_info
        qualified_protocol = type(module_instance).qualified_protocol
        if not qualified_protocol in self.module_versions:
            self.module_versions[qualified_protocol] = SortedSet()

        self.module_versions[qualified_protocol].add(version_info)

    def get_closest_module_for_msg(self, msg):
        """ Find the closest appropriate module for a given message.
        """
        if not msg.qualified_protocol in self.module_versions:
            return None

        registered_version_set = self.module_versions[msg.qualified_protocol]
        for version in reversed(registered_version_set):
            if msg.version_info.major == version.major:
                return self.modules[msg.qualified_protocol + '/' + str(version)]
            if msg.version_info.major > version.major:
                break

        return None

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
