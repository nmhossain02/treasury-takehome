from __future__ import annotations

import io
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CoordinateMap:
    """Maps processed pixels back to the EXIF-oriented source image."""

    oriented_width: int
    oriented_height: int
    processed_width: int
    processed_height: int

    def to_source_normalized(
        self, box: tuple[int, int, int, int]
    ) -> tuple[float, float, float, float]:
        left, top, width, height = box
        # Resize is aspect preserving and introduces no crop, so normalizing in
        # processed space preserves the oriented source coordinates exactly.
        return (
            _clip(left / self.processed_width),
            _clip(top / self.processed_height),
            _clip(width / self.processed_width),
            _clip(height / self.processed_height),
        )


@dataclass(frozen=True, slots=True)
class PreprocessedImage:
    content: bytes
    media_type: str
    coordinate_map: CoordinateMap


def preprocess_image(
    content: bytes, *, max_dimension: int = 2400, max_pixels: int = 20_000_000
) -> PreprocessedImage:
    if max_dimension < 1:
        raise ValueError("max_dimension must be positive")
    if max_pixels < 1:
        raise ValueError("max_pixels must be positive")
    try:
        from PIL import Image, ImageOps
    except ImportError as exc:  # pragma: no cover - dependency error is explicit
        raise RuntimeError("Pillow is required for image preprocessing") from exc

    try:
        with Image.open(io.BytesIO(content)) as source:
            if source.width * source.height > max_pixels:
                raise ValueError("image exceeds decoded pixel limit")
            oriented = ImageOps.exif_transpose(source)
            oriented.load()
            oriented_width, oriented_height = oriented.size
            if max(oriented.size) > max_dimension:
                scale = max_dimension / max(oriented.size)
                resized = oriented.resize(
                    (
                        max(1, round(oriented_width * scale)),
                        max(1, round(oriented_height * scale)),
                    ),
                    Image.Resampling.LANCZOS,
                )
            else:
                resized = oriented.copy()
            grayscale = ImageOps.grayscale(resized)
            normalized = ImageOps.autocontrast(grayscale)
            processed_width, processed_height = normalized.size
            output = io.BytesIO()
            normalized.save(output, format="PNG", optimize=False)
    except Exception as exc:
        raise ValueError("image could not be decoded") from exc

    return PreprocessedImage(
        content=output.getvalue(),
        media_type="image/png",
        coordinate_map=CoordinateMap(
            oriented_width=oriented_width,
            oriented_height=oriented_height,
            processed_width=processed_width,
            processed_height=processed_height,
        ),
    )


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))
