Version 0.5.0 (2019-10-21)
==========================

## Highlights

- **Add return route support.**
- **Add mechanism for directly awaiting a message, bypassing regular dispatch.**
  This makes it possible to treat messages more like a return-response model and
  significantly simplifies some flows.

## Detailed Changes

### General improvements

- Favor named arguments over keyword arguments where possible.

### Examples

- Added a [return route server example](examples/return_route_server.py),
  intended to be run with the corresponding client, to demonstrate return route
  support.
- Added a [return route client example](examples/return_route_client.py),
  intended to be run with the corresponding server, to demonstrate return route
  support.
- Removed original `cron_returnroute` example.

### Improvements to StaticConnection

- Add construct for conditionally awaiting a message on the connection,
  bypassing regular dispatch. As a result, two new methods are defined on
  `StaticConnection`: `await_message`, and `send_and_await_reply`. See [return
  route client example](examples/return_route_client.py)
- Add Reply construct to support return routing while keeping transport
  decoupled from the library. See [return route server
  example](examples/return_route_server.py).
- Add `MessageUndeliverable` Exception, raised when no endpoint or return route
  is currently available for the connection or other errors with the connection
  are encountered.
- Add support for unpacking plaintext messages.
- Better error handling in `send`.

### Improvements to Dispatcher

- Add `remove_handler` method.


Version 0.4.0 (2019-09-20)
==========================

## Highlights

- **Switch to PyNacl instead of PySodium.** PyNacl includes pre-built binary
  packages of `libsodium`; this switch means removing the dependency of
  `libsodium` being installed on the system.
- **`Module` and route definition rewrite.** The Module system has been
  significantly improved, allowing for cleaner and more flexible module
  definitions.

## Detailed Changes

### Improvements to Static (Agent) Connection

- Rename to `StaticConnection`.
- Reorder parameter into slightly more natural order. (Breaking change)
- Split out pack and unpack functionality into separate functions for a little
  added flexibility and simpler testing.
- `route` and `route_module` no longer simply wrap a dispatcher method. These
  methods are now responsible for creating Handlers corresponding to the route
  or routes defined by a module. See below for more on Dispatcher and Handler
  changes/additions.


### Improvements to Crypto

- Switch to PyNacl instead of PySodium.
- Add field signing and verification helpers.


### Improvements to Module

Overhauled route definitions (breaking changes):
- Use `@route` to define a route (instead of `@route_def`).
- No implicit routes. If a method of a module does not have a @route decorator,
  it will never be routed to.
- A bare `@route` will create a handler for the message type defined by
  combining the module's `DOC_URI`, `PROTOCOL`, `VERSION` and the method's name.
  Use `@route(name='...')` to specify a name that differs from the method name.
- Route a message that normally doesn't match the module's `DOC_URI`,
  `PROTOCOL`, or `VERSION` with `@route(doc_uri='...', protocol='...',
  version='...')`. If any of these keyword arguments are not specified, the
  module's defaults are used. You can also include name, as in the previous
  example, to specify a name that differs from the method name.
- `@route('<raw_type_string>')` will also work.


### Improvements to Dispatcher

- Altered Dispatcher to operate on "Handlers" rather than simple type routes and
  modules. This improves handler selection and provides an overall cleaner
  interface.


### Added Handler

- Relatively simple container used to help map a Type to a handler function.


### Added Type

- Object used for representing the @type string.
- Allows for comparing types, better version information.
- Reduced code duplication across Message, Module, and Dispatcher.


### Examples

- Cleaned up all examples.
- Added example for using a Module and web server.


Version 0.3.0 (2019-07-25)
==========================

This update includes many backported updates from the Aries Protocol Test Suite
"agent core" which was originally derived from this library.

Potentially Breaking Changes
----------------------------
- Messages with malformed message types will raise an `InvalidMessage` exception
  instead of `InvalidMessageType`.
- `Semver` class moved from `module` to `utils`.

Additions
---------
- Added `route_module()` to `StaticAgentConnection`.
- Added `clear_routes()` and `clear_modules()` to `StaticAgentConnection`.
- `StaticAgentConnection.__init__()` can now take the raw bytes of keys as well
    as base58 strings.
- [Message Trust Contexts](aries_staticagent/mtc.py);
  `StaticAgentConnection.handle()` will add contexts as appropriate. See [the
  tests](tests/test_mtc.py) for examples of querying or adding to these
  contexts.
- More tests
