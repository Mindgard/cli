from typing import Dict, List

from .image import LabelConfidence


def image_label_tensor_align(config: Dict[int, str], model_data: List[Dict[str, float]]) -> List[LabelConfidence]:
    if len(config) < len(model_data):
        raise ValueError("config contained less classes than the model returned!")

    aligned: List[LabelConfidence] = []

    # make a list in the true order
    for true_index, true_label in config.items():
        aligned.append(LabelConfidence(label=true_label, score=0.0))

    # where we have predictions,
    for index, label_and_score in enumerate(model_data):
        for item in aligned:
            if item.label == label_and_score.get("label"):
                item.score = label_and_score.get("score")

    return aligned
