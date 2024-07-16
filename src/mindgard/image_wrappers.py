from pydantic import BaseModel
from typing import List, Optional

import requests

class LabelConfidence(BaseModel):
    label: Optional[str]
    score: Optional[float]

class ImageModelWrapper():
    def __init__(self, api_key: str, url: str) -> None:
        self.url = url
        self.api_key = api_key

        # TODO: shape validation
        # self.shape = [3, 1, 224, 224]????
    
    def infer(self, image: bytes) -> List[LabelConfidence]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "image/jpeg"
        }
        
        res = requests.post(self.url, headers=headers, data=image)

        return [ LabelConfidence(label=item.get('label'), score=item.get('score')) for item in res.json() ]