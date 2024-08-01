from typing import Dict, List

from .image import LabelConfidence


def image_label_tensor_align(config: Dict[int, str], model_data: List[LabelConfidence]) -> List[LabelConfidence]:
    if len(config) < len(model_data):
        raise ValueError("Model returned more classes than the config!")

    aligned: List[LabelConfidence] = []

    # make a list in the true order
    for true_index, true_label in config.items():
        aligned.append(LabelConfidence(label=true_label, score=0.0))

    # where we have predictions, replace the score with the actual score
    for index, label_confidence in enumerate(model_data):
        for item in aligned:
            if item.label == label_confidence.label:
                item.score = label_confidence.score
                break

    return aligned
