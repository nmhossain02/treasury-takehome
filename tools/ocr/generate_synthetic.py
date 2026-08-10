#!/usr/bin/env python3
"""Generate a small deterministic, non-production OCR benchmark corpus."""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Sequence
from pathlib import Path

LABELS = (
    ("Harbor Reserve", "STRAIGHT BOURBON WHISKEY", "45% ALC/VOL", "750 mL"),
    ("Juniper House", "DISTILLED GIN", "40% ALC/VOL", "1 L"),
    ("North Fork", "VODKA", "40% ALC/VOL", "750 mL"),
)


def generate(destination: Path, *, variants: int, seed: int) -> Path:
    try:
        from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
    except ImportError as exc:
        raise SystemExit("Pillow is required: install packages/ocr first") from exc
    if variants < 1:
        raise ValueError("variants must be positive")
    random_source = random.Random(seed)
    image_dir = destination / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for label_index, (brand, category, abv, volume) in enumerate(LABELS):
        lines = (brand.upper(), category, abv, volume)
        for variant in range(variants):
            canvas = Image.new("RGB", (1000, 650), (244, 235, 210))
            draw = ImageDraw.Draw(canvas)
            font = ImageFont.load_default(size=36)
            annotations = []
            for line_index, line in enumerate(lines):
                left = 90 + random_source.randint(-8, 8)
                top = 100 + line_index * 105 + random_source.randint(-5, 5)
                draw.text((left, top), line, fill=(25, 20, 15), font=font)
                box = draw.textbbox((left, top), line, font=font)
                annotations.append(
                    {
                        "text": line,
                        "bbox": [
                            box[0] / canvas.width,
                            box[1] / canvas.height,
                            (box[2] - box[0]) / canvas.width,
                            (box[3] - box[1]) / canvas.height,
                        ],
                        "field_name": ("brand", "class_type", "abv", "net_contents")[
                            line_index
                        ],
                    }
                )
            angle = random_source.uniform(-2.5, 2.5)
            canvas = canvas.rotate(
                angle,
                resample=Image.Resampling.BICUBIC,
                expand=False,
                fillcolor="white",
            )
            if variant % 2:
                canvas = canvas.filter(ImageFilter.GaussianBlur(radius=0.35))
                canvas = ImageEnhance.Contrast(canvas).enhance(0.9)
            item_id = f"label-{label_index + 1:02d}-{variant + 1:02d}"
            filename = f"{item_id}.jpg"
            canvas.save(image_dir / filename, "JPEG", quality=88)
            items.append(
                {
                    "item_id": item_id,
                    "image_path": f"images/{filename}",
                    "media_type": "image/jpeg",
                    "expected_text": " ".join(lines),
                    "fields": {
                        "brand": brand,
                        "class_type": category,
                        "abv": abv,
                        "net_contents": volume,
                    },
                    # Rotation makes these approximate; they remain useful for
                    # fixture development but not localization scoring.
                    "annotations": annotations,
                }
            )
    manifest = {
        "schema_version": 1,
        "dataset_name": "synthetic-distilled-spirits",
        "seed": seed,
        "generator": "tools/ocr/generate_synthetic.py",
        "items": items,
    }
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variants", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260806)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    print(generate(args.output, variants=args.variants, seed=args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
