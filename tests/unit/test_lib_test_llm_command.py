from typing import Any
from unittest.mock import Mock

from azure.messaging.webpubsubclient import WebPubSubClient
import pytest
from mindgard.test import Test, TestConfig, TestImplementationProvider
from mindgard.wrappers.llm import TestStaticResponder

# Please there must be a better way to get pytest to ignore these
Test.__test__ = False # type: ignore
TestConfig.__test__ = False # type: ignore
TestImplementationProvider.__test__ = False # type: ignore
TestStaticResponder.__test__ = False # type: ignore

class MockProviderFixture():
    """
    Helper to set up a complete mock provider and access to the mock provider's methods/outputs
    """
    def __init__(self):
        self.test_wps_url = "my test wps url"
        self.test_group_id = "my test group id"
        self.test_id = "my test id"
        def mock_handler(payload: Any) -> Any:
            return {
                "response": f"hello {payload['prompt']}"
            }
        self.mock_handler = mock_handler
        self.wps_client = Mock(spec=WebPubSubClient)
        self.provider = Mock(spec=TestImplementationProvider)
        self.provider.init_test.return_value = (self.test_wps_url, self.test_group_id)
        self.provider.create_client.return_value = self.wps_client
        self.provider.wrapper_to_handler.return_value = mock_handler
        self.provider.start_test.return_value = self.test_id

@pytest.fixture
def mock_provider():
    return MockProviderFixture()

@pytest.fixture
def config():
    return TestConfig(
        api_base="your_api_base",
        api_access_token="your_api_access_token",
        target="your_target",
        model_type="your_model_type",
        system_prompt="your_system_prompt",
        attack_source="your_attack_source",
        parallelism=1,
        wrapper=TestStaticResponder(system_prompt="test"),
    )

def test_lib_runs_test_complete(mock_provider:MockProviderFixture, config:TestConfig):
    test = Test(config, provider=mock_provider.provider)
    test.run()

    mock_provider.provider.init_test.assert_called_once_with(config)
    mock_provider.provider.create_client.assert_called_once_with(mock_provider.test_wps_url)
    mock_provider.provider.connect_websocket.assert_called_once_with(mock_provider.wps_client)
    mock_provider.provider.register_handler.assert_called_once_with(mock_provider.mock_handler, mock_provider.wps_client, mock_provider.test_group_id)
    mock_provider.provider.start_test.assert_called_once_with(mock_provider.wps_client, mock_provider.test_group_id)
    mock_provider.provider.poll_test.assert_called_once_with(config, mock_provider.test_id) # assert that the default period parameter is used
    mock_provider.provider.close.assert_called_once_with(mock_provider.wps_client)


def test_lib_closes_on_exception(mock_provider:MockProviderFixture, config:TestConfig):
    """
    Unrecovered failures during execution should not leave the test running.
    Exception should be propagated to the caller unaltered (this is unhandled case).
    """
    exception = Exception("test exception")
    mock_provider.provider.poll_test.side_effect = exception

    with pytest.raises(Exception) as e:
        test = Test(config, provider=mock_provider.provider)
        test.run()
    assert e.value == exception, "the same exception should be propagated (not a copy/wrap)"
    assert mock_provider.provider.close.called, "the test should be closed even if an exception is raised"
