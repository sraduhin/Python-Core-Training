import pytest

from main import temporary_value


def test_01():
    mapping = {"k": "v"}
    with temporary_value(mapping, "k", "new") as m:
        assert m is mapping
        assert mapping["k"] == "new"
    assert mapping["k"] == "v"


def test_02():
    mapping = {}
    with temporary_value(mapping, "k", "new") as m:
        assert m is mapping
        assert mapping["k"] == "new"
    assert mapping == {}


def test_03():
    mapping = {"k": None}
    with temporary_value(mapping, "k", "new") as m:
        assert m is mapping
        assert mapping["k"] == "new"
    assert mapping["k"] is None


def test_05():
    mapping = {"k": "v"}
    try:
        with temporary_value(mapping, "k", "new") as m:
            assert m is mapping
            assert mapping["k"] == "new"
            raise RuntimeError
    except RuntimeError:
        pass
    assert mapping["k"] == "v"


def test_06():
    old = [1]
    mapping = {"k": old}
    with temporary_value(mapping, "k", "new") as m:
        assert m is mapping
        assert mapping["k"] == "new"
    old.append(2)
    assert mapping["k"] is old
    assert mapping["k"] == [1, 2]


def test_raises():
    with pytest.raises(TypeError):
        temporary_value(["someshit"], "k", "new")

    with pytest.raises(TypeError):
        temporary_value({"some": "shit"}, 5, "new")
