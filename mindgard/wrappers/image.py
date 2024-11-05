# Typing
from pydantic import BaseModel
from typing import List, Optional, Literal, Any
import logging
# Requests
import requests
import base64
# Utils
from mindgard.test import RequestHandler
from mindgard.utils import check_expected_args


class LabelConfidence(BaseModel):
    label: Optional[str]
    score: Optional[float]


class ImageModelWrapper:
    def __init__(self, url: str, labels: List[str], allow_redirects:bool = True, api_key: Optional[str] = None) -> None:
        self.url = url
        self.api_key = api_key
        self.labels = labels
        self._allow_redirects = allow_redirects

        # TODO: shape validation
        # self.shape = [3, 1, 224, 224]????


    def to_handler(self) -> RequestHandler:
        def handler(payload: Any) -> Any:
            logging.debug(f"received request {payload}")
            image_bytes = base64.b64decode(payload["image"])
            response = self(image=image_bytes)
            return {
                "response": [t.model_dump() for t in response]
            }
        return handler

    def __call__(self, image: bytes) -> List[LabelConfidence]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "image/jpeg",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        res = requests.post(
            self.url, 
            headers=headers,
            data=image,
            allow_redirects=self._allow_redirects,
        )

        model_response = [LabelConfidence(label=item.get("label"), score=item.get("score")) for item in res.json()]

        aligned_data = image_label_tensor_align(self.labels, model_response)

        return aligned_data
    
def image_label_tensor_align(labels: List[str], model_data: List[LabelConfidence]) -> List[LabelConfidence]:
    if len(labels) < len(model_data):
        raise ValueError("Model returned more classes than the specified labels!")

    aligned: List[LabelConfidence] = []
    # make a list in the true order
    for true_label in labels:
        aligned.append(LabelConfidence(label=true_label, score=0.0))
    
    for label_confidence in model_data:
        if label_confidence.label not in labels:
            raise ValueError(f"Model returned an unknown class! ({label_confidence.label}) Doesn't match provided labels!")
    
    # where we have predictions, replace the score with the actual score
    for _, label_confidence in enumerate(model_data):
        for item in aligned:
            if item.label == label_confidence.label:
                item.score = label_confidence.score
                break
    return aligned



def get_image_model_wrapper(
    preset: Optional[Literal["huggingface", "local"]],
    api_key: Optional[str],
    url: str,
    labels: List[str],
    allow_redirects: bool = True, # backward compatibility
) -> ImageModelWrapper:

    # Isn't a concept of presets for image model wrapper as we just bind to HF
    if preset == "huggingface" or preset == None:
        check_expected_args(locals(), ["api_key", "url"])
        return ImageModelWrapper(api_key=api_key, url=url, labels=labels, allow_redirects=allow_redirects)  
    elif preset == "local":
        check_expected_args(locals(), ["url"])
        return ImageModelWrapper(url=url, labels=labels, allow_redirects=allow_redirects)
