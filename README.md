Static Agent Library
====================

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
- `libsodium` version 1.0.15 or higher

> The most recent version of `libsodium` available in package repositories for some operating
> systems may not meet this requirement (notably, Ubuntu 16.04). Additionally, pre-built binaries
> may be altogether unavailable for your operating system. If possible, follow the standard
> installation method for your OS; otherwise, follow the instructions listed [here][2].
>
> We recognize that this dependency may be troublesome in some circumstances; we are open to/looking
> for appropriate alternatives.

#### Running the included examples

You will need to pair the static agent with a full agent capable of basic DIDComm to complete the
examples. The [Indy Python Reference Agent][3] can be used as the full agent for these examples.

Create and activate python virtual environment:
```sh
$ python3 -m venv env
$ source env/bin/activate
```

Install requirements:
```sh
$ pip install -r requirements.txt
```

Install the library into the virtual environment:
```sh
$ pip install -e .
```

Execute the included `keygen.py`:
```sh
$ python keygen.py

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
from aries_staticagent import StaticAgentConnection

# endpoint, endpointkey, mypublickey, myprivate key are obtained through some form of static
# configuration

a = StaticAgentConnection(endpoint, endpointkey, mypublickey, myprivatekey)
```

This will open a static connection with the full agent reachable at `endpoint` and messages packed
for `endpointkey`.

### Sending a message to the Full Agent

With the static agent connection `a`, to send messages to the full agent:

```python
a.send_blocking({
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message",
        "~l10n": {"locale": "en"},
        "sent_time": utils.timestamp(),
        "content": "The Cron Script has been executed."
})
```

An asynchronous method is also provided:
```python
await a.send({
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message",
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
from aries_staticagent import StaticAgentConnection, utils

# ... Configuration omitted

# Create static agent connection
a = StaticAgentConnection(args.endpoint, args.endpointkey, args.mypublickey, args.myprivatekey)

# Register a handler for the basicmessage/1.0/message message type
@a.route("did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message")
async def basic_message(agent, msg):
    # Respond to the received basic message by sending another basic message back
    await a.send({
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/basicmessage/1.0/message",
        "~l10n": {"locale": "en"},
        "sent_time": utils.timestamp(),
        "content": "You said: {}".format(msg['content'])
    })


# aiohttp request handler
async def handle(request):
    # Read request body and pass to StaticAgentConnection.handle
    await a.handle(await request.read())
    raise web.HTTPAccepted()

# Register aiohttp request handler
app = web.Application()
app.add_routes([web.post('/', handle)])

# Start the web server
web.run_app(app, port=args.port)
```

As seen in this example, registering a handler for a DIDComm message is done using the
`@a.route('<message_type>')` decorator. Passing raw, unpackaged messages to the static agent
connection over the decoupled transport mechanism is done by calling `a.handle(<raw message>)`.

Static agents can only unpack messages sent by the full agent.

### Unresolved Questions
* Are we allowing Agent routing between a static agent and it's full agent?
  * How about we start with 'no', and revisit in the future if needed?
