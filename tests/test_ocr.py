import cv2
import numpy as np
import pytest

from src import ocr_module
from src.ocr_module import extract_text, preprocess_image, verify_destination


def _sample_sign() -> np.ndarray:
    image = np.full((120, 320, 3), 245, dtype=np.uint8)
    cv2.putText(image, "LAB 101", (20, 75), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (15, 15, 15), 3)
    return image


def test_preprocess_image_returns_adaptively_thresholded_grayscale() -> None:
    processed = preprocess_image(_sample_sign())

    assert processed.ndim == 2
    assert processed.dtype == np.uint8
    assert set(np.unique(processed)).issubset({0, 255})
    assert len(np.unique(processed)) == 2


def test_preprocess_image_accepts_encoded_upload_bytes() -> None:
    success, encoded = cv2.imencode(".png", _sample_sign())
    assert success

    processed = preprocess_image(encoded.tobytes())

    assert processed.shape == (120, 320)


def test_preprocess_image_accepts_grayscale_camera_frame() -> None:
    processed = preprocess_image(np.full((40, 80), 180, dtype=np.uint8))

    assert processed.shape == (40, 80)


def test_preprocess_image_rejects_bad_image_and_block_size() -> None:
    with pytest.raises(ValueError, match="Unable to read image"):
        preprocess_image(b"not an image")
    with pytest.raises(ValueError, match="odd integer"):
        preprocess_image(_sample_sign(), adaptive_block_size=10)


def test_extract_text_uses_preprocessed_image(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_image_to_string(image, *, lang, config):
        captured["image"] = image
        captured["lang"] = lang
        captured["config"] = config
        return "  LAB 101\n"

    monkeypatch.setattr(ocr_module.pytesseract, "image_to_string", fake_image_to_string)

    text = extract_text(_sample_sign())

    assert text == "LAB 101"
    assert isinstance(captured["image"], np.ndarray)
    assert captured["image"].ndim == 2
    assert captured["lang"] == "eng"
    assert captured["config"] == "--psm 6"


def test_verify_destination_matches_name_id_and_aliases() -> None:
    name_match = verify_destination("Physics Lab 101", "LAB101", "Lab 101", ["Physics Lab"])
    alias_match = verify_destination("Physics Lab", "LAB101", "Lab 101", ["Physics Lab"])
    id_match = verify_destination("LAB101", "LAB101", "Lab 101")

    assert name_match.matched
    assert name_match.matched_label == "Lab 101"
    assert alias_match.matched
    assert alias_match.matched_label == "Physics Lab"
    assert id_match.matched
    assert id_match.matched_label == "LAB101"


def test_verify_destination_rejects_wrong_room_and_empty_ocr() -> None:
    wrong_room = verify_destination("LAB 102", "LAB101", "Lab 101", score_threshold=90)
    no_text = verify_destination("   ", "LAB101", "Lab 101")

    assert not wrong_room.matched
    assert wrong_room.score < 90
    assert not no_text.matched
    assert no_text.score == 0
    assert no_text.matched_label is None


def test_verify_destination_validates_inputs() -> None:
    with pytest.raises(ValueError, match="destination_id cannot be empty"):
        verify_destination("LAB 101", " ")
    with pytest.raises(ValueError, match="score_threshold must be between 0 and 100"):
        verify_destination("LAB 101", "LAB101", score_threshold=101)