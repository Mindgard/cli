from typing import Any, Dict, Literal

from mindgard.headers import parse_headers
from mindgard.wrappers.image import ImageModelWrapper, get_image_model_wrapper
from mindgard.wrappers.llm import LLMModelWrapper, get_llm_model_wrapper


# TODO: make an alias for model_type
def parse_args_into_model(
    model_type: Literal["image", "llm"], args: Dict[str, Any]
) -> LLMModelWrapper | ImageModelWrapper:
    if model_type == "llm":
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
        )
    elif model_type == "image":
        return get_image_model_wrapper(
            preset=args["preset"], api_key=args["api_key"], url=args["url"], labels=args["labels"]
        )
