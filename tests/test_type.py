""" Test Type """

import pytest

from aries_staticagent.type import Type, Semver, InvalidType


@pytest.mark.parametrize(
    'version_arg, expected_version, expected_semver',
    [
        ['1.0', '1.0', Semver(1, 0, 0)],
        ['1.3', '1.3', Semver(1, 3, 0)],
        ['1.3.4', '1.3.4', Semver(1, 3, 4)],
        [Semver(1, 0, 0), '1.0.0', Semver(1, 0, 0)],
        ['1.0.0-alpha', '1.0.0-alpha', Semver(1, 0, 0, 'alpha')]
    ]
)
def test_version_parsing(version_arg, expected_version, expected_semver):
    """ Test that version is being parsed correctly. """
    type_ = Type('doc;', 'protocol', version_arg, 'name')
    assert type_.version == expected_version
    assert type_.version_info == expected_semver


@pytest.mark.parametrize(
    'version_arg',
    ['a.b.c', 10]
)
def test_bad_version_raises_error(version_arg):
    """ Test that bad versions raise an error. """
    with pytest.raises(InvalidType):
        Type('doc;', 'protocol', version_arg, 'name')


@pytest.mark.parametrize(
    'type_str, expected',
    [
        (
            'doc;protocol/1.0/name',
            [
                'doc;',
                'protocol',
                '1.0',
                'name'
            ]
        ),
        (
            'https://didcomm.org/test_protocol/2.0/test_type',
            [
                'https://didcomm.org/',
                'test_protocol',
                '2.0',
                'test_type'
            ]
        ),
        (
            'doc;protocol/1.0.0-alpha/name',
            [
                'doc;',
                'protocol',
                '1.0.0-alpha',
                'name'
            ]
        )
    ]
)
def test_parse_from_str(type_str, expected):
    """ Test parsing type from string. """
    type_ = Type.from_str(type_str)
    assert [type_.doc_uri, type_.protocol, type_.version, type_.name] \
        == expected


@pytest.mark.parametrize(
    'lhs, rhs',
    [
        (Type.from_str('doc;protocol/1.0/name'), 'doc;protocol/1.0.0/name'),
        (
            Type.from_str('doc;protocol/1.0/name'),
            Type('doc;', 'protocol', '1.0', 'name')
        ),
        (
            Type('doc;', 'protocol', '1.0.0', 'name'),
            Type('doc;', 'protocol', '1.0.0', 'name')
        )
    ]
)
def test_equality(lhs, rhs):
    """ Test equality functions """
    assert lhs == rhs


def test_equality_wrong_types():
    """ Test incorrect type raises error. """
    with pytest.raises(TypeError):
        _ = Type.from_str('doc;protocol/1.0/name') == 10


@pytest.mark.parametrize(
    'lhs, rhs',
    [
        (Type.from_str('doc;protocol/1.0/name'), 'doc;protocol/2.0/name'),
        (
            Type.from_str('doc;protocol/1.0/name'),
            Type('doc;', 'protocol', '2.0', 'name')
        ),
        (
            Type('doc;', 'protocol', '1.0.0', 'name'),
            Type('doc;', 'protocol', '2.0.0', 'name')
        )
    ]
)
def test_not_equal(lhs, rhs):
    """ Test not equals. """
    assert lhs != rhs


@pytest.mark.parametrize(
    'type_, expected',
    [
        (Type('doc;', 'protocol', '1.0.0', 'name'), 'doc;protocol/1.0.0/name'),
        (Type('doc;', 'protocol', '1.0', 'name'), 'doc;protocol/1.0/name'),
    ]
)
def test_stringify(type_, expected):
    """ Testing stringifying of Type. Reported version should be the given (not
        normalized) version.
    """
    assert str(type_) == expected
