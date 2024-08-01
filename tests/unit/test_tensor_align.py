import pytest

from mindgard.wrappers.image import LabelConfidence
from ...src.mindgard.wrappers.image_label_tensor_config import image_label_tensor_align

image_tensor_align_config = {0: "0", 1: "1", 2: "2", 3: "3", 4: "4", 5: "5", 6: "6", 7: "7", 8: "8", 9: "9", }


def test_load_tensor_align_config():
    pass


def test_image_label_tensor_align_config_model_returns_n_classes():
    model_return_data = [{"label": "0", "score": 0.1}, {"label": "1", "score": 0.2},
                         {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05},
                         {"label": "4", "score": 0.1}, {"label": "5", "score": 0.05},
                         {"label": "6", "score": 0.1}, {"label": "7", "score": 0.1},
                         {"label": "8", "score": 0.1}, {"label": "9", "score": 0.1}

                         ]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]

    aligned_data = image_label_tensor_align(image_tensor_align_config, _model_return_data)

    assert len(image_tensor_align_config.keys()) == len(aligned_data)
    for index, true_label in image_tensor_align_config.items():
        assert true_label == aligned_data[index].label


def test_image_label_tensor_align_config_model_returns_less_than_n_classes():
    model_return_data = [{"label": "0", "score": 0.1}, {"label": "1", "score": 0.2},
                         {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05},
                         {"label": "4", "score": 0.1}, {"label": "5", "score": 0.05}]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]

    aligned_data = image_label_tensor_align(image_tensor_align_config, _model_return_data)

    assert len(image_tensor_align_config.keys()) == len(aligned_data)
    for index, true_label in image_tensor_align_config.items():
        assert true_label == aligned_data[index].label


def test_image_label_tensor_align_config_model_returns_unordered_classes():
    model_return_data = [{"label": "0", "score": 0.1}, {"label": "4", "score": 0.1},
                         {"label": "1", "score": 0.2}, {"label": "5", "score": 0.05},
                         {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05}, ]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]

    aligned_data = image_label_tensor_align(image_tensor_align_config, _model_return_data)

    assert len(image_tensor_align_config.keys()) == len(aligned_data)
    for index, true_label in image_tensor_align_config.items():
        assert true_label == aligned_data[index].label


def test_image_label_tensor_align_config_model_returns_non_contiguous_classes():
    model_return_data = [{"label": "0", "score": 0.1}, {"label": "4", "score": 0.1},
                         {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05}, ]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]

    aligned_data = image_label_tensor_align(image_tensor_align_config, _model_return_data)

    assert len(image_tensor_align_config.keys()) == len(aligned_data)
    for index, true_label in image_tensor_align_config.items():
        assert true_label == aligned_data[index].label


def test_image_label_tensor_align_config_model_returns_more_classes_than_config():
    image_tensor_align_config_reduced = {0: "0", 1: "1", 2: "2", 3: "3"}

    model_return_data = [{"label": "0", "score": 0.1}, {"label": "1", "score": 0.2},
                         {"label": "2", "score": 0.1}, {"label": "3", "score": 0.05},
                         {"label": "4", "score": 0.1}, {"label": "5", "score": 0.05}]

    _model_return_data = [LabelConfidence(**item) for item in model_return_data]

    with pytest.raises(ValueError):
        _ = image_label_tensor_align(image_tensor_align_config_reduced, _model_return_data)
