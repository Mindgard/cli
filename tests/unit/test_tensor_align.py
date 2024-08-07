
import pytest

from mindgard.wrappers.image import LabelConfidence
from ...src.mindgard.wrappers.image import image_label_tensor_align

image_tensor_align_config = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9",]


def test_image_label_tensor_align_config_model_returns_n_classes():
    model_return_data = [
        {"label": "0", "score": 0.1}, {"label": "1", "score": 0.2},
        {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05},
        {"label": "4", "score": 0.1}, {"label": "5", "score": 0.05},
        {"label": "6", "score": 0.1}, {"label": "7", "score": 0.1},
        {"label": "8", "score": 0.1}, {"label": "9", "score": 0.1}
    ]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]

    aligned_data = image_label_tensor_align(image_tensor_align_config, _model_return_data)

    assert len(image_tensor_align_config) == len(aligned_data)
    for index, true_label in enumerate(image_tensor_align_config):
        assert true_label == aligned_data[index].label


def test_image_label_tensor_align_config_model_returns_less_than_n_classes():
    model_return_data = [
        {"label": "0", "score": 0.1}, {"label": "1", "score": 0.2},
        {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05},
        {"label": "4", "score": 0.1}, {"label": "5", "score": 0.05}
    ]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]

    aligned_data = image_label_tensor_align(image_tensor_align_config, _model_return_data)

    assert len(image_tensor_align_config) == len(aligned_data)
    for index, true_label in enumerate(image_tensor_align_config):
        assert true_label == aligned_data[index].label


def test_image_label_tensor_align_config_model_returns_unordered_classes():
    model_return_data = [
        {"label": "0", "score": 0.1}, {"label": "4", "score": 0.1},
        {"label": "1", "score": 0.2}, {"label": "5", "score": 0.05},
        {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05},
    ]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]

    aligned_data = image_label_tensor_align(image_tensor_align_config, _model_return_data)

    assert len(image_tensor_align_config) == len(aligned_data)
    for index, true_label in enumerate(image_tensor_align_config):
        assert true_label == aligned_data[index].label


def test_image_label_tensor_align_config_model_returns_non_contiguous_classes():
    model_return_data = [
        {"label": "0", "score": 0.1}, {"label": "4", "score": 0.1},
        {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05}, 
    ]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]

    aligned_data = image_label_tensor_align(image_tensor_align_config, _model_return_data)

    assert len(image_tensor_align_config) == len(aligned_data)
    for index, true_label in enumerate(image_tensor_align_config):
        assert true_label == aligned_data[index].label

def test_image_label_tensor_align_empty_labels() -> None:
    model_return_data = [
        {"label": "0", "score": 0.1}, {"label": "4", "score": 0.1},
        {"label": "1", "score": 0.2}, {"label": "5", "score": 0.05},
        {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05},
    ]
    _model_return_data = [LabelConfidence(**item) for item in model_return_data]
    with pytest.raises(ValueError):
        image_label_tensor_align([], _model_return_data)

def test_image_label_tensor_align_config_model_returns_more_classes_than_config():
    image_tensor_align_config_reduced = ["0", "1", "2", "3"]

    model_return_data = [
        {"label": "0", "score": 0.1}, {"label": "1", "score": 0.2},
        {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05},
        {"label": "4", "score": 0.1}, {"label": "5", "score": 0.05}
    ]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]


    with pytest.raises(ValueError):
        image_label_tensor_align(image_tensor_align_config_reduced, _model_return_data)


def test_image_label_tensor_align_model_has_no_labels_in_common_with_config() -> None:
    image_tensor_align_config_reduced = ["0", "1", "2", "3"]

    model_return_data = [
        {"label": "bazinga", "score": 0.25}, {"label": "greatscott", "score": 0.25},
        {"label": "yarr", "score": 0.25}, {"label": "spongeboymebob", "score": 0.25},
    ]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]

    with pytest.raises(ValueError):
        image_label_tensor_align(image_tensor_align_config_reduced, _model_return_data)