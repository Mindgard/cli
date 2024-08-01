# Typing
from pydantic import BaseModel
from typing import List, Optional, Literal

# Requests
import requests

# Utils
from ..utils import check_expected_args, print_to_stderr


class LabelConfidence(BaseModel):
    label: Optional[str]
    score: Optional[float]


class ImageModelWrapper:
    def __init__(self, url: str, api_key: Optional[str] = None) -> None:
        self.url = url
        self.api_key = api_key

        # TODO: shape validation
        # self.shape = [3, 1, 224, 224]????

    def __call__(self, image: bytes) -> List[LabelConfidence]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "image/jpeg",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        res = requests.post(self.url, headers=headers, data=image)

        return [
            LabelConfidence(label=item.get("label"), score=item.get("score"))
            for item in res.json()
        ]


def get_image_model_wrapper(
    preset: Literal["huggingface", "local"],
    api_key: Optional[str],
    url: str,
) -> ImageModelWrapper:

    # Isn't a concept of presets for image model wrapper as we just bind to HF
    if preset == "huggingface" or preset == None:
        check_expected_args(locals(), ["api_key", "url"])
        return ImageModelWrapper(api_key=api_key, url=url)
    elif preset == "local":
        check_expected_args(locals(), ["url"])
        return ImageModelWrapper(url=url)
