import hashlib
from aries_staticagent import StaticConnection, crypto, utils


def main():
    """Start a server with a static connection."""
    my_vk, my_sk = crypto.create_keypair(
        seed=hashlib.sha256(b'client').digest()
    )
    their_vk, _ = crypto.create_keypair(
        seed=hashlib.sha256(b'server').digest()
    )
    conn = StaticConnection(my_vk, my_sk, their_vk, 'http://localhost:3000')

    reply = conn.send_and_await_reply({
        "@type": "did:sov:BzCbsNYhMrjHiqZDTUASHg;spec/"
                 "basicmessage/1.0/message",
        "~l10n": {"locale": "en"},
        "sent_time": utils.timestamp(),
        "content": "The Cron Script has been executed."
    }, return_route='all')
    print('Msg from conn:', reply and reply.pretty_print())


if __name__ == '__main__':
    main()
