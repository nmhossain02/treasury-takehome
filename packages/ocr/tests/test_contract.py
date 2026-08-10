import unittest

from label_ocr import OcrImage, OcrOutcome, OcrRequest, OcrStatus, TextSpan


class ContractTests(unittest.TestCase):
    def test_valid_contract(self):
        image = OcrImage("front", b"bytes", "image/png")
        request = OcrRequest((image,), 42.0, ("eng",))
        span = TextSpan("Brand", 0.9, "front", (0.1, 0.2, 0.3, 0.4), 1, 2, 3)
        outcome = OcrOutcome(
            OcrStatus.SUCCESS, (span,), provider="fixture", timings={"total_ms": 1}
        )
        self.assertEqual(request.images[0], image)
        self.assertEqual(outcome.status.value, "success")

    def test_rejects_empty_image(self):
        with self.assertRaises(ValueError):
            OcrImage("front", b"", "image/png")

    def test_rejects_invalid_bbox_or_confidence(self):
        with self.assertRaises(ValueError):
            TextSpan("Brand", 1.1, "front", (0, 0, 1, 1), 0, 0, 0)
        with self.assertRaises(ValueError):
            TextSpan("Brand", 1, "front", (0.8, 0, 0.3, 1), 0, 0, 0)

    def test_success_cannot_contain_error(self):
        with self.assertRaises(ValueError):
            OcrOutcome(OcrStatus.SUCCESS, error_codes=("bad",))


if __name__ == "__main__":
    unittest.main()
