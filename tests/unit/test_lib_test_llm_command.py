from unittest.mock import Mock

from azure.messaging.webpubsubclient import WebPubSubClient
from mindgard.test import Test, TestConfig, TestImplementationProvider
from mindgard.wrappers.llm import TestStaticResponder

# Please there must be a better way to get pytest to ignore these
Test.__test__ = False # type: ignore
TestConfig.__test__ = False # type: ignore
TestImplementationProvider.__test__ = False # type: ignore
TestStaticResponder.__test__ = False # type: ignore

def test_lib_runs_test_complete():
    test_group_id = "my test group id"
    test_wps_url = "my test wps url"
    test_id = "my test id"

    config = TestConfig(
        api_base="your_api_base",
        api_access_token="your_api_access_token",
        target="your_target",
        model_type="your_model_type",
        system_prompt="your_system_prompt",
        attack_source="your_attack_source",
        parallelism=1,
        wrapper=TestStaticResponder(system_prompt="test"),
    )

    mock_provider = Mock(spec=TestImplementationProvider)
    mock_provider.init_test.return_value = (test_wps_url, test_group_id)
    mock_provider.connect_websocket.return_value = Mock(spec=WebPubSubClient)
    mock_provider.start_test.return_value = test_id

    test = Test(config, provider=mock_provider)
    test.run()

    mock_provider.init_test.assert_called_once_with(config)
    mock_provider.connect_websocket.assert_called_once_with(test_wps_url)
    mock_provider.register_wrapper.assert_called_once_with(config, mock_provider.connect_websocket.return_value, test_group_id)
    mock_provider.start_test.assert_called_once_with(mock_provider.connect_websocket.return_value, test_group_id)
    mock_provider.poll_test.assert_called_once_with(config, test_id) # assert that the default period is used


