
import os
from typing import List, Tuple, cast
from unittest.mock import mock_open, patch
from ...src.mindgard.utils import parse_toml_and_args_into_final_args
import pytest

from argparse import Namespace
from ...src.mindgard.__main__ import parse_args


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
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, tokenizer=None, model_type=None, parallelism=None, dataset=None, model_name=None, api_key=None, url=None, preset=None, headers=None, target=None, risk_threshold=None)
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
    
        
def test_toml_and_args_parsing_model_type_empty():
    cli_command = "test --config-file=config.toml"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, tokenizer=None, model_type=None, parallelism=None, dataset=None, model_name=None, api_key=None, url=None, preset=None, headers=None, target=None, risk_threshold=None)
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
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, tokenizer=None, model_type=None, parallelism=None, dataset=None, model_name=None, api_key=None, url=None, preset=None, headers=None, target=None, risk_threshold=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    system-prompt = "You are a helpful, respectful and honest assistant."
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        
        assert final_args["api_key"] == "my-api-key"
        assert final_args["model_type"] == "image"
        assert final_args["command"] == namespace.command
        assert final_args["config_file"] == namespace.config_file
        assert final_args["risk_threshold"] == 50 # default value
        assert final_args["parallelism"] == 5 # default value

def test_toml_and_args_parsing_not_setting_risk_threshold():
    cli_command = "test --config-file=config.toml"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, tokenizer=None, model_type=None, parallelism=None, dataset=None, model_name=None, api_key=None, url=None, preset=None, headers=None, target=None, risk_threshold=None)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    system-prompt = "You are a helpful, respectful and honest assistant."
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        
        assert final_args["risk_threshold"] == 50 # default value

def test_toml_and_args_parsing_setting_risk_threshold():
    cli_command = "test --config-file=config.toml --risk-threshold=80"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, tokenizer=None, model_type=None, parallelism=None, dataset=None, model_name=None, api_key=None, url=None, preset=None, headers=None, target=None, risk_threshold=80)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    system-prompt = "You are a helpful, respectful and honest assistant."
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        
        assert final_args["risk_threshold"] == 80
        
def test_toml_and_args_parsing_setting_risk_threshold_zero():
    cli_command = "test --config-file=config.toml --risk-threshold=0"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, tokenizer=None, model_type=None, parallelism=None, dataset=None, model_name=None, api_key=None, url=None, preset=None, headers=None, target=None, risk_threshold=0)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    system-prompt = "You are a helpful, respectful and honest assistant."
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        print(f'final args: {final_args}')
        assert final_args["risk_threshold"] == 0
        
def test_toml_and_args_parsing_setting_json():
    cli_command = "test --config-file=config.toml --risk-threshold=80 --json"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=True, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, tokenizer=None, model_type=None, parallelism=None, dataset=None, model_name=None, api_key=None, url=None, preset=None, headers=None, target=None, risk_threshold=80)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    system-prompt = "You are a helpful, respectful and honest assistant."
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        
        assert final_args["json"] == True
    
def test_toml_and_args_parsing_not_setting_json():
    cli_command = "test --config-file=config.toml --risk-threshold=80"
    namespace = Namespace(command='test',config_file='config.toml', log_level='warn', json=False, az_api_version=None, prompt=None, system_prompt=None, selector=None, request_template=None, tokenizer=None, model_type=None, parallelism=None, dataset=None, model_name=None, api_key=None, url=None, preset=None, headers=None, target=None, risk_threshold=80)
    parsed_args = parse_args(cast(List[str], cli_command.split()))
    
    assert parsed_args == namespace 
    
    toml_content = """
    api_key = "my-api-key"
    target= "my_model"
    model_type = "image"
    system-prompt = "You are a helpful, respectful and honest assistant."
    """
    
    with patch('builtins.open', mock_open(read_data=toml_content)):
        final_args = parse_toml_and_args_into_final_args("config.toml", parsed_args)
        
        assert final_args["json"] == False