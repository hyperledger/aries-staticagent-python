# Static Agent Library

[![pypi release](https://img.shields.io/pypi/v/aries-staticagent)](https://pypi.org/project/aries-staticagent/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Tests](https://github.com/hyperledger/aries-staticagent-python/actions/workflows/tests.yml/badge.svg)](https://github.com/hyperledger/aries-staticagent-python/actions/workflows/tests.yml)


This repo contains an example Aries Static Agent Library in Python.

A static agent is a form of agent that can speak DIDComm at a basic level but its keys and
connections are configured statically. Static Agents have a direct relationship with a single full
agent. Static Agents do not have a wallet.

Examples of static agents may include:
- Remote administration interface for an agent
- IoT devices
- [Relays][1]
- OpenAPI to DIDComm translator

A static agent's configuration minimally consists of:
- Its own public and private key
- The public key of its full agent counterpart
- The endpoint of its full agent counterpart

_**It is up to you to secure your static agent's configuration.**_ The examples included in this
repository use command line arguments or environment variables to configure the agent for simplicity
and demonstration purposes only. _**This is not recommended for production environments.**_

This library makes as few assumptions about it's running environment as possible. This includes
few dependencies, assumptions about web frameworks, etc.

[1]: https://github.com/hyperledger/aries-rfcs/tree/master/concepts/0046-mediators-and-relays#summary

Quick Start Guide
-----------------

#### Requirements

- Python 3.6 or higher

#### Running the included examples

You will need to pair the static agent with a full agent capable of basic DIDComm to complete the
examples. The [Indy Python Reference Agent][3] can be used as the full agent for these examples.

Create and activate python virtual environment:
```sh
$ python3 -m venv env
$ source env/bin/activate
```

Install dependencies and the library into the virtual environment:
```sh
$ pip install -e .
```

> If you want to run the included tests, install the `test` feature with pip:
> `pip install -e .[test]`

Execute `keygen()`:
```sh
$ python -c "import aries_staticagent; aries_staticagent.keygen()"

For full agent:
        DID: <Base58 encoded DID>
        VK: <Base58 encoded verkey>

For static agent:
        VK: <the same Base58 encoded verkey>
        SK: <Base58 encoded sigkey>
```

As the output implies, the first section is intended to be entered in on the full agent to configure
a static connection. The second section is used to configure the static agent. The `verkey` (VK) in
the first and second section are the _same_ key, representing the key the static agent will use
for the connection. The `keygen` script does _not_ generate the keys that the full agent will use.

If using the [Indy Python Reference Agent][3], open the web interface and
click `Add Static Connection`. Enter the information output by `keygen.py` and a label of your
choice. The endpoint of the static agent is optional and must match the hostname and port you
configure for the static agent if running the web server example. After clicking `Add`, a new
dialogue window will open with the information needed to now start up the static agent.

If you are using another agent that supports configuring a static connection, follow the
instructions provided by that agent.

Start the static agent (in this case, `exapmles/cron.py`):
```sh
$ python examples/cron.py --endpoint <the endpoint of the full agent> \
$ --endpointkey <the verkey output by the full agent> \
$ --mypublickey <the verkey output by keygen.py> \
$ --myprivatekey <the sigkey output by keygen.py>
```

In the full agent's BasicMessages, you should now see a message sent from the static agent script.

> TODO: Include screencast of running the example with the Indy Python Reference Agent

[2]: https://download.libsodium.org/doc/installation
[3]: https://github.com/hyperledger/indy-agent/tree/master/python

Using the library
-----------------

Refer to the `examples` directory for complete working examples of using this library.

### Setting up a Static Agent Connection

```python
from aries_staticagent import Connection

# endpoint, endpointkey, mypublickey, myprivatekey key are obtained through some form of static
# configuration

conn = Connection((mypublickey, myprivatekey), their_vk=endpointkey, endpoint=endpoint)
```

This will open a static connection with the full agent reachable at `endpoint` and messages packed
for `endpointkey`.

### Sending a message to the Full Agent

With the static agent connection `a`, to send messages to the full agent:

```python
conn.send({
    "@type": "https://didcomm.org/basicmessage/1.0/message",
    "~l10n": {"locale": "en"},
    "sent_time": utils.timestamp(),
    "content": "The Cron Script has been executed."
})
```

An asynchronous method is also provided:
```python
await conn.send_async({
    "@type": "https://didcomm.org/basicmessage/1.0/message",
    "~l10n": {"locale": "en"},
    "sent_time": utils.timestamp(),
    "content": "The Cron Script has been executed."
})
```

### Receiving messages from the Full Agent

Transport mechanisms are completely decoupled from the Static Agent Library. This is intended to
allow library consumers to choose which transport is appropriate for their use case. The
`examples/webserver_aiohttp.py` example shows how one might use the `aiohttp` library as an inbound
transport mechanism for the static agent:

```python
from aiohttp import web
from aries_staticagent import Connection, utils

# ... Configuration omitted

# Create static agent connection
conn = Connection((args.mypublickey, args.myprivatekey), their_vk=args.endpointkey, endpoint=args.endpoint)

# Register a handler for the basicmessage/1.0/message message type
@conn.route("https://didcomm.org/basicmessage/1.0/message")
async def basic_message(msg, conn):
    # Respond to the received basic message by sending another basic message back
    await conn.send_async({
        "@type": "https://didcomm.org/basicmessage/1.0/message",
        "~l10n": {"locale": "en"},
        "sent_time": utils.timestamp(),
        "content": "You said: {}".format(msg['content'])
    })


# aiohttp request handler
async def handle(request):
    # Read request body and pass to Connection.handle
    await conn.handle(await request.read())
    raise web.HTTPAccepted()

# Register aiohttp request handler
app = web.Application()
app.add_routes([web.post('/', handle)])

# Start the web server
web.run_app(app, port=args.port)
```

As seen in this example, registering a handler for a DIDComm message is done using the
`@conn.route('<message_type>')` decorator. Passing raw, unpackaged messages to the static agent
connection over the decoupled transport mechanism is done by calling `conn.handle(<raw message>)`.

Static agents can only unpack messages sent by the full agent.

### Unresolved Questions
* Are we allowing Agent routing between a static agent and it's full agent?
  * We're starting with no and will revisit in the future.

## License

[Apache License Version 2.0](https://github.com/hyperledger/aries-staticagent-python/blob/main/LICENSE)
