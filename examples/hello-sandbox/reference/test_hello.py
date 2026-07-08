from auto.sandbox.hello import greet


def test_greet_normal_case():
    assert greet("World") == "Hello, World!"


def test_greet_empty_string():
    assert greet("") == "Hello, !"
