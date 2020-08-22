"""Test included examples."""

import asyncio
from contextlib import suppress, closing
import socket
import pytest
from aiohttp import web
from aries_staticagent import StaticConnection, Keys, crypto, utils

# pylint: disable=redefined-outer-name


async def server_ready(host, port, retry_max=5):
    """Check if the subprocess has spawned the webserver yet."""
    attempt = 0

    def can_connect():
        with closing(
                socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ) as sock:
            return sock.connect_ex((host, port)) == 0

    while not can_connect():
        attempt += 1
        if attempt > retry_max:
            raise RuntimeError(
                'Could not connect to server at {}:{}'.format(host, port)
            )
        await asyncio.sleep(1)


@pytest.fixture
def example_keys():
    """Generate keys for example end of connection."""
    yield Keys(*crypto.create_keypair())


@pytest.fixture
def test_keys():
    """Generate keys for test end of connection."""
    yield Keys(*crypto.create_keypair())


@pytest.fixture
def connection(example_keys, test_keys):
    """Connection fixture."""
    return StaticConnection.from_parts(test_keys, their_vk=example_keys.verkey)


@pytest.fixture
def connection_ws(example_keys, test_keys):
    """Connection fixture with ws send."""
    return StaticConnection.from_parts(
        test_keys,
        their_vk=example_keys.verkey,
        send=utils.ws_send
    )


@pytest.fixture
async def listening_endpoint(connection, unused_tcp_port):
    """Create http server task."""

    async def handle(request):
        """aiohttp handle POST."""
        await connection.handle(await request.read())
        raise web.HTTPAccepted()

    app = web.Application()
    app.router.add_post('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', unused_tcp_port)
    server_task = asyncio.ensure_future(site.start())
    yield 'http://localhost:{}'.format(unused_tcp_port)
    server_task.cancel()
    with suppress(asyncio.CancelledError):
        await server_task
    await runner.cleanup()


@pytest.mark.asyncio
async def test_cron_example(
        example_keys, test_keys, connection, listening_endpoint
):
    """Test the cron example."""
    with connection.next() as next_msg:
        process = await asyncio.create_subprocess_exec(
            'env/bin/python', 'examples/cron.py',
            '--my-verkey', crypto.bytes_to_b58(example_keys.verkey),
            '--my-sigkey', crypto.bytes_to_b58(example_keys.sigkey),
            '--their-verkey', crypto.bytes_to_b58(test_keys.verkey),
            '--endpoint', listening_endpoint
        )
        assert await process.wait() == 0
        msg = await asyncio.wait_for(next_msg, 30)

    assert 'basicmessage' in msg.type
    assert msg['content'] == 'The Cron script was executed.'


@pytest.mark.asyncio
async def test_webserver_aiohttp(
        example_keys, test_keys, connection, listening_endpoint,
        unused_tcp_port_factory
):
    """Test the webserver aiohttp example."""
    example_port = unused_tcp_port_factory()
    connection.target.update(endpoint='http://localhost:{}'.format(example_port))

    process = await asyncio.create_subprocess_exec(
        'env/bin/python', 'examples/webserver_aiohttp.py',
        '--my-verkey', crypto.bytes_to_b58(example_keys.verkey),
        '--my-sigkey', crypto.bytes_to_b58(example_keys.sigkey),
        '--their-verkey', crypto.bytes_to_b58(test_keys.verkey),
        '--endpoint', listening_endpoint,
        '--port', str(example_port),
        stdout=asyncio.subprocess.DEVNULL,
    )

    await server_ready('localhost', example_port)

    with connection.next() as next_msg:
        await connection.send_async({
            "@type": "https://didcomm.org/"
                     "basicmessage/1.0/message",
            "~l10n": {"locale": "en"},
            "sent_time": utils.timestamp(),
            "content": "Your hovercraft is full of eels."
        })
        msg = await asyncio.wait_for(next_msg, 30)

    assert 'basicmessage' in msg.type
    assert msg['content'] == 'You said: Your hovercraft is full of eels.'
    process.terminate()
    await process.wait()


@pytest.mark.asyncio
async def test_preprocessor_example(
        example_keys, test_keys, connection, listening_endpoint,
        unused_tcp_port_factory
):
    """Test the preprocessor example."""
    example_port = unused_tcp_port_factory()
    connection.target.update(
        endpoint='http://localhost:{}'.format(example_port)
    )

    process = await asyncio.create_subprocess_exec(
        'env/bin/python', 'examples/preprocessors.py',
        '--my-verkey', crypto.bytes_to_b58(example_keys.verkey),
        '--my-sigkey', crypto.bytes_to_b58(example_keys.sigkey),
        '--their-verkey', crypto.bytes_to_b58(test_keys.verkey),
        '--endpoint', listening_endpoint,
        '--port', str(example_port),
        stdout=asyncio.subprocess.DEVNULL,
    )

    await server_ready('localhost', example_port)

    with connection.next() as next_msg:
        await connection.send_async({
            "@type": "https://didcomm.org/"
                     "basicmessage/1.0/message",
            "~l10n": {"locale": "en"},
            "sent_time": utils.timestamp(),
            "content": "Your hovercraft is full of eels."
        })
        msg = await asyncio.wait_for(next_msg, 30)

    assert 'basicmessage' in msg.type
    assert msg['content'] == \
        'The preprocessor validated this message and added: Something!'
    process.terminate()
    await process.wait()


@pytest.mark.asyncio
async def test_webserver_with_websockets(
        example_keys, test_keys, connection_ws, listening_endpoint,
        unused_tcp_port_factory
):
    """Test the webserver with websockets example."""
    example_port = unused_tcp_port_factory()
    connection_ws.target.update(
        endpoint='http://localhost:{}'.format(example_port)
    )

    process = await asyncio.create_subprocess_exec(
        'env/bin/python', 'examples/webserver_with_websockets.py',
        '--my-verkey', crypto.bytes_to_b58(example_keys.verkey),
        '--my-sigkey', crypto.bytes_to_b58(example_keys.sigkey),
        '--their-verkey', crypto.bytes_to_b58(test_keys.verkey),
        '--endpoint', listening_endpoint,
        '--port', str(example_port),
        stdout=asyncio.subprocess.DEVNULL,
    )

    await server_ready('localhost', example_port)

    with connection_ws.next() as next_msg:
        await connection_ws.send_async({
            "@type": "https://didcomm.org/"
                     "basicmessage/1.0/message",
            "~l10n": {"locale": "en"},
            "sent_time": utils.timestamp(),
            "content": "Your hovercraft is full of eels."
        }, return_route='all')
        msg = await asyncio.wait_for(next_msg, 30)

    assert 'basicmessage' in msg.type
    assert msg['content'] == 'You said: Your hovercraft is full of eels.'
    process.terminate()
    await process.wait()


@pytest.mark.asyncio
async def test_webserver_with_module(
        example_keys, test_keys, connection, listening_endpoint,
        unused_tcp_port_factory
):
    """Test the webserver plus module example."""
    example_port = unused_tcp_port_factory()
    connection.target.update(
        endpoint='http://localhost:{}'.format(example_port)
    )
    process = await asyncio.create_subprocess_exec(
        'env/bin/python', 'examples/webserver_with_module.py',
        '--my-verkey', crypto.bytes_to_b58(example_keys.verkey),
        '--my-sigkey', crypto.bytes_to_b58(example_keys.sigkey),
        '--their-verkey', crypto.bytes_to_b58(test_keys.verkey),
        '--endpoint', listening_endpoint,
        '--port', str(example_port),
        stdout=asyncio.subprocess.DEVNULL,
    )

    await server_ready('localhost', example_port)

    with connection.next() as next_msg:
        await connection.send_async({
            "@type": "https://didcomm.org/"
                     "basicmessage/1.0/message",
            "~l10n": {"locale": "en"},
            "sent_time": utils.timestamp(),
            "content": "Your hovercraft is full of eels."
        })
        msg = await asyncio.wait_for(next_msg, 30)

    assert 'basicmessage' in msg.type
    assert msg['content'] == '1 message(s) received.'

    with connection.next() as next_msg:
        await connection.send_async({
            "@type": "https://didcomm.org/"
                     "basicmessage/1.0/message",
            "~l10n": {"locale": "en"},
            "sent_time": utils.timestamp(),
            "content": "My last message was nonsense."
        })
        msg = await asyncio.wait_for(next_msg, 30)

    assert 'basicmessage' in msg.type
    assert msg['content'] == '2 message(s) received.'

    process.terminate()
    await process.wait()


@pytest.mark.asyncio
async def test_return_route_examples(unused_tcp_port_factory):
    """Test the return route client-server exapmles."""
    example_port = unused_tcp_port_factory()
    server_process = await asyncio.create_subprocess_exec(
        'env/bin/python', 'examples/return_route_server.py',
        stdout=asyncio.subprocess.DEVNULL,
        env={'PORT': str(example_port)}
    )

    await server_ready('localhost', example_port)

    client_process = await asyncio.create_subprocess_exec(
        'env/bin/python', 'examples/return_route_client.py',
        stdout=asyncio.subprocess.PIPE,
        env={'PORT': str(example_port)}
    )

    assert await client_process.wait() == 0
    out, _err = await client_process.communicate()
    out = out.decode('ascii')
    assert 'Msg from conn:' in out
    assert 'The Cron script has been executed.' in out

    server_process.terminate()
    await server_process.wait()
