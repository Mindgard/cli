import os
import sys
from argparse import Namespace
from dataclasses import dataclass
from typing import Dict, List, Tuple, cast
from unittest import mock
from unittest.mock import mock_open, patch

import pytest
from mindgard.utils import parse_toml_and_args_into_final_args
from mindgard.types import valid_image_datasets, valid_llm_datasets
from mindgard.__main__ import main, parse_args
from mindgard.orchestrator import OrchestratorSetupRequest, OrchestratorTestResponse




@dataclass
class Case:
    name: str
    input_args: list[str]
    expected_request: OrchestratorSetupRequest
    cli_run_response: OrchestratorTestResponse
    expected_exit_code: int

cases = [
    Case(
        name="basic",
        input_args=[
            'mindgard', 'test', 'mytarget', 
            '--system-prompt', 'mysysprompt', 
            '--preset', 'tester',
            '--parallelism', '4',
        ],
        expected_request=OrchestratorSetupRequest(
            target="mytarget",
            modelType="llm",
            system_prompt="mysysprompt",
            attackPack="sandbox",
            attackSource="user",
            parallelism=4,
            labels=None
        ),
        cli_run_response=OrchestratorTestResponse(
            id="123",
            mindgardModelName="model",
            source="user",
            createdAt="2022-01-01",
            attacks=[],
            isCompleted=True,
            hasFinished=True,
            risk=12,
            test_url="http://example.com"
        ),
        expected_exit_code=0,
    ),
    Case(
        name="mode-fast",
        input_args=[
            'mindgard', 'test', 'mytarget', 
            '--system-prompt', 'mysysprompt', 
            '--preset', 'tester',
            '--parallelism', '4',
            '--mode', 'fast',
        ],
        expected_request=OrchestratorSetupRequest(
            target="mytarget",
            modelType="llm",
            system_prompt="mysysprompt",
            attackPack="sandbox",
            attackSource="user",
            parallelism=4,
            labels=None
        ),
        cli_run_response=OrchestratorTestResponse(
            id="123",
            mindgardModelName="model",
            source="user",
            createdAt="2022-01-01",
            attacks=[],
            isCompleted=True,
            hasFinished=True,
            risk=12,
            test_url="http://example.com"
        ),
        expected_exit_code=0,
    ),
    Case(
        name="mode-exhaustive",
        input_args=[
            'mindgard', 'test', 'mytarget', 
            '--system-prompt', 'mysysprompt', 
            '--preset', 'tester',
            '--parallelism', '4',
            '--mode', 'exhaustive',
        ],
        expected_request=OrchestratorSetupRequest(
            target="mytarget",
            modelType="llm",
            system_prompt="mysysprompt",
            attackPack="large",
            attackSource="user",
            parallelism=4,
            labels=None
        ),
        cli_run_response=OrchestratorTestResponse(
            id="123",
            mindgardModelName="model",
            source="user",
            createdAt="2022-01-01",
            attacks=[],
            isCompleted=True,
            hasFinished=True,
            risk=12,
            test_url="http://example.com"
        ),
        expected_exit_code=0,
    ),
    Case(
        name="mode-thorough",
        input_args=[
            'mindgard', 'test', 'mytarget', 
            '--system-prompt', 'mysysprompt', 
            '--preset', 'tester',
            '--parallelism', '4',
            '--mode', 'thorough',
        ],
        expected_request=OrchestratorSetupRequest(
            target="mytarget",
            modelType="llm",
            system_prompt="mysysprompt",
            attackPack="medium",
            attackSource="user",
            parallelism=4,
            labels=None
        ),
        cli_run_response=OrchestratorTestResponse(
            id="123",
            mindgardModelName="model",
            source="user",
            createdAt="2022-01-01",
            attacks=[],
            isCompleted=True,
            hasFinished=True,
            risk=12,
            test_url="http://example.com"
        ),
        expected_exit_code=0,
    )
]


@pytest.mark.parametrize("test_case", cases, ids=lambda x: x.name)
@mock.patch("mindgard.__main__.exit")
@mock.patch("mindgard.__main__.cli_run")
@mock.patch("mindgard.__main__.model_test_submit_factory")
def test_orchestrator_setup_request(
    mock_model_test_submit_factory:mock.MagicMock, 
    mock_cli_run: mock.MagicMock, 
    mock_exit: mock.MagicMock,
    test_case: Case
):
    """
    Given a set of input arguments and a final response, validate that:
     - The OrchestratorSetupRequest is correctly constructed
     - Exit code is as expected
    """
    with mock.patch.object(sys, 'argv', test_case.input_args):
        mock_cli_run.return_value = test_case.cli_run_response
        
        main()
        
        mock_model_test_submit_factory.assert_called_once_with(
            request=test_case.expected_request,
            model_wrapper=mock.ANY,
            message_handler=mock.ANY,
        )
        mock_cli_run.assert_called_once_with(mock_model_test_submit_factory.return_value, mock.ANY, output_func=mock.ANY, json_out=mock.ANY)
        mock_exit.assert_called_once_with(test_case.expected_exit_code)



argparse_success_test_cases: List[Tuple[str, Namespace]] = [
    # normal user login
    ("login", Namespace(command='login', log_level='warn', instance=None)),

    # login to an instance
    ("login --instance deployed_instance", Namespace(command='login', log_level='warn', instance='deployed_instance')),

    # when no --instance parameter is passed it should default to sandbox
    ("login --instance", Namespace(command='login', log_level='warn', instance=None)),  # missing instance value
    # new cli structure:
    ("sandbox cfp_faces", Namespace(command='sandbox', target='cfp_faces', json=False, risk_threshold=80, log_level='warn')),

    ("list tests", Namespace(command='list', list_command='tests', json=False, id=None, log_level='warn')),
    ("list tests --json", Namespace(command='list', list_command='tests', json=True, id=None, log_level='warn')),
    ("list tests --json --id 123", Namespace(command='list', list_command='tests', json=True, id='123', log_level='warn')),
]

argparse_failure_test_cases: List[str] = [
    ("attackcategories --json --id 123"),
    ("auth --json"),
    ("tests run --name cfp_faces --json --id 123"),
    ("attacks --json --id 123 --name cfp_faces"),
    ("attacks --json --id 123 --name cfp_faces --json"),
]


# pytest test for each argparse_test_case

@pytest.mark.parametrize("test_case", argparse_success_test_cases, ids=lambda x: x[0])
def test_argparse_expected_namespaces(test_case: Tuple[str, Namespace]) -> None:
    command, namespace = test_case
    print(f"command: {command.split()}, namespace: {namespace}")
    parsed_args = parse_args(command.split())
    assert parsed_args == namespace
    
@pytest.mark.parametrize("test_case", argparse_failure_test_cases, ids=lambda x: x)
def test_argparse_expected_failures(test_case: str) -> None:
    with pytest.raises(SystemExit):
        parse_args(test_case.split())

def test_toml_and_args_parsing_model_type_llm():
    cli_command = "test --config-file=config.toml"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=None, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    model_type = "llm"
    target= "my_model"
    system-prompt = "You are a helpful, respectful and honest assistant."
    """

    with patch.dict(os.environ, {"MODEL_API_KEY": "my-api-key"}):
        with patch('builtins.open', mock_open(read_data=toml_content)):
            final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
            
            assert final_args["api_key"] == "my-api-key"
            assert final_args["model_type"] == "llm"
            assert final_args["command"] == namespace.command
            assert final_args["config_file"] == namespace.config_file
            assert final_args["mode"] == "fast"
    
        
def test_toml_and_args_parsing_model_type_empty():
    cli_command = "test --config-file=config.toml"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=None, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    target= "my_model"
    system-prompt = "You are a helpful, respectful and honest assistant."
    """

    with patch.dict(os.environ, {"MODEL_API_KEY": "my-api-key"}):
        with patch('builtins.open', mock_open(read_data=toml_content)):
            final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
            
            assert final_args["api_key"] == "my-api-key"
            assert final_args["model_type"] == "llm"
            assert final_args["command"] == namespace.command
            assert final_args["config_file"] == namespace.config_file
            
            if "MODEL_API_KEY" in os.environ:
                del os.environ["MODEL_API_KEY"]
            
def test_toml_and_args_parsing_model_type_image():
    cli_command = "test --config-file=config.toml"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=None, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    dataset="beans"
    system-prompt = "You are a helpful, respectful and honest assistant."
    labels='''{
        "0": "angular_leaf_spot",
        "1": "bean_rust",
        "2": "healthy"
    }'''
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        
        assert final_args["api_key"] == "my-api-key"
        assert final_args["model_type"] == "image"
        assert final_args["command"] == namespace.command
        assert final_args["config_file"] == namespace.config_file
        assert final_args["risk_threshold"] == 50 # default value
        assert final_args["parallelism"] == 5 # default value

def test_toml_and_args_parsing_model_type_image_without_labels_set():
    cli_command = "test --config-file=config.toml"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=None, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    dataset="beans"
    system-prompt = "You are a helpful, respectful and honest assistant."
    """
    
    with pytest.raises(ValueError):
        with patch('builtins.open', mock_open(read_data=toml_content)):
            final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
            assert final_args["api_key"] == "my-api-key"
            assert final_args["model_type"] == "image"

def test_toml_and_args_parsing_model_type_image_with_labels_set():
    cli_command = "test --config-file=config.toml"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=None, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    dataset="beans"
    system-prompt = "You are a helpful, respectful and honest assistant."
    labels='''{
        "0": "angular_leaf_spot",
        "1": "bean_rust",
        "2": "healthy"
    }'''
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        assert final_args["api_key"] == "my-api-key"
        assert final_args["model_type"] == "image"
        assert len(final_args["labels"]) == 3

def test_toml_and_args_parsing_not_setting_risk_threshold():
    cli_command = "test --config-file=config.toml"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=None, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    dataset="beans"
    system-prompt = "You are a helpful, respectful and honest assistant."
    labels='''{
        "0": "angular_leaf_spot",
        "1": "bean_rust",
        "2": "healthy"
    }'''
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        
        assert final_args["risk_threshold"] == 50 # default value

def test_toml_and_args_parsing_setting_risk_threshold():
    cli_command = "test --config-file=config.toml --risk-threshold=80"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=80, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    dataset="beans"
    system-prompt = "You are a helpful, respectful and honest assistant."
    labels='''{
        "0": "angular_leaf_spot",
        "1": "bean_rust",
        "2": "healthy"
    }'''
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        
        assert final_args["risk_threshold"] == 80
        
def test_toml_and_args_parsing_setting_risk_threshold_zero():
    cli_command = "test --config-file=config.toml --risk-threshold=0"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=0, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    dataset="beans"
    system-prompt = "You are a helpful, respectful and honest assistant."
    labels='''{
        "0": "angular_leaf_spot",
        "1": "bean_rust",
        "2": "healthy"
    }'''
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        print(f'final args: {final_args}')
        assert final_args["risk_threshold"] == 0
        
def test_toml_and_args_parsing_setting_json():
    cli_command = "test --config-file=config.toml --risk-threshold=80 --json"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=True, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=80, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    dataset="beans"
    system-prompt = "You are a helpful, respectful and honest assistant."
    labels='''{
        "0": "angular_leaf_spot",
        "1": "bean_rust",
        "2": "healthy"
    }'''
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        
        assert final_args["json"] == True
    
def test_toml_and_args_parsing_not_setting_json():
    cli_command = "test --config-file=config.toml --risk-threshold=80"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=80, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    dataset="beans"
    system-prompt = "You are a helpful, respectful and honest assistant."
    labels='''{
        "0": "angular_leaf_spot",
        "1": "bean_rust",
        "2": "healthy"
    }'''
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        
        assert final_args["json"] == False

def test_pass_random_dataset_not_in_approved_choices() -> None:
    cli_command = "test --config-file=config.toml --risk-threshold=80"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=80, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    dataset = "Immadeup,notreal"
    labels='''{
        "0": "angular_leaf_spot",
        "1": "bean_rust",
        "2": "healthy"
    }'''
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        expected = f"Dataset set in config file (Immadeup,notreal) was invalid! (choices: {[x for x in valid_image_datasets]})"
        with pytest.raises(ValueError) as exc_info:
            parse_toml_and_args_into_final_args("config.toml", parsed_args)

        assert exc_info.type is ValueError
        assert str(exc_info.value) == expected

def test_passing_mode_thorough_through_toml_args() -> None:
    cli_command = "test --config-file=config.toml"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, rate_limit=60000, tokenizer=None, model_type=None, parallelism=None, dataset=None, domain=None, model_name=None, api_key=None, url=None, preset=None, headers=None, header=None, target=None, risk_threshold=None, mode=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    model_type = "llm"
    target= "my_model"
    system-prompt = "You are a helpful, respectful and honest assistant."
    mode = "thorough"
    """

    with patch.dict(os.environ, {"MODEL_API_KEY": "my-api-key"}):
        with patch('builtins.open', mock_open(read_data=toml_content)):
            final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
            
            assert final_args["mode"] == "thorough"

def test_passing_domain() -> None:
    cli_command = "test --domain my_random_domain"

    with patch.dict(valid_llm_datasets, {"my_random_domain": "MyRandomDataset"}):
        parsed_args = parse_args(cast(List[str], cli_command.split()))

        assert parsed_args.domain == "my_random_domain"

        final_args = parse_toml_and_args_into_final_args(None, parsed_args)

        assert final_args["dataset"] == "MyRandomDataset", 'Domain should be converted to dataset based on valid_llm_datasets'



@dataclass
class ArgParsingTestCase:
    name: str
    cli_command: str # the input command

    should_exit_error: bool # if we expect argparse to raise SystemExit
    final_args_should_include: Dict[str, str] # test should check that these values are in final_args

arg_parse_test_cases = [
    ArgParsingTestCase(
        name="invalid domain",
        cli_command="test --domain my_non_existant_domain",
        should_exit_error=True,
        final_args_should_include={}
    ),
    ArgParsingTestCase(
        name="valid domain",
        cli_command="test --domain my_domain",
        should_exit_error=False,
        final_args_should_include={
            "dataset": "my_domain_dataset"
        }
    ),

    ArgParsingTestCase(
        name="medium mode",
        cli_command="test --mode thorough",
        should_exit_error=False,
        final_args_should_include={
            "attack_pack": "medium"
        }
    ),
    ArgParsingTestCase(
        name="thorough mode",
        cli_command="test --mode exhaustive",
        should_exit_error=False,
        final_args_should_include={
            "attack_pack": "large"
        }
    ),
    ArgParsingTestCase(
        name="fast mode",
        cli_command="test --mode fast",
        should_exit_error=False,
        final_args_should_include={
            "attack_pack": "sandbox"
        }
    ),
    ArgParsingTestCase(
        name="fast mode default",
        cli_command="test",
        should_exit_error=False,
        final_args_should_include={
            "attack_pack": "sandbox"
        }
    )
]
@pytest.mark.parametrize("test_case", arg_parse_test_cases, ids=lambda x: x.name)
def test_arg_parsing_final_args(test_case: ArgParsingTestCase) -> None:
    def _test():
        parsed_args = parse_args(test_case.cli_command.split())
        final_args = parse_toml_and_args_into_final_args(None, parsed_args)
        for key, value in test_case.final_args_should_include.items():
            assert final_args[key] == value, f"final_args[{key}] should be {value}"
    with patch.dict(valid_llm_datasets, {'my_domain': 'my_domain_dataset'}, clear=True):
        if test_case.should_exit_error:
            with pytest.raises(SystemExit):
                _test()
        else:
            _test()