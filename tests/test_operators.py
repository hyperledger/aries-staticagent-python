from aries_staticagent.operators import all, any


def test_all():
    assert all([lambda f: True, lambda f: True, lambda f: True], "value")
    assert all([lambda f: True, lambda f: True, lambda f: False], "value") is False


def test_any():
    assert any([lambda f: True, lambda f: True, lambda f: True], "value")
    assert any([lambda f: True, lambda f: True, lambda f: False], "value")
    assert any([lambda f: True, lambda f: False, lambda f: False], "value")
    assert any([lambda f: False, lambda f: False, lambda f: False], "value") is False


def test_msg_type_is():
    assert False


def test_msg_type_matches():
    assert False


def test_msg_type_is_compatibile_with():
    assert False


def test_in_protocol():
    assert False


def test_is_reply_to():
    assert False
