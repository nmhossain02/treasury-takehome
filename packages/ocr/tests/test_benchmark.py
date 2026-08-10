import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from label_ocr.benchmark import build_fixture_provider, render_markdown, run_benchmark


class BenchmarkTests(unittest.TestCase):
    def test_fixture_benchmark_reports_metrics_and_environment(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            (base / "image.png").write_bytes(b"fixture-image-content")
            manifest_path = base / "manifest.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "dataset_name": "fixture-benchmark",
                        "items": [
                            {
                                "item_id": "one",
                                "image_path": "image.png",
                                "media_type": "image/png",
                                "expected_text": "Harbor Reserve 45% ALC/VOL",
                                "fields": {
                                    "brand": "Harbor Reserve",
                                    "abv": "45% ALC/VOL",
                                },
                                "annotations": [
                                    {
                                        "text": "Harbor Reserve",
                                        "bbox": [0, 0, 0.5, 0.2],
                                    },
                                    {"text": "45% ALC/VOL", "bbox": [0, 0.3, 0.5, 0.2]},
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            provider = build_fixture_provider(manifest_path)
            report = asyncio.run(
                run_benchmark(manifest_path, provider, deadline_seconds=1)
            )
            self.assertEqual(report["summary"]["mean_cer"], 0)
            self.assertEqual(report["summary"]["mean_wer"], 0)
            self.assertEqual(report["summary"]["critical_field_recall"], 1)
            self.assertIn("platform", report["environment"])
            self.assertIn("Mean CER", render_markdown(report))


if __name__ == "__main__":
    unittest.main()
