import json
import tempfile
import unittest
from pathlib import Path

from label_ocr.dataset import DatasetManifest


class DatasetTests(unittest.TestCase):
    def test_loads_schema(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "dataset_name": "tiny",
                        "items": [
                            {
                                "item_id": "one",
                                "image_path": "one.png",
                                "media_type": "image/png",
                                "expected_text": "Brand",
                                "fields": {"brand": "Brand"},
                                "annotations": [
                                    {
                                        "text": "Brand",
                                        "bbox": [0, 0, 1, 1],
                                        "field_name": "brand",
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            manifest = DatasetManifest.load(path)
            self.assertEqual(manifest.dataset_name, "tiny")
            self.assertEqual(manifest.items[0].annotations[0].field_name, "brand")

    def test_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            item = {
                "item_id": "same",
                "image_path": "one.png",
                "media_type": "image/png",
                "expected_text": "Brand",
            }
            path.write_text(json.dumps({"schema_version": 1, "items": [item, item]}))
            with self.assertRaises(ValueError):
                DatasetManifest.load(path)


if __name__ == "__main__":
    unittest.main()
