---
layout: default
title: Aries Static Agent - Python
---

The Aries Static Agent Library aims to be as light and simple as possible but no
simpler. The following is one of several included examples.

```python
{% include examples/cron.py %}
```

More than half of this example is boilerplate to run an agent from the command
line with no prior configuration. In `main` we see that opening a connection and
sending a DIDComm message is just a few lines of code.

The previous example shows a static agent that runs once and shuts down and does
not listen for incoming messages. Let's take a look at another example that can
accept and process messages asynchronously over HTTP -- a [BasicMessage][1]
"echo server" that repeats back the contents of the message it received:

```python
{% include examples/webserver_aiohttp.py %}
```

As with the previous example we see the same CLI boilerplate but also an example
of the `route` decorator. Inspired by [flask's simple HTTP handler
declaration][2], a DIDComm message handler can simply be decorated with
`StaticConnection.route('<msg_type>')` and messages will be appropriately
dispatched to the handler. In our case, our handler inspects the message
contents and asynchronously sends another basic message back on the connection.

In `main`, we see a simple [AIOHTTP][3] web server running with a single handler
for posted messages to our web root. To begin handling by the connection,
`StaticConnection.handle` is called with the raw bytes read from the HTTP body.

WIP

[1]: https://github.com/hyperledger/aries-rfcs/tree/master/features/0095-basic-message
[2]: https://flask.palletsprojects.com/en/1.1.x/quickstart/#routing
[3]: https://docs.aiohttp.org/en/stable/
