This repo contains an example Aries Static Agent in Python.


The StaticAgent library should make as few assumptions about it's running
environment as possible. This includes low dependancies, assumptions about web frameworks, etc.

### Assumptions
- Static Agents have a direct relationship with a full agent
- Static Agents have no wallet. Any wallet info is loaded via
configuration and is not updatable by code.


A static agent config consists of:
- It's own public/private key
- Public key of full agent
- Endpoint of full agent

Questions:
* Are we allowing Agent routing between a static agent and it's full agent?
**  How about we start with 'no', and revisit in the future if needed?

### Keys
You'll need to configure a keypair for this new static agent.
Use the keypair_gen.py file to create a keypair.

you'll give the public key to the full agent you are connecting with,
and will receive an endpoint and public key in return.

these three things are needed as configuration. The examples show providing these
as command line arguments or environment variables.