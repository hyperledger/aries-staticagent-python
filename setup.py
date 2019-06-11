from setuptools import setup, find_packages

setup(
    name='aries_staticagent_python',
    version='0.1.0',
    auther='Daniel Bluhm <daniel.bluhm@sovrin.org>, Sam Curren <sam@sovrin.org>',
    description='Library and example Python Static Agent for Aries',
    license='Apache 2.0',
    package_dir={'staticagent': 'src'},
    packages=find_packages(where='src'),
)
