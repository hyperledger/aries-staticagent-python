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
