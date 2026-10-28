"""Preprocess room-sign images, extract text, and verify a destination match."""

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import re

import cv2
import numpy as np
from rapidfuzz import fuzz
import pytesseract

ImageSource = str | Path | bytes | bytearray | memoryview | np.ndarray


@dataclass(frozen=True)
class DestinationVerification:
    destination_id: str
    matched: bool
    score: float
    matched_label: str | None


def _decode_image(source: ImageSource) -> np.ndarray:
    if isinstance(source, (str, Path)):
        image = cv2.imread(str(source), cv2.IMREAD_UNCHANGED)
    elif isinstance(source, (bytes, bytearray, memoryview)):
        encoded_image = np.frombuffer(source, dtype=np.uint8)
        image = cv2.imdecode(encoded_image, cv2.IMREAD_UNCHANGED)
    elif isinstance(source, np.ndarray):
        image = source
    else:
        raise TypeError("image source must be a path, encoded bytes, or NumPy array")

    if image is None or image.size == 0:
        raise ValueError("Unable to read image or image data is empty")
    if image.dtype != np.uint8:
        raise ValueError("Image data must use 8-bit unsigned pixels")

    if image.ndim == 2:
        return image
    if image.ndim != 3:
        raise ValueError("Image must be grayscale, BGR, or BGRA")
    if image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
    raise ValueError("Color images must have 3 (BGR) or 4 (BGRA) channels")


def preprocess_image(
    source: ImageSource,
    adaptive_block_size: int = 31,
    adaptive_c: float = 11,
) -> np.ndarray:
    """Decode an image, enhance local contrast, and apply adaptive thresholding."""
    if adaptive_block_size <= 1 or adaptive_block_size % 2 == 0:
        raise ValueError("adaptive_block_size must be an odd integer greater than 1")

    grayscale = _decode_image(source)
    contrast_enhanced = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8),
    ).apply(grayscale)
    return cv2.adaptiveThreshold(
        contrast_enhanced,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=adaptive_block_size,
        C=adaptive_c,
    )


def extract_text(
    source: ImageSource,
    language: str = "eng",
    config: str = "--psm 6",
) -> str:
    """Extract room-sign text from a path, uploaded image bytes, or camera frame.

    The Tesseract executable must be installed separately from the Python package.
    """
    processed_image = preprocess_image(source)
    return pytesseract.image_to_string(
        processed_image,
        lang=language,
        config=config,
    ).strip()


def _normalize_text(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


def verify_destination(
    extracted_text: str,
    destination_id: str,
    destination_name: str | None = None,
    aliases: Iterable[str] = (),
    score_threshold: float = 85.0,
) -> DestinationVerification:
    """Compare OCR text with the active destination ID, name, and optional aliases."""
    if not 0 <= score_threshold <= 100:
        raise ValueError("score_threshold must be between 0 and 100")
    if not destination_id.strip():
        raise ValueError("destination_id cannot be empty")

    labels = [destination_id, destination_name or "", *aliases]
    candidates = [(label.strip(), _normalize_text(label)) for label in labels if label.strip()]
    normalized_text = _normalize_text(extracted_text)
    if not normalized_text:
        return DestinationVerification(destination_id, False, 0.0, None)

    matched_label, score = max(
        (
            (label, max(
                fuzz.WRatio(normalized_text, normalized_label),
                fuzz.token_set_ratio(normalized_text, normalized_label),
            ))
            for label, normalized_label in candidates
        ),
        key=lambda match: match[1],
    )
    return DestinationVerification(
        destination_id=destination_id,
        matched=score >= score_threshold,
        score=score,
        matched_label=matched_label,
    )