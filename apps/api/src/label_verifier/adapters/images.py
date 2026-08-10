from __future__ import annotations

import io
import warnings
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from label_verifier.config.settings import Settings
from label_verifier.domain.models import TransientImage


SIGNATURES = {
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
}


async def validate_images(files: list[UploadFile], settings: Settings) -> tuple[TransientImage, ...]:
    if not files:
        raise HTTPException(status_code=422, detail="at least one image is required")
    accepted: list[TransientImage] = []
    aggregate_bytes = 0
    aggregate_pixels = 0
    try:
        for index, upload in enumerate(files):
            media_type = (upload.content_type or "").lower()
            if media_type not in SIGNATURES:
                raise HTTPException(status_code=415, detail=f"image {index + 1} must be JPEG or PNG")
            content = await upload.read(settings.max_image_bytes + 1)
            if len(content) > settings.max_image_bytes:
                raise HTTPException(status_code=413, detail=f"image {index + 1} exceeds the encoded-size limit")
            if not any(content.startswith(signature) for signature in SIGNATURES[media_type]):
                raise HTTPException(status_code=415, detail=f"image {index + 1} signature does not match its media type")
            aggregate_bytes += len(content)
            if aggregate_bytes > settings.max_aggregate_bytes:
                raise HTTPException(status_code=413, detail="images exceed the aggregate encoded-size limit")
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", Image.DecompressionBombWarning)
                    with Image.open(io.BytesIO(content)) as decoded:
                        decoded.verify()
                    with Image.open(io.BytesIO(content)) as decoded:
                        width, height = decoded.size
            except (UnidentifiedImageError, OSError, Image.DecompressionBombWarning, Image.DecompressionBombError):
                raise HTTPException(status_code=415, detail=f"image {index + 1} could not be safely decoded") from None
            aggregate_pixels += width * height
            if aggregate_pixels > settings.max_decoded_pixels:
                raise HTTPException(status_code=413, detail="images exceed the aggregate decoded-pixel limit")
            accepted.append(TransientImage(f"img_{index + 1}", content, media_type, width, height))
        return tuple(accepted)
    finally:
        for upload in files:
            await upload.close()
