"""Tests for djangordf.namespaces (LangString in this milestone)."""


def test_langstring_holds_value_and_lang():
    from djangordf.namespaces import LangString
    ls = LangString("Buch", "de")
    assert ls.value == "Buch"
    assert ls.lang == "de"


def test_langstring_is_frozen():
    import dataclasses
    from djangordf.namespaces import LangString
    ls = LangString("Buch", "de")
    try:
        ls.value = "Roman"
    except dataclasses.FrozenInstanceError:
        return
    raise AssertionError("LangString must be frozen")


def test_langstring_equality_by_value_and_lang():
    from djangordf.namespaces import LangString
    assert LangString("Buch", "de") == LangString("Buch", "de")
    assert LangString("Buch", "de") != LangString("Buch", "en")
    assert LangString("Buch", "de") != LangString("Roman", "de")


def test_langstring_is_hashable():
    from djangordf.namespaces import LangString
    s = {LangString("Buch", "de"), LangString("Buch", "de")}
    assert len(s) == 1
