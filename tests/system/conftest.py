import os


def pytest_configure() -> None:
    os.environ["MINDGARD_CONFIG_DIR"] = os.path.join(os.path.dirname(__file__))


def pytest_unconfigure() -> None:
    os.environ.pop("MINDGARD_CONFIG_DIR")