import os


def pytest_configure(config) -> None:
    os.environ["MINDGARD_CONFIG_DIR"] = os.path.join(os.path.dirname(__file__))