from __future__ import annotations

import asyncio
import csv
import io
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from .contract import OcrOutcome, OcrRequest, OcrStatus, TextSpan
from .preprocess import CoordinateMap, preprocess_image


@dataclass(frozen=True, slots=True)
class TesseractConfig:
    executable: str = "tesseract"
    page_segmentation_mode: int = 11
    engine_mode: int = 1
    max_dimension: int = 2400
    max_pixels: int = 20_000_000
    per_image_timeout_seconds: float = 2.5
    default_languages: tuple[str, ...] = ("eng",)

    def __post_init__(self) -> None:
        if not 0 <= self.page_segmentation_mode <= 13:
            raise ValueError("page_segmentation_mode must be between 0 and 13")
        if self.engine_mode not in (0, 1, 2, 3):
            raise ValueError("engine_mode must be between 0 and 3")
        if (
            self.max_dimension < 1
            or self.max_pixels < 1
            or self.per_image_timeout_seconds <= 0
        ):
            raise ValueError("image and timeout limits must be positive")
        if not self.default_languages or not all(self.default_languages):
            raise ValueError("default_languages must not be empty")


class TesseractOcrProvider:
    def __init__(self, config: TesseractConfig | None = None) -> None:
        self.config = config or TesseractConfig()
        # Resolve once. Runtime requests cannot alter the executable or CLI
        # configuration and subprocess execution never invokes a shell.
        resolved = shutil.which(self.config.executable)
        self._executable = resolved or self.config.executable
        self._version = _read_version(self._executable)

    @property
    def name(self) -> str:
        return "tesseract-local"

    @property
    def version(self) -> str:
        return self._version

    async def recognize(self, request: OcrRequest) -> OcrOutcome:
        started = time.monotonic()
        spans: list[TextSpan] = []
        warnings: list[str] = []
        errors: list[str] = []
        timings: dict[str, float] = {}
        completed = 0

        for image in request.images:
            remaining = request.deadline_monotonic - time.monotonic()
            if remaining <= 0:
                errors.append("deadline_exceeded")
                break
            image_started = time.monotonic()
            try:
                processed = preprocess_image(
                    image.content,
                    max_dimension=self.config.max_dimension,
                    max_pixels=self.config.max_pixels,
                )
            except ValueError:
                errors.append("invalid_image")
                continue
            timeout = min(remaining, self.config.per_image_timeout_seconds)
            languages = request.language_hints or self.config.default_languages
            try:
                tsv = await self._invoke(processed.content, languages, timeout)
            except FileNotFoundError:
                errors.append("provider_unavailable")
                break
            except asyncio.TimeoutError:
                errors.append(
                    "deadline_exceeded" if timeout == remaining else "image_timeout"
                )
                continue
            except TesseractProcessError as exc:
                errors.append("provider_error")
                if exc.message:
                    warnings.append(exc.message)
                continue
            try:
                parsed = parse_tesseract_tsv(
                    tsv, image.image_id, processed.coordinate_map
                )
            except TesseractProcessError as exc:
                errors.append("provider_error")
                warnings.append(exc.message)
                continue
            spans.extend(parsed)
            completed += 1
            timings[f"image.{image.image_id}.ms"] = (
                time.monotonic() - image_started
            ) * 1000.0

        if not errors:
            status = OcrStatus.SUCCESS
        elif completed or spans:
            status = OcrStatus.PARTIAL
        else:
            status = OcrStatus.FAILED
        timings["total_ms"] = (time.monotonic() - started) * 1000.0
        return OcrOutcome(
            status=status,
            spans=tuple(spans),
            warnings=tuple(dict.fromkeys(warnings)),
            error_codes=tuple(dict.fromkeys(errors)),
            provider=self.name,
            version=self.version,
            timings=timings,
        )

    async def _invoke(
        self, image_content: bytes, languages: tuple[str, ...], timeout: float
    ) -> str:
        with tempfile.TemporaryDirectory(prefix="label-ocr-") as temporary:
            image_path = Path(temporary) / "input.png"
            # This is a private mode-0700 directory with a fixed filename.
            image_path.write_bytes(image_content)
            args = (
                self._executable,
                os.fspath(image_path),
                "stdout",
                "-l",
                "+".join(languages),
                "--oem",
                str(self.config.engine_mode),
                "--psm",
                str(self.config.page_segmentation_mode),
                "tsv",
            )
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                raise
            except asyncio.CancelledError:
                process.kill()
                await process.communicate()
                raise
            if process.returncode != 0:
                message = stderr.decode("utf-8", errors="replace").strip()[:500]
                raise TesseractProcessError(message)
            return stdout.decode("utf-8", errors="replace")


class TesseractProcessError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def parse_tesseract_tsv(
    content: str, image_id: str, coordinate_map: CoordinateMap
) -> tuple[TextSpan, ...]:
    spans: list[TextSpan] = []
    reader = csv.DictReader(io.StringIO(content), delimiter="\t")
    required = {
        "block_num",
        "line_num",
        "word_num",
        "left",
        "top",
        "width",
        "height",
        "conf",
        "text",
    }
    if reader.fieldnames is None or not required.issubset(reader.fieldnames):
        raise TesseractProcessError("Tesseract returned invalid TSV")
    for row in reader:
        try:
            confidence_raw = float(row["conf"])
            text = row["text"].strip()
            if confidence_raw < 0 or not text:
                continue
            pixel_box = (
                int(row["left"]),
                int(row["top"]),
                int(row["width"]),
                int(row["height"]),
            )
            bbox = _fit_box(coordinate_map.to_source_normalized(pixel_box))
            spans.append(
                TextSpan(
                    text=text,
                    confidence=max(0.0, min(1.0, confidence_raw / 100.0)),
                    image_id=image_id,
                    bbox=bbox,
                    block_order=max(0, int(row["block_num"])),
                    line_order=max(0, int(row["line_num"])),
                    word_order=max(0, int(row["word_num"])),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return tuple(spans)


def _fit_box(
    box: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    x, y, width, height = box
    return x, y, min(width, 1.0 - x), min(height, 1.0 - y)


def _read_version(executable: str) -> str:
    import subprocess

    try:
        completed = subprocess.run(
            [executable, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=1,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return "unavailable"
    first_line = (completed.stdout or completed.stderr).splitlines()
    return first_line[0].strip()[:100] if first_line else "unknown"
