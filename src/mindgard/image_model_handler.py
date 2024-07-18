# Types
from typing import Optional, Callable, List
from pydantic import BaseModel
from .wrappers import ModelWrapper


def submit_image_test(
    access_token: str,
    target: str,
    parallelism: int,
    model_wrapper: ModelWrapper,
    visual_exception_callback: Callable[[str], None],
    modality_specific_args: Optional[BaseModel | None] = None,
) -> List[str]:
    return ["whatever"]
