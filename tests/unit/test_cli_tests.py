
from typing import Any, Dict
from unittest import mock

import pytest
from mindgard.main_lib import run_test
from mindgard.test import ImageModelConfig, LLMModelConfig, TestConfig
from mindgard.wrappers.image import ImageModelWrapper
from mindgard.wrappers.llm import TestStaticResponder


@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
def test_run_image_test(
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock
):
    final_args: Dict[str, Any] = {
        "model_type": "image",
        "target": "mytarget",
        "parallelism": 1,
        "dataset": "mydataset",
        "labels": ["label1", "label2"],
    }
    
    model_wrapper = ImageModelWrapper(
        url="https://example.com/somewhere", 
        labels=[], api_key="myapikey"
    )
    
    with pytest.raises(SystemExit):
        run_test(final_args=final_args, model_wrapper=model_wrapper)
    
    mock_test.assert_called_once_with(
        TestConfig(
            api_base="https://api.sandbox.mindgard.ai/api/v1",
            api_access_token="myApiKey",
            target="mytarget",
            attack_source="user",
            parallelism=1,
            model=ImageModelConfig(
                wrapper=model_wrapper,
                dataset="mydataset",
                model_type="image",
                labels=["label1", "label2"],
            )
        )
    )

@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
def test_run_llm_test(
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock
):
    final_args: Dict[str, Any] = {
        "model_type": "llm",
        "target": "mytarget",
        "parallelism": 1,
        "system_prompt": "mysysprompt",
    }
    
    model_wrapper = TestStaticResponder(system_prompt="test")
    
    with pytest.raises(SystemExit):
        run_test(final_args=final_args, model_wrapper=model_wrapper)
    
    mock_test.assert_called_once_with(
        TestConfig(
            api_base="https://api.sandbox.mindgard.ai/api/v1",
            api_access_token="myApiKey",
            target="mytarget",
            attack_source="user",
            parallelism=1,
            model=LLMModelConfig(
                wrapper=model_wrapper,
                system_prompt="mysysprompt",
            )
        )
    )

@mock.patch("mindgard.main_lib.load_access_token", return_value=None)
def test_missing_access_token(
    mock_load_access_token: mock.MagicMock,
    capsys: pytest.CaptureFixture[str]
):
    with pytest.raises(SystemExit, match="2"):
        run_test(final_args={}, model_wrapper=mock.MagicMock())
        
    captured = capsys.readouterr()
    assert captured.err == "\033[1;37mRun `mindgard login`\033[0;0m to authenticate.\n"
    
    
@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
@mock.patch("mindgard.main_lib.TestUI", return_value=mock.MagicMock())
def test_final_exit_code(
    mock_test_ui: mock.MagicMock,
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock,
):
    with pytest.raises(SystemExit, match="0"):
        run_test(final_args={
            "model_type": 'llm', 
            "target": "myTarget", 
            "parallelism": 1,
            "system_prompt": "mysysprompt",
            }, model_wrapper=mock.MagicMock())
        
        
    mock_test.return_value.run.assert_called_once()
    mock_test_ui.assert_called_once_with(mock_test.return_value)
    mock_test_ui.return_value.run.assert_called_once()