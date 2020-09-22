""" package aries_staticagent """

from setuptools import setup, find_packages
from version import VERSION


def parse_requirements(filename):
    """Load requirements from a pip requirements file."""
    lineiter = (line.strip() for line in open(filename))
    return [line for line in lineiter if line and not line.startswith("#")]


if __name__ == '__main__':
    with open('README.md', 'r') as fh:
        LONG_DESCRIPTION = fh.read()

    setup(
        name='aries-staticagent',
        version=VERSION,
        author='Daniel Bluhm <daniel.bluhm@sovrin.org>, '
               'Sam Curren <sam@sovrin.org>',
        description='Python Static Agent Library and Examples for Aries',
        long_description=LONG_DESCRIPTION,
        long_description_content_type='text/markdown',
        url='https://github.com/hyperledger/aries-staticagent-python',
        license='Apache 2.0',
        packages=find_packages(),
        install_requires=parse_requirements('requirements.txt'),
        extras_require={
            'test': parse_requirements('requirements.dev.txt')
        },
        python_requires='>=3.6',
        classifiers=[
            'Programming Language :: Python :: 3',
            'License :: OSI Approved :: Apache Software License',
            'Operating System :: OS Independent'
        ]
    )
