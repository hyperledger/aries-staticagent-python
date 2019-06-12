from setuptools import setup, find_packages

setup(
    name='aries-staticagent',
    version='0.1.0',
    author='Daniel Bluhm <daniel.bluhm@sovrin.org>, Sam Curren <sam@sovrin.org>',
    description='Library and example Python Static Agent for Aries',
    license='Apache 2.0',
    packages_dir={'aries_staticagent': 'aries_staticagent'},
    packages=['aries_staticagent']
)
