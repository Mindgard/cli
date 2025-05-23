
from typing import Any, Dict
from unittest import mock

import pytest
from mindgard.constants import EXIT_CODE_NOT_PASSED, EXIT_CODE_PASSED
from mindgard.main_lib import run_test
from mindgard.test import LLMModelConfig, TestConfig, UnauthorizedError
from mindgard.wrappers.llm import TestStaticResponder


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
        "attack_pack": "myattackpack",
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
            attack_pack="myattackpack",
            parallelism=1,
            model=LLMModelConfig(
                wrapper=model_wrapper,
                system_prompt="mysysprompt",
            )
        )
    )

@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
def test_run_llm_test_with_domain(
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock
):
    final_args: Dict[str, Any] = {
        "model_type": "llm",
        "target": "mytarget",
        "parallelism": 1,
        "system_prompt": "mysysprompt",
        "attack_pack": "myattackpack",
        "domain": "my_domain"
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
            attack_pack="myattackpack",
            dataset_domain="my_domain",
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

@mock.patch("mindgard.main_lib.clear_token")
@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
@mock.patch("mindgard.main_lib.TestUI", return_value=mock.MagicMock())
@mock.patch("mindgard.main_lib.Thread", return_value=mock.MagicMock())
def test_run_uuthorization_exceptions(
    mock_thread: mock.MagicMock,
    mock_test_ui: mock.MagicMock,
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock,
    mock_clear_token: mock.MagicMock,
    capsys: pytest.CaptureFixture[str]
):
    mock_test.return_value.run.side_effect = UnauthorizedError()
    with pytest.raises(SystemExit, match="2"):
        run_test(final_args={
            "model_type": 'llm', 
            "target": "myTarget", 
            "parallelism": 1,
            "system_prompt": "mysysprompt",
            }, model_wrapper=mock.MagicMock())
    mock_clear_token.assert_called_once()
    captured = capsys.readouterr()
    assert captured.err == "Access token is invalid. Please re-authenticate using `mindgard login`\n"
    
@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
@mock.patch("mindgard.main_lib.TestUI", return_value=mock.MagicMock())
@mock.patch("mindgard.main_lib.Thread", return_value=mock.MagicMock())
def test_final_exit_code(
    mock_thread: mock.MagicMock,
    mock_test_ui: mock.MagicMock,
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock
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

    # following also asserts: mock_test_ui.return_value.run.assert_called_once()
    mock_thread.assert_called_once_with(target=mock_test_ui.return_value.run, name="TestUI")
    mock_thread.return_value.start.assert_called_once()
    mock_thread.return_value.join.assert_called_once()

@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
@mock.patch("mindgard.main_lib.TestUI", return_value=mock.MagicMock())
@mock.patch("mindgard.main_lib.Thread", return_value=mock.MagicMock())
def test_exit_code_test_passed(
    mock_thread: mock.MagicMock,
    mock_test_ui: mock.MagicMock,
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock
):
    mock_test.return_value.get_state.return_value.passed = True
    with pytest.raises(SystemExit, match=str(EXIT_CODE_PASSED)):
        run_test(final_args={
            "model_type": 'llm', 
            "target": "myTarget", 
            "parallelism": 1,
            "system_prompt": "mysysprompt",
            }, model_wrapper=mock.MagicMock())
        
        
@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
@mock.patch("mindgard.main_lib.TestUI", return_value=mock.MagicMock())
@mock.patch("mindgard.main_lib.Thread", return_value=mock.MagicMock())
def test_exit_code_test_failed(
    mock_thread: mock.MagicMock,
    mock_test_ui: mock.MagicMock,
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock
):
    mock_test.return_value.get_state.return_value.passed = False
    with pytest.raises(SystemExit, match=str(EXIT_CODE_NOT_PASSED)):
        run_test(final_args={
            "model_type": 'llm', 
            "target": "myTarget", 
            "parallelism": 1,
            "system_prompt": "mysysprompt",
            }, model_wrapper=mock.MagicMock())
        

@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
def test_run_llm_test_with_exclusions(
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock
):
    final_args: Dict[str, Any] = {
        "model_type": "llm",
        "target": "mytarget",
        "parallelism": 1,
        "system_prompt": "mysysprompt",
        "attack_pack": "myattackpack",
        "exclude": ["exclusion1", "exclusion2"]
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
            attack_pack="myattackpack",
            parallelism=1,
            model=LLMModelConfig(
                wrapper=model_wrapper,
                system_prompt="mysysprompt",
            ),
            exclude=["exclusion1", "exclusion2"]
        )
    )


@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
def test_run_llm_test_with_inclusions(
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock
):
    final_args: Dict[str, Any] = {
        "model_type": "llm",
        "target": "mytarget",
        "parallelism": 1,
        "system_prompt": "mysysprompt",
        "attack_pack": "myattackpack",
        "include": ["inclusion1", "inclusion2"]
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
            attack_pack="myattackpack",
            parallelism=1,
            model=LLMModelConfig(
                wrapper=model_wrapper,
                system_prompt="mysysprompt",
            ),
            include=["inclusion1", "inclusion2"]
        )
    )

@mock.patch("mindgard.main_lib.load_access_token", return_value="myApiKey")
@mock.patch("mindgard.main_lib.Test", return_value=mock.MagicMock())
def test_run_llm_test_with_include_and_exclude(
    mock_test: mock.MagicMock,
    mock_load_access_token: mock.MagicMock
):
    final_args: Dict[str, Any] = {
        "model_type": "llm",
        "target": "mytarget",
        "parallelism": 1,
        "system_prompt": "mysysprompt",
        "attack_pack": "myattackpack",
        "exclude": ["exclusion1", "exclusion2"],
        "include": ["inclusion1", "inclusion2"]
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
            attack_pack="myattackpack",
            parallelism=1,
            model=LLMModelConfig(
                wrapper=model_wrapper,
                system_prompt="mysysprompt",
            ),
            exclude=["exclusion1", "exclusion2"],
            include=["inclusion1", "inclusion2"]
        )
    )
