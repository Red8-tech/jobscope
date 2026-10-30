import jobscope


def test_package_has_version() -> None:
    assert jobscope.__version__ == "0.1.0"