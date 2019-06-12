from aries_staticagent import crypto

vk_bytes, sk_bytes = crypto.create_keypair()
did_bytes = vk_bytes[0:16]

vk = crypto.bytes_to_b58(vk_bytes)
sk = crypto.bytes_to_b58(sk_bytes)
did = crypto.bytes_to_b58(did_bytes)


print('For full agent:\n\tDID: {}\n\tVK: {}\n'.format(did, vk))

print('For static agent:\n\tVK: {}\n\tSK: {}'.format(vk, sk))
