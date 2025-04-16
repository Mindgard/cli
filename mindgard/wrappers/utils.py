from typing import Any, Dict, Literal, Union

from mindgard.headers import parse_headers
from mindgard.wrappers.llm import LLMModelWrapper, get_llm_model_wrapper


# TODO: make an alias for model_type
def parse_args_into_model(args: Dict[str, Any]) -> LLMModelWrapper:
    return get_llm_model_wrapper(
        preset=args["preset"],
        headers=parse_headers(headers_comma_separated=args["headers"], headers_list=args["header"]),
        api_key=args["api_key"],
        url=args["url"],
        selector=args["selector"],
        request_template=args["request_template"],
        system_prompt=args["system_prompt"],
        model_name=args["model_name"],
        az_api_version=args["az_api_version"],
        tokenizer=args["tokenizer"],
        rate_limit=args["rate_limit"],
        force_multi_turn=args.get("force_multi_turn") or False,
    )
