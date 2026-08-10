from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import platform
import statistics
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .contract import OcrImage, OcrRequest, TextSpan
from .dataset import DatasetManifest
from .fixture import FixtureEntry, FixtureOcrProvider
from .metrics import ExactNormalizedFieldRecall, character_error_rate, word_error_rate
from .tesseract import TesseractConfig, TesseractOcrProvider


async def run_benchmark(
    manifest_path: Path,
    provider: Any,
    *,
    deadline_seconds: float,
) -> dict[str, Any]:
    manifest = DatasetManifest.load(manifest_path)
    base = manifest_path.parent
    item_results: list[dict[str, Any]] = []
    field_hook = ExactNormalizedFieldRecall()

    for item in manifest.items:
        image_path = (base / item.image_path).resolve()
        image = OcrImage(item.item_id, image_path.read_bytes(), item.media_type)
        started = time.monotonic()
        outcome = await provider.recognize(
            OcrRequest((image,), started + deadline_seconds)
        )
        latency_ms = (time.monotonic() - started) * 1000.0
        ordered = sorted(
            outcome.spans,
            key=lambda span: (
                span.image_id,
                span.block_order,
                span.line_order,
                span.word_order,
            ),
        )
        actual_text = " ".join(span.text for span in ordered)
        item_results.append(
            {
                "item_id": item.item_id,
                "status": outcome.status.value,
                "expected_text": item.expected_text,
                "actual_text": actual_text,
                "cer": character_error_rate(item.expected_text, actual_text),
                "wer": word_error_rate(item.expected_text, actual_text),
                "field_results": field_hook.score(item.fields, actual_text),
                "latency_ms": latency_ms,
                "error_codes": list(outcome.error_codes),
            }
        )

    latencies = [item["latency_ms"] for item in item_results]
    field_values = [
        result for item in item_results for result in item["field_results"].values()
    ]
    return {
        "schema_version": 1,
        "dataset": manifest.dataset_name,
        "provider": {"name": provider.name, "version": provider.version},
        "configuration": _configuration(provider),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
        },
        "summary": {
            "items": len(item_results),
            "mean_cer": statistics.fmean(item["cer"] for item in item_results),
            "mean_wer": statistics.fmean(item["wer"] for item in item_results),
            "critical_field_recall": (
                sum(field_values) / len(field_values) if field_values else None
            ),
            "latency_p50_ms": _percentile(latencies, 0.50),
            "latency_p95_ms": _percentile(latencies, 0.95),
        },
        "items": item_results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    field_recall = summary["critical_field_recall"]
    field_display = "n/a" if field_recall is None else f"{field_recall:.3f}"
    return "\n".join(
        (
            f"# OCR benchmark: {report['dataset']}",
            "",
            f"Provider: `{report['provider']['name']}` ({report['provider']['version']})",
            "",
            "| Metric | Result |",
            "| --- | ---: |",
            f"| Images | {summary['items']} |",
            f"| Mean CER | {summary['mean_cer']:.4f} |",
            f"| Mean WER | {summary['mean_wer']:.4f} |",
            f"| Critical-field recall | {field_display} |",
            f"| Latency p50 | {summary['latency_p50_ms']:.1f} ms |",
            f"| Latency p95 | {summary['latency_p95_ms']:.1f} ms |",
            "",
            "## Environment",
            "",
            "```json",
            json.dumps(report["environment"], indent=2, sort_keys=True),
            "```",
            "",
        )
    )


def build_fixture_provider(manifest_path: Path) -> FixtureOcrProvider:
    manifest = DatasetManifest.load(manifest_path)
    fixtures: dict[str, FixtureEntry] = {}
    for item in manifest.items:
        content = (manifest_path.parent / item.image_path).read_bytes()
        spans = tuple(
            TextSpan(
                text=annotation.text,
                confidence=1.0,
                image_id=item.item_id,
                bbox=annotation.bbox,
                block_order=0,
                line_order=index,
                word_order=0,
            )
            for index, annotation in enumerate(item.annotations)
        )
        if not spans:
            spans = (
                TextSpan(
                    item.expected_text, 1.0, item.item_id, (0.0, 0.0, 1.0, 1.0), 0, 0, 0
                ),
            )
        fixtures[hashlib.sha256(content).hexdigest()] = FixtureEntry(spans=spans)
    return FixtureOcrProvider(fixtures)


def _configuration(provider: Any) -> dict[str, Any]:
    config = getattr(provider, "config", None)
    return asdict(config) if config is not None else {}


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) * fraction) + 0.999999) - 1))
    return ordered[index]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark a label_ocr provider")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument(
        "--provider", choices=("fixture", "tesseract"), default="tesseract"
    )
    parser.add_argument("--deadline-seconds", type=float, default=2.9)
    parser.add_argument("--tesseract-executable", default="tesseract")
    parser.add_argument("--psm", type=int, default=11)
    parser.add_argument("--json-out", type=Path, required=True)
    parser.add_argument("--markdown-out", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.deadline_seconds <= 0:
        raise SystemExit("--deadline-seconds must be positive")
    if args.provider == "fixture":
        provider = build_fixture_provider(args.manifest)
    else:
        provider = TesseractOcrProvider(
            TesseractConfig(
                executable=args.tesseract_executable,
                page_segmentation_mode=args.psm,
            )
        )
    report = asyncio.run(
        run_benchmark(args.manifest, provider, deadline_seconds=args.deadline_seconds)
    )
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    args.markdown_out.write_text(render_markdown(report), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
